import copy
import json
import logging
from pathlib import Path

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util
import voluptuous as vol
import aiofiles

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
                    }],
                    "backfill_from": user_input.get("backfill_from")
                },
                options=copy.deepcopy(DEFAULT_CONFIG)
            )

        schema = vol.Schema({
            vol.Required("name"): str,
            vol.Required("source"): str,
            vol.Required("tag"): str,
            vol.Optional(
                "backfill_from",
                default=dt_util.now().date().isoformat()
            ): selector.DateSelector(),
        })

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EnergyPeriodsOptionsFlow(config_entry)


class EnergyPeriodsOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry):
        # Estado persistente del editor
        
        self.tariffs = copy.deepcopy(config_entry.options.get("tariffs", []))

        self._current_day_type = None
        self._edit_price_type = None

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

    # Tariffs file management

    async def async_step_import_tariffs_config(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            if user_input.get("action") == "cancel":
                return await self.async_step_init()
            
            if user_input.get("tariffs_json"):
                json_text = user_input["tariffs_json"].strip()
                _LOGGER.debug("Reading tariffs from JSON text (length: %d chars)", len(json_text))
                
                try:
                    _LOGGER.debug("JSON content (first 200 chars): %s", json_text[:200])
                    
                    # Parsear JSON
                    config = json.loads(json_text)
                    _LOGGER.debug("JSON parsed successfully")
                    
                    # Validar estructura
                    self._validate_tariffs_config({"tariffs": config})
                    _LOGGER.debug("Config validated successfully")
                    
                    # Guardar en estado temporal
                    self.tariffs = config
                    
                    _LOGGER.info("Tariffs read from JSON text successfully")
                    return await self.async_step_init()
                
                except json.JSONDecodeError as e:
                    errors["tariffs_json"] = "invalid_json"
                    _LOGGER.error("JSON decode error: %s", e)
                except ValueError as e:
                    errors["tariffs_json"] = "invalid_config"
                    _LOGGER.error("Config validation error: %s", e)
                except Exception as e:
                    errors["tariffs_json"] = "unknown_error"
                    _LOGGER.error("Unexpected error loading tariffs: %s", type(e).__name__, exc_info=True)
        
        try:
            return self.async_show_form(
                step_id="import_tariffs_config",
                data_schema=vol.Schema({
                    vol.Optional("tariffs_json", default=""): selector.TextSelector(
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
        except Exception as e:
            _LOGGER.exception("Error showing import_tariffs_config form: %s", e)
            raise
      
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
    
    def _validate_tariffs_config(self, config: dict):
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a JSON object")
        
        if "tariffs" in config:
            tariffs = config["tariffs"]
            if not isinstance(tariffs, list):
                raise ValueError("'tariffs' must be an array")
            if len(tariffs) == 0:
                raise ValueError("'tariffs' array cannot be empty")
            
            for i, tariff in enumerate(tariffs):
                self._validate_tariff(tariff, i)
        
        else:
            raise ValueError("Configuration must have 'tariffs'")
    
    def _validate_tariff(self, tariff: dict, index: int):
        if not isinstance(tariff, dict):
            raise ValueError(f"Tariff {index} must be a dict")
        
        if "periods" not in tariff:
            raise ValueError(f"Tariff {index} must have 'periods'")
        
        periods = tariff["periods"]
        if not isinstance(periods, dict):
            raise ValueError(f"Tariff {index} 'periods' must be a dict")
        
        for day_type in ["working_day", "non_working_day"]:
            if day_type in periods:
                validate_periods(periods[day_type])
        
        if "prices" not in tariff:
            raise ValueError(f"Tariff {index} must have 'prices'")
        
        prices = tariff["prices"]
        if not isinstance(prices, dict):
            raise ValueError(f"Tariff {index} 'prices' must be a dict")
        
        for ptype, price in prices.items():
            if not isinstance(price, (int, float)):
                raise ValueError(f"Tariff {index}, price for '{ptype}' must be a number")
            if price < 0:
                raise ValueError(f"Tariff {index}, price for '{ptype}' cannot be negative")

    # Prices management

    async def async_step_prices(self, user_input=None):
        return await self.async_step_prices_menu()

    async def async_step_prices_menu(self, user_input=None):
        if user_input is not None:
            if user_input["action"] == "back":
                return await self.async_step_init()
            if user_input["action"] == "edit":
                self._edit_price_type = user_input["price_type"]
                return await self.async_step_edit_price()
        
        price_types = set()
        for day_type in ["working_day", "non_working_day"]:
            for period in self.periods.get(day_type, []):
                price_types.add(period["type"])
        
        options = [
            {"value": pt, "label": f"{pt}: {self.prices.get(pt, 0.0):.6f}"}
            for pt in sorted(price_types)
        ]
        
        if not options:
            return await self.async_step_init()
        
        return self.async_show_form(
            step_id="prices_menu",
            data_schema=vol.Schema({
                vol.Required("price_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options)
                ),
                vol.Required("action", default="edit"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "edit"],
                        translation_key="action"
                    )
                )
            })
        )

    async def async_step_edit_price(self, user_input=None):
        errors = {}
        price_type = self._edit_price_type
        current_price = self.prices.get(price_type, 0.0)
        
        if user_input is not None:
            if user_input["action"] == "back":
                return await self.async_step_prices_menu()
            
            try:
                price_value = float(user_input.get("price", current_price))
                if price_value < 0:
                    errors["price"] = "negative"
                else:
                    self.prices[price_type] = price_value
                    return await self.async_step_prices_menu()
            except (ValueError, TypeError):
                errors["price"] = "invalid"
        
        return self.async_show_form(
            step_id="edit_price",
            data_schema=vol.Schema({
                vol.Optional("price", default=current_price): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        step=0.001
                    )
                ),
                vol.Required("action", default="save"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["back", "save"],
                        translation_key="action"
                    )
                )
            }),
            errors=errors
        )

    async def async_step_save(self, user_input=None):

        try:
            # Validar períodos en el formato de tariffs
            for tariff in self.tariffs:
                for day_type in ["working_day", "non_working_day"]:
                    if day_type in tariff.get("periods", {}):
                        validate_periods(tariff["periods"].get(day_type, []))

        except ValueError as e:
            _LOGGER.error("Validation error: %s", e)
            return await self.async_step_init()

        return self.async_create_entry(
            title="Energy Periods",
            data={"tariffs": copy.deepcopy(self.tariffs)}
        )
