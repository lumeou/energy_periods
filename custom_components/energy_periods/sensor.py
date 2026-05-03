import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .tariff_engine import get_period
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        EnergyPeriodSensor(coordinator, entry),
        EnergyPriceSensor(coordinator, entry)
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
        return self.coordinator.get_current_period()


class EnergyPriceSensor(SensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator

        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_energy_price"
        self._attr_name = f"{entry.title} Energy Price"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:hand-coin"
    
    @property
    def state(self):
        return self.coordinator.get_current_price()

    @property
    def native_unit_of_measurement(self):
        return "€/kWh"
    
    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        return None
    
    @property
    def last_reset(self):
        return None
    