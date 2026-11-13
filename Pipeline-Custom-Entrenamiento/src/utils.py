"""
Funciones compartidas por los componentes: leer y escribir datasets MLTable.
"""

import glob
import os

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
    """Lee una entrada mltable (carpeta con archivo MLTable) o una carpeta/archivo CSV."""
    if os.path.exists(os.path.join(ruta, "MLTable")):
        import mltable

        return mltable.load(ruta).to_pandas_dataframe()
    if os.path.isfile(ruta):
        return pd.read_csv(ruta)
    csvs = glob.glob(os.path.join(ruta, "**", "*.csv"), recursive=True)
    if not csvs:
        raise FileNotFoundError(f"No se encontró MLTable ni CSV en {ruta}")
    return pd.read_csv(csvs[0])


def escribir_tabla(df, carpeta, archivo="datos.csv"):
    """Guarda el DataFrame como carpeta MLTable (CSV + archivo MLTable)."""
    os.makedirs(carpeta, exist_ok=True)
    df.to_csv(os.path.join(carpeta, archivo), index=False)
    with open(os.path.join(carpeta, "MLTable"), "w") as f:
        f.write(MLTABLE_YAML.format(archivo=archivo))
