import logging

from datetime import timedelta
from datetime import date

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .tariff_engine import get_period


_LOGGER = logging.getLogger(__name__)


class EnergyPeriodsCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, providers, entry):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="energy_periods",
            update_interval=timedelta(seconds=30),
        )
        self.providers = providers
        self.entry = entry

    async def _async_update_data(self):
        merged = {}

        for p in self.providers:
            data = await p.get_holidays()
            _LOGGER.debug("Provider returned: %s", data)
            
            for d, tags in data.items():
                merged.setdefault(d, set()).update(tags)

        _LOGGER.debug("Merged holidays: %s", merged)
        
        return merged
    
    def get_active_tariff(self, target_date: date = None):
        """Obtiene el tariff activo para la fecha dada (hoy si no se especifica).
        
        Si la configuración usa tariffs (nuevo formato), busca cuál está vigente.
        Si usa el formato antiguo, retorna None para que los callers usen periods/prices directamente.
        """
        if target_date is None:
            target_date = dt_util.now().date()
        
        options = self.entry.options
        
        # Si no estamos en formato tariffs, retornar None
        if "tariffs" not in options:
            return None
        
        tariffs = options.get("tariffs", [])
        
        for tariff in tariffs:
            from_date = tariff.get("from_date")
            to_date = tariff.get("to_date")
            
            # Convertir strings a date objects si es necesario
            if isinstance(from_date, str):
                from_date = dt_util.parse_date(from_date)
            if isinstance(to_date, str):
                to_date = dt_util.parse_date(to_date)
            
            # Verificar si target_date cae en este rango
            if from_date is None or target_date >= from_date:
                if to_date is None or target_date <= to_date:
                    return tariff
        
        return None

    def get_active_consumption_tariff(self, target_date: date = None):
        active_tariff = self.get_active_tariff(target_date)
        if not active_tariff:
            _LOGGER.error("No active tariff found in configuration")
            return {}
        return active_tariff.get("consumption", {})

    def get_active_power_tariff(self, target_date: date = None):
        active_tariff = self.get_active_tariff(target_date)
        if not active_tariff:
            _LOGGER.error("No active tariff found in configuration")
            return {}
        return active_tariff.get("power", {})

    
    def get_consumption_periods(self):
        return self.get_active_consumption_tariff().get("periods", {})

    def get_current_consumption_period(self):
        now = dt_util.now()
        is_non_working_day = self.is_non_working_day()

        return get_period(now, self.get_consumption_periods(), is_non_working_day)

    def get_power_periods(self):
        return self.get_active_power_tariff().get("periods", {})

    def get_current_power_period(self):
        now = dt_util.now()
        is_non_working_day = self.is_non_working_day()

        return get_period(now, self.get_power_periods(), is_non_working_day)


    def get_consumption_prices(self):
        return self.get_active_consumption_tariff().get("prices", {})

    def get_current_consumption_price(self):
        period_type = self.get_current_consumption_period()
        prices = self.get_consumption_prices()
        return prices.get(period_type, 0.0)

    def get_power_prices(self):
        return self.get_active_power_tariff().get("prices", {})

    def get_contracted_power(self):
        return self.get_active_power_tariff().get("contracted_power", {})

    # def get_current_power_price(self):
    #     period_type = self.get_current_power_period()
    #     prices = self.get_power_prices()
    #     return prices.get(period_type, 0.0)

    def get_current_contracted_power(self):
        period_type = self.get_current_power_period()
        contracted_power = self.get_active_power_tariff().get("contracted_power", {})
        return contracted_power.get(period_type, 0.0)

    def get_daily_power_price(self):
        """Obtiene el precio diario de la potencia contratada."""
        daily_price = 0.0
        power_prices = self.get_power_prices()
        contracted_power = self.get_contracted_power()
        for period_type, price_per_kw_day in power_prices.items():
            contracted_kw = contracted_power.get(period_type, 0.0)
            daily_price += contracted_kw * price_per_kw_day
        return daily_price
    

    def get_standing_charges(self):
        active_tariff = self.get_active_tariff()
        if not active_tariff:
            _LOGGER.error("No active tariff found in configuration")
            return []
        return active_tariff.get("standing_charges", [])
    
    def get_current_standing_charge_by_id(self, entity_id: str):
        standing_charges = self.get_standing_charges()
        for standing_charge in standing_charges:
            if standing_charge.get("unique_id") == entity_id:
                return standing_charge
        return None


    def is_public_holiday(self):
        if not self.data:
            return False
    
        today = dt_util.now().date().isoformat()
        return today in self.data
    
    def is_weekend(self):
        return dt_util.now().weekday() >= 5

    def is_non_working_day(self):
        return self.is_weekend() or self.is_public_holiday()

    
    def get_raw_holidays(self):
        return self.data
