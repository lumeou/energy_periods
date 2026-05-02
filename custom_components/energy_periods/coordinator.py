from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta, date
import logging

_LOGGER = logging.getLogger(__name__)


class EnergyPeriodsCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, providers, config):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="energy_periods",
            update_interval=timedelta(hours=12),
        )
        self.providers = providers
        self.config = config

    async def _async_update_data(self):
        merged = {}

        for p in self.providers:
            data = await p.get_holidays()
            _LOGGER.debug("Provider returned: %s", data)
            
            for d, tags in data.items():
                merged.setdefault(d, set()).update(tags)

        _LOGGER.debug("Merged holidays: %s", merged)
        
        return merged

    def is_public_holiday(self):
        if not self.data:
            return False
    
        today = date.today().isoformat()
        return today in self.data
    
    def is_weekend(self):
        return date.today().weekday() >= 5

    def is_non_working_day(self):
        return self.is_weekend() or self.is_public_holiday()

    def get_raw_holidays(self):
        return self.data
