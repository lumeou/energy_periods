DOMAIN = "energy_periods"

DEFAULT_CONFIG = {
    "working_day": [
        {"start": "00:00", "end": "08:00", "type": "valle"},
        {"start": "08:00", "end": "10:00", "type": "llano"},
        {"start": "10:00", "end": "14:00", "type": "punta"},
        {"start": "14:00", "end": "18:00", "type": "llano"},
        {"start": "18:00", "end": "22:00", "type": "punta"},
        {"start": "22:00", "end": "00:00", "type": "llano"},
    ],
    "non_working_day": [
        {"start": "00:00", "end": "00:00", "type": "valle"}
    ],
    "fallback": {
        "type": "valle"
    }
}
