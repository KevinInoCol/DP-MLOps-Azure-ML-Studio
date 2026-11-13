"""
Dividir Datos (Split Data): Divide en entrenamiento y prueba. Equivale a Split Data.
Ejemplo del framework (generado con tools/nuevo_componente.py).
"""

import argparse
from sklearn.model_selection import train_test_split

from utils import escribir_tabla, leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos", required=True)
    parser.add_argument("--fraccion_entrenamiento", type=float, default=0.7)
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--datos_entrenamiento", required=True)
    parser.add_argument("--datos_prueba", required=True)
    args = parser.parse_args()
    print(f"⚙️  Argumentos: {vars(args)}")

    df = leer_tabla(args.datos)

    train, test = train_test_split(df, train_size=args.fraccion_entrenamiento, random_state=args.semilla)

    escribir_tabla(train, args.datos_entrenamiento, "entrenamiento.csv")
    escribir_tabla(test, args.datos_prueba, "prueba.csv")
    print(f"📊 {len(df)} → entrenamiento {len(train)} | prueba {len(test)}")
    print("✅ Componente dividir_datos terminado")


if __name__ == "__main__":
    main()
