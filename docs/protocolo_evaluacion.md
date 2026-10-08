# Protocolo de evaluación de modelos

Estado: propuesta inicial pendiente de revisión del equipo y la BCR.

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

Se propone enero de 2023 a agosto de 2025, inclusive: 32 meses.

El período permite evaluar el comportamiento reciente durante más de
dos ciclos anuales y conservar varios años anteriores para entrenar.

Agosto de 2025 es el último mes marcado como no provisorio en ambas
bases revisadas del repositorio. Se debe confirmar cómo se genera esta
etiqueta y si coincide con el criterio de consolidación de la BCR.

Los meses posteriores quedan fuera del test principal por estar
marcados como provisorios.

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

Todos los modelos de una misma serie utilizarán el mismo inicio.

## 5. Validación walk-forward

Se utilizará una ventana de entrenamiento expansiva y un horizonte
de predicción de un mes.

Para cada mes del test:

1. Entrenar con observaciones hasta el mes anterior.
2. Predecir la producción del mes evaluado.
3. Guardar la predicción y el valor real.
4. Incorporar el valor real al entrenamiento para la siguiente iteración.

Ejemplo: para predecir enero de 2023 se entrena hasta diciembre de 2022.
Para predecir febrero de 2023 se entrena hasta enero de 2023.

Este procedimiento supone que el dato del mes anterior está disponible.
Se debe confirmar este supuesto según el retraso de publicación de la
Secretaría de Energía y el momento de predicción de la BCR.

## 6. Prevención del uso de información futura

- Las transformaciones y el preprocesamiento se ajustan solo con
  los datos de entrenamiento de cada iteración.
- Las variables externas deben estar disponibles en la fecha de predicción.
- No se utilizarán automáticamente valores del mes que se está prediciendo.
- La selección de parámetros se realizará con datos anteriores al test
  o con validación temporal dentro del entrenamiento de cada iteración.
- No se utilizará el test completo para elegir parámetros.

Si solo se dispone de la historia revisada actual, se documentará que
la evaluación no reproduce las versiones disponibles en cada fecha.

## 7. Escala de evaluación

Las predicciones se evaluarán en las unidades originales de producción.

Si un modelo utiliza logaritmos o diferencias, deberá reconstruir el nivel
antes de calcular las métricas.

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
Menor es mejor.

Los meses con producción real igual a cero se excluirán únicamente
del MAPE. Se informará la cantidad de meses excluidos.
Si todos los valores reales son cero, el MAPE se informará como no definido.
Los valores cercanos a cero pueden producir porcentajes muy elevados.

### Acierto de signo

Porcentaje de meses en que coincide la dirección de la variación
predicha y la real.

Ambas variaciones se calcularán respecto del mismo valor real del
mes anterior:

- Variación real: real del mes menos real del mes anterior.
- Variación predicha: predicción del mes menos real del mes anterior.

Se utilizarán tres categorías: sube, baja y sin cambio.
Solo la coincidencia de categorías contará como acierto.

Inicialmente se evaluará sobre producción original.
Queda pendiente confirmar si la BCR requiere producción desestacionalizada.

## 9. Datos faltantes y fallos

- Los datos faltantes no se reemplazarán automáticamente por cero.
- Se comprobará que haya una observación por mes, sin fechas duplicadas.
- Si falta un dato necesario, la evaluación deberá señalar el problema.
- Si un modelo falla, se registrará el mes y el motivo.
- Se informará la cobertura: meses predichos sobre meses previstos.
- No se presentará una evaluación incompleta como equivalente a una
  evaluación sobre los 32 meses.

## 10. Modelos simples para comprobar la función

- Último valor: predice el mismo valor que el mes anterior.
- Estacional: predice el mismo valor que el mismo mes del año anterior.

La función deberá admitir otros modelos mediante una interfaz común.

## 11. Resultados esperados

Una tabla mensual con:

- Serie.
- Modelo.
- Mes evaluado.
- Valor real.
- Predicción.
- Error, definido como predicción menos valor real.

Una tabla resumen con:

- Serie y modelo.
- Inicio y final del test.
- Cantidad de meses evaluados y cobertura.
- MAE.
- RMSE.
- MAPE y cantidad de meses válidos para calcularlo.
- Acierto de signo.

## 12. Pendientes de confirmación

- Acuerdo del equipo sobre el test y los inicios de entrenamiento.
- Criterio de consolidación y origen de la columna provisorio.
- Fecha de emisión de la predicción y retraso de publicación de los datos.
- Disponibilidad de las variables externas en cada fecha.
- Serie sobre la que se requiere medir el acierto de signo.
- Configuración de X-13 de la BCR y disponibilidad del archivo .spc.

## 13. Criterios de finalización

- Protocolo documentado.
- Función reutilizable en el repositorio.
- Función probada con un modelo simple.