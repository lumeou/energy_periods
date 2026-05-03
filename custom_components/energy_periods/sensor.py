import logging

from homeassistant.components.sensor import SensorEntity

from .tariff_engine import get_period
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        EnergyPeriodSensor(coordinator, entry)
    ])


class EnergyPeriodSensor(SensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator

        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_energy_period"
        self._attr_name = f"{entry.title} Energy Period"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:clock-time-four"
    
    @property
    def state(self):
        value = self.coordinator.get_current_period()
        _LOGGER.debug("Energy period recalculated: %s", value)  
        return value

