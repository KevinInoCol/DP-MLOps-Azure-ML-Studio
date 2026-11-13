"""
Puntuar Modelo (equivalente a Score Model del Classic).
Agrega la columna "Scored Labels" con la predicción.
"""

import argparse

import mlflow.sklearn

from utils import escribir_tabla, leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--datos", required=True)
    parser.add_argument("--columna_objetivo", default="charges")
    parser.add_argument("--datos_puntuados", required=True)
    args = parser.parse_args()

    modelo = mlflow.sklearn.load_model(args.modelo)
    df = leer_tabla(args.datos)
    X = df.drop(columns=[args.columna_objetivo], errors="ignore")
    df["Scored Labels"] = modelo.predict(X[modelo.feature_names_in_])

    escribir_tabla(df, args.datos_puntuados, "puntuados.csv")
    print(f"✅ {len(df)} filas puntuadas\n{df.head()}")


if __name__ == "__main__":
    main()
