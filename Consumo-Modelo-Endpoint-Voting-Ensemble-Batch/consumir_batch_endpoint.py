"""
Consumo de un Batch Endpoint en Azure Machine Learning usando el SDK v2.

Uso:
  python consumir_batch_endpoint.py             # crea un job nuevo y lo monitorea
  python consumir_batch_endpoint.py <job_name>  # monitorea un job ya existente
"""

import os
import sys
from pathlib import Path

from azure.ai.ml import Input, MLClient
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ["AZURE_RESOURCE_GROUP"]
WORKSPACE_NAME = os.environ["AZURE_WORKSPACE_NAME"]
ENDPOINT_NAME = os.environ.get("BATCH_ENDPOINT_NAME", "modelo-voting-ensemble-batch")
DEPLOYMENT_NAME = os.environ.get("BATCH_DEPLOYMENT_NAME")

ARCHIVO_ENTRADA = Path(__file__).parent / "datos" / "datos_entrada.csv"
CARPETA_SALIDA = Path(__file__).parent / "predicciones"


def construir_cliente() -> MLClient:
    credencial = DefaultAzureCredential()
    return MLClient(
        credential=credencial,
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        workspace_name=WORKSPACE_NAME,
    )


def studio_url(job_name: str) -> str:
    return (
        f"https://ml.azure.com/runs/{job_name}"
        f"?wsid=/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.MachineLearningServices/workspaces/{WORKSPACE_NAME}"
    )


def invocar_endpoint(ml_client: MLClient) -> str:
    entrada = Input(type=AssetTypes.URI_FILE, path=str(ARCHIVO_ENTRADA))

    kwargs = {"endpoint_name": ENDPOINT_NAME, "input": entrada}
    if DEPLOYMENT_NAME:
        kwargs["deployment_name"] = DEPLOYMENT_NAME

    print(f"Invocando endpoint '{ENDPOINT_NAME}' con archivo: {ARCHIVO_ENTRADA.name}")
    job = ml_client.batch_endpoints.invoke(**kwargs)
    print(f"Job creado: {job.name}")
    print(f"Studio URL: {studio_url(job.name)}")
    return job.name


def esperar_y_descargar(ml_client: MLClient, job_name: str) -> None:
    print(f"Monitoreando job: {job_name}")
    print(f"Studio URL: {studio_url(job_name)}")
    print("Esperando a que el job termine (esto puede tardar varios minutos)...")
    ml_client.jobs.stream(job_name)

    estado = ml_client.jobs.get(job_name).status
    print(f"Estado final del job: {estado}")

    if estado != "Completed":
        raise RuntimeError(f"El job no terminó correctamente: {estado}")

    CARPETA_SALIDA.mkdir(exist_ok=True)
    print(f"Descargando predicciones a: {CARPETA_SALIDA}")
    ml_client.jobs.download(
        name=job_name,
        download_path=str(CARPETA_SALIDA),
        output_name="score",
    )
    print("Predicciones descargadas. Revisa la carpeta 'predicciones/named-outputs/score/'.")


def main() -> None:
    ml_client = construir_cliente()
    if len(sys.argv) > 1:
        job_name = sys.argv[1]
        print(f"Reanudando monitoreo de job existente: {job_name}")
    else:
        job_name = invocar_endpoint(ml_client)
    esperar_y_descargar(ml_client, job_name)


if __name__ == "__main__":
    main()
