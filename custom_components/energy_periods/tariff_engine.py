from datetime import datetime
import json
import logging

_LOGGER = logging.getLogger(__name__)

def parse_to_seconds(value):
    parts = list(map(int, value.split(":")))

    if len(parts) == 2:
        h, m = parts
        s = 0
    else:
        h, m, s = parts

    return h * 3600 + m * 60 + s

def in_range(current, start, end):
    if start < end:
        # tramo normal
        return start <= current < end
    else:
        # cruza medianoche
        return current >= start or current < end
    
def get_period(now, periods, is_holiday):
    day_type = "non_working_day" if is_holiday else "working_day"

    current = now.hour * 3600 + now.minute * 60 + now.second

    for block in periods.get(day_type, []):
        start = parse_to_seconds(block["start"])
        end = parse_to_seconds(block["end"])

        if in_range(current, start, end):
            return block["type"]

    fallback = periods.get("fallback", {}).get("type")
    return fallback if fallback else "unknown"

def validate_periods(periods):

    sorted_periods = sorted(periods, key=lambda x: parse_to_seconds(x["start"]))

    for i in range(len(sorted_periods) - 1):
        end = parse_to_seconds(sorted_periods[i]["end"])
        next_start = parse_to_seconds(sorted_periods[i + 1]["start"])

        if end > next_start:
            raise ValueError(
                f"Overlap: {sorted_periods[i]} with {sorted_periods[i+1]}"
            )

    return True


# Parseo de configuración de tarifas

class TariffsError(Exception):
    """Error base para tarifas."""
    def __init__(self, error_key: str, message: str = ""):
        super().__init__(message or error_key)
        self.error_key = error_key  # "invalid_json" | "invalid_config" | "unknown_error"

def parse_tariffs_from_json(json_text: str) -> list:
    """
    Parsea y valida un JSON de tarifas.
    Devuelve la lista de tarifas ya validada.
    Lanza TariffsError con un error_key traducible en caso de fallo.
    """
    json_text = (json_text or "").strip()
    if not json_text:
        raise TariffsError("invalid_json", "Empty JSON")

    _LOGGER.debug("Reading tariffs from JSON text (length: %d chars)", len(json_text))
    _LOGGER.debug("JSON content (first 200 chars): %s", json_text[:200])

    try:
        config = json.loads(json_text)
    except json.JSONDecodeError as e:
        _LOGGER.error("JSON decode error: %s", e)
        raise TariffsError("invalid_json", str(e)) from e

    try:
        validate_tariffs({"tariffs": config})
    except ValueError as e:
        _LOGGER.error("Config validation error: %s", e)
        raise TariffsError("invalid_config", str(e)) from e
    except Exception as e:
        _LOGGER.error("Unexpected error loading tariffs: %s", type(e).__name__, exc_info=True)
        raise TariffsError("unknown_error", str(e)) from e

    _LOGGER.info("Tariffs parsed and validated successfully")
    return config

def validate_tariffs(config: dict):
    """Valida la estructura de la configuración de tarifas."""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    
    if "tariffs" in config:
        tariffs = config["tariffs"]
        if not isinstance(tariffs, list):
            raise ValueError("'tariffs' must be an array")
        if len(tariffs) == 0:
            raise ValueError("'tariffs' array cannot be empty")
        
        for i, tariff in enumerate(tariffs):
            validate_tariff_entry(tariff, i)
    
    else:
        raise ValueError("Configuration must have 'tariffs'")

def validate_tariff_entry(tariff_entry: dict, index: int):
    """Valida una entrada de la lista de tarifas."""
    if not isinstance(tariff_entry, dict):
        raise ValueError(f"Tariff {index} must be a dict")

    if "consumption" not in tariff_entry:
        raise ValueError(f"Tariff {index} must have 'consumption'")

    if "power" not in tariff_entry:
        raise ValueError(f"Tariff {index} must have 'power'")

    validate_tariff(tariff_entry["consumption"], index, "consumption")
    validate_tariff(tariff_entry["power"], index, "power")

    if "standing_charges" in tariff_entry:
        validate_standing_charges(tariff_entry["standing_charges"], index)

def validate_tariff(tariff: dict, index: int, tariff_type: str):
    """Valida una tarifa."""
    if not isinstance(tariff, dict):
        raise ValueError(f"Tariff {tariff_type} {index} must be a dict")

    if "periods" not in tariff:
        raise ValueError(f"Tariff {tariff_type} {index} must have 'periods'")
    
    periods = tariff["periods"]
    if not isinstance(periods, dict):
        raise ValueError(f"Tariff {tariff_type} {index} 'periods' must be a dict")
    
    for day_type in ["working_day", "non_working_day"]:
        if day_type in periods:
            validate_periods(periods[day_type])
    
    if "prices" not in tariff:
        raise ValueError(f"Tariff {tariff_type} {index} must have 'prices'")
    
    prices = tariff["prices"]
    if not isinstance(prices, dict):
        raise ValueError(f"Tariff {tariff_type} {index} 'prices' must be a dict")
    
    for ptype, price in prices.items():
        if not isinstance(price, (int, float)):
            raise ValueError(f"Tariff {tariff_type} {index}, price for '{ptype}' must be a number")
        if price < 0:
            raise ValueError(f"Tariff {tariff_type} {index}, price for '{ptype}' cannot be negative")

def validate_standing_charges(standing_charges: list, index: int):
    """Valida la lista de cargos fijos (standing charges)."""
    if not isinstance(standing_charges, list):
        raise ValueError(f"Tariff {index} 'standing_charges' must be a list")
    
    for i, charge in enumerate(standing_charges):
        if not isinstance(charge, dict):
            raise ValueError(f"Tariff {index} standing charge {i} must be a dict")
        
        required_keys = ["name", "unique_id", "value"]
        for key in required_keys:
            if key not in charge:
                raise ValueError(f"Tariff {index} standing charge {i} must have '{key}'")
        
        if not isinstance(charge["value"], (int, float)):
            raise ValueError(f"Tariff {index} standing charge {i} 'value' must be a number")
        
        if charge["value"] < 0:
            raise ValueError(f"Tariff {index} standing charge {i} 'value' cannot be negative")