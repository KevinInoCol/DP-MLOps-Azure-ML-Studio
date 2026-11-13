#!/usr/bin/env bash
# Registra un CSV como data asset MLTable v2 en Azure ML.
#
# Uso (elige UNA fuente):
#   registrar_mltable.sh -w <workspace> -g <rg> -n <nombre> --csv ./ruta/archivo.csv
#   registrar_mltable.sh -w <workspace> -g <rg> -n <nombre> --desde-dataset <dataset_v1>:<version>
#   registrar_mltable.sh -w <workspace> -g <rg> -n <nombre> --blob azureml://datastores/<ds>/paths/<ruta>/archivo.csv
#
# Opcionales: -v <version> (default: siguiente libre), -d "<descripción>", --sep ";" (default ",")
#
# --csv            sube una copia del CSV junto al archivo MLTable.
# --desde-dataset  toma la ruta del CSV de un dataset existente (p. ej. Tabular v1) y NO copia datos.
# --blob           apunta a un CSV que ya está en un datastore y NO copia datos.

set -euo pipefail

WS="" RG="" NAME="" VER="" DESC="" SEP="," CSV="" DESDE="" BLOB=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -w) WS="$2"; shift 2;;
    -g) RG="$2"; shift 2;;
    -n) NAME="$2"; shift 2;;
    -v) VER="$2"; shift 2;;
    -d) DESC="$2"; shift 2;;
    --sep) SEP="$2"; shift 2;;
    --csv) CSV="$2"; shift 2;;
    --desde-dataset) DESDE="$2"; shift 2;;
    --blob) BLOB="$2"; shift 2;;
    *) echo "Argumento desconocido: $1" >&2; exit 1;;
  esac
done
[[ -z "$WS" || -z "$RG" || -z "$NAME" ]] && { echo "Faltan -w, -g o -n" >&2; exit 1; }
[[ -z "$CSV$DESDE$BLOB" ]] && { echo "Indica --csv, --desde-dataset o --blob" >&2; exit 1; }

TMP="$(mktemp -d)/mltable"
mkdir -p "$TMP"

if [[ -n "$CSV" ]]; then
  [[ -f "$CSV" ]] || { echo "No existe $CSV" >&2; exit 1; }
  cp "$CSV" "$TMP/"
  RUTA="./$(basename "$CSV")"
  [[ -z "$DESC" ]] && DESC="$(basename "$CSV") como MLTable v2 (copia subida)"
else
  if [[ -n "$DESDE" ]]; then
    DS="${DESDE%%:*}"; DV="${DESDE##*:}"
    RUTA="$(az ml data show -n "$DS" -v "$DV" -w "$WS" -g "$RG" --query path -o tsv)"
    RUTA="${RUTA%/}"   # los Tabular v1 de la UI terminan en "archivo.csv/"
    [[ -z "$DESC" ]] && DESC="MLTable v2 del mismo CSV que $DS:$DV (sin copiar datos)"
  else
    RUTA="$BLOB"
    [[ -z "$DESC" ]] && DESC="MLTable v2 apuntando a $BLOB (sin copiar datos)"
  fi
  [[ "$RUTA" == *.csv ]] || echo "⚠️  La ruta no termina en .csv: $RUTA (si es una carpeta usa 'folder:' en el MLTable)" >&2
fi

cat > "$TMP/MLTable" <<EOF
paths:
  - file: $RUTA
transformations:
  - read_delimited:
      delimiter: '$SEP'
      header: all_files_same_headers
      encoding: utf8
EOF

echo "📄 MLTable generado:"; cat "$TMP/MLTable"

VER_ARG=()
if [[ -n "$VER" ]]; then
  VER_ARG=(--version "$VER")
fi

az ml data create -w "$WS" -g "$RG" --name "$NAME" ${VER_ARG[@]+"${VER_ARG[@]}"} \
  --type mltable --path "$TMP" --description "$DESC" \
  --query "{name:name,version:version,type:type,path:path}" -o json
