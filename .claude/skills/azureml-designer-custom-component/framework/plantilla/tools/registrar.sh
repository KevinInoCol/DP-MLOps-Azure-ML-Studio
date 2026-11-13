#!/usr/bin/env bash
# Registra el entorno y/o los componentes en Azure ML (lee config.env).
#
# Uso (desde la raíz del proyecto):
#   tools/registrar.sh --entorno                      # registra entorno/environment.yml
#   tools/registrar.sh                                # registra TODOS los componentes/*.yml
#   tools/registrar.sh componentes/dividir_datos.yml  # registra uno
#   tools/registrar.sh --nueva-version componentes/dividir_datos.yml
#       → sube la versión (última registrada + 1) y la escribe en el .yml.
#         Úsalo cada vez que cambies el código: Azure no deja reusar una versión con otro contenido.

set -euo pipefail
cd "$(dirname "$0")/.."
source ./config.env

AZ=(-w "$AML_WORKSPACE" -g "$AML_RESOURCE_GROUP")
ENTORNO=false
NUEVA=false
ARCHIVOS=()
for arg in "$@"; do
  case "$arg" in
    --entorno) ENTORNO=true;;
    --nueva-version) NUEVA=true;;
    *) ARCHIVOS+=("$arg");;
  esac
done

siguiente_version() {  # $1=tipo (component|environment) $2=nombre
  local v
  v=$(az ml "$1" list "${AZ[@]}" --name "$2" --query "[].version" -o tsv 2>/dev/null | grep -E '^[0-9]+$' | sort -n | tail -1 || true)
  echo $(( ${v:-0} + 1 ))
}

fijar_version() {  # $1=archivo $2=version
  sed -i.bak -E "s/^version: .*/version: \"$2\"/" "$1" && rm -f "$1.bak"
}

if $ENTORNO; then
  F=entorno/environment.yml
  if $NUEVA; then
    V=$(siguiente_version environment "$AML_ENVIRONMENT"); fijar_version "$F" "$V"
  fi
  echo "📦 Registrando entorno $AML_ENVIRONMENT ($(grep '^version' "$F"))"
  az ml environment create -f "$F" "${AZ[@]}" --set name="$AML_ENVIRONMENT" \
    --query "{nombre:name,version:version}" -o tsv
  [[ ${#ARCHIVOS[@]} -eq 0 ]] && exit 0
fi

[[ ${#ARCHIVOS[@]} -eq 0 ]] && ARCHIVOS=(componentes/*.yml)

for F in "${ARCHIVOS[@]}"; do
  NOMBRE=$(grep -E '^name:' "$F" | head -1 | awk '{print $2}')
  if $NUEVA; then
    V=$(siguiente_version component "$NOMBRE"); fijar_version "$F" "$V"
  fi
  echo "🧩 Registrando $NOMBRE ($(grep '^version' "$F"))"
  if ! az ml component create -f "$F" "${AZ[@]}" --query "{nombre:name,version:version}" -o tsv 2>/tmp/registrar_err_$$; then
    MSG=$(grep -m1 '^Message:' /tmp/registrar_err_$$ || grep -m1 '^ERROR' /tmp/registrar_err_$$ || true)
    echo "   Azure dice: ${MSG#Message: }"
    echo "❌ No se pudo registrar $NOMBRE. Si cambiaste el código usa: tools/registrar.sh --nueva-version $F"
    rm -f /tmp/registrar_err_$$; exit 1
  fi
  rm -f /tmp/registrar_err_$$
done
echo "✅ Listo. En el Designer búscalos por su display_name (recarga la página; el índice puede tardar unos minutos)."
