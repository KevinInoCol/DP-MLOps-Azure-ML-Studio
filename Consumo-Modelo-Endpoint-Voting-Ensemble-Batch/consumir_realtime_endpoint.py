"""
Consumo de un Online Endpoint (real-time) en Azure Machine Learning.

A diferencia del batch endpoint, aquí enviamos un POST HTTP con un payload JSON
y recibimos las predicciones inmediatamente (~50-200 ms).

Uso:
  python consumir_realtime_endpoint.py
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

ENDPOINT_URL = os.environ["ONLINE_ENDPOINT_URL"]
ENDPOINT_KEY = os.environ["ONLINE_ENDPOINT_KEY"]
DEPLOYMENT_NAME = os.environ.get("ONLINE_DEPLOYMENT_NAME")

ARCHIVO_ENTRADA = Path(__file__).parent / "datos" / "datos_entrada.csv"


def construir_payload() -> dict:
    """
    Convierte el CSV en el formato que espera el scoring script auto-generado
    de Azure ML: {"input_data": {"columns": [...], "index": [...], "data": [[...]]}}
    """
    df = pd.read_csv(ARCHIVO_ENTRADA)
    return {
        "input_data": {
            "columns": df.columns.tolist(),
            "index": df.index.tolist(),
            "data": df.values.tolist(),
        }
    }


def invocar(payload: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ENDPOINT_KEY}",
    }
    if DEPLOYMENT_NAME:
        headers["azureml-model-deployment"] = DEPLOYMENT_NAME

    inicio = time.perf_counter()
    respuesta = requests.post(
        ENDPOINT_URL, headers=headers, data=json.dumps(payload), timeout=30
    )
    duracion_ms = (time.perf_counter() - inicio) * 1000

    print(f"HTTP {respuesta.status_code} en {duracion_ms:.0f} ms")
    respuesta.raise_for_status()
    return respuesta.json()


def main() -> None:
    payload = construir_payload()
    print(f"Enviando {len(payload['input_data']['data'])} filas a {ENDPOINT_URL}")

    resultado = invocar(payload)

    print("\nPredicciones (charges estimados):")
    df = pd.read_csv(ARCHIVO_ENTRADA)
    df["prediction"] = resultado if isinstance(resultado, list) else resultado.get(
        "predictions", resultado
    )
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
