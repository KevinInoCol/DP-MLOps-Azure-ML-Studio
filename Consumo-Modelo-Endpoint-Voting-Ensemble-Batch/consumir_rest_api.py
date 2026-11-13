"""
Alternativa: consumir el batch endpoint usando la REST API directamente.

Útil cuando no se quiere depender del SDK (por ejemplo, desde un servicio
externo o desde un lenguaje distinto a Python). Aquí se hace en Python con
'requests' para mantenerlo simple.

El input debe ser un Data Asset registrado en el workspace o un URI accesible
(por ejemplo en un Datastore). Los batch endpoints NO aceptan payloads
inline — siempre trabajan sobre archivos en almacenamiento.
"""

import os
import time

import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

REST_ENDPOINT = os.environ["AZURE_ML_REST_ENDPOINT"]
DEPLOYMENT_NAME = os.environ.get("BATCH_DEPLOYMENT_NAME")

# URI del Data Asset o ruta en Datastore que contiene los datos a inferir.
# Ejemplo de URI de un Data Asset registrado:
#   azureml:nombre-data-asset:1
# Ejemplo de URI directo en un Datastore:
#   azureml://datastores/workspaceblobstore/paths/datos/datos_entrada.csv
INPUT_URI = os.environ.get(
    "BATCH_INPUT_URI",
    "azureml://datastores/workspaceblobstore/paths/datos/datos_entrada.csv",
)


def obtener_token() -> str:
    credencial = DefaultAzureCredential()
    token = credencial.get_token("https://ml.azure.com/.default")
    return token.token


def lanzar_job(token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if DEPLOYMENT_NAME:
        headers["azureml-model-deployment"] = DEPLOYMENT_NAME

    payload = {
        "properties": {
            "InputData": {
                "mnistinput": {
                    "JobInputType": "UriFile",
                    "Uri": INPUT_URI,
                }
            }
        }
    }

    print(f"POST {REST_ENDPOINT}")
    respuesta = requests.post(REST_ENDPOINT, headers=headers, json=payload, timeout=60)
    respuesta.raise_for_status()
    job = respuesta.json()
    print(f"Job creado: {job.get('name')}")
    return job


def consultar_estado(token: str, job: dict) -> str:
    url_estado = job["properties"]["statusLocationUri"]
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        respuesta = requests.get(url_estado, headers=headers, timeout=30)
        respuesta.raise_for_status()
        estado = respuesta.json().get("status", "Unknown")
        print(f"  estado: {estado}")
        if estado in {"Completed", "Failed", "Canceled"}:
            return estado
        time.sleep(15)


def main() -> None:
    token = obtener_token()
    job = lanzar_job(token)
    estado_final = consultar_estado(token, job)
    print(f"Estado final: {estado_final}")
    print(
        "Para descargar los resultados, abre el Job en Azure ML Studio o usa "
        "'consumir_batch_endpoint.py' (más sencillo)."
    )


if __name__ == "__main__":
    main()
