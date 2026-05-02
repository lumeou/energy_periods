from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        HolidayBinarySensor(coordinator, entry.entry_id)
    ])


class HolidayBinarySensor(BinarySensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_holiday_today"

    @property
    def name(self):
        return "Is holiday today"

    @property
    def is_on(self):
        return self.coordinator.is_today_holiday()
