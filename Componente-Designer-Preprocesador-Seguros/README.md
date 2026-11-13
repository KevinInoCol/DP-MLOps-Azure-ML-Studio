# Componente Custom para Azure ML Designer — Preprocesador de Seguros

One-hot encoding (`sex`, `smoker`, `region`) + normalización (`age`, `bmi`, `children`, zscore o minmax).
Probado de punta a punta en `<tu-workspace>` (job `cool_carpet_xlhl6kvnxm`, Completed).

## Archivos

| Archivo | Qué es |
|---|---|
| `component.yml` | Definición del componente (entrada `mltable`, salidas `mltable` + `uri_folder`) |
| `conda.yml` | Entorno propio: pandas, scikit-learn, mltable, azureml-fsspec, `setuptools<81` |
| `src/preprocesar.py` | Lógica del preprocesamiento |
| `data/` | `insurance.csv` como MLTable v2 + YAML para registrarlo |
| `pipeline_prueba.yml` | Pipeline para probar el componente desde la CLI |

## Comandos

```bash
W="-w <tu-workspace> -g <tu-resource-group>"

# 1. Registrar el dataset como MLTable v2 (una sola vez)
az ml data create -f data/data_asset.yml $W

# 2. Registrar el componente (sube "version" en component.yml en cada cambio)
az ml component create -f component.yml $W

# 3. Probarlo sin abrir el Designer
az ml job create -f pipeline_prueba.yml $W
```

## Usarlo en el Designer (Custom)

1. Designer → **Create a new pipeline using custom components**.
2. Pestaña **Data** → arrastra `plan-de-salud-mltable`.
3. Pestaña **Component** → arrastra **Preprocesador de Seguros**, conecta el dataset a `datos_entrada`.
4. Elige `metodo_normalizacion`, asigna el cluster en *Settings* y **Submit**.
5. La salida `datos_salida` es MLTable: se puede conectar a otro componente con entrada `mltable`.

## Errores que encontramos (y por qué fallaban los intentos anteriores)

| Error | Causa | Solución |
|---|---|---|
| El dataset no conecta / no se lee | El dataset subido por la UI como *Tabular* es **v1** (tipo `mltable` legacy), no `uri_file` | Entrada tipo `mltable` |
| `Specified environment AzureML-ai-ml-automl not found` | Ese entorno no existe en el registry `azureml` | Entorno propio con `conda.yml` |
| `V1 tabular dataset can only be consumed as type mltable and direct mode` | Los datasets v1 exigen `mode: direct` | — (ver siguiente fila) |
| `No module named 'pkg_resources'` | setuptools ≥ 81 eliminó `pkg_resources` y `mltable` aún lo usa | `setuptools<81` en `conda.yml` |
| `Data asset service returned invalid MLTable yaml` | Azure no logra convertir el dataset Tabular **v1** a MLTable | **No usar datasets v1**: registrar el CSV como **MLTable v2** (`data/`) |

> Regla práctica: para componentes Custom, registra los datos en formato v2
> (en la UI: *Create data asset* → tipo **Table (mltable)** o **File (uri_file)**), nunca el *Tabular* antiguo.
