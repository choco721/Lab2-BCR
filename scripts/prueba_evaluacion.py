from pathlib import Path

import pandas as pd

from evaluacion import evaluar_modelo, UltimoValor, Estacional


RAIZ = Path(__file__).resolve().parents[1]

biodiesel = pd.read_csv(
    RAIZ / "data" / "produccion_biodiesel.csv",
    parse_dates=["fecha"],
).set_index("fecha")

bioetanol = pd.read_csv(
    RAIZ / "data" / "produccion_bioetanol.csv",
    parse_dates=["fecha"],
).set_index("fecha")

series = {
    "biodiesel": (biodiesel["produccion_tn"], "2008-01"),
    "bioetanol_total": (bioetanol["produccion_total_m3"], "2013-01"),
    "bioetanol_maiz": (bioetanol["produccion_maiz_m3"], "2012-09"),
    "bioetanol_cana": (bioetanol["produccion_cana_m3"], "2013-01"),
}

modelos = {
    "ultimo_valor": UltimoValor,
    "estacional": Estacional,
}

detalles = []
resumenes = []

for nombre_serie, (serie, inicio) in series.items():
    for nombre_modelo, crear_modelo in modelos.items():
        detalle, resumen = evaluar_modelo(
            serie=serie,
            crear_modelo=crear_modelo,
            inicio_entrenamiento=inicio,
            nombre_serie=nombre_serie,
            nombre_modelo=nombre_modelo,
        )

        # Comprobar cobertura y predicciones de los modelos simples.
        assert len(detalle) == 32
        assert resumen.iloc[0]["evaluacion_completa"], detalle[
            detalle["estado"] != "ok"
        ].to_string()

        for fila in detalle.itertuples():
            mes = pd.Timestamp(fila.fecha)
            rezago = 1 if nombre_modelo == "ultimo_valor" else 12
            esperado = serie.loc[mes - pd.DateOffset(months=rezago)]
            assert abs(fila.prediccion - esperado) < 1e-8

        detalles.append(detalle)
        resumenes.append(resumen)

# Caso pequeño con métricas calculables a mano.
ejemplo = pd.Series(
    [10.0, 12.0, 12.0],
    index=pd.date_range("2023-01-01", periods=3, freq="MS"),
)

_, prueba = evaluar_modelo(
    ejemplo,
    UltimoValor,
    inicio_entrenamiento="2023-01",
    inicio_test="2023-02",
    fin_test="2023-03",
)

metricas = prueba.iloc[0]
assert abs(metricas["MAE"] - 1.0) < 1e-8
assert abs(metricas["RMSE"] - 2**0.5) < 1e-8
assert abs(metricas["MAPE_pct"] - 100 / 12) < 1e-8
assert metricas["acierto_signo_pct"] == 50.0

salida = RAIZ / "resultados"
salida.mkdir(exist_ok=True)

pd.concat(detalles, ignore_index=True).to_csv(
    salida / "predicciones_baselines.csv", index=False
)

tabla = pd.concat(resumenes, ignore_index=True)
tabla.to_csv(salida / "metricas_baselines.csv", index=False)

print(tabla.to_string(index=False))
print("\nPruebas completadas. Resultados guardados en resultados/.")