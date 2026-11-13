"""
Preprocesador del dataset de seguros médicos para Azure ML Designer (Custom).

Entrada : dataset tipo mltable (p. ej. el Tabular "plan-de-salud" subido por la UI)
          o una carpeta con un CSV (fallback).
Salidas : - datos_salida     -> carpeta MLTable (datos_procesados.csv + MLTable)
          - reporte          -> carpeta con reporte.json
"""

import argparse
import glob
import json
import os
from datetime import datetime

import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

COLUMNAS_CATEGORICAS = ["sex", "smoker", "region"]
COLUMNAS_NUMERICAS = ["age", "bmi", "children"]
NOMBRE_CSV = "datos_procesados.csv"


def cargar_dataset(ruta):
    """Lee la entrada como MLTable; si no hay archivo MLTable, busca un CSV."""
    print(f"📂 Entrada: {ruta}")
    if os.path.isdir(ruta):
        print(f"   Contenido: {os.listdir(ruta)}")

    if os.path.exists(os.path.join(ruta, "MLTable")) or ruta.startswith("azureml://"):
        import mltable

        df = mltable.load(ruta).to_pandas_dataframe()
        print("✅ Leído con mltable")
        return df

    if os.path.isfile(ruta):
        return pd.read_csv(ruta)

    csvs = glob.glob(os.path.join(ruta, "**", "*.csv"), recursive=True)
    if not csvs:
        raise FileNotFoundError(f"No se encontró MLTable ni CSV en {ruta}")
    print(f"✅ Leído CSV: {csvs[0]}")
    return pd.read_csv(csvs[0])


def escribir_mltable(df, carpeta):
    """Guarda el CSV y un archivo MLTable para que la salida sea encadenable."""
    os.makedirs(carpeta, exist_ok=True)
    df.to_csv(os.path.join(carpeta, NOMBRE_CSV), index=False)
    with open(os.path.join(carpeta, "MLTable"), "w") as f:
        f.write(
            "paths:\n"
            f"  - file: ./{NOMBRE_CSV}\n"
            "transformations:\n"
            "  - read_delimited:\n"
            "      delimiter: ','\n"
            "      header: all_files_same_headers\n"
            "      encoding: utf8\n"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos_entrada", required=True)
    parser.add_argument("--metodo_normalizacion", default="zscore", choices=["zscore", "minmax"])
    parser.add_argument("--datos_salida", required=True)
    parser.add_argument("--reporte", required=True)
    args = parser.parse_args()

    df = cargar_dataset(args.datos_entrada)
    print(f"📋 Shape original: {df.shape} | Columnas: {list(df.columns)}")
    reporte = {
        "timestamp": datetime.now().isoformat(),
        "metodo_normalizacion": args.metodo_normalizacion,
        "filas_originales": len(df),
        "columnas_originales": list(df.columns),
    }

    # 1. One-hot encoding
    df = pd.get_dummies(df, columns=COLUMNAS_CATEGORICAS, drop_first=True)
    cols_bool = df.select_dtypes(include=["bool"]).columns
    df[cols_bool] = df[cols_bool].astype(int)

    # 2. Normalización
    scaler = StandardScaler() if args.metodo_normalizacion == "zscore" else MinMaxScaler()
    df[COLUMNAS_NUMERICAS] = scaler.fit_transform(df[COLUMNAS_NUMERICAS])

    # 3. Guardar
    escribir_mltable(df, args.datos_salida)
    os.makedirs(args.reporte, exist_ok=True)
    reporte.update({"filas_finales": len(df), "columnas_finales": list(df.columns)})
    with open(os.path.join(args.reporte, "reporte.json"), "w") as f:
        json.dump(reporte, f, indent=2)

    print(f"💾 Guardado en {args.datos_salida} | Shape final: {df.shape}")
    print(df.head())


if __name__ == "__main__":
    main()
