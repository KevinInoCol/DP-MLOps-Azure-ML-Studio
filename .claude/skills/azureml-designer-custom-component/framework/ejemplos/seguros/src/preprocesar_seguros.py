"""
Preprocesar Seguros: One-hot (sex, smoker, region) y normalización (age, bmi, children). Equivale a Edit Metadata.
Ejemplo del framework (generado con tools/nuevo_componente.py).
"""

import argparse
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from utils import escribir_tabla, leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos", required=True)
    parser.add_argument("--metodo_normalizacion", type=str, default='zscore')
    parser.add_argument("--datos_procesados", required=True)
    args = parser.parse_args()
    print(f"⚙️  Argumentos: {vars(args)}")

    df = leer_tabla(args.datos)

    df = pd.get_dummies(df, columns=["sex", "smoker", "region"], drop_first=True)
    cols_bool = df.select_dtypes(include=["bool"]).columns
    df[cols_bool] = df[cols_bool].astype(int)
    scaler = StandardScaler() if args.metodo_normalizacion == "zscore" else MinMaxScaler()
    cols_num = ["age", "bmi", "children"]
    df[cols_num] = scaler.fit_transform(df[cols_num])

    escribir_tabla(df, args.datos_procesados)
    print(f"📊 Shape final: {df.shape}")
    print("✅ Componente preprocesar_seguros terminado")


if __name__ == "__main__":
    main()
