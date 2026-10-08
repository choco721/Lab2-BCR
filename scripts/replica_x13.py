"""Réplica del modelo X-13ARIMA-SEATS que usa BCR (SCRUM-23).

Corre X-13 sobre las series de producción con validación walk-forward a un
mes, usando el **protocolo de evaluación del equipo** (`evaluacion.py`,
SCRUM-21) para que las métricas sean idénticas a las de los baselines y los
modelos propios. Guarda el resumen en `results/x13.csv` y el detalle mensual
en `results/predicciones_x13.csv`.

El X-13 se expone como un modelo con interfaz `fit(serie)` / `predict()`, la
misma que usan los baselines, así que entra directo en `evaluar_modelo`.

El binario de X-13 lo provee el paquete `x13binary` (pip); no hace falta
instalar el programa del Census ni el Win X-13.

Transformación por serie (igual que BCR): biodiesel log (multiplicativo),
bioetanol nivel (aditivo).

Requiere: pip install x13binary pandas numpy
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from x13binary import find_x13_bin

sys.path.append(str(Path(__file__).resolve().parent))
from evaluacion import evaluar_modelo  # protocolo del equipo (SCRUM-21)

X13 = find_x13_bin()

# Ventana de test acordada con el equipo (últimos 12 meses).
INICIO_TEST = "2025-09"
FIN_TEST = "2026-08"


def _escribir_spec(serie: pd.Series, carpeta: Path, log: bool) -> Path:
    """Escribe un archivo .spc de X-13 para la serie dada.

    Args:
        serie: Serie mensual (valores crudos positivos), índice de fechas.
        carpeta: Directorio donde dejar el .spc.
        log: Si True, aplica transformación logarítmica (multiplicativo).

    Returns:
        Ruta base al .spc (sin extensión, como la espera X-13).
    """
    vals = np.asarray(serie.values, dtype=float)
    primero = serie.index[0]
    start = f"{primero.year}.{primero.month}"
    chunks = [vals[i:i + 10] for i in range(0, len(vals), 10)]
    datalines = "\n".join("    " + " ".join(f"{v:.3f}" for v in c) for c in chunks)
    transform = "transform{ function=log }" if log else "transform{ function=none }"
    spec = (
        f"series{{\n  start={start}\n  period=12\n  data=(\n{datalines}\n  )\n}}\n"
        f"{transform}\n"
        "automdl{}\n"
        "forecast{ maxlead=1 save=(fct) }\n"
    )
    base = carpeta / "run"
    base.with_suffix(".spc").write_text(spec)
    return base


def pronostico_x13(serie: pd.Series, log: bool) -> float:
    """Corre X-13 sobre la serie y devuelve el pronóstico a un mes.

    Args:
        serie: Historia disponible (hasta el mes t-1).
        log: Si la serie se transforma en log.

    Returns:
        Pronóstico de producción para el mes t, en unidades originales.
    """
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        base = _escribir_spec(serie, carpeta, log)
        subprocess.run([X13, str(base)], cwd=carpeta,
                       capture_output=True, text=True, timeout=60)
        fct = base.with_suffix(".fct")
        if not fct.exists():
            return np.nan
        lineas = [l for l in fct.read_text().splitlines() if l and l[0].isdigit()]
        if not lineas:
            return np.nan
        return float(lineas[-1].split("\t")[1].strip().replace("E", "e"))


class ModeloX13:
    """X-13 con interfaz fit/predict, compatible con el protocolo de evaluación.

    Args:
        log: Transformación logarítmica (biodiesel True, bioetanol False).
    """

    def __init__(self, log: bool) -> None:
        self.log = log
        self._serie: pd.Series | None = None

    def fit(self, serie: pd.Series) -> "ModeloX13":
        """Guarda la historia disponible (el ajuste real lo hace X-13 al predecir)."""
        self._serie = serie
        return self

    def predict(self) -> float:
        """Pronostica el mes siguiente corriendo X-13 sobre la historia guardada."""
        return pronostico_x13(self._serie, self.log)


def main() -> None:
    raiz = Path(__file__).resolve().parent.parent
    bd = pd.read_csv(raiz / "data/produccion_biodiesel.csv", parse_dates=["fecha"]).set_index("fecha")
    be = pd.read_csv(raiz / "data/produccion_bioetanol.csv", parse_dates=["fecha"]).set_index("fecha")

    # (serie, inicio de entrenamiento del protocolo, transformación log)
    objetivo = {
        "biodiesel":       (bd["produccion_tn"],        "2008-01", True),
        "bioetanol_total": (be["produccion_total_m3"],  "2013-01", False),
        "bioetanol_maiz":  (be["produccion_maiz_m3"],   "2012-09", False),
        "bioetanol_cana":  (be["produccion_cana_m3"],   "2013-01", False),
    }

    detalles, resumenes = [], []
    for nombre, (serie, inicio, log) in objetivo.items():
        detalle, resumen = evaluar_modelo(
            serie=serie,
            crear_modelo=lambda log=log: ModeloX13(log=log),
            inicio_entrenamiento=inicio,
            inicio_test=INICIO_TEST,
            fin_test=FIN_TEST,
            nombre_serie=nombre,
            nombre_modelo="x13",
        )
        detalles.append(detalle)
        resumenes.append(resumen)
        r = resumen.iloc[0]
        print(f"{nombre:16s}: MAPE={r['MAPE_pct']:.1f}%  signo={r['acierto_signo_pct']:.0f}%  "
              f"(test {r['inicio_test']}→{r['fin_test']}, {int(r['meses_evaluados'])} meses)")

    out = raiz / "results"
    out.mkdir(exist_ok=True)
    pd.concat(resumenes, ignore_index=True).to_csv(out / "x13.csv", index=False)
    pd.concat(detalles, ignore_index=True).to_csv(out / "predicciones_x13.csv", index=False)
    print(f"\nGuardado en {out}/x13.csv y predicciones_x13.csv")


if __name__ == "__main__":
    main()
