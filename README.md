# MLOps · Azure ML Studio — Designer Custom + despliegue de endpoints

Material de la Sesión 5: pipeline de **Designer en modo Custom** con componentes propios,
registro del modelo y despliegue como **real-time endpoint**, más el consumo del mejor modelo de
**Automated ML** (VotingEnsemble). Dataset: `insurance.csv` (predicción de `charges`).

| Carpeta | Qué contiene |
|---|---|
| `Componente-Designer-Preprocesador-Seguros/` | Primer componente custom + data asset MLTable |
| `Pipeline-Custom-Entrenamiento/` | Componentes Dividir → Entrenar → Puntuar → Evaluar y los pipelines |
| `Consumo-Modelo-Endpoint-Voting-Ensemble-Batch/` | Scripts y app Streamlit para consumir los endpoints (real-time y batch) |
| `MLOps - Slides Sesion 5/` | Slides HTML paso a paso (abrir `Registrar-Modelo-Custom.html` en el navegador) |
| `.claude/skills/` | Skills de Claude Code usadas en la sesión |

## Antes de empezar

1. Reemplaza `<tu-workspace>` y `<tu-resource-group>` por los de **tu** workspace de Azure ML.
2. En la carpeta de consumo: `cp .env.example .env` y rellena tus valores. **El `.env` nunca se sube.**
3. Borra los endpoints al terminar la práctica: cada deployment `Standard_D2as_v4` cuesta ~$0.15/h aunque nadie lo llame.

## Skills de Claude Code (`.claude/skills/`)

Al abrir esta carpeta con Claude Code se cargan solas. También puedes llamarlas con `/nombre`:

- **`azureml-data-mltable-v2`** — registrar datos como MLTable (v2) para que los lean los componentes custom.
- **`azureml-designer-custom-component`** — crear, registrar y probar componentes para Designer Custom (incluye plantilla y ejemplo completo).
- **`azureml-online-endpoint-deploy`** — desplegar un modelo MLflow como real-time endpoint, vigilar el despliegue en segundo plano y escribir URL / key en el `.env` sin mostrarla. Incluye la tabla de errores reales (`No module named 'azureml'`, cuota, tráfico en 0 %…).
