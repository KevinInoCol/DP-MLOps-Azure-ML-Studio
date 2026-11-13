#!/usr/bin/env bash
# Escribe en un .env los datos para consumir un online endpoint, SIN mostrar la key.
#
# Uso:
#   configurar_env_consumo.sh -w <workspace> -g <rg> -e <endpoint> -d <deployment> --env ruta/.env
#
# Variables que escribe (las reemplaza si existen, las agrega si no):
#   ONLINE_ENDPOINT_URL      scoring URI del endpoint
#   ONLINE_DEPLOYMENT_NAME   deployment al que va la cabecera azureml-model-deployment
#   ONLINE_ENDPOINT_KEY      primaryKey (solo se informa su longitud)
# Antes de escribir guarda una copia en <env>.bak.

set -euo pipefail
WS="" RG="" EP="" DP="" ENVF=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -w) WS="$2"; shift 2;;  -g) RG="$2"; shift 2;;
    -e) EP="$2"; shift 2;;  -d) DP="$2"; shift 2;;
    --env) ENVF="$2"; shift 2;;
    *) echo "Argumento desconocido: $1" >&2; exit 64;;
  esac
done
[[ -z "$WS" || -z "$RG" || -z "$EP" || -z "$DP" || -z "$ENVF" ]] && { echo "Faltan -w -g -e -d --env" >&2; exit 64; }

URL=$(az ml online-endpoint show -n "$EP" -w "$WS" -g "$RG" --query scoring_uri -o tsv 2>/dev/null)
KEY=$(az ml online-endpoint get-credentials -n "$EP" -w "$WS" -g "$RG" --query primaryKey -o tsv 2>/dev/null)
[[ -z "$URL" || -z "$KEY" ]] && { echo "No pude leer URL o key de $EP (¿existe? ¿auth por key?)" >&2; exit 1; }

touch "$ENVF"; cp "$ENVF" "$ENVF.bak"
URL="$URL" KEY="$KEY" DP="$DP" ENVF="$ENVF" python3 - <<'EOF'
import os, re
p = os.environ["ENVF"]; s = open(p).read()
vals = {"ONLINE_ENDPOINT_URL": os.environ["URL"],
        "ONLINE_DEPLOYMENT_NAME": os.environ["DP"],
        "ONLINE_ENDPOINT_KEY": os.environ["KEY"]}
for k, v in vals.items():
    if re.search(rf"^{k}=", s, flags=re.M):
        s = re.sub(rf"^{k}=.*$", lambda m: f"{k}={v}", s, flags=re.M)
    else:
        s += ("" if s.endswith("\n") or not s else "\n") + f"{k}={v}\n"
open(p, "w").write(s)
EOF
echo "📝 $ENVF actualizado (copia en $ENVF.bak):"
grep -E "^ONLINE_(ENDPOINT_URL|DEPLOYMENT_NAME)=" "$ENVF"
awk -F= '/^ONLINE_ENDPOINT_KEY=/{print "ONLINE_ENDPOINT_KEY=<oculta, " length($2) " caracteres>"}' "$ENVF"
