#!/usr/bin/env bash
# Vigila un deployment de un managed online endpoint de Azure ML hasta que termine.
#
# Uso:
#   vigilar_endpoint.sh -w <workspace> -g <rg> -e <endpoint> -d <deployment> \
#       [--trafico] [--probar payload.json] [--env ruta/.env] [--intervalo 30] [--max-min 40]
#
#   --trafico   al terminar bien, pone 100% de tráfico a <deployment> si no lo tiene.
#   --probar    al terminar bien, invoca el endpoint con ese JSON y muestra la respuesta.
#   --env       al terminar bien, escribe URL / deployment / key en ese .env (ver configurar_env_consumo.sh).
#
# Pensado para correr en segundo plano: avisa al terminar (notificación de macOS si existe)
# y, si falla, imprime las líneas de error del log con la causa probable.
# Exit: 0 = Succeeded, 1 = Failed/Canceled, 2 = se acabó el tiempo.

set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
WS="" RG="" EP="" DP="" TRAFICO=false PROBAR="" ENVF="" INTERVALO=30 MAXMIN=40
while [[ $# -gt 0 ]]; do
  case "$1" in
    -w) WS="$2"; shift 2;;  -g) RG="$2"; shift 2;;
    -e) EP="$2"; shift 2;;  -d) DP="$2"; shift 2;;
    --trafico) TRAFICO=true; shift;;
    --probar) PROBAR="$2"; shift 2;;
    --env) ENVF="$2"; shift 2;;
    --intervalo) INTERVALO="$2"; shift 2;;
    --max-min) MAXMIN="$2"; shift 2;;
    *) echo "Argumento desconocido: $1" >&2; exit 64;;
  esac
done
[[ -z "$WS" || -z "$RG" || -z "$EP" || -z "$DP" ]] && { echo "Faltan -w -g -e -d" >&2; exit 64; }
A=(-w "$WS" -g "$RG")

avisar() {  # $1 = mensaje
  echo "$1"
  command -v osascript >/dev/null && osascript -e "display notification \"$1\" with title \"Azure ML endpoint\"" 2>/dev/null || true
}

FIN=$(( $(date +%s) + MAXMIN * 60 ))
E="" D=""
while :; do
  E=$(az ml online-endpoint show -n "$EP" "${A[@]}" --query provisioning_state -o tsv 2>/dev/null)
  D=$(az ml online-deployment show -n "$DP" --endpoint-name "$EP" "${A[@]}" --query provisioning_state -o tsv 2>/dev/null)
  echo "$(date +%H:%M:%S) endpoint=${E:-no-existe} deployment=${D:-no-existe}"
  case "$D" in Succeeded|Failed|Canceled) break;; esac
  [[ "$E" == "Failed" ]] && break
  if (( $(date +%s) > FIN )); then avisar "⏱️ $DP sigue en ${D:-?} tras ${MAXMIN} min"; exit 2; fi
  sleep "$INTERVALO"
done

if [[ "$D" != "Succeeded" ]]; then
  avisar "❌ $DP terminó en ${D:-$E}"
  LOG=$(az ml online-deployment get-logs -n "$DP" --endpoint-name "$EP" "${A[@]}" --lines 400 2>/dev/null)
  echo "--- Líneas de error del log (sin el ruido de conda-anaconda-*):"
  echo "$LOG" | grep -nE "Traceback|Error|Exception|No module|Killed|OOM|memory" | grep -v "conda-anaconda" | head -15
  echo "--- Causa probable:"
  if echo "$LOG" | grep -q "No module named 'azureml'"; then
    echo "El score script autogenerado de MLflow importa azureml.ai.monitoring y el entorno del modelo no lo trae."
    echo "→ Registrar nueva versión del modelo con 'azureml-ai-monitoring' en conda.yaml/requirements.txt"
    echo "  (o guardar con extra_pip_requirements=['azureml-ai-monitoring']) y crear un deployment NUEVO:"
    echo "  'online-deployment update' reutiliza el entorno viejo y vuelve a fallar."
  elif echo "$LOG" | grep -qiE "Killed|out of memory|OOM"; then
    echo "Memoria insuficiente → usar una VM más grande (p. ej. Standard_D4as_v4)."
  elif [[ -z "$LOG" ]]; then
    echo "Sin log: el contenedor no llegó a arrancar. Revisar 'Error details' del deployment, la cuota"
    echo "(az ml online-deployment create … muestra 'Not enough quota') y que Microsoft.PolicyInsights esté registrado."
  else
    echo "Ver el traceback de arriba (error en el modelo o en su entorno)."
  fi
  echo "Recordatorio: un deployment Failed puede seguir reservando cuota/VM. Bórralo si no lo vas a corregir."
  exit 1
fi

avisar "✅ $DP en $EP: Succeeded"
if $TRAFICO; then
  T=$(az ml online-endpoint show -n "$EP" "${A[@]}" --query "traffic.\"$DP\"" -o tsv 2>/dev/null)
  if [[ "$T" != "100" ]]; then
    echo "Tráfico de $DP era ${T:-0}% → 100%"
    az ml online-endpoint update -n "$EP" "${A[@]}" --traffic "$DP=100" --query traffic -o json 2>/dev/null
  fi
fi
if [[ -n "$PROBAR" ]]; then
  echo "--- Prueba con $PROBAR:"
  az ml online-endpoint invoke -n "$EP" -d "$DP" "${A[@]}" --request-file "$PROBAR" 2>&1 | grep -v -i experimental
fi
if [[ -n "$ENVF" ]]; then
  "$DIR/configurar_env_consumo.sh" -w "$WS" -g "$RG" -e "$EP" -d "$DP" --env "$ENVF"
fi
exit 0
