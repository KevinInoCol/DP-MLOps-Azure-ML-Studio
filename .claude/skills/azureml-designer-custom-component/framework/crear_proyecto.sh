#!/usr/bin/env bash
# Crea un proyecto nuevo con el framework de componentes Custom del Designer.
# Uso: crear_proyecto.sh <carpeta-destino> [--con-ejemplo]
#   --con-ejemplo  copia los 5 componentes del ejemplo de seguros (preprocesar, dividir,
#                  entrenar, puntuar, evaluar) y su pipeline.
set -euo pipefail
DEST="${1:?Indica la carpeta destino}"
FW="$(cd "$(dirname "$0")" && pwd)"
[[ -e "$DEST" && -n "$(ls -A "$DEST" 2>/dev/null)" ]] && { echo "❌ $DEST ya existe y no está vacía" >&2; exit 1; }
mkdir -p "$DEST"
cp -R "$FW/plantilla/." "$DEST/"
chmod +x "$DEST"/tools/*.sh
if [[ "${2:-}" == "--con-ejemplo" ]]; then
  cp "$FW/ejemplos/seguros/componentes/"*.yml "$DEST/componentes/"
  cp "$FW/ejemplos/seguros/src/"*.py "$DEST/src/"
  cp "$FW/ejemplos/seguros/pipelines/"*.yml "$DEST/pipelines/"
fi
printf 'salidas_locales/\nsalidas_azure/\n__pycache__/\nmlruns/\n.venv/\n' > "$DEST/.gitignore"
echo "✅ Proyecto creado en $DEST"
echo "   1) Edita $DEST/config.env   2) Lee $DEST/README.md"
