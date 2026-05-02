import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

DOMAIN = "energy_periods"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Energy Periods",
                data={"sources": [user_input]}
            )

        schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("source"): str,
            vol.Required("tag"): str,
        })

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyPeriodsOptionsFlow(config_entry)


class EnergyPeriodsOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        self.periods = dict(config_entry.options.get("periods", {}))

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "working_day": "Working day",
                "non_working_day": "Non-working day",
                "save": "Save"
            }
        )

    async def async_step_working_day(self, user_input=None):
        return await self._render_period_list("working_day", user_input)

    async def async_step_non_working_day(self, user_input=None):
        return await self._render_period_list("non_working_day", user_input)

    
    async def _render_period_list(self, day_type, user_input=None):
    
        periods = self.periods.setdefault(day_type, [])
    
        # Procesar acciones
        if user_input:
            action = list(user_input.keys())[0]

            if action.endswith(":add"):
                return await self._add_period_form(day_type)
            
            if ":delete_" in action:
                dt, rest = action.split(":")
                idx = int(rest.split("_")[1])

                if dt in self.periods and idx < len(self.periods[dt]):
                    self.periods[dt].pop(idx)

                return await self._render_period_list(dt)
            
            if action.endswith(":back"):
                return await self.async_step_init()
        
            if action.endswith(":save"):
                return await self.async_step_save()
        
        # UI lista
        options = {}
    
        for i, p in enumerate(periods):
            options[f"{day_type}:delete_{i}"] = (
                f"🗑 {p['start']} → {p['end']} ({p['type']})"
            )
    
        options[f"{day_type}:add"] = "➕ Add period"
        options[f"{day_type}:back"] = "⬅ Back"
        options[f"{day_type}:save"] = "💾 Save"
    
        return self.async_show_menu(
            step_id=day_type,
            menu_options=options
        )

    
    async def _add_period_form(self, day_type):
    
        schema = vol.Schema({
            vol.Required("start"): selector.TimeSelector(),
            vol.Required("end"): selector.TimeSelector(),
            vol.Required("type"): selector.TextSelector(),
        })
    
        return self.async_show_form(
            step_id=f"add_{day_type}",
            data_schema=schema
        )

    
    async def async_step_add_working_day(self, user_input=None):
    
        if user_input is not None:
            self.periods.setdefault("working_day", []).append(user_input)
            return await self._render_period_list("working_day")
    
        return await self._add_period_form("working_day")

    
    async def async_step_add_non_working_day(self, user_input=None):
        if user_input is not None:
            self.periods.setdefault("non_working_day", []).append(user_input)
            return await self._render_period_list("non_working_day")
    
        return await self._add_period_form("non_working_day")

    
    async def async_step_save(self, user_input=None):
    
        return self.async_create_entry(
            title="Energy Periods",
            data=self.config_entry.data,
            options={
                "periods": self.periods
            }
        )
  
