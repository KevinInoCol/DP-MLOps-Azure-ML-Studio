"""
Utilidades comunes a todos los componentes del framework.

- leer_tabla / escribir_tabla : datasets tipo mltable (carpeta con CSV + archivo MLTable)
- guardar_modelo / cargar_modelo : modelos tipo mlflow_model
- preparar_carpeta : salidas tipo uri_folder
"""

import glob
import os
import shutil
import tempfile

import pandas as pd

MLTABLE_YAML = (
    "paths:\n"
    "  - file: ./{archivo}\n"
    "transformations:\n"
    "  - read_delimited:\n"
    "      delimiter: ','\n"
    "      header: all_files_same_headers\n"
    "      encoding: utf8\n"
)


def leer_tabla(ruta):
    """Lee una entrada mltable, una carpeta con CSV o un archivo CSV y devuelve un DataFrame."""
    if os.path.isfile(ruta):
        return pd.read_csv(ruta)
    if os.path.exists(os.path.join(ruta, "MLTable")):
        try:
            import mltable

            return mltable.load(ruta).to_pandas_dataframe()
        except ImportError:
            pass  # en local sin mltable: se lee el CSV de la carpeta
    csvs = sorted(glob.glob(os.path.join(ruta, "**", "*.csv"), recursive=True))
    if not csvs:
        raise FileNotFoundError(f"No se encontró MLTable ni CSV en {ruta}")
    return pd.read_csv(csvs[0])


def escribir_tabla(df, carpeta, archivo="datos.csv"):
    """Guarda un DataFrame como salida mltable (CSV + archivo MLTable) para poder encadenarla."""
    os.makedirs(carpeta, exist_ok=True)
    df.to_csv(os.path.join(carpeta, archivo), index=False)
    with open(os.path.join(carpeta, "MLTable"), "w") as f:
        f.write(MLTABLE_YAML.format(archivo=archivo))


def guardar_modelo(modelo, carpeta, ejemplo_entrada=None):
    """Guarda un modelo scikit-learn en formato MLflow (salida tipo mlflow_model)."""
    import mlflow.sklearn

    # save_model exige una carpeta inexistente: se guarda en temporal y se copia.
    tmp = os.path.join(tempfile.mkdtemp(), "modelo")
    mlflow.sklearn.save_model(modelo, tmp, input_example=ejemplo_entrada)
    shutil.copytree(tmp, carpeta, dirs_exist_ok=True)


def cargar_modelo(carpeta):
    """Carga un modelo scikit-learn guardado en formato MLflow (entrada tipo mlflow_model)."""
    import mlflow.sklearn

    return mlflow.sklearn.load_model(carpeta)


def preparar_carpeta(carpeta):
    """Crea la carpeta de una salida uri_folder y la devuelve."""
    os.makedirs(carpeta, exist_ok=True)
    return carpeta
