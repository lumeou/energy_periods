import copy
import logging

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .providers import get_provider
from .coordinator import EnergyPeriodsCoordinator
from .history import async_backfill_energy_consumption_price_history, async_backfill_power_term_daily_price_history, async_backfill_standing_charge_history
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_REBUILD_SENSOR_HISTORY = "rebuild_sensor_history"

REBUILD_SENSOR_HISTORY_SCHEMA = vol.Schema({
    vol.Required("config_entry_id"): cv.string,
    vol.Required("start_date"): cv.date,
    vol.Optional("end_date"): cv.date,
})


async def async_setup(hass, config):
    """Registro de servicios a nivel de componente (una sola vez)."""

    async def _async_handle_rebuild_sensor_history(call):
        entry_id = call.data["config_entry_id"]
        entry = hass.config_entries.async_get_entry(entry_id)

        if entry is None or entry.domain != DOMAIN:
            raise HomeAssistantError(
                f"No existe ninguna entrada de {DOMAIN} con id '{entry_id}'"
            )

        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator is None:
            raise HomeAssistantError(
                f"La entrada '{entry.title}' no está cargada actualmente"
            )

        await async_backfill_energy_consumption_price_history(
            hass,
            entry,
            coordinator,
            call.data["start_date"],
            call.data.get("end_date"),
        )

        await async_backfill_power_term_daily_price_history(
            hass,
            entry,
            coordinator,
            call.data["start_date"],
            call.data.get("end_date"),
        )

        await async_backfill_standing_charge_history(
            hass,
            entry,
            coordinator,
            call.data["start_date"],
            call.data.get("end_date"),
        )
        

    hass.services.async_register(
        DOMAIN,
        SERVICE_REBUILD_SENSOR_HISTORY,
        _async_handle_rebuild_sensor_history,
        schema=REBUILD_SENSOR_HISTORY_SCHEMA,
    )

    return True


async def async_setup_entry(hass, entry):
    holiday_sources = entry.options.get("holiday_sources", [])

    _LOGGER.debug("Setup entry with options: %s", entry.options)

    providers = []

    for hs in holiday_sources:
        provider = get_provider(
            hs.get("type", "ics"),
            {
                "source": hs["source"],
                "tag": hs["tag"]
            }
        )
        providers.append(provider)

    coordinator = EnergyPeriodsCoordinator(hass, providers, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    hass.data[DOMAIN].setdefault("_options_snapshot", {})[entry.entry_id] = (
        copy.deepcopy(dict(entry.options))
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor"]
    )

    return True


async def update_listener(hass, entry):
    """Recarga la entrada solo si `entry.options` ha cambiado de verdad.

    `async_update_entry` dispara este listener ante CUALQUIER cambio, ya sea
    en `data` o en `options`. Nuestro propio backfill inicial actualiza
    `entry.data` (flag `_history_backfilled`) sin tocar `options`, así que
    comparamos contra el snapshot de `options` guardado al montar la entrada
    para evitar una recarga innecesaria en ese caso. Si en el futuro se
    añadiera un flujo de reconfiguración que modifique `entry.data` con
    cambios que sí deban recargar la entrada, habría que revisar esto.
    """
    snapshot = hass.data.get(DOMAIN, {}).get("_options_snapshot", {}).get(
        entry.entry_id
    )

    if snapshot is not None and snapshot == dict(entry.options):
        return

    await hass.config_entries.async_reload(entry.entry_id)