---
name: azureml-designer-custom-component
description: Framework para crear componentes Custom (command components) del Designer de Azure Machine Learning — el modo Custom, no el Classic prebuilt. Crea un proyecto con estructura fija (config.env, entorno/ compartido, src/utils.py, componentes/, pipelines/) y herramientas que generan un componente desde una línea de comando (tools/nuevo_componente.py), lo prueban en local con un CSV (tools/probar_local.py), lo registran con versionado automático (tools/registrar.sh --nueva-version) y ejecutan pipelines descargando el log del paso que falla (tools/ejecutar_pipeline.sh). Incluye ejemplo completo probado (equivalente Custom de Edit Metadata → Split Data → Train Model → Score Model → Evaluate Model) y la tabla de errores reales (dataset Tabular v1, "invalid MLTable yaml", "pkg_resources", "fields ... are immutable, try specifying a new version", entorno curado inexistente). Use when the user or a student asks to "crear un componente para el Designer", "bloque custom en Azure ML Studio", "framework de componentes", "pasar mi pipeline Classic a Custom", "no encuentro Split Data en Custom", "command component", "az ml component create", "mi componente falla en el Designer", or types /azureml-designer-custom-component.
---

# Framework de componentes Custom — Azure ML Designer

Probado el 2026-11-12 en `<tu-workspace>`: proyecto creado con `crear_proyecto.sh`, 5 componentes generados con `nuevo_componente.py`, cadena completa con `probar_local.py`, registro con `registrar.sh --nueva-version` y pipeline con `ejecutar_pipeline.sh`.

Datos: los componentes Custom necesitan **data assets v2** → usar la skill `azureml-data-mltable-v2`.

## Qué es el modo Custom (para explicarlo)

El Custom **no trae** Split Data, Train Model, Score Model ni Evaluate Model (el registry `azureml` solo tiene AutoML, RAI, evaluación). Es un lienzo para conectar **componentes propios**: código Python versionado, reutilizable desde Designer, CLI, SDK o CI/CD, con modelos en MLflow. Se construyen una vez y luego se arrastran.

## Estructura del framework (`framework/plantilla/`)

```
proyecto/
├── config.env            ← AML_WORKSPACE, AML_RESOURCE_GROUP, AML_COMPUTE, AML_ENVIRONMENT
├── entorno/              ← conda.yml + environment.yml: UN entorno para todos (setuptools<81, mltable, mlflow)
├── src/utils.py          ← leer_tabla, escribir_tabla, guardar_modelo, cargar_modelo, preparar_carpeta
├── src/<bloque>.py       ← lógica de cada bloque (generado con TODO)
├── componentes/<bloque>.yml
├── pipelines/*.yml
├── data/                 ← CSV para pruebas locales
└── tools/                ← nuevo_componente.py · probar_local.py · registrar.sh · ejecutar_pipeline.sh
```

Convenciones: `code: ../src` (todos comparten utils), `environment: azureml:<env>@latest`, tablas como `mltable` (CSV + archivo `MLTable`), modelos como `mlflow_model`, archivos sueltos como `uri_folder`. Nunca `uri_file` en salidas.

## Flujo

```bash
FW=~/.claude/skills/azureml-designer-custom-component/framework
$FW/crear_proyecto.sh <destino> [--con-ejemplo]     # --con-ejemplo copia los 5 bloques de seguros
cd <destino> && editar config.env                    # descubrir valores con az ml workspace/compute list

python tools/nuevo_componente.py --nombre <snake> --titulo "<Visible (Equivalente Classic)>" \
  --descripcion "..." --entrada datos:mltable --salida resultado:mltable \
  --parametro umbral:number=0.5 [--opciones metodo=a,b]
#  → completar el bloque TODO de src/<snake>.py

uv run tools/probar_local.py componentes/<snake>.yml --entrada datos=data/x.csv [--param k=v]
#  → salidas en salidas_locales/<snake>/<salida>/ (se encadenan como --entrada del siguiente)

tools/registrar.sh --entorno               # 1ª vez o si cambia entorno/conda.yml (añadir --nueva-version)
tools/registrar.sh [--nueva-version] [componentes/<snake>.yml]
tools/ejecutar_pipeline.sh pipelines/<p>.yml   # espera, lista pasos y muestra el log del que falle
```

Al ayudar a un alumno: generar con la herramienta (no escribir YAML a mano), escribir solo la lógica dentro del TODO, probar en local antes de registrar, y poner el equivalente Classic en el título para que lo encuentre en el Designer.

## Ejemplo incluido (`framework/ejemplos/seguros/`)

| Classic | Componente | Entradas → Salidas |
|---|---|---|
| Edit Metadata | `preprocesar_seguros` | mltable → mltable (one-hot + zscore/minmax) |
| Split Data | `dividir_datos` | mltable → 2× mltable |
| Boosted Decision Tree Regression + Train Model | `entrenar_regresor` | mltable → mlflow_model (no existe tipo "untrained model") |
| Score Model | `puntuar_modelo` | mlflow_model + mltable → mltable con "Scored Labels" |
| Evaluate Model | `evaluar_regresion` | mltable → uri_folder (`metricas.json`) + `mlflow.log_metrics` |

Resultado en insurance.csv: R² ≈ 0.866, MAE ≈ 2,490, RMSE ≈ 4,438.

## Errores reales y solución

| Síntoma | Causa | Solución |
|---|---|---|
| Dataset no conecta / no se lee | Dataset Tabular **v1** (UI "Tabular"); `v1_type: tabular` | Registrar como MLTable v2 (`azureml-data-mltable-v2`) |
| `V1 tabular dataset can only be consumed as type mltable and direct mode` | Dataset v1 | Igual que arriba (con `mode: direct` luego falla la conversión) |
| `Data asset service returned invalid MLTable yaml` | Azure no convierte el Tabular v1 | Igual que arriba |
| `No module named 'pkg_resources'` | setuptools ≥ 81; `azureml-dataprep` lo importa | `setuptools<81` en `entorno/conda.yml` (ya incluido) |
| `Specified environment AzureML-ai-ml-automl not found` | Entorno curado inexistente | Entorno propio del framework |
| `fields "environment, code, command" are immutable, try specifying a new version` | Se cambió código con la misma versión | `tools/registrar.sh --nueva-version` |
| Bloque no aparece en el buscador del Designer | Índice de búsqueda con retraso | Recargar / esperar; o abrir un job que lo use y **Clone**; o Assets → Components |
| "Port(s) X are required to be connected" | Falta un cable (p. ej. `datos_prueba` → Puntuar) | Conectar y elegir cluster en Settings |
| `mlflow.save_model` falla: carpeta existe | La salida ya existe | `guardar_modelo()` de utils (temporal + copytree) |

## Notas técnicas

- macOS trae bash 3.2: con `set -u`, expandir arrays vacíos rompe (`${arr[@]+"${arr[@]}"}`).
- La 1ª corrida con un entorno nuevo construye la imagen (~10–15 min); después, segundos.
- Log de un paso: `az ml job download -n <hijo> --all` → `user_logs/std_log.txt` (error de tu código) o `logs/azureml/stderrlogs.txt` (error de plataforma).
- No mezclar bloques Classic y Custom en un mismo pipeline.
