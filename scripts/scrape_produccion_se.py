"""Descarga y parsea la producción mensual de biocombustibles de la Secretaría de Energía.

Fuente: planilla oficial "estadisticas_biocombustibles" (la misma que usa BCR
como insumo de su modelo X-13 para el IACA):
    http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/
    mercado_hidrocarburos/bio/estadisticas_biocombustibles.xls

Genera dos CSV mensuales en data/:
    - produccion_biodiesel.csv: produccion_tn, ventas_corte_tn,
      otras_ventas_mdo_interno_tn, exportaciones_tn, provisorio
    - produccion_bioetanol.csv: produccion_total_m3, ventas_total_m3,
      produccion_maiz_m3, ventas_maiz_m3, produccion_cana_m3, ventas_cana_m3,
      provisorio

La columna ``provisorio`` marca los meses que la Secretaría publica con (*)
("dato provisorio"), que todavía pueden ser revisados.

Uso:
    python scripts/scrape_produccion_se.py               # descarga de la web
    python scripts/scrape_produccion_se.py ruta/al.xlsx  # usa un archivo local

Requiere: pip install requests pandas openpyxl xlrd
"""

from __future__ import annotations

import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

URL = (
    "http://www.energia.gob.ar/contenidos/archivos/Reorganizacion/"
    "informacion_del_mercado/mercado_hidrocarburos/bio/estadisticas_biocombustibles.xls"
)

MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

COLS_BIODIESEL = [
    "produccion_tn",
    "ventas_corte_tn",
    "otras_ventas_mdo_interno_tn",
    "exportaciones_tn",
]
COLS_BIOETANOL = [
    "produccion_total_m3",
    "ventas_total_m3",
    "produccion_maiz_m3",
    "ventas_maiz_m3",
    "produccion_cana_m3",
    "ventas_cana_m3",
]


def _leer_bytes(origen: str | None) -> bytes:
    """Obtiene el contenido crudo de la planilla, de la web o de un archivo local.

    Args:
        origen: Ruta a un archivo local, o None para descargar de la web.

    Returns:
        Los bytes del archivo Excel.
    """
    if origen is not None:
        return Path(origen).read_bytes()
    resp = requests.get(URL, timeout=60)
    resp.raise_for_status()
    return resp.content


def _engine_para(contenido: bytes) -> str:
    """Detecta el formato real del Excel por su firma de bytes.

    La URL termina en .xls, pero el archivo puede venir como .xlsx; la
    extensión no es confiable, así que se mira la firma del contenido.

    Args:
        contenido: Bytes del archivo.

    Returns:
        'openpyxl' para .xlsx (zip) o 'xlrd' para .xls legacy (OLE).
    """
    if contenido[:2] == b"PK":
        return "openpyxl"
    if contenido[:4] == b"\xd0\xcf\x11\xe0":
        return "xlrd"
    raise ValueError("Formato de archivo no reconocido (no es .xls ni .xlsx).")


def _parsear_periodo(valor: object) -> tuple[pd.Timestamp | None, bool]:
    """Convierte una celda de período a fecha mensual.

    La planilla mezcla dos formatos en la misma columna: fechas reales
    (meses consolidados) y textos tipo 'ago-25 (*)' (meses provisorios).
    Las filas anuales (enteros como 2008) y los textos de nota se descartan.

    Args:
        valor: Contenido de la celda de la columna PERÍODO.

    Returns:
        Tupla (fecha del primer día del mes o None, es_provisorio).
    """
    if isinstance(valor, (datetime, pd.Timestamp)):
        return pd.Timestamp(valor).to_period("M").to_timestamp(), False
    if isinstance(valor, str):
        texto = valor.strip().lower()
        provisorio = "(*)" in texto
        base = texto.replace("(*)", "").strip()
        partes = base.split("-")
        if len(partes) == 2 and partes[0] in MESES and partes[1].isdigit():
            anio = 2000 + int(partes[1])
            return pd.Timestamp(anio, MESES[partes[0]], 1), provisorio
    return None, False


def _parsear_hoja(contenido: bytes, engine: str, hoja: str, columnas: list[str]) -> pd.DataFrame:
    """Extrae la serie mensual de una hoja RESUMEN de la planilla.

    Args:
        contenido: Bytes del archivo Excel.
        engine: Motor de pandas para leerlo.
        hoja: Nombre de la hoja a leer.
        columnas: Nombres a asignar a las columnas de datos, en orden.

    Returns:
        DataFrame mensual con columnas [fecha, *columnas, provisorio].
    """
    crudo = pd.read_excel(BytesIO(contenido), sheet_name=hoja, header=None, engine=engine)

    filas = []
    for _, fila in crudo.iterrows():
        fecha, provisorio = _parsear_periodo(fila.iloc[0])
        if fecha is None:
            continue
        valores = pd.to_numeric(fila.iloc[1 : 1 + len(columnas)], errors="coerce").tolist()
        filas.append([fecha, *valores, provisorio])

    df = pd.DataFrame(filas, columns=["fecha", *columnas, "provisorio"])
    df = df.drop_duplicates(subset="fecha", keep="last").sort_values("fecha")
    return df.reset_index(drop=True)


def _chequear_meses(df: pd.DataFrame, nombre: str) -> None:
    """Avisa si faltan meses en la serie (gaps en el índice mensual).

    Si la Secretaría cambia la abreviatura de un mes (p. ej. 'sept' en vez de
    'sep'), esa fila se descarta al parsear y queda un hueco silencioso. Este
    chequeo lo detecta comparando contra el rango mensual completo esperado.

    Args:
        df: DataFrame con columna 'fecha' mensual.
        nombre: Nombre de la serie, para el mensaje.
    """
    esperado = pd.date_range(df["fecha"].min(), df["fecha"].max(), freq="MS")
    faltan = esperado.difference(pd.to_datetime(df["fecha"]))
    if len(faltan):
        print(f"  ¡ATENCIÓN! {nombre}: faltan {len(faltan)} meses → "
              f"{[d.strftime('%Y-%m') for d in faltan]}")


def main() -> None:
    origen = sys.argv[1] if len(sys.argv) > 1 else None
    contenido = _leer_bytes(origen)
    engine = _engine_para(contenido)

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    # copia fechada de cada descarga, para el análisis de revisiones (SCRUM-20)
    hist_dir = out_dir / "historico"
    hist_dir.mkdir(exist_ok=True)
    hoy = pd.Timestamp.today().strftime("%Y-%m-%d")

    biodiesel = _parsear_hoja(contenido, engine, "RESUMEN BIODIESEL", COLS_BIODIESEL)
    bioetanol = _parsear_hoja(contenido, engine, "RESUMEN BIOETANOL", COLS_BIOETANOL)

    for nombre, df in (("biodiesel", biodiesel), ("bioetanol", bioetanol)):
        _chequear_meses(df, nombre)
        df.to_csv(out_dir / f"produccion_{nombre}.csv", index=False)
        # snapshot con la fecha de descarga (no pisa; sirve para comparar revisiones)
        df.to_csv(hist_dir / f"produccion_{nombre}_{hoy}.csv", index=False)
        print(
            f"produccion_{nombre}.csv: {len(df)} meses "
            f"({df['fecha'].min():%Y-%m} a {df['fecha'].max():%Y-%m}), "
            f"{int(df['provisorio'].sum())} provisorios  "
            f"[copia: historico/produccion_{nombre}_{hoy}.csv]"
        )


if __name__ == "__main__":
    main()
