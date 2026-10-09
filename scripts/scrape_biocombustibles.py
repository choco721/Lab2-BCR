"""Scraper mensual de precios oficiales de biodiesel y bioetanol.

Fuente: Secretaría de Energía de la Nación.
  - Biodiesel: http://glp.se.gob.ar/biocombustible/reporte_precios.php
  - Bioetanol: https://glp.se.gob.ar/biocombustible/reporte_precios_bioetanol.php

IMPORTANTE: este script no corre en el sandbox de Claude (esas URLs no
están en la lista de dominios permitidos del entorno), pero sí debería
funcionar en tu notebook/PC o en un runner de GitHub Actions/cron. Es la
base para la Etapa 2 (automatizar la recolección mensual).

Requiere: pip install requests pandas lxml
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd
import requests

BIODIESEL_URL = "http://glp.se.gob.ar/biocombustible/reporte_precios.php"
BIOETANOL_URL = "https://glp.se.gob.ar/biocombustible/reporte_precios_bioetanol.php"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _fetch_tables(url: str) -> list[pd.DataFrame]:
    """Descarga una URL y devuelve todas las tablas HTML como DataFrames.

    Args:
        url: Página a descargar.

    Returns:
        Lista de tablas encontradas en la página (pandas.read_html).
    """
    # Muchos sitios de gobierno devuelven una página de error si el request no
    # parece venir de un navegador: mandamos un User-Agent de navegador.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = "iso-8859-1"  # el sitio publica en Latin-1, no UTF-8

    # Si la página no trae tablas (p. ej. devolvió un "404 / page not found"),
    # pandas tira un error críptico. Lo detectamos y avisamos claro.
    if "<table" not in resp.text.lower():
        raise RuntimeError(
            f"La página {url} no devolvió ninguna tabla (¿el sitio está caído, "
            f"la URL cambió, o un antivirus/firewall intercepta el pedido?). "
            f"Probá abrir esa URL en el navegador: si ves un error, el problema "
            f"es de la fuente o de tu red, no del script."
        )

    # pandas 2.2+ (y Python nuevo) ya no acepta un string crudo: hay que
    # envolverlo en io.StringIO.
    return pd.read_html(io.StringIO(resp.text))


def _parse_periodo(texto: str) -> pd.Timestamp | None:
    """Convierte una celda de período ('Enero 2026', '02-2024', etc.) a fecha.

    Devuelve None si el texto no matchea un patrón mes-año reconocible
    (p. ej. líneas tipo "a partir del 28/12/2023", que se resuelven aparte).

    Args:
        texto: Contenido de la celda de período.

    Returns:
        Timestamp del primer día del mes, o None si no se pudo parsear.
    """
    texto = texto.strip().lower()

    m = re.match(r"([a-záéíóú]+)\s+(\d{4})", texto)
    if m and m.group(1) in MESES:
        return pd.Timestamp(int(m.group(2)), MESES[m.group(1)], 1)

    m = re.match(r"(\d{1,2})\s*-\s*(\d{4})", texto)
    if m:
        return pd.Timestamp(int(m.group(2)), int(m.group(1)), 1)

    return None


def scrape_biodiesel() -> pd.DataFrame:
    """Extrae la serie mensual de precio único de biodiesel (desde 2018).

    Returns:
        DataFrame con columnas [fecha, precio_ars_tn], ordenado y sin
        duplicados de mes (se conserva el último valor vigente del mes).
    """
    tablas = _fetch_tables(BIODIESEL_URL)
    # La primera tabla de la página es "Precios de Biodiesel desde Enero 2018"
    df = tablas[0].copy()
    df.columns = ["periodo", "precio"]
    df["fecha"] = df["periodo"].apply(_parse_periodo)
    df = df.dropna(subset=["fecha"])
    df["precio"] = (
        df["precio"].astype(str).str.replace(".", "", regex=False).astype(float)
    )
    df = df.sort_values("fecha").drop_duplicates(subset="fecha", keep="last")
    return df[["fecha", "precio"]].rename(columns={"precio": "precio_ars_tn"})


def scrape_bioetanol() -> pd.DataFrame:
    """Extrae la serie mensual de bioetanol caña/maíz (desde 2018).

    Returns:
        DataFrame con columnas [fecha, precio_cana_ars_l, precio_maiz_ars_l].
    """
    tablas = _fetch_tables(BIOETANOL_URL)
    df = tablas[0].copy()
    df.columns = ["periodo", "cana", "maiz"]
    df["fecha"] = df["periodo"].apply(_parse_periodo)
    df = df.dropna(subset=["fecha"])
    for col in ("cana", "maiz"):
        df[col] = (
            df[col].astype(str).str.extract(r"([\d.,]+)")[0]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .astype(float)
        )
    df = df.sort_values("fecha").drop_duplicates(subset="fecha", keep="last")
    return df.rename(columns={"cana": "precio_cana_ars_l", "maiz": "precio_maiz_ars_l"})[
        ["fecha", "precio_cana_ars_l", "precio_maiz_ars_l"]
    ]


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)

    biodiesel = scrape_biodiesel()
    biodiesel.to_csv(out_dir / "biodiesel_precios.csv", index=False)
    print(f"biodiesel_precios.csv actualizado: {len(biodiesel)} filas")

    bioetanol = scrape_bioetanol()
    bioetanol.to_csv(out_dir / "bioetanol_precios.csv", index=False)
    print(f"bioetanol_precios.csv actualizado: {len(bioetanol)} filas")


if __name__ == "__main__":
    main()
