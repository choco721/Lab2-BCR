"""
Modelos de referencia (baselines) para la producción de biocombustibles.

- Naive: la predicción es el valor del mes anterior.
- Naive estacional: la predicción es el valor del mismo mes del año anterior.

Ambos se evalúan con el protocolo de docs/protocolo_evaluacion.md
(walk-forward a un mes, test 2025-09 a 2026-08) para las cuatro series
del protocolo: biodiesel, bioetanol total, bioetanol de maíz y bioetanol
de caña.

Uso, desde la raíz del proyecto:

    python scripts/baselines.py

Salida: results/baselines.csv
"""
from pathlib import Path

import pandas as pd

from evaluacion import Estacional, UltimoValor, evaluar_modelo

RAIZ = Path(__file__).resolve().parents[1]
INICIO_TEST = "2025-09"
FIN_TEST = "2026-08"

# serie: (archivo, columna, unidad, inicio de entrenamiento según protocolo)
SERIES = {
    "biodiesel": ("produccion_biodiesel.csv", "produccion_tn", "tn", "2008-01"),
    "bioetanol_total": ("produccion_bioetanol.csv", "produccion_total_m3", "m3", "2013-01"),
    "bioetanol_maiz": ("produccion_bioetanol.csv", "produccion_maiz_m3", "m3", "2012-09"),
    "bioetanol_cana": ("produccion_bioetanol.csv", "produccion_cana_m3", "m3", "2013-01"),
}

MODELOS = {
    "naive": UltimoValor,
    "naive_estacional": Estacional,
}


def main():
    filas = []

    for nombre_serie, (archivo, columna, unidad, inicio) in SERIES.items():
        datos = pd.read_csv(
            RAIZ / "data" / archivo, parse_dates=["fecha"]
        ).set_index("fecha")

        for nombre_modelo, crear_modelo in MODELOS.items():
            _, resumen = evaluar_modelo(
                serie=datos[columna],
                crear_modelo=crear_modelo,
                inicio_entrenamiento=inicio,
                inicio_test=INICIO_TEST,
                fin_test=FIN_TEST,
                nombre_serie=nombre_serie,
                nombre_modelo=nombre_modelo,
            )
            r = resumen.iloc[0]

            if not r["evaluacion_completa"]:
                raise RuntimeError(
                    f"Evaluación incompleta: {nombre_serie} / {nombre_modelo}"
                )

            filas.append({
                "serie": nombre_serie,
                "modelo": nombre_modelo,
                "unidad": unidad,
                "inicio_test": r["inicio_test"],
                "fin_test": r["fin_test"],
                "n_test": int(r["meses_evaluados"]),
                "MAPE_pct": round(r["MAPE_pct"], 2),
                "RMSE": round(r["RMSE"], 2),
                "MAE": round(r["MAE"], 2),
                "acierto_signo_pct": round(r["acierto_signo_pct"], 2),
            })

    tabla = pd.DataFrame(filas)

    salida = RAIZ / "results"
    salida.mkdir(exist_ok=True)
    tabla.to_csv(salida / "baselines.csv", index=False)

    print(tabla.to_string(index=False))
    print(f"\nGuardado en {salida / 'baselines.csv'}")


if __name__ == "__main__":
    main()
