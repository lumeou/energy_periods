from .providers import get_provider
from .coordinator import EnergyPeriodsCoordinator
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    sources = entry.data.get("sources", [])
    config = entry.option["periods"]

    _LOGGER.debug("Config: %s", config)

    providers = []

    for s in sources:
        provider = get_provider(
            s.get("type", "ics"),
            {
                "source": s["source"],
                "tag": s["tag"]
            }
        )
        providers.append(provider)

    coordinator = EnergyPeriodsCoordinator(hass, providers, config)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor"]
    )

    return True


async def update_listener(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
