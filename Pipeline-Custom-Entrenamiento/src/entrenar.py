"""
Entrenar Regresor (equivalente a Boosted Decision Tree Regression + Train Model del Classic).

v3: el modelo guardado incluye el preprocesamiento (one-hot de columnas de texto y
escalado de columnas numéricas) dentro de un Pipeline de scikit-learn. Así recibe
DATOS CRUDOS ({"age": 19, "sex": "female", ...}) y se puede desplegar directo
como endpoint, sin score.py.
"""

import argparse
import os
import shutil
import tempfile

import mlflow
import mlflow.sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler

from utils import leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos_entrenamiento", required=True)
    parser.add_argument("--columna_objetivo", default="charges")
    parser.add_argument("--metodo_normalizacion", default="zscore", choices=["zscore", "minmax"])
    parser.add_argument("--n_estimators", type=int, default=100)
    parser.add_argument("--learning_rate", type=float, default=0.1)
    parser.add_argument("--max_depth", type=int, default=3)
    parser.add_argument("--modelo", required=True)
    args = parser.parse_args()

    df = leer_tabla(args.datos_entrenamiento)
    X = df.drop(columns=[args.columna_objetivo])
    y = df[args.columna_objetivo]

    # Detecta solas qué columnas son texto (one-hot) y cuáles numéricas (escalado)
    cols_texto = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    cols_num = [c for c in X.columns if c not in cols_texto]
    escalador = StandardScaler() if args.metodo_normalizacion == "zscore" else MinMaxScaler()
    preprocesamiento = ColumnTransformer(
        [
            ("texto", OneHotEncoder(drop="first", handle_unknown="ignore"), cols_texto),
            ("numericas", escalador, cols_num),
        ]
    )

    params = {
        "n_estimators": args.n_estimators,
        "learning_rate": args.learning_rate,
        "max_depth": args.max_depth,
    }
    modelo = Pipeline(
        [
            ("preprocesamiento", preprocesamiento),
            ("regresor", GradientBoostingRegressor(random_state=42, **params)),
        ]
    ).fit(X, y)

    mlflow.log_params({**params, "metodo_normalizacion": args.metodo_normalizacion})
    print(f"✅ Entrenado con {len(df)} filas | texto: {cols_texto} | numéricas: {cols_num}")

    # mlflow.save_model exige una carpeta inexistente: guardar en temporal y copiar.
    tmp = os.path.join(tempfile.mkdtemp(), "modelo")
    # azureml-ai-monitoring: lo importa el score script que Azure autogenera al desplegar
    # un modelo MLflow como endpoint; sin él el deployment falla con "No module named 'azureml'".
    mlflow.sklearn.save_model(
        modelo, tmp, input_example=X.head(3), extra_pip_requirements=["azureml-ai-monitoring"]
    )
    shutil.copytree(tmp, args.modelo, dirs_exist_ok=True)
    print(f"💾 Modelo MLflow (preprocesamiento + regresor) guardado en {args.modelo}")


if __name__ == "__main__":
    main()
