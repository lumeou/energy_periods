from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        WeekendBinarySensor(coordinator, entry.entry),
        HolidayBinarySensor(coordinator, entry.entry),
        NonWorkingDayBinarySensor(coordinator, entry.entry),
    ])


class WeekendBinarySensor(BinarySensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_weekend"
        self._attr_name = f"{entry.title} Is Weekend"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:calendar-weekend"

    @property
    def is_on(self):
        return self.coordinator.is_weekend()


class HolidayBinarySensor(BinarySensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_holiday"
        self._attr_name = f"{entry.title} Is Holiday"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:calendar-star"

    @property
    def is_on(self):
        return self.coordinator.is_public_holiday()


class NonWorkingDayBinarySensor(BinarySensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_non_working_day"
        self._attr_name = f"{entry.title} Is Holiday"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:calendar-remove"

    @property
    def is_on(self):
        return (
            self.coordinator.is_weekend()
            or self.coordinator.is_public_holiday()
        )
