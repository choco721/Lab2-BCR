"""Réplica del modelo X-13ARIMA-SEATS que usa BCR (SCRUM-23).

Corre X-13 sobre las series de producción con validación walk-forward a un
mes y guarda las métricas en results/x13.csv, para comparar contra los
baselines y los modelos propios con el mismo protocolo.

El binario de X-13 lo provee el paquete `x13binary` (pip), así que no hace
falta instalar el programa del Census ni el Win X-13.

Transformación por serie (igual que BCR):
    - biodiesel: logarítmica (esquema multiplicativo)
    - bioetanol: ninguna (esquema aditivo)

Requiere: pip install x13binary statsmodels pandas numpy
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from x13binary import find_x13_bin

X13 = find_x13_bin()


def _escribir_spec(serie: pd.Series, carpeta: Path, log: bool) -> Path:
    """Escribe un archivo .spc de X-13 para la serie dada.

    Args:
        serie: Serie mensual (valores crudos, positivos).
        carpeta: Directorio donde dejar el .spc.
        log: Si True, aplica transformación logarítmica (multiplicativo).

    Returns:
        Ruta al .spc (sin extensión, como lo espera X-13).
    """
    vals = serie.values
    start = f"{serie.index[0].year}.{serie.index[0].month}"
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
        serie: Historia disponible (serie hasta el mes t-1).
        log: Si la serie se transforma en log.

    Returns:
        Pronóstico de producción para el mes t (en unidades originales).
    """
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        base = _escribir_spec(serie, carpeta, log)
        subprocess.run(
            [X13, str(base)], cwd=carpeta,
            capture_output=True, text=True, timeout=60,
        )
        fct = base.with_suffix(".fct")
        if not fct.exists():
            return np.nan
        lineas = [l for l in fct.read_text().splitlines() if l and l[0].isdigit()]
        if not lineas:
            return np.nan
        # columnas: date  forecast  lowerci  upperci
        valor = lineas[-1].split("\t")[1].strip()
        return float(valor.replace("E", "e"))


def walk_forward_x13(serie: pd.Series, n_test: int, log: bool) -> pd.DataFrame:
    """Walk-forward a un mes con X-13 sobre los últimos n_test meses.

    Args:
        serie: Serie mensual completa (ordenada, sin ceros).
        n_test: Meses finales de test.
        log: Transformación logarítmica.

    Returns:
        DataFrame con columnas 'real' y 'pred', indexado por fecha.
    """
    filas = []
    for i in range(len(serie) - n_test, len(serie)):
        hist = serie.iloc[:i]
        filas.append(
            {"fecha": serie.index[i], "real": float(serie.iloc[i]),
             "pred": pronostico_x13(hist, log)}
        )
    return pd.DataFrame(filas).set_index("fecha")


def metricas(real: pd.Series, pred: pd.Series) -> dict[str, float]:
    """Calcula MAE, RMSE y MAPE entre valores reales y predichos.

    Nota: se replican acá para que el script sea autosuficiente y no
    dependa del protocolo de evaluación del equipo (SCRUM-21). Cuando
    ese módulo esté en el repo, conviene unificar y usar sus funciones.

    Args:
        real: Valores observados.
        pred: Valores predichos, alineados con ``real``.

    Returns:
        Diccionario con las claves ``mae``, ``rmse`` y ``mape`` (en %).
    """
    err = real - pred
    mae = float(err.abs().mean())
    rmse = float(np.sqrt((err ** 2).mean()))
    mape = float((err.abs() / real.abs()).mean() * 100)
    return {"mae": mae, "rmse": rmse, "mape": mape}


def acierto_signo(df: pd.DataFrame) -> float:
    """Porcentaje de meses donde la predicción acierta la dirección mensual.

    Compara el signo del cambio real mes a mes contra el signo del cambio
    predicho (ambos respecto del valor real del mes anterior).

    Args:
        df: DataFrame con columnas ``real`` y ``pred`` indexado por fecha.

    Returns:
        Porcentaje de aciertos de signo (0-100).
    """
    real_prev = df["real"].shift(1)
    dir_real = np.sign(df["real"] - real_prev)
    dir_pred = np.sign(df["pred"] - real_prev)
    ok = (dir_real == dir_pred)[real_prev.notna()]
    return float(ok.mean() * 100)


def main() -> None:
    raiz = Path(__file__).resolve().parent.parent
    bd = pd.read_csv(raiz / "data/produccion_biodiesel.csv", parse_dates=["fecha"]).set_index("fecha")
    be = pd.read_csv(raiz / "data/produccion_bioetanol.csv", parse_dates=["fecha"]).set_index("fecha")

    # (serie, transform log)
    objetivo = {
        "biodiesel":       (bd["produccion_tn"], True),
        "bioetanol_total": (be["produccion_total_m3"], False),
        "bioetanol_maiz":  (be["produccion_maiz_m3"], False),
        "bioetanol_cana":  (be["produccion_cana_m3"], False),
    }

    N_TEST = 12
    filas = []
    for nom, (serie, log) in objetivo.items():
        serie = serie[serie > 0]
        df = walk_forward_x13(serie, N_TEST, log)
        m = metricas(df["real"], df["pred"])
        filas.append({
            "serie": nom, "modelo": "x13", "n_test": N_TEST,
            "mae": m["mae"], "rmse": m["rmse"], "mape": m["mape"],
            "acierto_signo": acierto_signo(df),
        })
        print(f"{nom:16s}: MAPE={m['mape']:.1f}%  signo={acierto_signo(df):.0f}%")

    out = raiz / "results"
    out.mkdir(exist_ok=True)
    pd.DataFrame(filas).to_csv(out / "x13.csv", index=False)
    print(f"\nGuardado en {out / 'x13.csv'}")


if __name__ == "__main__":
    main()
