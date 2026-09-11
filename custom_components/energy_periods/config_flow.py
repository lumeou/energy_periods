import copy
import json
import logging

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DEFAULT_TARIFFS_JSON
from .tariff_engine import parse_tariffs_from_json, TariffsError

_LOGGER = logging.getLogger(__name__)

DOMAIN = "energy_periods"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:

            tariffs = None
            try:
                tariffs = parse_tariffs_from_json(user_input["tariffs_json"])
            except TariffsError as e:
                errors["tariffs_json"] = e.error_key
            
            if not errors:
                return self.async_create_entry(
                    title=user_input["name"],
                    data={
                        "name": user_input["name"]
                    },
                    options={
                        "holiday_sources": [{
                            "type": "ics",
                            "source": user_input["source"],
                            "tag": user_input["tag"]
                        }],
                        "tariffs": tariffs
                    }
                )

        config_json = (user_input or {}).get("tariffs_json") or DEFAULT_TARIFFS_JSON

        schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("source"): str,
            vol.Required("tag"): str,
            vol.Required("tariffs_json", default=config_json): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            )
        })          

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyPeriodsOptionsFlow(config_entry)


class EnergyPeriodsOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        # Estado persistente del editor
        
        self.holiday_sources = copy.deepcopy(config_entry.options.get("holiday_sources", []))
        self.tariffs = copy.deepcopy(config_entry.options.get("tariffs", []))

        _LOGGER.debug("Tariffs loaded: %s", self.tariffs)


    # ----------------------------------------------------
    # MENÚ PRINCIPAL
    # ----------------------------------------------------

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "import_tariffs_config",
                "export_tariffs_config",
                "save"
            ]
        )

    # Tariffs file management

    async def async_step_import_tariffs_config(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            if user_input.get("action") == "cancel":
                return await self.async_step_init()

            if user_input.get("tariffs_json"):
                try:
                    self.tariffs = parse_tariffs_from_json(user_input["tariffs_json"])
                    return await self.async_step_init()
                except TariffsError as e:
                    errors["tariffs_json"] = e.error_key

        config_json = (user_input or {}).get("tariffs_json") or json.dumps(self.tariffs, indent=2, ensure_ascii=False)
        
        return self.async_show_form(
            step_id="import_tariffs_config",
            data_schema=vol.Schema({
                vol.Optional("tariffs_json", default=config_json): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Required("action", default="accept"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["cancel", "accept"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )
    
    async def async_step_export_tariffs_config(self, user_input=None):
        """Download current configuration as JSON file."""
        if user_input is not None:
            return await self.async_step_init()
        
        # Create download link/text
        config_json = json.dumps(self.tariffs, indent=2, ensure_ascii=False)
        
        return self.async_show_form(
            step_id="export_tariffs_config",
            data_schema=vol.Schema({}),
            description_placeholders={
                "config": config_json,
                "filename": "tariffs_config.json"
            }
        )

    async def async_step_save(self, user_input=None):
        return self.async_create_entry(
            title="Energy Periods",
            data={
                "holiday_sources": copy.deepcopy(self.holiday_sources),
                "tariffs": copy.deepcopy(self.tariffs)
            }
        )
