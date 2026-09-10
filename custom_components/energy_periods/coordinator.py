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
    
    def _get_active_tariff(self, target_date: date = None):
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
        
        # Si no hay tariff vigente, usar el primero como fallback
        if tariffs:
            _LOGGER.warning("No active tariff for %s, using first tariff", target_date)
            return tariffs[0]
        
        return None
    
    def get_periods(self):
        active_tariff = self._get_active_tariff()
        if not active_tariff:
            _LOGGER.error("No active tariff found in configuration")
            return {}
        return active_tariff.get("periods", {})

    def get_current_period(self):
        now = dt_util.now()
        is_non_working_day = self.is_non_working_day()

        return get_period(now, self.get_periods(), is_non_working_day)


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


    def get_prices(self):
        active_tariff = self._get_active_tariff()
        if not active_tariff:
            _LOGGER.error("No active tariff found in configuration")
            return {}
        return active_tariff.get("prices", {})

    def get_current_price(self):
        period_type = self.get_current_period();
        prices = self.get_prices()
        return prices.get(period_type, 0.0)
