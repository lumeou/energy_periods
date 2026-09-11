import json

DOMAIN = "energy_periods"

# Tarifa por defecto
DEFAULT_CONSUMPTION_TARIFF = {
    "periods": {
        "working_day": [
            {"start": "00:00", "end": "08:00", "type": "valle"},
            {"start": "08:00", "end": "10:00", "type": "llano"},
            {"start": "10:00", "end": "14:00", "type": "punta"},
            {"start": "14:00", "end": "18:00", "type": "llano"},
            {"start": "18:00", "end": "22:00", "type": "punta"},
            {"start": "22:00", "end": "00:00", "type": "llano"}
        ],
        "non_working_day": [
            {"start": "00:00", "end": "00:00", "type": "valle"}
        ],
        "fallback": {
            "type": "valle"
        }
    },
    "prices": {
        "valle": 0.082673,
        "llano": 0.117512,
        "punta": 0.190465
    }
}

DEFAULT_POWER_TARIFF = {
    "periods": {
        "working_day": [
            {"start": "00:00", "end": "08:00", "type": "valle"},
            {"start": "08:00", "end": "00:00", "type": "punta"}
        ],
        "non_working_day": [
            {"start": "00:00", "end": "00:00", "type": "valle"}
        ],
        "fallback": {
            "type": "valle"
        }
    },
    "prices": {
        "punta": 0.110283,  # €/kW día P1
        "valle": 0.033469   # €/kW día P2
    },
    "contracted_power": {
        "punta": 4.6,       # kW P1
        "valle": 4.6        # kW P2
    }
}

# Configuración por defecto: tariff único con rango abierto
DEFAULT_CONFIG = {
    "tariffs": [
        {
            "from_date": None,  # Desde siempre
            "to_date": None,    # Hasta siempre
            "consumption": DEFAULT_CONSUMPTION_TARIFF,
            "power": DEFAULT_POWER_TARIFF,
            "standing_charges": [
                {
                    "name": "Alquiler contador",
                    "unique_id": "meter_rent",
                    "value": 0.026630,
                    "unit_of_measurement": "€/day",
                    "icon": "mdi:counter",
                    "state_class": "measurement"
                },
                {
                    "name": "Bono social",
                    "unique_id": "social_bonus",
                    "value": 0.019121,
                    "unit_of_measurement": "€/day",
                    "icon": "mdi:hand-heart",
                    "state_class": "measurement"
                },
                {
                    "name": "Impuesto eléctrico",
                    "unique_id": "electricity_tax",
                    "value": 5.112696,
                    "unit": "%",
                    "icon": "mdi:bank",
                    "state_class": "measurement"
                },
                {
                    "name": "IVA",
                    "unique_id": "iva",
                    "value": 21,
                    "unit_of_measurement": "%",
                    "icon": "mdi:bank",
                    "state_class": "measurement"
                },
                {
                    "name": "Compensación excedentes",
                    "unique_id": "export_compensation",
                    "value": 0.060000,
                    "unit_of_measurement": "€/kWh",
                    "icon": "mdi:solar-power",
                    "state_class": "measurement"
                }
            ]
        }
    ]
}

DEFAULT_TARIFFS_JSON = json.dumps(DEFAULT_CONFIG.get("tariffs", []), indent=2, ensure_ascii=False)
