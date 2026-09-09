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

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
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


def _price_entity_id(hass, entry):
    """Localiza el entity_id real del sensor de precio de esta entrada."""
    ent_reg = er.async_get(hass)
    unique_id = f"{entry.entry_id}_energy_price"
    return ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)


async def async_backfill_price_history(
    hass, entry, coordinator, start_date: date, end_date: date | None = None
) -> int:
    """Reconstruye la estadística horaria del sensor de precio.

    Genera un punto por cada hora completa entre el inicio del día
    `start_date` (hora local) y:
      - el final del día `end_date` (hora local), si se indica, o
      - la última hora completa anterior al momento actual, en caso
        contrario.

    Devuelve el número de puntos horarios escritos.
    """
    entity_id = _price_entity_id(hass, entry)

    if entity_id is None:
        _LOGGER.warning(
            "No se pudo reconstruir el histórico de precio: la entidad "
            "'%s_energy_price' aún no está registrada",
            entry.entry_id,
        )
        return 0

    periods = coordinator.get_periods()
    prices = coordinator.get_prices()
    holidays = coordinator.get_raw_holidays() or {}

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
        non_working = _is_non_working_day(local_dt.date(), holidays)
        period_type = get_period(local_dt, periods, non_working)
        price = prices.get(period_type, 0.0)

        stats.append(
            StatisticData(start=current, mean=price, min=price, max=price)
        )
        current += timedelta(hours=1)

    metadata = StatisticMetaData(
        has_mean=True,
        has_sum=False,
        name=f"{entry.title} Energy Price",
        source="recorder",
        statistic_id=entity_id,
        unit_of_measurement="€/kWh",
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