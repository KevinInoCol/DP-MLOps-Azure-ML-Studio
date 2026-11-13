---
name: azureml-data-mltable-v2
description: Registra datos (CSV) como data asset MLTable v2 en Azure Machine Learning para que los lean los componentes Custom del Designer y los pipelines v2 — desde un CSV local (sube copia), desde un dataset Tabular v1 existente o desde una ruta del Blob/datastore (sin copiar datos). Incluye script probado (scripts/registrar_mltable.sh), cómo detectar un dataset v1 (properties.v1_type tabular), la diferencia v1 vs v2 explicada para alumnos y cómo verificar que dos datasets apuntan al mismo CSV. Use when the user asks to "pasar la data a MLTable", "convertir el dataset a v2", "registrar el CSV como mltable", "mi dataset Tabular no funciona con el componente custom", "invalid MLTable yaml", "plan-de-salud-mltable", "qué diferencia hay entre Tabular y MLTable", or types /azureml-data-mltable-v2.
---

# Datos en formato MLTable v2 para Azure ML

Probado el 2026-11-12 en `<tu-workspace>`: `plan-de-salud-mltable:1` (copia) y `:2` (sin copia, apunta al CSV del Tabular v1) — ambos leídos con éxito por el componente `preprocesador_seguros:4`.

## v1 vs v2 en una frase (para explicar a alumnos)

Mismo CSV, distinta "ficha" de registro:
- **Tabular v1** (UI → "Tabular"): la leen los bloques **Classic** del Designer. Los componentes **Custom** fallan con `Data asset service returned invalid MLTable yaml`.
- **MLTable v2**: carpeta con un archivo `MLTable` (4 líneas YAML que dicen "este CSV, separado por comas, con encabezado"). La leen los componentes **Custom** y pipelines v2.

Detectar un v1: `az ml data show -n <ds> -v <v> -w <ws> -g <rg> --query "{type:type,props:properties}"` → `v1_type: tabular`.

## Script: `scripts/registrar_mltable.sh`

```bash
S=~/.claude/skills/azureml-data-mltable-v2/scripts/registrar_mltable.sh

# A) Desde un Tabular v1 existente — NO copia datos (recomendado si el CSV ya está en el Blob)
$S -w <ws> -g <rg> -n plan-de-salud-mltable --desde-dataset plan-de-salud:1

# B) Desde una ruta de datastore — NO copia datos
$S -w <ws> -g <rg> -n mis-datos --blob azureml://datastores/workspaceblobstore/paths/<ruta>/archivo.csv

# C) Desde un CSV local — sube una copia junto al MLTable
$S -w <ws> -g <rg> -n mis-datos --csv ./insurance.csv
```

Opcionales: `-v <version>`, `-d "<descripción>"`, `--sep ";"`.

Qué hace: genera el archivo `MLTable` (en A/B con ruta absoluta `azureml://...` al CSV; en C con `./archivo.csv`), lo registra con `az ml data create --type mltable` e imprime nombre/versión/ruta. Los Tabular v1 de la UI guardan la ruta como `.../archivo.csv/` (con `/` final): el script lo quita.

En la UI equivale a *Data → Create → tipo **Table (mltable)***.

## Verificar

1. Que se registró: `az ml data show -n <nombre> -v <v> -w -g --query "{type:type,path:path}"`.
2. Que se lee: correr un componente con entrada `mltable` sobre el asset (ver skill `azureml-designer-custom-component`). En el log debe verse `Contenido: ['MLTable']` y `Leído con mltable`.
3. Que dos datasets tienen el mismo CSV (si el usuario duda): listar y descargar los blobs con `az storage blob list/download --account-name <acc> -c <container> --prefix <ruta>` y comparar `md5`/`cmp`.
   - Cuenta y contenedor: `az ml datastore show -n workspaceblobstore -w -g --query "{a:account_name,c:container_name}"`.
   - Si `--auth-mode login` da "required permissions", usar `AZURE_STORAGE_AUTH_MODE=key` (la CLI pide la key al vuelo; no imprimirla).

## Notas

- Montaje (modo por defecto) funciona tanto con CSV copiado como con ruta absoluta `azureml://`: el runtime resuelve la ruta con la identidad del job.
- Si el origen es una carpeta con varios CSV, usar `- folder: <ruta>` en lugar de `- file:` dentro del MLTable.
- No borrar el Tabular v1 original si hay pipelines Classic que lo usan: conviven.
