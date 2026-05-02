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
    def state(self):
        now = datetime.now()
        
        is_holiday = (
            self.coordinator.is_today_holiday()
            or now.weekday() >= 5
        )
        
        return get_period(
            now,
            self.coordinator.config,
            is_holiday
        )

    @property
    def extra_state_attributes(self):
        now = datetime.now()
        return {
            "is_weekend": now.weekday() >= 5,
            "is_holiday": self.coordinator.is_today_holiday(),
        }
