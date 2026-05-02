from homeassistant.components.binary_sensor import BinarySensorEntity

class HolidayBinarySensor(BinarySensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def name(self):
        return "Is holiday today"

    @property
    def is_on(self):
        return self.coordinator.is_today_holiday()
