"""Descarga el tipo de cambio oficial (USD/ARS) desde la API pública del BCRA.

Fuente: API de Estadísticas Cambiarias del BCRA (sin autenticación).
Documentación: https://www.bcra.gob.ar/archivos/Catalogo/Content/files/pdf/estadisticascambiarias-v1.pdf

Endpoint usado: GET api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD
    ?fechadesde=yyyy-MM-dd&fechahasta=yyyy-MM-dd&limit=1000&offset=n

La API solo devuelve hasta 1000 registros por request, así que se pagina
en ventanas de tiempo. La serie es diaria (días hábiles); acá se agrega a
mensual (promedio y cierre de mes) para poder cruzarla con las series de
biodiesel/bioetanol, que son mensuales.

IMPORTANTE: este script no corre en el sandbox de Claude porque
api.bcra.gob.ar no está en la lista de dominios permitidos del entorno.
Correrlo en tu PC/notebook con acceso a internet.

Requiere: pip install requests pandas
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD"


def _fetch_window(fecha_desde: date, fecha_hasta: date) -> list[dict]:
    """Pide una ventana de fechas a la API, paginando con offset si hace falta.

    Args:
        fecha_desde: Primer día del rango (inclusive).
        fecha_hasta: Último día del rango (inclusive).

    Returns:
        Lista de registros diarios crudos (cada uno con 'fecha' y 'detalle').
    """
    registros: list[dict] = []
    offset = 0
    while True:
        params = {
            "fechadesde": fecha_desde.isoformat(),
            "fechahasta": fecha_hasta.isoformat(),
            "limit": 1000,
            "offset": offset,
        }
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        registros.extend(results)
        count = data.get("metadata", {}).get("resultset", {}).get("count", 0)
        if offset + len(results) >= count or not results:
            break
        offset += 1000
    return registros


def scrape_tipo_cambio(desde: str = "2018-01-01", hasta: str | None = None) -> pd.DataFrame:
    """Descarga la serie diaria de tipo de cambio USD y la agrega a mensual.

    Se pide en ventanas anuales para no pisar límites de la API con rangos
    demasiado largos.

    Args:
        desde: Fecha de inicio (yyyy-MM-dd).
        hasta: Fecha de fin (yyyy-MM-dd); si es None, usa hoy.

    Returns:
        DataFrame con columnas [fecha, tc_promedio_mes, tc_cierre_mes].
    """
    fecha_desde = date.fromisoformat(desde)
    fecha_hasta = date.today() if hasta is None else date.fromisoformat(hasta)

    todos: list[dict] = []
    anio_actual = fecha_desde.year
    while anio_actual <= fecha_hasta.year:
        ventana_desde = max(fecha_desde, date(anio_actual, 1, 1))
        ventana_hasta = min(fecha_hasta, date(anio_actual, 12, 31))
        todos.extend(_fetch_window(ventana_desde, ventana_hasta))
        anio_actual += 1

    filas = []
    for reg in todos:
        fecha = reg.get("fecha")
        detalle = reg.get("detalle", [])
        if not fecha or not detalle:
            continue
        # tipoCotizacion viene en pesos por unidad de moneda extranjera
        filas.append({"fecha": pd.Timestamp(fecha), "tc": detalle[0]["tipoCotizacion"]})

    df = pd.DataFrame(filas).sort_values("fecha")
    df["mes"] = df["fecha"].dt.to_period("M").dt.to_timestamp()

    mensual = (
        df.groupby("mes")
        .agg(tc_promedio_mes=("tc", "mean"), tc_cierre_mes=("tc", "last"))
        .reset_index()
        .rename(columns={"mes": "fecha"})
    )
    return mensual


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)

    tc = scrape_tipo_cambio(desde="2018-01-01")
    tc.to_csv(out_dir / "tipo_cambio_mensual.csv", index=False)
    print(f"tipo_cambio_mensual.csv: {len(tc)} filas")


if __name__ == "__main__":
    main()
