#!/usr/bin/env bash
# Lanza un pipeline, espera a que termine y, si un paso falla, descarga y muestra su log.
#
# Uso (desde la raíz del proyecto):
#   tools/ejecutar_pipeline.sh pipelines/entrenamiento.yml
#   tools/ejecutar_pipeline.sh pipelines/entrenamiento.yml --sin-esperar

set -euo pipefail
cd "$(dirname "$0")/.."
source ./config.env

AZ=(-w "$AML_WORKSPACE" -g "$AML_RESOURCE_GROUP")
F="${1:?Indica el pipeline, p. ej. pipelines/entrenamiento.yml}"

JOB=$(az ml job create -f "$F" "${AZ[@]}" --set settings.default_compute="azureml:$AML_COMPUTE" \
  --query name -o tsv 2>/dev/null)
URL=$(az ml job show -n "$JOB" "${AZ[@]}" --query services.Studio.endpoint -o tsv 2>/dev/null)
echo "🚀 Job: $JOB"
echo "🔗 $URL"
[[ "${2:-}" == "--sin-esperar" ]] && exit 0

echo "⏳ Esperando (la 1ª vez Azure construye la imagen del entorno: ~10-15 min)..."
while true; do
  S=$(az ml job show -n "$JOB" "${AZ[@]}" --query status -o tsv 2>/dev/null || echo Unknown)
  [[ "$S" =~ ^(Completed|Failed|Canceled|NotResponding)$ ]] && break
  sleep 30
done

echo "📋 Estado final: $S"
az ml job list --parent-job-name "$JOB" "${AZ[@]}" --query "[].[display_name,status]" -o tsv 2>/dev/null \
  | while read -r paso estado; do echo "   $paso: $estado"; done

if [[ "$S" != "Completed" ]]; then
  FALLO=$(az ml job list --parent-job-name "$JOB" "${AZ[@]}" --query "[?status=='Failed'].name | [0]" -o tsv 2>/dev/null)
  if [[ -n "$FALLO" ]]; then
    DIR="salidas_azure/$JOB"
    az ml job download -n "$FALLO" "${AZ[@]}" --all --download-path "$DIR" >/dev/null 2>&1 || true
    echo "❌ Log del paso que falló ($DIR):"
    LOG=$(find "$DIR" -name std_log.txt | head -1)
    if [[ -n "$LOG" ]]; then tail -30 "$LOG"; else tail -5 "$(find "$DIR" -name stderrlogs.txt | head -1)"; fi
  fi
  exit 1
fi
