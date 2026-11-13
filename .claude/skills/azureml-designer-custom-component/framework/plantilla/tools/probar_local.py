# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Ejecuta un componente en tu laptop, igual que lo haría Azure, antes de registrarlo.

Uso (desde la raíz del proyecto):
    uv run tools/probar_local.py componentes/dividir_datos.yml \
        --entrada datos=data/insurance.csv --param fraccion_entrenamiento=0.8

- Las entradas pueden ser un CSV, una carpeta con CSV o la salida local de otro componente.
- Las salidas quedan en salidas_locales/<componente>/<salida>/ (encadénalas como entradas).
- Instala solo las librerías de entorno/conda.yml que sirven en local (omite mltable/azureml-*).
"""

import argparse
import os
import re
import shlex
import subprocess
import sys

import yaml

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OMITIR_LOCAL = ("mltable", "azureml-")


def deps_locales():
    conda = yaml.safe_load(open(os.path.join(RAIZ, "entorno", "conda.yml")))
    deps = ["setuptools<81"]
    for d in conda.get("dependencies", []):
        if isinstance(d, dict) and "pip" in d:
            deps += [p for p in d["pip"] if not p.startswith(OMITIR_LOCAL)]
    return deps


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("componente", help="ruta a componentes/<nombre>.yml")
    p.add_argument("--entrada", action="append", default=[], help="nombre=ruta")
    p.add_argument("--param", action="append", default=[], help="nombre=valor")
    a = p.parse_args()

    yml_path = os.path.abspath(a.componente)
    comp = yaml.safe_load(open(yml_path))
    code_dir = os.path.normpath(os.path.join(os.path.dirname(yml_path), comp.get("code", ".")))
    entradas = dict(e.split("=", 1) for e in a.entrada)
    params = dict(x.split("=", 1) for x in a.param)

    valores = {}
    for nombre, spec in (comp.get("inputs") or {}).items():
        es_dato = spec.get("type") in ("mltable", "uri_folder", "uri_file", "mlflow_model", "custom_model")
        if es_dato:
            if nombre not in entradas:
                sys.exit(f"❌ Falta --entrada {nombre}=<ruta>")
            valores[f"inputs.{nombre}"] = os.path.abspath(entradas[nombre])
        else:
            if nombre in params:
                valores[f"inputs.{nombre}"] = params[nombre]
            elif "default" in spec:
                valores[f"inputs.{nombre}"] = str(spec["default"])
            elif not spec.get("optional"):
                sys.exit(f"❌ Falta --param {nombre}=<valor> (no tiene default)")

    salida_base = os.path.join(RAIZ, "salidas_locales", comp["name"])
    for nombre in (comp.get("outputs") or {}):
        ruta = os.path.join(salida_base, nombre)
        os.makedirs(ruta, exist_ok=True)
        valores[f"outputs.{nombre}"] = ruta

    def reemplazar(m):
        clave = m.group(1).strip()
        if clave not in valores:
            sys.exit(f"❌ El command usa ${{{{{clave}}}}} pero no tiene valor")
        return shlex.quote(valores[clave])

    comando = re.sub(r"\$\{\{\s*([^}]+?)\s*\}\}", reemplazar, comp["command"])
    partes = shlex.split(comando)
    if partes[0] == "python":
        partes = partes[1:]
    uv = ["uv", "run", "--quiet", "--no-project"]
    for d in deps_locales():
        uv += ["--with", d]

    print(f"▶️  {comp['name']}  (cwd: {os.path.relpath(code_dir, RAIZ)})")
    print("   " + " ".join(shlex.quote(x) for x in partes))
    r = subprocess.run(uv + ["python"] + partes, cwd=code_dir, env={**os.environ, "MLFLOW_TRACKING_URI": f"file://{salida_base}/mlruns"})
    if r.returncode != 0:
        sys.exit(f"❌ Falló con código {r.returncode}")
    print(f"✅ OK. Salidas en {os.path.relpath(salida_base, RAIZ)}/")
    for nombre in (comp.get("outputs") or {}):
        print(f"   {nombre}: {os.path.relpath(os.path.join(salida_base, nombre), RAIZ)}")


if __name__ == "__main__":
    main()
