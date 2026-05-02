from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        HolidayBinarySensor(coordinator)
    ])


class HolidayBinarySensor(BinarySensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def name(self):
        return "Is holiday today"

    @property
    def is_on(self):
        return self.coordinator.is_today_holiday()
