import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .tariff_engine import get_period
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # sensores fijos que siempre existen
    entities = [
        EnergyConsumptionPeriodSensor(coordinator, entry),
        EnergyConsumptionPriceSensor(coordinator, entry),
        PowerTermPeriodSensor(coordinator, entry),
        PowerTermDailyPriceSensor(coordinator, entry)
    ]

    # sensores dinámicos según los standing_charges de la tarifa ACTIVA actual
    for charge in coordinator.get_standing_charges():
        unique_id = charge.get("unique_id")
        entities.append(StandingChargeSensor(coordinator, entry, unique_id))

    async_add_entities(entities)


class EnergyConsumptionPeriodSensor(SensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator

        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_energy_consumption_period"
        self._attr_name = f"{entry.title} Energy Consumption Period"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:clock-time-four"
    
    @property
    def native_value(self):
        return self.coordinator.get_current_consumption_period()


class EnergyConsumptionPriceSensor(SensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator

        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_energy_consumption_price"
        self._attr_name = f"{entry.title} Energy Consumption Price"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:hand-coin"
    
    @property
    def native_value(self):
        return self.coordinator.get_current_consumption_price()

    @property
    def native_unit_of_measurement(self):
        return "€/kWh"
    
    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        return None


class PowerTermPeriodSensor(SensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator

        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_power_term_period"
        self._attr_name = f"{entry.title} Power Term Period"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:clock-time-four"
    
    @property
    def native_value(self):
        return self.coordinator.get_current_power_period()


class PowerTermDailyPriceSensor(SensorEntity):

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator

        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_power_term_daily_price"
        self._attr_name = f"{entry.title} Power Term Daily Price"

    @property
    def name(self):
        return self._attr_name

    @property
    def icon(self):
        return "mdi:hand-coin"
    
    @property
    def native_value(self):
        return self.coordinator.get_daily_power_price()

    @property
    def native_unit_of_measurement(self):
        return "€/day"
    
    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self):
        return None

class StandingChargeSensor(SensorEntity):

    def __init__(self, coordinator, entry, charge_id: str):
        self.coordinator = coordinator
        self._entry = entry
        self._charge_id = charge_id

        # El unique_id de HA debe ser único globalmente. Usamos el id de la entrada + el del cargo
        self._attr_unique_id = f"{entry.entry_id}_standing_charge_{charge_id}"

    @property
    def _charge_config(self):
        """Atajo interno para obtener la configuración actual de la tarifa activa."""
        return self.coordinator.get_current_standing_charge_by_id(self._charge_id) or {}

    @property
    def name(self):
        name_prefix = self._entry.title
        charge_name = self._charge_config.get("name", self._charge_id.replace("_", " ").title())
        return f"{name_prefix} {charge_name}"

    @property
    def icon(self):
        return self._charge_config.get("icon", "mdi:cash")

    @property
    def native_value(self):
        return self._charge_config.get("value")

    @property
    def native_unit_of_measurement(self):
        return self._charge_config.get("unit_of_measurement", "€/day")

    @property
    def state_class(self):
        return self._charge_config.get("state_class", "measurement")