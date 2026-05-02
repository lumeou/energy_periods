from homeassistant.components.sensor import SensorEntity
from datetime import datetime

from .tariff_engine import get_period
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        EnergyPeriodSensor(coordinator, entry.entry_id)
    ])


class EnergyPeriodSensor(SensorEntity):
    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_energy_period"

    @property
    def name(self):
        return "Energy period"

    @property
    def icon(self):
        return "mdi:clock-time-four"
    
    @property
    def state(self):      
        return get_period(
            now,
            self.coordinator.config,
            self.coordinator.is_non_working_day()
        )
