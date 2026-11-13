# Framework de componentes Custom — Azure ML Designer

Crea tus propios bloques para el Designer (modo **Custom**) sin pelearte con YAML ni con Azure.

## Requisitos (una vez)

- Azure CLI con la extensión ml: `az extension add -n ml` y `az login`
- [uv](https://docs.astral.sh/uv/) para las pruebas locales
- Edita `config.env` con tu workspace, resource group, cluster y nombre de entorno.

## Flujo para crear un bloque

```bash
# 1. Generar el bloque (crea componentes/<nombre>.yml y src/<nombre>.py)
python tools/nuevo_componente.py --nombre filtrar_filas --titulo "Filtrar Filas" \
    --entrada datos:mltable --salida datos_filtrados:mltable \
    --parametro columna:string=age --parametro minimo:number=18

# 2. Escribir tu lógica en el bloque TODO de src/filtrar_filas.py

# 3. Probarlo en tu laptop con un CSV (salidas en salidas_locales/)
uv run tools/probar_local.py componentes/filtrar_filas.yml --entrada datos=data/mi.csv

# 4. Registrar entorno (solo la 1ª vez o si cambias entorno/conda.yml) y componente
tools/registrar.sh --entorno
tools/registrar.sh componentes/filtrar_filas.yml
#    ¿Cambiaste el código después? → tools/registrar.sh --nueva-version componentes/filtrar_filas.yml

# 5. Usarlo: en el Designer (Custom) búscalo por su título, o por CLI con un pipeline:
tools/ejecutar_pipeline.sh pipelines/mi_pipeline.yml
```

## Tipos

| Para… | Tipo | En `src/` usa |
|---|---|---|
| Tablas (CSV) | `mltable` | `leer_tabla()` / `escribir_tabla()` |
| Modelos | `mlflow_model` | `cargar_modelo()` / `guardar_modelo()` |
| Archivos sueltos (reportes, gráficos) | `uri_folder` | `preparar_carpeta()` |
| Parámetros | `string`, `number`, `integer`, `boolean` | `args.<nombre>` |

## Reglas que evitan el 90 % de errores

1. **Datos en formato v2.** Un dataset subido como *Tabular* (v1) no funciona con bloques Custom → regístralo como **Table (mltable)**.
2. **Salidas tabulares como `mltable`** (no `uri_file`): así se pueden conectar al siguiente bloque.
3. **Un solo entorno** para todos los bloques (`entorno/`): la imagen se construye una vez.
4. **Cambiaste código → nueva versión** (`--nueva-version`). El Designer usa la versión registrada, no tu archivo local.
5. **Prueba en local antes de registrar**: un error en local tarda segundos; en Azure, minutos.
