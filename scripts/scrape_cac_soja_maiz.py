"""Descarga el histórico de precios promedio mensuales de soja y maíz
directo de la fuente oficial: la Cámara Arbitral de Cereales de la BCR.

Se usa el mismo endpoint que dispara el botón "Descargar Excel" del
buscador público (https://www.cac.bcr.com.ar/es/precios-de-pizarra/consultas),
reconstruido a partir de inspeccionar ese botón en el navegador:

    GET https://www.cac.bcr.com.ar/es/api/prices/987/export
        ?product={3|13}&type=average&date_start={yyyy-mm-01}
        &year={yyyy}&month={1-12}&period=month

    product=3  -> Maíz
    product=13 -> Soja

El endpoint devuelve un .xlsx por cada mes consultado (no admite pedir
un año completo de una sola vez), así que este script itera mes a mes
y concatena todo en un único DataFrame.

IMPORTANTE: este script no corre en el sandbox de Claude (cac.bcr.com.ar
no está en la lista de dominios permitidos del entorno). Correrlo en tu
PC/notebook con acceso a internet.

Requiere: pip install requests pandas openpyxl
"""

from __future__ import annotations

import time
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://www.cac.bcr.com.ar/es/api/prices/987/export"

PRODUCTOS = {"maiz": 3, "soja": 13}


def _fetch_mes(producto_id: int, anio: int, mes: int) -> float | None:
    """Pide el precio promedio de un producto para un mes puntual.

    Args:
        producto_id: Código de producto (3=maíz, 13=soja).
        anio: Año a consultar.
        mes: Mes a consultar (1-12).

    Returns:
        El precio promedio de ese mes, o None si no hay dato (ej. el mes
        todavía no ocurrió, o la fuente no tiene precio cargado).
    """
    params = {
        "product": producto_id,
        "type": "average",
        "date_start": f"{anio}-{mes:02d}-01",
        "year": anio,
        "month": mes,
        "period": "month",
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()

    df = pd.read_excel(BytesIO(resp.content), header=None)
    # La fila 5 (índice 5) tiene los datos: [Fecha Desde, Fecha Hasta,
    # Producto, Promedio, NaN, ...] según el archivo de ejemplo.
    fila_datos = df.iloc[5]
    promedio = fila_datos[3]
    if pd.isna(promedio):
        return None
    return float(promedio)


def scrape_producto(nombre: str, desde: tuple[int, int], hasta: tuple[int, int]) -> pd.DataFrame:
    """Recorre mes a mes el histórico de un producto en un rango de fechas.

    Args:
        nombre: 'maiz' o 'soja'.
        desde: (año, mes) de inicio, inclusive.
        hasta: (año, mes) de fin, inclusive.

    Returns:
        DataFrame con columnas [fecha, precio].
    """
    producto_id = PRODUCTOS[nombre]
    anio_desde, mes_desde = desde
    anio_hasta, mes_hasta = hasta

    filas = []
    anio, mes = anio_desde, mes_desde
    while (anio, mes) <= (anio_hasta, mes_hasta):
        precio = _fetch_mes(producto_id, anio, mes)
        filas.append({"fecha": pd.Timestamp(anio, mes, 1), "precio": precio})
        print(f"  {nombre} {anio}-{mes:02d}: {precio}")

        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
        time.sleep(0.5)  # no golpear la API muy rápido

    return pd.DataFrame(filas)


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)

    hoy = date.today()

    print("Descargando maíz...")
    maiz = scrape_producto("maiz", desde=(2018, 1), hasta=(hoy.year, hoy.month))

    print("Descargando soja...")
    soja = scrape_producto("soja", desde=(2018, 1), hasta=(hoy.year, hoy.month))

    df = maiz.rename(columns={"precio": "maiz_ars_tn"}).merge(
        soja.rename(columns={"precio": "soja_ars_tn"}), on="fecha", how="outer"
    )
    df = df.sort_values("fecha")
    df.to_csv(out_dir / "soja_maiz_cac_mensual.csv", index=False)
    print(f"\nsoja_maiz_cac_mensual.csv: {len(df)} filas")


if __name__ == "__main__":
    main()
