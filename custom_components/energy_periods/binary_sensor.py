from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        WeekendBinarySensor(coordinator, entry.entry_id),
        HolidayBinarySensor(coordinator, entry.entry_id),
        NonWorkingDayBinarySensor(coordinator, entry.entry_id),
    ])


class WeekendBinarySensor(BinarySensorEntity):

    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_weekend"

    @property
    def name(self):
        return "Is weekend"

    @property
    def icon(self):
        return "mdi:calendar-weekend"

    @property
    def is_on(self):
        return self.coordinator.is_weekend()


class HolidayBinarySensor(BinarySensorEntity):

    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_holiday"

    @property
    def name(self):
        return "Is public holiday"

    @property
    def icon(self):
        return "mdi:calendar-star"

    @property
    def is_on(self):
        return self.coordinator.is_public_holiday()


class NonWorkingDayBinarySensor(BinarySensorEntity):

    def __init__(self, coordinator, entry_id):
        self.coordinator = coordinator
        self._attr_unique_id = f"{entry_id}_non_working_day"

    @property
    def name(self):
        return "Is non-working day"

    @property
    def icon(self):
        return "mdi:calendar-remove"

    @property
    def is_on(self):
        return (
            self.coordinator.is_weekend()
            or self.coordinator.is_public_holiday()
        )
