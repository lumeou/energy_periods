import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import logging

_LOGGER = logging.getLogger(__name__)

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
        # estado persistente del editor
        self.periods = dict(config_entry.options.get("periods", {}))
        self._current_day_type = None

        _LOGGER.debug("Periods: %s", self.periods)


    # ----------------------------------------------------
    # MENÚ PRINCIPAL
    # ----------------------------------------------------

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "working_day": "Working day",
                "non_working_day": "Non-working day",
                "save": "Save"
            }
        )

    # ----------------------------------------------------
    # ENTRADA WORKING DAY
    # ----------------------------------------------------

    async def async_step_working_day(self, user_input=None):
        self._current_day_type = "working_day"
        return await self.async_step_editor()

    # ----------------------------------------------------
    # ENTRADA NON WORKING DAY
    # ----------------------------------------------------

    async def async_step_non_working_day(self, user_input=None):
        self._current_day_type = "non_working_day"
        return await self.async_step_editor()

    # ----------------------------------------------------
    # EDITOR
    # ----------------------------------------------------

    async def async_step_editor(self, user_input=None):
    
        periods = self.periods.setdefault(self._current_day_type, [])
    
        # SOLO UI ESTÁTICA
        menu = {
            "add": "➕ Add period",
            "edit": "✏️ Edit period",
            "delete": "🗑 Delete period",
            "back": "⬅ Back",
            "save": "💾 Save",
        }
    
        return self.async_show_menu(
            step_id="editor",
            menu_options=menu
        )

    async def async_step_add(self, user_input=None):
    
        if user_input is not None:
            self.periods[self._current_day_type].append(user_input)
            return await self.async_step_editor()
    
        return self.async_show_form(
            step_id="add",
            data_schema=vol.Schema({
                vol.Required("start"): selector.TimeSelector(),
                vol.Required("end"): selector.TimeSelector(),
                vol.Required("type"): selector.TextSelector(),
            })
        )

    async def async_step_edit(self, user_input=None):
    
        periods = self.periods[self._current_day_type]
    
        if user_input is not None:
            idx = int(user_input["index"])
            self._edit_index = idx
            return await self.async_step_edit_form()
    
        options = {
            str(i): f"{p['start']} → {p['end']} ({p['type']})"
            for i, p in enumerate(periods)
        }
    
        return self.async_show_form(
            step_id="edit",
            data_schema=vol.Schema({
                vol.Required("index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                )
            })
        )
    

    async def async_step_delete(self, user_input=None):
    
        periods = self.periods[self._current_day_type]
    
        if user_input is not None:
            idx = int(user_input["index"])
            if 0 <= idx < len(periods):
                periods.pop(idx)
            return await self.async_step_editor()
    
        options = {
            str(i): f"{p['start']} → {p['end']} ({p['type']})"
            for i, p in enumerate(periods)
        }
    
        return self.async_show_form(
            step_id="delete",
            data_schema=vol.Schema({
                vol.Required("index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                )
            })
        )

    async def async_step_back(self, user_input=None):
        return await self.async_step_init()

    # ----------------------------------------------------
    # SAVE FINAL
    # ----------------------------------------------------

    async def async_step_save(self, user_input=None):

        return self.async_create_entry(
            title="Energy Periods",
            data=self.config_entry.data,
            options={
                "periods": self.periods
            }
        )
  
