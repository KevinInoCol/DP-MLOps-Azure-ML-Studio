"""
Entrenar Regresor (Train Model): GradientBoostingRegressor en formato MLflow. Equivale a Boosted Decision Tree Regression + Train Model.
Ejemplo del framework (generado con tools/nuevo_componente.py).
"""

import argparse
import mlflow
from sklearn.ensemble import GradientBoostingRegressor

from utils import guardar_modelo, leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos_entrenamiento", required=True)
    parser.add_argument("--columna_objetivo", type=str, default='charges')
    parser.add_argument("--n_estimators", type=int, default=100)
    parser.add_argument("--learning_rate", type=float, default=0.1)
    parser.add_argument("--max_depth", type=int, default=3)
    parser.add_argument("--modelo", required=True)
    args = parser.parse_args()
    print(f"⚙️  Argumentos: {vars(args)}")

    df = leer_tabla(args.datos_entrenamiento)
    X = df.drop(columns=[args.columna_objetivo])
    y = df[args.columna_objetivo]

    params = {"n_estimators": args.n_estimators, "learning_rate": args.learning_rate, "max_depth": args.max_depth}
    modelo = GradientBoostingRegressor(random_state=42, **params).fit(X, y)
    mlflow.log_params(params)

    guardar_modelo(modelo, args.modelo, ejemplo_entrada=X.head(3))
    print(f"📊 Entrenado con {len(df)} filas y {X.shape[1]} variables")
    print("✅ Componente entrenar_regresor terminado")


if __name__ == "__main__":
    main()
