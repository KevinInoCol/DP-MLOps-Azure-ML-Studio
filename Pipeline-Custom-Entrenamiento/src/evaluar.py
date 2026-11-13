"""
Evaluar Modelo (equivalente a Evaluate Model del Classic, regresión).
Registra las métricas en MLflow (pestaña Metrics del job) y en metricas.json.
"""

import argparse
import json
import os

import mlflow
import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from utils import leer_tabla


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos_puntuados", required=True)
    parser.add_argument("--columna_objetivo", default="charges")
    parser.add_argument("--resultados", required=True)
    args = parser.parse_args()

    df = leer_tabla(args.datos_puntuados)
    y, pred = df[args.columna_objetivo], df["Scored Labels"]

    metricas = {
        "mean_absolute_error": float(mean_absolute_error(y, pred)),
        "root_mean_squared_error": float(np.sqrt(mean_squared_error(y, pred))),
        "relative_absolute_error": float(np.abs(y - pred).sum() / np.abs(y - y.mean()).sum()),
        "relative_squared_error": float(((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()),
        "coefficient_of_determination": float(r2_score(y, pred)),
    }
    mlflow.log_metrics(metricas)

    os.makedirs(args.resultados, exist_ok=True)
    with open(os.path.join(args.resultados, "metricas.json"), "w") as f:
        json.dump(metricas, f, indent=2)
    print(json.dumps(metricas, indent=2))


if __name__ == "__main__":
    main()
