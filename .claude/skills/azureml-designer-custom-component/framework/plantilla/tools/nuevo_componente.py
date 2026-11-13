"""
Genera un componente Custom para el Designer de Azure ML: componentes/<nombre>.yml + src/<nombre>.py

Uso (desde la raíz del proyecto):
    python tools/nuevo_componente.py --nombre dividir_datos --titulo "Dividir Datos" \
        --descripcion "Divide en entrenamiento y prueba" \
        --entrada datos:mltable \
        --salida datos_entrenamiento:mltable --salida datos_prueba:mltable \
        --parametro fraccion_entrenamiento:number=0.7 --parametro semilla:integer=42

Tipos de entrada/salida : mltable | uri_folder | uri_file | mlflow_model
Tipos de parámetro      : string | number | integer | boolean   (formato nombre:tipo=default)
Opciones de un string   : --parametro metodo:string=zscore --opciones metodo=zscore,minmax
"""

import argparse
import os
import re
import sys

TIPOS_DATOS = {"mltable", "uri_folder", "uri_file", "mlflow_model"}
TIPOS_PARAM = {"string": "str", "number": "float", "integer": "int", "boolean": "str2bool"}
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE_VALIDO = re.compile(r"^[a-z][a-z0-9_]*$")


def parsear_puerto(texto):
    nombre, _, tipo = texto.partition(":")
    tipo = tipo or "mltable"
    if not NOMBRE_VALIDO.match(nombre):
        sys.exit(f"❌ Nombre inválido '{nombre}': usa minúsculas, números y _ (empieza con letra)")
    if tipo not in TIPOS_DATOS:
        sys.exit(f"❌ Tipo '{tipo}' no soportado. Usa: {', '.join(sorted(TIPOS_DATOS))}")
    return nombre, tipo


def parsear_parametro(texto):
    cabeza, igual, default = texto.partition("=")
    nombre, _, tipo = cabeza.partition(":")
    tipo = tipo or "string"
    if not NOMBRE_VALIDO.match(nombre):
        sys.exit(f"❌ Nombre de parámetro inválido '{nombre}'")
    if tipo not in TIPOS_PARAM:
        sys.exit(f"❌ Tipo de parámetro '{tipo}' no soportado. Usa: {', '.join(TIPOS_PARAM)}")
    return nombre, tipo, (default if igual else None)


def yaml_componente(a, entradas, salidas, params, opciones, entorno):
    l = [
        "$schema: https://azuremlschemas.azureedge.net/latest/commandComponent.schema.json",
        "type: command",
        f"name: {a.nombre}",
        f"display_name: {a.titulo}",
        f"description: {a.descripcion}",
        'version: "1"',
        "",
        "inputs:",
    ]
    for n, t in entradas:
        l.append(f"  {n}:\n    type: {t}")
    for n, t, d in params:
        l.append(f"  {n}:\n    type: {t}")
        if d is not None:
            l.append(f"    default: {d}")
        if n in opciones:
            l.append(f"    enum: [{', '.join(opciones[n])}]")
    if not entradas and not params:
        l[-1] = "inputs: {}"
    l += ["", "outputs:"]
    for n, t in salidas:
        l.append(f"  {n}:\n    type: {t}")
    cmd = [f"python {a.nombre}.py"]
    cmd += [f"--{n} ${{{{inputs.{n}}}}}" for n, _ in entradas]
    cmd += [f"--{n} ${{{{inputs.{n}}}}}" for n, _, _ in params]
    cmd += [f"--{n} ${{{{outputs.{n}}}}}" for n, _ in salidas]
    l += [
        "",
        "code: ../src",
        f"environment: azureml:{entorno}@latest",
        "",
        "command: >-",
        *[f"  {c}" for c in cmd],
        "",
    ]
    return "\n".join(l)


def python_componente(a, entradas, salidas, params):
    usa = set()
    lineas_args, lineas_in, lineas_out = [], [], []
    for n, t in entradas:
        lineas_args.append(f'    parser.add_argument("--{n}", required=True)')
        if t == "mltable":
            usa.add("leer_tabla")
            lineas_in.append(f"    {n} = leer_tabla(args.{n})  # DataFrame")
        elif t == "mlflow_model":
            usa.add("cargar_modelo")
            lineas_in.append(f"    {n} = cargar_modelo(args.{n})  # modelo scikit-learn")
        else:
            lineas_in.append(f"    {n} = args.{n}  # ruta ({t})")
    for n, t, d in params:
        conv = TIPOS_PARAM[t]
        default = "" if d is None else f", default={conv_default(t, d)}"
        req = ", required=True" if d is None else ""
        lineas_args.append(f'    parser.add_argument("--{n}", type={conv}{default}{req})')
    for n, t in salidas:
        lineas_args.append(f'    parser.add_argument("--{n}", required=True)')
        if t == "mltable":
            usa.add("escribir_tabla")
            lineas_out.append(f"    escribir_tabla(resultado, args.{n})  # TODO: DataFrame a guardar")
        elif t == "mlflow_model":
            usa.add("guardar_modelo")
            lineas_out.append(f"    guardar_modelo(modelo, args.{n})  # TODO: modelo entrenado")
        else:
            usa.add("preparar_carpeta")
            lineas_out.append(
                f"    carpeta_{n} = preparar_carpeta(args.{n})  # TODO: escribe archivos aquí"
            )
    necesita_bool = any(t == "boolean" for _, t, _ in params)
    imports = ["import argparse", ""]
    if usa:
        imports.append(f"from utils import {', '.join(sorted(usa))}")
    str2bool = (
        "\n\ndef str2bool(valor):\n"
        '    return str(valor).strip().lower() in ("true", "1", "yes", "si", "sí")\n'
        if necesita_bool
        else ""
    )
    return f'''"""
{a.titulo}: {a.descripcion}
Generado con tools/nuevo_componente.py — completa la sección TODO.
"""

{chr(10).join(imports)}
{str2bool}

def main():
    parser = argparse.ArgumentParser()
{chr(10).join(lineas_args)}
    args = parser.parse_args()
    print(f"⚙️  Argumentos: {{vars(args)}}")

    # ---------- Entradas ----------
{chr(10).join(lineas_in) or "    pass"}

    # ---------- TODO: tu lógica aquí ----------
    resultado = None
    modelo = None

    # ---------- Salidas ----------
{chr(10).join(lineas_out) or "    pass"}
    print("✅ Componente {a.nombre} terminado")


if __name__ == "__main__":
    main()
'''


def conv_default(tipo, valor):
    if tipo in ("number", "integer"):
        return valor
    if tipo == "boolean":
        return str(valor.lower() in ("true", "1", "yes", "si", "sí"))
    return repr(valor)


def leer_entorno():
    ruta = os.path.join(RAIZ, "config.env")
    if os.path.exists(ruta):
        for linea in open(ruta):
            if linea.startswith("AML_ENVIRONMENT="):
                return linea.split("=", 1)[1].strip()
    return "env-designer-custom"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nombre", required=True, help="snake_case, p. ej. dividir_datos")
    p.add_argument("--titulo", help="Nombre visible en el Designer")
    p.add_argument("--descripcion", default="Componente Custom del Designer")
    p.add_argument("--entrada", action="append", default=[], help="nombre:tipo")
    p.add_argument("--salida", action="append", default=[], help="nombre:tipo")
    p.add_argument("--parametro", action="append", default=[], help="nombre:tipo=default")
    p.add_argument("--opciones", action="append", default=[], help="parametro=a,b,c")
    p.add_argument("--forzar", action="store_true", help="sobrescribir si ya existe")
    a = p.parse_args()

    if not NOMBRE_VALIDO.match(a.nombre):
        sys.exit("❌ --nombre debe ser snake_case (minúsculas, números y _)")
    a.titulo = a.titulo or a.nombre.replace("_", " ").title()
    entradas = [parsear_puerto(x) for x in a.entrada]
    salidas = [parsear_puerto(x) for x in a.salida]
    params = [parsear_parametro(x) for x in a.parametro]
    opciones = {k: v.split(",") for k, _, v in (o.partition("=") for o in a.opciones)}

    if not salidas:
        sys.exit("❌ Define al menos una --salida")
    nombres = [n for n, _ in entradas] + [n for n, _, _ in params] + [n for n, _ in salidas]
    if len(nombres) != len(set(nombres)):
        sys.exit("❌ Hay nombres de entradas/parámetros/salidas repetidos")
    for n, t in salidas:
        if t == "uri_file":
            print(f"⚠️  Salida '{n}' es uri_file: en el Designer es más robusto usar uri_folder o mltable")

    yml = os.path.join(RAIZ, "componentes", f"{a.nombre}.yml")
    py = os.path.join(RAIZ, "src", f"{a.nombre}.py")
    for ruta in (yml, py):
        if os.path.exists(ruta) and not a.forzar:
            sys.exit(f"❌ Ya existe {os.path.relpath(ruta, RAIZ)} (usa --forzar para sobrescribir)")

    os.makedirs(os.path.dirname(yml), exist_ok=True)
    with open(yml, "w") as f:
        f.write(yaml_componente(a, entradas, salidas, params, opciones, leer_entorno()))
    with open(py, "w") as f:
        f.write(python_componente(a, entradas, salidas, params))

    print(f"✅ Creado componentes/{a.nombre}.yml")
    print(f"✅ Creado src/{a.nombre}.py  → completa el bloque TODO")
    print("Siguiente: uv run tools/probar_local.py componentes/" + a.nombre + ".yml --entrada ...")


if __name__ == "__main__":
    main()
