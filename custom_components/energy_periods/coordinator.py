import logging

from datetime import timedelta

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
    
    def get_periods(self):
        return self.entry.options.get("periods", {})

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
        return self.entry.options.get("prices", {})

    def get_current_price(self):
        period_type = self.get_current_period();
        prices = self.get_prices()
        return prices.get(period_type, 0.0)
