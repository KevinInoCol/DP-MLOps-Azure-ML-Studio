"""
Puntuar Modelo (Score Model): Agrega Scored Labels. Equivale a Score Model.
Ejemplo del framework (generado con tools/nuevo_componente.py).
"""

import argparse

from utils import cargar_modelo, escribir_tabla, leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--datos", required=True)
    parser.add_argument("--columna_objetivo", type=str, default='charges')
    parser.add_argument("--datos_puntuados", required=True)
    args = parser.parse_args()
    print(f"⚙️  Argumentos: {vars(args)}")

    modelo = cargar_modelo(args.modelo)
    df = leer_tabla(args.datos)

    X = df.drop(columns=[args.columna_objetivo], errors="ignore")
    df["Scored Labels"] = modelo.predict(X[modelo.feature_names_in_])

    escribir_tabla(df, args.datos_puntuados, "puntuados.csv")
    print(f"📊 {len(df)} filas puntuadas")
    print("✅ Componente puntuar_modelo terminado")


if __name__ == "__main__":
    main()
