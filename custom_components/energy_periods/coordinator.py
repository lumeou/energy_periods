from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from datetime import timedelta

from .tariff_engine import get_period

import logging

_LOGGER = logging.getLogger(__name__)


class EnergyPeriodsCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, providers, periods):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="energy_periods",
            update_interval=timedelta(seconds=30),
        )
        self.providers = providers
        self.periods = periods

    async def _async_update_data(self):
        merged = {}

        for p in self.providers:
            data = await p.get_holidays()
            _LOGGER.debug("Provider returned: %s", data)
            
            for d, tags in data.items():
                merged.setdefault(d, set()).update(tags)

        _LOGGER.debug("Merged holidays: %s", merged)
        
        return merged
    
    def get_current_period(self):
        now = dt_util.now()
        is_non_working_day = self.is_non_working_day()

        return get_period(now, self.periods, is_non_working_day)


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

    
    def get_day_type(self):
        return "non_working_day" if self.is_non_working_day() else "working_day"

    def get_periods_for_today(self):
        day_type = self.get_day_type()
        return self.periods.get(day_type, [])
        
    def get_fallback(self):
        return self.periods.get("fallback", {"type": "unknown"})

    def validate_periods(periods):
        sorted_periods = sorted(periods, key=lambda x: x["start"])
    
        for i in range(len(sorted_periods) - 1):
            if sorted_periods[i]["end"] > sorted_periods[i + 1]["start"]:
                raise ValueError("Overlapping periods detected")
    
        return True

    def get_current_type(self, now):
        periods = self.get_periods_for_today()
    
        for p in periods:
            if p["start"] <= now < p["end"]:
                return p["type"]
    
        return self.get_fallback()["type"]
