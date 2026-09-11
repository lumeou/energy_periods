"""Reconstrucción del histórico (long-term statistics) del sensor de precio.

Los valores de tramo/precio de esta integración son una función determinista
de la fecha/hora (calendario de festivos + configuración de tramos), por lo
que es posible recalcular qué habría marcado el sensor en cualquier momento
pasado sin necesidad de que Home Assistant lo hubiera registrado en su día.

Este módulo no toca la tabla `states` del Recorder (eso no está soportado ni
es necesario aquí). En su lugar escribe directamente en las *long-term
statistics* horarias asociadas a la entidad `sensor.<nombre>_energy_price`,
usando el mismo mecanismo interno que emplea el servicio nativo
`recorder.import_statistics`. Esas estadísticas son las que alimentan el
histórico del panel de energía y los gráficos de larga duración.

Nota: se apoya en `homeassistant.components.recorder.statistics`, que es una
API interna del Recorder (no pública/estable entre versiones de Home
Assistant). Si tras una actualización de HA cambia su firma, revisa este
fichero.

Importante sobre los festivos: los festivos usados aquí son los que ya ha
cargado el coordinator (`coordinator.get_raw_holidays()`), tal cual los
devuelve el proveedor ICS configurado. Si ese ICS no incluye fechas antiguas,
los días festivos anteriores a su cobertura no se detectarán como tales y el
tramo calculado para esos días será el de un día laborable normal. No se hace
ninguna comprobación en tiempo de ejecución sobre el rango cubierto por el
ICS: es responsabilidad de quien configura el origen de datos.
"""

import logging
from datetime import date, datetime, timedelta

from homeassistant.components.recorder.models import StatisticMeanType, StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .tariff_engine import get_period

_LOGGER = logging.getLogger(__name__)


def _is_non_working_day(day: date, holidays: dict) -> bool:
    """Determina si `day` (objeto date) es festivo o fin de semana."""
    if day.weekday() >= 5:
        return True
    return bool(holidays) and day.isoformat() in holidays


def _get_tariff_for_date(options: dict, target_date: date) -> dict | None:
    """Obtiene el tariff vigente para la fecha dada."""

    if "tariffs" not in options:
        return None
    
    tariffs = options.get("tariffs", [])
    
    for tariff in tariffs:
        from_date = tariff.get("from_date")
        to_date = tariff.get("to_date")
        
        if isinstance(from_date, str):
            from_date = dt_util.parse_date(from_date) if from_date else None
        if isinstance(to_date, str):
            to_date = dt_util.parse_date(to_date) if to_date else None
        
        if from_date is None or target_date >= from_date:
            if to_date is None or target_date <= to_date:
                return tariff
    
    return None

def _get_consumption_tariff_for_date(options: dict, target_date: date) -> dict:
    """Obtiene la tarifa de consumo de energía vigente para la fecha dada."""
    tariff = _get_tariff_for_date(options, target_date)
    if not tariff:
        _LOGGER.error("No active tariff found in configuration")
        return {}
    return tariff.get("consumption", {})

def _get_consumption_periods_for_date(options: dict, target_date: date) -> dict:
    """Obtiene los períodos vigentes para la fecha dada."""
    tariff = _get_consumption_tariff_for_date(options, target_date)
    return tariff.get("periods", {})

def _get_consumption_prices_for_date(options: dict, target_date: date) -> dict:
    """Obtiene los precios vigentes para la fecha dada."""
    tariff = _get_consumption_tariff_for_date(options, target_date)
    return tariff.get("prices", {})


def _energy_consumption_price_entity_id(hass, entry):
    """Localiza el entity_id real del sensor de precio de consumo de energía de esta entrada."""
    ent_reg = er.async_get(hass)
    unique_id = f"{entry.entry_id}_energy_consumption_price"
    return ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)


async def async_backfill_energy_consumption_price_history(
    hass, entry, coordinator, start_date: date, end_date: date | None = None
) -> int:
    """Reconstruye la estadística horaria del sensor de precio de consumo de energía.

    Genera un punto por cada hora completa entre el inicio del día
    `start_date` (hora local) y:
      - el final del día `end_date` (hora local), si se indica, o
      - la última hora completa anterior al momento actual, en caso contrario.

    Devuelve el número de puntos horarios escritos.
    """
    entity_id = _energy_consumption_price_entity_id(hass, entry)

    if entity_id is None:
        _LOGGER.warning(
            "No se pudo reconstruir el histórico de precio: la entidad "
            "'%s_energy_consumption_price' aún no está registrada",
            entry.entry_id,
        )
        return 0

    holidays = coordinator.get_raw_holidays() or {}
    options = entry.options

    start_utc = dt_util.as_utc(dt_util.start_of_local_day(start_date)).replace(
        minute=0, second=0, microsecond=0
    )

    now_hour_utc = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)

    if end_date is not None:
        end_utc = dt_util.as_utc(
            dt_util.start_of_local_day(end_date) + timedelta(days=1)
        ).replace(minute=0, second=0, microsecond=0)
        end_utc = min(end_utc, now_hour_utc)
    else:
        end_utc = now_hour_utc

    if start_utc >= end_utc:
        _LOGGER.debug(
            "Nada que reconstruir para %s: rango vacío (%s -> %s)",
            entity_id,
            start_utc,
            end_utc,
        )
        return 0

    stats: list[StatisticData] = []
    current = start_utc

    while current < end_utc:
        local_dt = dt_util.as_local(current)
        
        # Obtener periods y prices para esta fecha
        periods = _get_consumption_periods_for_date(options, local_dt.date())
        prices = _get_consumption_prices_for_date(options, local_dt.date())
        
        non_working = _is_non_working_day(local_dt.date(), holidays)
        period_type = get_period(local_dt, periods, non_working)
        price = prices.get(period_type, 0.0)

        stats.append(
            StatisticData(start=current, mean=price, min=price, max=price)
        )
        current += timedelta(hours=1)

    metadata = StatisticMetaData(
        # has_mean=True,
        mean_type=StatisticMeanType.ARITHMETIC,
        has_sum=False,
        name=f"{entry.title} Energy Consumption Price",
        source="recorder",
        statistic_id=entity_id,
        unit_of_measurement="€/kWh",
        unit_class=None
    )

    async_import_statistics(hass, metadata, stats)

    _LOGGER.info(
        "Reconstruidos %s puntos horarios de histórico para %s (%s -> %s)",
        len(stats),
        entity_id,
        start_utc,
        end_utc,
    )

    return len(stats)


def _power_term_daily_price_entity_id(hass, entry):
    """Localiza el entity_id real del sensor de precio de diario de potencia de esta entrada."""
    ent_reg = er.async_get(hass)
    unique_id = f"{entry.entry_id}_power_term_daily_price"
    return ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)

async def async_backfill_power_term_daily_price_history(
    hass, entry, coordinator, start_date: date, end_date: date | None = None
) -> int:
    """Reconstruye el histórico estadístico para el coste diario total de potencia."""
    # entity_id = f"sensor.{entry.entry_id}_power_term_daily_price"
    entity_id = _power_term_daily_price_entity_id(hass, entry)
    stat_name = f"{entry.title} Power Term Daily Price"
    unit = "€/day"

    # 1. Gestión de rangos temporales UTC / Local
    start_utc = dt_util.as_utc(dt_util.start_of_local_day(start_date)).replace(minute=0, second=0, microsecond=0)
    now_hour_utc = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    
    if end_date is not None:
        end_utc = dt_util.as_utc(dt_util.start_of_local_day(end_date) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        end_utc = min(end_utc, now_hour_utc)
    else:
        end_utc = now_hour_utc

    if start_utc >= end_utc:
        return 0

    stats: list[StatisticData] = []
    current = start_utc
    last_processed_local_date = None
    current_day_value = 0.0

    # 2. Bucle horario enfocado únicamente en la potencia
    while current < end_utc:
        local_dt = dt_util.as_local(current)
        local_date = local_dt.date()
        
        if local_date != last_processed_local_date:
            tariff_for_date = coordinator.get_active_tariff(local_date)
            
            if not tariff_for_date:
                current_day_value = 0.0
            else:
                power_tariff = tariff_for_date.get("power", {})
                power_prices = power_tariff.get("prices", {})
                contracted_power = power_tariff.get("contracted_power", {})
                
                daily_price = 0.0
                for period_type, price_per_kw_day in power_prices.items():
                    contracted_kw = contracted_power.get(period_type, 0.0)
                    daily_price += contracted_kw * price_per_kw_day
                current_day_value = daily_price
                
            last_processed_local_date = local_date

        stats.append(
            StatisticData(start=current, mean=current_day_value, min=current_day_value, max=current_day_value)
        )
        current += timedelta(hours=1)

    # 3. Inyección en la Base de Datos
    metadata = StatisticMetaData(
        # has_mean=True,
        mean_type=StatisticMeanType.ARITHMETIC,
        has_sum=False,
        name=stat_name,
        source="recorder",
        statistic_id=entity_id,
        unit_of_measurement=unit,
        unit_class=None
    )

    async_import_statistics(hass, metadata, stats)
    _LOGGER.info("Reconstruido histórico de potencia para %s (%s puntos)", entity_id, len(stats))
    return len(stats)


def _standing_charge_entity_id(hass, entry, charge_id: str):
    """Localiza el entity_id real del sensor de cargo fijo de esta entrada."""
    ent_reg = er.async_get(hass)
    unique_id = f"{entry.entry_id}_standing_charge_{charge_id}"
    return ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)

async def async_backfill_standing_charge_history(
    hass, entry, coordinator, start_date: date, end_date: date | None = None
) -> int:
    """Reconstruye el histórico estadístico de todos los cargos fijos (standing charges)."""

    # 1. Definición de rangos temporales UTC / Local
    start_utc = dt_util.as_utc(dt_util.start_of_local_day(start_date)).replace(minute=0, second=0, microsecond=0)
    now_hour_utc = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    
    if end_date is not None:
        end_utc = dt_util.as_utc(dt_util.start_of_local_day(end_date) + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        end_utc = min(end_utc, now_hour_utc)
    else:
        end_utc = now_hour_utc

    if start_utc >= end_utc:
        _LOGGER.debug("Nada que reconstruir: rango vacío")
        return

    # 2. Estructuras de acumulación dinámicas
    # Estructura: { "charge_id": [StatisticData, StatisticData, ...] }
    charges_stats: dict[str, list[StatisticData]] = {}
    # Estructura: { "charge_id": {"name": str, "unit": str} }
    charges_metadata: dict[str, dict] = {}

    current = start_utc
    last_processed_local_date = None
    
    # Cachés diarias
    current_day_charges: dict[str, float] = {} # { "charge_id": valor_ese_dia }

    # 3. BUCLE HORARIO GLOBAL
    while current < end_utc:
        local_dt = dt_util.as_local(current)
        local_date = local_dt.date()
        
        # Solo recalculamos costes al cambiar de día local
        if local_date != last_processed_local_date:
            tariff_for_date = coordinator.get_active_tariff(local_date)
            current_day_charges = {} # Limpiamos los cargos del día anterior
            
            if tariff_for_date:
                # Mapear Standing Charges del día
                standing_charges = tariff_for_date.get("standing_charges", [])
                for charge in standing_charges:
                    c_id = charge.get("unique_id")
                    if c_id:
                        current_day_charges[c_id] = charge.get("value", 0.0)
                        
                        # Guardamos/actualizamos la metadata con la última que veamos pasar
                        charges_metadata[c_id] = {
                            "name": charge.get("name", c_id.replace("_", " ").title()),
                            "unit": charge.get("unit_of_measurement", "€/day")
                        }
            
            last_processed_local_date = local_date

        # Inyectamos los puntos horarios de TODOS los cargos fijos conocidos hasta el momento
        # Si un cargo no está activo este día concreto, se inyecta 0.0 de forma automática
        for known_id in charges_metadata.keys():
            if known_id not in charges_stats:
                charges_stats[known_id] = []
            
            # Buscamos el valor de hoy, si no existía el cargo hoy, imputamos 0.0
            val = current_day_charges.get(known_id, 0.0)
            charges_stats[known_id].append(
                StatisticData(start=current, mean=val, min=val, max=val)
            )

        current += timedelta(hours=1)

    # 4. PROCESO DE INSERCIÓN (FLUSH) EN LA BASE DE DATOS
    
    # Importar dinámicamente cada Standing Charge acumulado
    total_stats = 0
    for c_id, stats_list in charges_stats.items():
        # entity_id = f"sensor.{entry.entry_id}_standing_charge_{c_id}"
        entity_id = _standing_charge_entity_id(hass, entry, c_id)
        meta_info = charges_metadata[c_id]
        
        metadata = StatisticMetaData(
            # has_mean=True,
            mean_type=StatisticMeanType.ARITHMETIC,
            has_sum=False,
            source="recorder",
            statistic_id=entity_id,
            name=f"{entry.title} {meta_info['name']}",
            unit_of_measurement=meta_info['unit'],
            unit_class=None
        )
        async_import_statistics(hass, metadata, stats_list)

        total_stats += len(stats_list)
        
    _LOGGER.info(
        "Reconstrucción completada para la entrada %s. %s cargos fijos procesados. Total de puntos horarios reconstruidos: %s", 
        entry.title, len(charges_stats), total_stats
    )

    return total_stats
