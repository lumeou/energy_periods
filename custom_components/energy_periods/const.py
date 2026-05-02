DOMAIN = "energy_periods"

DEFAULT_CONFIG = {
    "working_day": [
        {"start": "10:00", "end": "14:00", "period": "punta"},
        {"start": "18:00", "end": "22:00", "period": "punta"}
    ],
    "non_working_day": [
        {"start": "00:00", "end": "24:00", "period": "valle"}
    ]
}
