"""
Recrea la batch deployment con un environment custom que evita el conflicto
de bokeh del environment auto-generado por AutoML.

Pasos:
  1. Borra el online endpoint fallido (si existe).
  2. Crea un Environment custom con dependencias mínimas para sklearn + MLflow.
  3. Crea una nueva BatchDeployment usando ese environment + scoring script local.
  4. La establece como default del endpoint.
"""

import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.constants import BatchDeploymentOutputAction
from azure.ai.ml.entities import (
    BatchDeployment,
    BatchRetrySettings,
    CodeConfiguration,
    Environment,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ["AZURE_RESOURCE_GROUP"]
WORKSPACE_NAME = os.environ["AZURE_WORKSPACE_NAME"]

ENDPOINT_NAME = "modelo-voting-ensemble-batch"
NEW_DEPLOYMENT_NAME = "salud-ensemble-mini-env"
MODEL_NAME = "Modelo_Salud_Ensemble_V1"
MODEL_VERSION = "1"
COMPUTE_NAME = "cluster-aml-salud"

ROOT = Path(__file__).parent
ENV_FILE = ROOT / "deployment_files" / "environment" / "conda.yaml"
CODE_DIR = ROOT / "deployment_files" / "code"


def construir_cliente() -> MLClient:
    return MLClient(
        DefaultAzureCredential(),
        SUBSCRIPTION_ID,
        RESOURCE_GROUP,
        WORKSPACE_NAME,
    )


def borrar_realtime(ml: MLClient) -> None:
    print("=== 1. Borrar real-time endpoint fallido (si existe) ===")
    try:
        ep = ml.online_endpoints.get("modelo-voting-ensemble-realtime")
        print(f"Encontrado real-time '{ep.name}' (state={ep.provisioning_state}). Borrando...")
        ml.online_endpoints.begin_delete("modelo-voting-ensemble-realtime").result()
        print("Real-time borrado.")
    except Exception as e:
        print(f"No se borra (no existe o ya borrado): {e.__class__.__name__}")


def crear_environment(ml: MLClient) -> Environment:
    print("=== 2. Crear environment custom ===")
    env = Environment(
        name="env-batch-salud-mini",
        description="Env minimo para inferencia MLflow sklearn (sin AutoML stack)",
        conda_file=str(ENV_FILE),
        image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04",
    )
    env = ml.environments.create_or_update(env)
    print(f"Env creado: {env.name}:{env.version}")
    return env


def crear_deployment(ml: MLClient, env: Environment) -> None:
    print("=== 3. Crear nueva batch deployment ===")
    deployment = BatchDeployment(
        name=NEW_DEPLOYMENT_NAME,
        endpoint_name=ENDPOINT_NAME,
        model=f"azureml:{MODEL_NAME}:{MODEL_VERSION}",
        environment=f"azureml:{env.name}:{env.version}",
        code_configuration=CodeConfiguration(
            code=str(CODE_DIR),
            scoring_script="score.py",
        ),
        compute=COMPUTE_NAME,
        instance_count=1,
        max_concurrency_per_instance=1,
        mini_batch_size=10,
        output_action=BatchDeploymentOutputAction.APPEND_ROW,
        output_file_name="predictions.csv",
        retry_settings=BatchRetrySettings(max_retries=3, timeout=300),
        logging_level="info",
    )
    print(f"Lanzando creación de '{NEW_DEPLOYMENT_NAME}' (esto demora ~10-15 min mientras builda la imagen)...")
    ml.batch_deployments.begin_create_or_update(deployment).result()
    print(f"Deployment '{NEW_DEPLOYMENT_NAME}' creada.")


def hacer_default(ml: MLClient) -> None:
    print("=== 4. Establecer como default ===")
    ep = ml.batch_endpoints.get(ENDPOINT_NAME)
    ep.defaults.deployment_name = NEW_DEPLOYMENT_NAME
    ml.batch_endpoints.begin_create_or_update(ep).result()
    print(f"'{NEW_DEPLOYMENT_NAME}' es ahora el default de '{ENDPOINT_NAME}'.")


def main() -> None:
    ml = construir_cliente()
    borrar_realtime(ml)
    env = crear_environment(ml)
    crear_deployment(ml, env)
    hacer_default(ml)
    print()
    print("Listo. Ahora ejecuta:")
    print("  python consumir_batch_endpoint.py")


if __name__ == "__main__":
    main()
