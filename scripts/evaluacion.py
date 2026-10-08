## Integración futura de variables externas

#La primera versión evalúa modelos usando únicamente producción histórica.

#Más adelante se incorporarán variables externas mediante una interfaz común: fit(y_train, X_train=None) y predict(X_next=None).

#Antes de incorporarlas se acordarán nombres, unidades, fechas de disponibilidad, rezagos y tratamiento de faltantes. Cada predicción utilizará únicamente información disponible al momento de emitirla.

import numpy as np
import pandas as pd


class UltimoValor:
    """Predice el mismo valor que el mes anterior."""

    def fit(self, serie):
        self.valor = float(serie.iloc[-1])
        return self

    def predict(self):
        return self.valor


class Estacional:
    """Predice el mismo valor que el mismo mes del año anterior."""

    def fit(self, serie):
        if len(serie) < 12:
            raise ValueError("Se necesitan al menos 12 meses.")
        self.valor = float(serie.iloc[-12])
        return self

    def predict(self):
        return self.valor


def evaluar_modelo(
    serie,
    crear_modelo,
    inicio_entrenamiento,
    inicio_test="2023-01",
    fin_test="2025-08",
    nombre_serie="serie",
    nombre_modelo="modelo",
):
    """
    Evalúa un modelo mediante walk-forward a un mes.

    Parámetros
    ----------
    serie : pd.Series
        Producción mensual con fechas como índice.
    crear_modelo : callable
        Devuelve un modelo nuevo que implementa fit(serie) y predict().
    inicio_entrenamiento : str
        Primer mes de entrenamiento, por ejemplo "2008-01".
    inicio_test, fin_test : str
        Primer y último mes del período de evaluación.

    Devuelve
    --------
    detalle : pd.DataFrame
        Predicciones, valores reales y fallos por mes.
    resumen : pd.DataFrame
        Métricas y cobertura de la evaluación.

    Las predicciones deben estar en las unidades originales.
    """
    if not isinstance(serie, pd.Series):
        raise TypeError("serie debe ser una Series de pandas.")

    serie = serie.copy()

    if isinstance(serie.index, pd.PeriodIndex):
        serie.index = serie.index.asfreq("M")
    else:
        serie.index = pd.to_datetime(serie.index).to_period("M")

    if serie.index.isna().any():
        raise ValueError("Hay fechas faltantes.")

    if serie.index.has_duplicates:
        raise ValueError("Hay meses duplicados.")

    serie = serie.sort_index()

    inicio = pd.Period(inicio_entrenamiento, freq="M")
    primero = pd.Period(inicio_test, freq="M")
    ultimo = pd.Period(fin_test, freq="M")

    if not inicio < primero <= ultimo:
        raise ValueError(
            "El entrenamiento debe empezar antes del test "
            "y el final del test no puede preceder a su inicio."
        )

    meses = pd.period_range(inicio, ultimo, freq="M")
    faltantes = meses.difference(serie.index)

    if len(faltantes):
        raise ValueError(f"Faltan meses: {list(faltantes)}")

    serie = pd.to_numeric(
        serie.reindex(meses), errors="raise"
    ).astype(float)

    if not np.isfinite(serie.to_numpy()).all():
        raise ValueError("Hay valores faltantes o infinitos.")

    if (serie < 0).any():
        raise ValueError("La producción real no puede ser negativa.")

    registros = []

    for mes in pd.period_range(primero, ultimo, freq="M"):
        entrenamiento = serie.loc[serie.index < mes].copy()
        real = float(serie.loc[mes])
        anterior = float(entrenamiento.iloc[-1])

        registro = {
            "serie": nombre_serie,
            "modelo": nombre_modelo,
            "fecha": mes.to_timestamp(),
            "real": real,
            "real_anterior": anterior,
            "prediccion": np.nan,
            "error": np.nan,
            "acierto_signo": np.nan,
            "estado": "fallo",
            "motivo": "",
        }

        try:
            modelo = crear_modelo()
            modelo.fit(entrenamiento)

            salida = np.asarray(modelo.predict(), dtype=float)

            if salida.size != 1:
                raise ValueError(
                    "El modelo debe devolver una sola predicción."
                )

            prediccion = float(salida.reshape(-1)[0])

            if not np.isfinite(prediccion) or prediccion < 0:
                raise ValueError(
                    "La predicción debe ser finita y no negativa."
                )

            signo_predicho = np.sign(prediccion - anterior)
            signo_real = np.sign(real - anterior)

            registro.update({
                "prediccion": prediccion,
                "error": prediccion - real,
                "acierto_signo": int(signo_predicho == signo_real),
                "estado": "ok",
            })

        except Exception as exc:
            registro["motivo"] = f"{type(exc).__name__}: {exc}"

        registros.append(registro)

    detalle = pd.DataFrame(registros)

    validos = detalle.loc[detalle["estado"] == "ok"]
    para_mape = validos.loc[validos["real"] != 0]

    resumen = {
        "serie": nombre_serie,
        "modelo": nombre_modelo,
        "inicio_test": str(primero),
        "fin_test": str(ultimo),
        "meses_previstos": len(detalle),
        "meses_evaluados": len(validos),
        "cobertura_pct": 100 * len(validos) / len(detalle),
        "evaluacion_completa": len(validos) == len(detalle),
        "MAE": validos["error"].abs().mean(),
        "RMSE": np.sqrt((validos["error"] ** 2).mean()),
        "MAPE_pct": 100 * (
            para_mape["error"].abs() / para_mape["real"].abs()
        ).mean(),
        "meses_validos_MAPE": len(para_mape),
        "ceros_excluidos_MAPE": int((validos["real"] == 0).sum()),
        "acierto_signo_pct": 100 * validos["acierto_signo"].mean(),
    }

    return detalle, pd.DataFrame([resumen])