import copy
import logging

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DEFAULT_CONFIG
from .tariff_engine import validate_periods

_LOGGER = logging.getLogger(__name__)

DOMAIN = "energy_periods"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    "name": user_input["name"],
                    "sources": [{
                        "type": "ics",
                        "source": user_input["source"],
                        "tag": user_input["tag"]
                    }]
                },
                options=copy.deepcopy(DEFAULT_CONFIG)
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
        self.periods = copy.deepcopy(config_entry.options.get("periods", {}))
        self.prices = copy.deepcopy(config_entry.options.get("prices", {}))
        self._current_day_type = None

        _LOGGER.debug("Periods: %s", self.periods)


    # ----------------------------------------------------
    # MENÚ PRINCIPAL
    # ----------------------------------------------------

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "working_day",
                "non_working_day",
                "save"
            ]
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

    async def async_step_editor(self, user_input=None, errors=None):
    
        periods = self.periods[self._current_day_type]
    
        # procesar acción
        if user_input is not None:
            action = user_input["action"]
    
            if action == "add":
                return await self.async_step_add()
    
            if action == "edit":
                return await self.async_step_edit()
    
            if action == "delete":
                return await self.async_step_delete()
            
            if action == "fallback":
                return await self.async_step_fallback()
    
            if action == "back":
                return await self.async_step_init()
    
            if action == "save":
                return await self.async_step_save()
    
        # construir lista visible
        if periods:
            text = "\n".join(
                f"{p['start']} → {p['end']} ({p['type']})"
                for p in periods
            )
        else:
            text = "No periods defined"
    
        schema = vol.Schema({
            vol.Required("action"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["add", "edit", "delete", "fallback", "back", "save"],
                    translation_key="action"
                )
            )
        })
    
        return self.async_show_form(
            step_id="editor",
            data_schema=schema,
            errors=errors or {},
            description_placeholders={
                "periods": text
            }
        )

    def _validate_period(self, user_input: dict) -> dict:
        """Devuelve dict de errores, vacío si todo ok."""
        errors = {}
        if not user_input.get("start"):
            errors["start"] = "required"
        if not user_input.get("end"):
            errors["end"] = "required"
        if not user_input.get("type"):
            errors["type"] = "required"
        return errors
    
    def _validate_period_selection(self, user_input: dict) -> dict:
        """Devuelve dict de errores, vacío si todo ok."""
        errors = {}
        if not user_input.get("index"):
            errors["index"] = "required"
        return errors
    
    def _validate_period_type(self, user_input: dict) -> dict:
        """Devuelve dict de errores, vacío si todo ok."""
        errors = {}
        if not user_input.get("type"):
            errors["type"] = "required"
        return errors

    async def async_step_add(self, user_input=None):
    
        errors = {}

        if user_input is not None:
            # cancelar
            if user_input["action"] == "back":
                return await self.async_step_editor()
            
            # comprobar datos requeridos
            errors = self._validate_period(user_input)
            if not errors:
                # guardar cambios
                self.periods[self._current_day_type].append(user_input)
                return await self.async_step_editor()
    
        return self.async_show_form(
            step_id="add",
            data_schema=vol.Schema({
                vol.Optional("start"): selector.TimeSelector(),
                vol.Optional("end"): selector.TimeSelector(),
                vol.Optional("type"): selector.TextSelector(),

                vol.Required("action", default="save"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "save"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )

    async def async_step_edit(self, user_input=None):
    
        periods = self.periods[self._current_day_type]

        if not periods:
            return await self.async_step_editor()
    
        errors = {}
        
        if user_input is not None:
            # cancelar
            if user_input["action"] == "back":
                return await self.async_step_editor()
            
            # comprobar datos requeridos
            errors = self._validate_period_selection(user_input)
            if not errors:
                idx = int(user_input["index"])
                self._edit_index = idx
                return await self.async_step_edit_form()
    
        options = [
            {"value": str(i), "label": f"{p['start']} → {p['end']} ({p['type']})"}
            for i, p in enumerate(periods)
        ]
    
        return self.async_show_form(
            step_id="edit",
            data_schema=vol.Schema({
                vol.Optional("index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                ),

                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "edit"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )

    async def async_step_edit_form(self, user_input=None):
    
        periods = self.periods[self._current_day_type]

        if not periods:
            return await self.async_step_editor()
        
        if self._edit_index is None or self._edit_index >= len(periods):
            return await self.async_step_editor()

        errors = {}

        if user_input is not None:
            # cancelar
            if user_input["action"] == "back":
                return await self.async_step_editor()
            
            # comprobar datos requeridos
            errors = self._validate_period(user_input)
            if not errors:
                # guardar cambios
                periods[self._edit_index] = user_input
                return await self.async_step_editor()
    
        # cargar valores actuales
        p = periods[self._edit_index]
    
        return self.async_show_form(
            step_id="edit_form",
            data_schema=vol.Schema({
                vol.Optional("start", default=p["start"]): selector.TimeSelector(),
                vol.Optional("end", default=p["end"]): selector.TimeSelector(),
                vol.Optional("type", default=p["type"]): selector.TextSelector(),

                vol.Required("action", default="save"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "save"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )

    async def async_step_delete(self, user_input=None):
    
        periods = self.periods[self._current_day_type]
    
        errors = {}

        if user_input is not None:
            # cancelar
            if user_input["action"] == "back":
                return await self.async_step_editor()
            
            # comprobar datos requeridos
            errors = self._validate_period_selection(user_input)
            if not errors:
                # eliminar
                idx = int(user_input["index"])
                if 0 <= idx < len(periods):
                    periods.pop(idx)
                return await self.async_step_editor()
    
        options = [
            {"value": str(i), "label": f"{p['start']} → {p['end']} ({p['type']})"}
            for i, p in enumerate(periods)
        ]
    
        return self.async_show_form(
            step_id="delete",
            data_schema=vol.Schema({
                vol.Optional("index"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                ),

                vol.Required("action", default="delete"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "delete"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )
    
    async def async_step_fallback(self, user_input=None):

        current = self.periods.get("fallback", {}).get("type", "")

        errors = {}

        if user_input is not None:
            # cancelar
            if user_input["action"] == "back":
                return await self.async_step_editor()
            
            # comprobar datos requeridos
            errors = self._validate_period_type(user_input)
            if not errors:
                # guardar cambios
                self.periods["fallback"] = {
                    "type": user_input["type"]
                }
                return await self.async_step_editor()

        return self.async_show_form(
            step_id="fallback",
            data_schema=vol.Schema({
                vol.Optional("type", default=current): selector.TextSelector(),

                vol.Required("action", default="save"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "save"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )

    async def async_step_back(self, user_input=None):
        return await self.async_step_init()

    async def async_step_save(self, user_input=None):

        try:
            for day_type in ["working_day", "non_working_day"]:
                validate_periods(self.periods.get(day_type, []))

        except ValueError:
            return await self.async_step_editor(
                errors={"base": "overlap"}
            )

        return self.async_create_entry(
            title="Energy Periods",
            data={
                "periods": copy.deepcopy(self.periods),
                "prices": copy.deepcopy(self.prices)
            }
        )
