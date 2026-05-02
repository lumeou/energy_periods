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

        # contexto del editor actual
        self._current_day_type = None
        self._edit_index = None

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

    
    async def _render_period_list(self):

        day_type = self._current_day_type
        periods = self.periods.setdefault(day_type, [])

        menu_options = {}

        # lista de tramos
        for i, p in enumerate(periods):
            menu_options[f"delete_{i}"] = (
                f"🗑 {p['start']} → {p['end']} ({p['type']})"
            )

        # acciones globales del editor
        menu_options["add"] = "➕ Add period"
        menu_options["back"] = "⬅ Back"
        menu_options["save"] = "💾 Save"

        return self.async_show_menu(
            step_id="period_editor",
            menu_options=menu_options
        )


    async def async_step_period_editor(self, user_input=None):

        if not user_input:
            return await self._render_period_list()

        action = list(user_input.keys())[0]
        day_type = self._current_day_type
        periods = self.periods.setdefault(day_type, [])

        if action == "add":
            return await self._add_period_form()

        if action == "save":
            return await self.async_step_save()

        if action == "back":
            return await self.async_step_init()

        if action.startswith("delete_"):
            idx = int(action.split("_")[1])

            if 0 <= idx < len(periods):
                periods.pop(idx)

            return await self._render_period_list()

        return await self._render_period_list()

    
    async def _add_period_form(self, day_type):
    
        schema = vol.Schema({
            vol.Required("start"): selector.TimeSelector(),
            vol.Required("end"): selector.TimeSelector(),
            vol.Required("type"): selector.TextSelector(),
        })
    
        return self.async_show_form(
            step_id="add_period",
            data_schema=schema
        )

    
    async def async_step_add_period(self, user_input=None):

        if user_input is not None:
            self.periods.setdefault(self._current_day_type, []).append(user_input)
            return await self._render_period_list()

        return await self._add_period_form()

    
    async def async_step_save(self, user_input=None):
    
        return self.async_create_entry(
            title="Energy Periods",
            data=self.config_entry.data,
            options={
                "periods": self.periods
            }
        )
  
