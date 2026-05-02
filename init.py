from .providers.ics import ICSProvider
from .coordinator import EnergyPeriodsCoordinator
from .const import DOMAIN, DEFAULT_CONFIG

async def async_setup_entry(hass, entry):
    sources = entry.data.get("sources", [])
    config = entry.options.get("periods", DEFAULT_CONFIG)

    providers = [
        ICSProvider(s["source"], s["tag"])
        for s in sources
    ]

    coordinator = EnergyPeriodsCoordinator(hass, providers, config)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor"]
    )

    return True
