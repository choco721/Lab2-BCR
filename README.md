# Lab 2 · BCR — Predicción de producción de biocombustibles

Proyecto del **Laboratorio de Consultoría de Datos 2** (UCA Rosario) junto a la
**Bolsa de Comercio de Rosario (BCR)**.

## Contexto

La BCR publica mensualmente el **IACA** (Índice de Actividad de la Cadena
Agropecuaria). Una de sus componentes es la producción de biodiesel y
bioetanol, cuyo dato oficial lo informa la **Secretaría de Energía** con
retraso. Para publicar a tiempo, la BCR **estima** ese dato con un modelo
estadístico (X-13ARIMA-SEATS, de la familia SARIMA).

El objetivo del proyecto es **mejorar esa estimación aplicando modelos de
machine learning** a la predicción de series de tiempo. El target es la
**producción mensual** (toneladas de biodiesel, m³ de bioetanol), no el
precio.

## Estructura del repositorio

```
BCR/
├── data/           # series mensuales en CSV (target + variables externas)
├── notebooks/      # análisis exploratorio y modelado
├── scripts/        # scrapers de cada fuente
└── README.md
```

## Fuentes de datos

| Archivo | Contenido | Fuente | Rango |
|---|---|---|---|
| `produccion_biodiesel.csv` | Producción, ventas y exportaciones de biodiesel (tn) — **target** | Secretaría de Energía | 2008→ |
| `produccion_bioetanol.csv` | Producción y ventas de bioetanol total, maíz y caña (m³) — **target** | Secretaría de Energía | 2009→ |
| `soja_maiz_cac_mensual.csv` | Precio de pizarra de soja y maíz | Cámara Arbitral de Cereales (BCR) | 2018→ |
| `tipo_cambio_mensual.csv` | Tipo de cambio oficial USD/ARS | API del BCRA | 2018→ |
| `biodiesel_precios.csv` | Precio regulado del biodiesel | Secretaría de Energía | 2018→ |
| `bioetanol_precios.csv` | Precio regulado del bioetanol (caña y maíz) | Secretaría de Energía | 2018→ |

Los precios regulados son **variables externas candidatas**; se decide si
entran al modelo en el análisis de variables (Etapa 3).

## Requisitos

```bash
pip install pandas numpy openpyxl xlrd requests beautifulsoup4 matplotlib statsmodels jupyter
```

## Cómo actualizar los datos

Cada script descarga su fuente y regenera el CSV correspondiente en `data/`.
Correr desde la carpeta raíz del proyecto:

```bash
python scripts/scrape_produccion_se.py     # producción (target)
python scripts/scrape_cac_soja_maiz.py     # soja y maíz
python scripts/scrape_tipo_cambio.py       # tipo de cambio
python scripts/scrape_biocombustibles.py   # precios regulados
```

`scrape_produccion_se.py` también acepta la ruta a un `.xlsx` local como
argumento, por si la descarga automática falla:

```bash
python scripts/scrape_produccion_se.py ruta/al/estadisticas_biocombustibles.xlsx
```

## Notebooks

- `notebooks/eda_produccion.ipynb` — análisis exploratorio del target:
  tendencia, estacionalidad, estacionariedad, outliers y propuesta de
  transformación por serie.

## Estado del proyecto

- [x] **Etapa 1** — Entendimiento del problema y del modelo actual de la BCR.
- [x] **Etapa 2** — Recolección de datos (target + variables externas).
- [~] **Etapa 3** — Análisis exploratorio (EDA de producción hecho).
- [ ] **Etapa 4** — Modelado (baselines, réplica de X-13, SARIMAX, ML, LSTM).

## Equipo

*Chocobares Juan Cruz*

*Formenti Agustín*

*Morenico Andrés*

*Romero María Florencia*

*Ortíz Victoria*

