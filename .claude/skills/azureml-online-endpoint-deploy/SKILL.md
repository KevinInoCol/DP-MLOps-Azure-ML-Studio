---
name: azureml-online-endpoint-deploy
description: Despliega y vigila modelos MLflow de Azure Machine Learning en managed online endpoints (real-time), y deja listo el consumo. Incluye un vigía en segundo plano (scripts/vigilar_endpoint.sh) que avisa apenas el deployment termina o falla, pone el tráfico al 100%, prueba el endpoint con un JSON y escribe URL / deployment / key en el .env de la app de consumo sin mostrar la key (scripts/configurar_env_consumo.sh). Trae la tabla de errores reales — "No module named 'azureml'" del score script autogenerado de MLflow, update que reutiliza el entorno viejo, "Not enough quota ... usage/limit", tráfico en 0%, cabecera azureml-model-deployment desactualizada, Microsoft.PolicyInsights. Use when the user asks to "desplegar el modelo como endpoint", "real-time endpoint", "vigila el despliegue", "avísame cuando termine de desplegar", "el deployment falló", "actualiza el .env con el endpoint", "consumir el endpoint", "Use this model → Real-time endpoint", "az ml online-deployment", or types /azureml-online-endpoint-deploy.
---

# Despliegue y vigilancia de online endpoints (Azure ML)

Probado el 2026-11-12 en `<tu-workspace>` (brazilsouth) con dos modelos MLflow:
`modelo-voting-ensemble` (AutoML) y `modelo-seguros` (pipeline Custom, sklearn Pipeline).

## Flujo

1. **Desplegar** (portal: Models → modelo → *Use this model ▾ → Real-time endpoint*; o CLI con un YAML
   `managedOnlineDeployment` con `model: azureml:<modelo>:<v>`, `instance_type`, `instance_count: 1`).
   Para modelos MLflow no hace falta `score.py` ni entorno: Azure los autogenera.
2. **Vigilar en segundo plano** (no consume tokens mientras espera; un subagente sí):
   ```bash
   S=~/.claude/skills/azureml-online-endpoint-deploy/scripts
   $S/vigilar_endpoint.sh -w <ws> -g <rg> -e <endpoint> -d <deployment> \
     --trafico --probar payload.json --env <carpeta-consumo>/.env
   ```
   Ejecutarlo con `run_in_background`. Termina con exit 0 (Succeeded), 1 (Failed: imprime líneas
   de error + causa probable) o 2 (timeout, default 40 min). Notifica en macOS.
3. **Solo actualizar el .env** (endpoint ya desplegado):
   `$S/configurar_env_consumo.sh -w <ws> -g <rg> -e <endpoint> -d <deployment> --env ruta/.env`
   Escribe `ONLINE_ENDPOINT_URL`, `ONLINE_DEPLOYMENT_NAME`, `ONLINE_ENDPOINT_KEY`; deja `.env.bak`;
   nunca imprime la key (solo su longitud).

Payload (orient `split` de pandas; `index` opcional):
```json
{"input_data": {"columns": ["age","sex","bmi","children","smoker","region"],
                "index": [0], "data": [[19, "female", 27.9, 0, "yes", "southwest"]]}}
```

## Errores reales y solución

| Síntoma | Causa | Solución |
|---|---|---|
| Deployment `Failed`; log: `mlflow_score_script.py line 20 … No module named 'azureml'` | El score script autogenerado importa `azureml.ai.monitoring`; el `conda.yaml` que `mlflow.sklearn.save_model` escribe no incluye `azureml-ai-monitoring`. (Los modelos de AutoML sí lo traen.) | Guardar con `extra_pip_requirements=["azureml-ai-monitoring"]`, o descargar el modelo, añadirlo a `conda.yaml` y `requirements.txt` y registrar versión nueva |
| Se hizo `online-deployment update --set model=…:2` y falla igual | El update **reutiliza el entorno autogenerado** del modelo anterior (mismo `azureml_<hash>` en el log) | Crear un **deployment nuevo** con la versión corregida; luego mover tráfico y borrar el viejo |
| `Not enough quota available for Standard_D2as_v4 … Current usage/limit: 8/10. Additional needed: 4` | Cada deployment reserva 2× los núcleos de la VM (VM + margen de actualización). Un deployment `Failed` **sigue reservando** | Borrar deployments fallidos/no usados; con límite 10 caben 2 deployments D2as_v4 |
| Deployment `Succeeded` pero el endpoint no responde | Tráfico en 0% | `--trafico` del vigía, o *Update traffic* → 100 |
| La app de consumo da error tras cambiar de endpoint | `ONLINE_DEPLOYMENT_NAME` viejo en la cabecera `azureml-model-deployment` | `configurar_env_consumo.sh` (actualiza las tres variables) |
| `Error details: --` vacío en el portal | Falta el resource provider `Microsoft.PolicyInsights` | `az provider register --namespace Microsoft.PolicyInsights` y esperar unos minutos |
| Log lleno de `Error while loading conda entry point: conda-anaconda-tos/telemetry` | Ruido de la imagen base | Ignorar; el vigía lo filtra |

## Notas

- Tiempos observados: endpoint ~1 min; deployment MLflow 8–15 min (construye la imagen la 1ª vez).
- `get-logs` no devuelve nada mientras el deployment está en *Creating*/*Updating*.
- Costo: Standard_D2as_v4 ≈ $0.15/h por instancia mientras exista, aunque nadie lo llame. Borrar al terminar.
- Para que un modelo reciba datos crudos, el preprocesamiento debe ir **dentro** del modelo MLflow
  (ver `azureml-designer-custom-component`, componente `entrenar_regresor` v3+).
- zsh no separa palabras en `$VAR`: usar arrays (`A=(-w ws -g rg)` y `"${A[@]}"`) en comandos `az`.
