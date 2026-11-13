# Consumo de un modelo VotingEnsemble en Azure Machine Learning

Modelo de regresión entrenado con **Azure AutoML** sobre el dataset
`insurance.csv` (n=1338), que estima el costo anual de un plan de salud
(`charges`) a partir de `age`, `sex`, `bmi`, `children`, `smoker` y `region`.

El mejor modelo del experimento fue un **VotingEnsemble**
(Normalized RMSE = 0.07706), servido en un **managed online endpoint**.

DataPath — MLOps, Módulo 3 Sesión 6.

## Interfaz

```bash
streamlit run app_streamlit.py
```

Dos modos: predicción individual con formulario, y predicción por lote desde un
CSV con descarga de resultados. La app no reimplementa la llamada HTTP: importa
`invocar()` de `consumir_realtime_endpoint.py`.

## Scripts

| Archivo | Qué hace |
| --- | --- |
| `app_streamlit.py` | Interfaz web sobre el online endpoint |
| `consumir_realtime_endpoint.py` | POST al online endpoint, respuesta inmediata (~50-200 ms) |
| `consumir_batch_endpoint.py` | Batch endpoint vía SDK v2: crea un job y lo monitorea |
| `consumir_rest_api.py` | Batch endpoint vía REST API, sin SDK |
| `recrear_batch_deployment.py` | Recrea la batch deployment con un environment custom |

Los batch endpoints **no aceptan payloads inline**: siempre operan sobre
archivos en un datastore o Data Asset registrado.

## Formato del payload

El scoring script auto-generado por AutoML espera el orient `split` de pandas:

```json
{
  "input_data": {
    "columns": ["age", "sex", "bmi", "children", "smoker", "region"],
    "index": [0],
    "data": [[45, "female", 25.175, 2, "no", "northeast"]]
  }
}
```

## Setup

```bash
conda create -n MLOps-AZURE-Consumo-Endpoint python=3.11 -y
conda activate MLOps-AZURE-Consumo-Endpoint
pip install -r requirements.txt

cp .env.example .env   # y rellenar
```

La key del endpoint se obtiene sin pasar por el portal:

```bash
az ml online-endpoint get-credentials -n <endpoint> \
  -g <resource-group> -w <workspace> --query primaryKey -o tsv
```

## Requisito previo del despliegue (que no está en el wizard)

Los **managed online endpoints** exigen el resource provider
`Microsoft.PolicyInsights` registrado a nivel de suscripción. Si falta, el
despliegue falla y el portal muestra `Error details: --` vacío:

```bash
az provider register --namespace Microsoft.PolicyInsights
```

Espera un par de minutos a que propague antes de lanzar el deploy, o verás un
`ResourceOperationFailure` transitorio en el primer intento.

El mensaje real de un despliegue fallido se saca así, no desde el portal:

```bash
az ml online-endpoint show -n <endpoint> -g <rg> -w <ws> \
  --query "properties.AzureAsyncOperationUri" -o tsv
az rest --method get --url "<esa-uri>"
```

## Costos

Un online endpoint cobra la VM aunque no reciba tráfico
(`Standard_D2as_v4` ≈ $0.15/hr). Al terminar:

```bash
az ml online-endpoint delete -n <endpoint> -g <rg> -w <ws> --yes
```
