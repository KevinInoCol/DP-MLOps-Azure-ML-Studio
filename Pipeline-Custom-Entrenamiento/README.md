# Pipeline de entrenamiento Custom — Seguros (equivalente al Classic)

Probado en `<tu-workspace>` — job `joyful_kettle_9qt1dc06bt`: 5/5 pasos Completed.
Métricas (prueba, 402 filas): MAE 2,490.6 · RMSE 4,438.1 · RAE 0.276 · RSE 0.134 · **R² 0.866**.

| Classic | Custom (buscar en el Designer por este nombre) |
|---|---|
| plan-de-salud | `plan-de-salud-mltable` (versión 2) |
| Edit Metadata | Preprocesador de Seguros |
| Split Data | Dividir Datos |
| Boosted Decision Tree Regression + Train Model | Entrenar Regresor (Boosted Trees) |
| Score Model | Puntuar Modelo |
| Evaluate Model | Evaluar Modelo (Regresión) |

## Registrar y ejecutar

```bash
W="-w <tu-workspace> -g <tu-resource-group>"
az ml environment create -f environment.yml $W
for c in dividir entrenar puntuar evaluar; do az ml component create -f componentes/$c.yml $W; done
az ml job create -f pipeline_entrenamiento.yml $W
```

El componente Preprocesador está en `../Componente-Designer-Preprocesador-Seguros/`.
