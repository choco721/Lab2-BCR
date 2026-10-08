# Protocolo de evaluación de modelos

Estado: ventana de test acordada con el equipo. Pendiente de revisión
de los demás criterios y de las confirmaciones indicadas para la BCR.

## 1. Objetivo

Establecer un procedimiento común para comparar los modelos de predicción
de producción mensual de biocombustibles en igualdad de condiciones.

## 2. Variables objetivo

- Producción de biodiesel, en toneladas.
- Producción de bioetanol total, en metros cúbicos.
- Producción de bioetanol de maíz, en metros cúbicos.
- Producción de bioetanol de caña de azúcar, en metros cúbicos.

Las métricas se calcularán por separado para cada serie.

## 3. Período de test

Se utiliza septiembre de 2025 a agosto de 2026, inclusive: 12 meses.

Esta ventana fue acordada con el equipo para comparar los modelos simples
con la evaluación de X-13 ya realizada. Comprende un ciclo anual completo.

Los 12 meses están marcados como provisorios en los CSV utilizados.
Se incluyen por acuerdo del equipo y se conserva esta condición en los
resultados. Las métricas pueden cambiar si se revisan los datos reales.

Todos los modelos deben evaluarse sobre los mismos meses y la misma
versión de los datos. Una actualización de las fuentes requerirá volver
a evaluar todos los modelos incluidos en la comparación.

## 4. Inicio del entrenamiento

Se adoptan provisionalmente los inicios propuestos en
notebooks/eda_produccion.ipynb:

| Serie | Inicio |
|---|---|
| Biodiesel | Enero de 2008 |
| Bioetanol total | Enero de 2013 |
| Bioetanol de maíz | Septiembre de 2012 |
| Bioetanol de caña | Enero de 2013 |

Los cortes del bioetanol buscan excluir la etapa de arranque.
Para maíz, también se excluyen los ceros anteriores al inicio de producción.

Para la comparación final se verificará que todos los modelos de una
misma serie, incluido X-13, utilicen el mismo inicio de entrenamiento.
Cualquier diferencia deberá acordarse y documentarse.

## 5. Validación walk-forward

Se utiliza una ventana de entrenamiento expansiva y un horizonte
de predicción de un mes.

Para cada mes del test:

1. Crear y ajustar el modelo con observaciones hasta el mes anterior.
2. Predecir la producción del mes evaluado.
3. Guardar la predicción y el valor real.
4. Incorporar el valor real al entrenamiento de la siguiente iteración.

Primera predicción: septiembre de 2025, entrenando hasta agosto de 2025.
Última predicción: agosto de 2026, entrenando hasta julio de 2026.

El equipo confirmó que su evaluación de X-13 también realiza
12 predicciones a un mes, reajustando el modelo en cada iteración
con forecast maxlead=1.

Este backtest supone que el dato del mes anterior está disponible.
Se debe confirmar si este supuesto reproduce el retraso de publicación
de la Secretaría de Energía y el momento de predicción de la BCR.

## 6. Prevención del uso de información futura

- Las transformaciones y el preprocesamiento se ajustan solo con
  los datos de entrenamiento de cada iteración.
- La selección de parámetros se realiza con datos anteriores al test
  o con validación temporal dentro del entrenamiento de cada iteración.
- No se utiliza el test completo para elegir parámetros.
- Al incorporar variables externas, se respetarán sus fechas de disponibilidad.
- No se utilizarán automáticamente valores del mes que se está prediciendo.

La evaluación utiliza la historia contenida en los CSV actuales.
No reproduce necesariamente las versiones de los datos disponibles
en cada fecha histórica.

## 7. Escala de evaluación

Las predicciones se evalúan en las unidades originales de producción.

Si un modelo utiliza logaritmos o diferencias, debe reconstruir el nivel
antes de calcular las métricas.

La comparación con X-13 debe utilizar pronósticos de producción original
en las mismas unidades, no índices ni valores desestacionalizados.

## 8. Métricas

### MAE

Promedio de los errores absolutos.
Se expresa en toneladas o metros cúbicos. Menor es mejor.

### RMSE

Raíz del promedio de los errores al cuadrado.
Penaliza especialmente los errores grandes.
Se expresa en toneladas o metros cúbicos. Menor es mejor.

### MAPE

Promedio del error absoluto porcentual respecto del valor real.
Se informa en porcentaje. Menor es mejor.

Los meses con producción real igual a cero se excluyen únicamente
del MAPE. Se informa la cantidad de meses excluidos.

Si todos los valores reales evaluados son cero, el MAPE se informa
como no definido. Los valores cercanos a cero pueden producir
porcentajes muy elevados.

### Acierto de signo

Porcentaje de meses en que coincide la dirección de la variación
predicha y la real.

Ambas variaciones se calculan respecto del mismo valor real del
mes anterior:

- Variación real: real del mes menos real del mes anterior.
- Variación predicha: predicción del mes menos real del mes anterior.

Se utilizan tres categorías: sube, baja y sin cambio.
Solo la coincidencia de categorías cuenta como acierto.

El modelo último valor siempre predice sin cambio. Por eso su acierto
es cero cuando todos los meses reales presentan subas o bajas.
Puede acertar en meses cuya producción real no cambia.

Inicialmente se evalúa sobre producción original.
Queda pendiente confirmar si la BCR requiere también una evaluación
sobre producción desestacionalizada.

## 9. Datos faltantes y fallos

- Los datos faltantes no se reemplazan automáticamente por cero.
- Se comprueba que haya una observación por mes, sin fechas duplicadas.
- Si falta un dato necesario, la evaluación señala el problema.
- Las predicciones deben ser finitas y no negativas.
- Si un modelo falla, se registra el mes y el motivo.
- Se informa la cobertura: meses predichos sobre los 12 meses previstos.
- Las métricas de una evaluación incompleta se calculan sobre los meses
  exitosos y se identifican como parciales.
- No se compara directamente una evaluación parcial con otra completa.

## 10. Modelos simples para comprobar la función

- Último valor: predice el mismo valor que el mes anterior.
- Estacional: predice el mismo valor que el mismo mes del año anterior.

La interfaz actual requiere:

- fit(serie): recibe la producción histórica de entrenamiento.
- predict(): devuelve una única predicción en unidades originales.
- Una función o clase que cree un modelo nuevo para cada iteración.

Otros modelos podrán conectarse mediante adaptadores.

## 11. Archivos y resultados

- docs/protocolo_evaluacion.md: reglas de evaluación.
- scripts/evaluacion.py: función reutilizable y modelos simples.
- scripts/prueba_evaluacion.py: ejecución y comprobaciones.
- results/predicciones_baselines.csv: resultados mensuales.
- results/metricas_baselines.csv: métricas por serie y modelo.

Se utiliza results/ como carpeta común de resultados del equipo.

La tabla mensual incluye:

- Serie y modelo.
- Mes evaluado.
- Valor real y valor real del mes anterior.
- Predicción.
- Error, definido como predicción menos valor real.
- Acierto de signo.
- Estado de la predicción y motivo de fallo, si corresponde.
- Marca provisorio tomada de la fuente.

La tabla resumen incluye:

- Serie y modelo.
- Inicio y final del test.
- Meses previstos y evaluados.
- Cobertura y condición de evaluación completa.
- MAE y RMSE.
- MAPE, meses válidos y ceros excluidos.
- Acierto de signo.
- Cantidad de meses provisorios.

## 12. Pruebas realizadas

Se ejecutaron los dos modelos simples sobre las cuatro series,
con 12 meses por evaluación y cobertura del 100 %.

Se comprobaron:

- La cantidad de meses y la ausencia de fallos.
- Las predicciones contra los valores históricos correspondientes.
- Las cuatro métricas con un ejemplo pequeño calculable a mano.
- La presencia de la marca provisorio en cada mes evaluado.

Los 12 meses de cada evaluación están marcados como provisorios.
No hubo valores reales iguales a cero en el período evaluado.

## 13. Pendientes de confirmación

- Alinear con X-13 los inicios de entrenamiento y la versión de los datos.
- Confirmar el origen y significado de la columna provisorio.
- Confirmar la fecha de emisión de la predicción y el retraso de publicación.
- Confirmar la serie sobre la que la BCR requiere medir el acierto de signo.
- Obtener la configuración de X-13 de la BCR y su archivo .spc,
  si se requiere reproducir exactamente su procedimiento.

La ventana de test y el procedimiento walk-forward a un mes
ya fueron acordados con el equipo.

## 14. Integración futura de variables externas

La primera versión utiliza únicamente producción histórica.

Más adelante se incorporarán variables externas mediante una interfaz común:

- fit(y_train, X_train=None).
- predict(X_next=None).

Antes de incorporarlas se acordarán nombres, unidades, fechas de
disponibilidad, rezagos y tratamiento de faltantes.

Cada predicción utilizará únicamente información disponible al
momento de emitirla.

## 15. Criterios de finalización

- Protocolo documentado.
- Función reutilizable en el repositorio.
- Función probada con un modelo simple.