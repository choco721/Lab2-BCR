"""Arma la tabla comparativa de los modelos de referencia (integración 21/22/23).

Junta las métricas de los baselines (SCRUM-22) y del X-13 (SCRUM-23), que ya
salen del mismo protocolo de evaluación (SCRUM-21), en un único
`results/comparacion.csv`. Es el "piso" a superar por los modelos propios.

Requiere que existan results/metricas_baselines.csv y results/x13.csv.

Uso: python scripts/comparacion.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    res = Path(__file__).resolve().parent.parent / "results"
    partes = []
    for nombre in ("metricas_baselines.csv", "x13.csv"):
        p = res / nombre
        if not p.exists():
            raise FileNotFoundError(f"Falta {p}; corré primero el protocolo y el X-13.")
        partes.append(pd.read_csv(p))

    comp = pd.concat(partes, ignore_index=True)
    comp.to_csv(res / "comparacion.csv", index=False)

    # resumen legible: MAPE y acierto de signo por serie y modelo
    mape = comp.pivot_table(index="serie", columns="modelo", values="MAPE_pct").round(1)
    signo = comp.pivot_table(index="serie", columns="modelo", values="acierto_signo_pct").round(0)
    orden = [c for c in ["ultimo_valor", "estacional", "x13"] if c in mape.columns]
    mape, signo = mape[orden], signo[orden]

    print("MAPE % por serie y modelo (menor = mejor):")
    print(mape.to_string())
    print("\nMejor modelo por serie:")
    for s in mape.index:
        best = mape.loc[s].idxmin()
        print(f"  {s:16s}: {best}  ({mape.loc[s, best]:.1f}%)")
    print("\nAcierto de signo % (mayor = mejor):")
    print(signo.to_string())
    print(f"\nGuardado en {res / 'comparacion.csv'}")


if __name__ == "__main__":
    main()
