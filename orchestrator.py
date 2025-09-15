#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orquestador de Proyecto Google - Versión UTF-8
===============================================

Orquestador para ejecutar api_youtube.py y financial_api.py
secuencialmente, con configuración específica para resolver problemas de codificación UTF-8 en Windows.
"""

import subprocess
import sys
import datetime
import os


def configure_utf8_environment():
    """Configura el entorno para manejar UTF-8 correctamente en Windows"""
    # Configurar variables de entorno para UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Intentar configurar la codificación de la consola
    try:
        # Esto funciona en Windows 10 versión 1903 y posteriores
        os.system('chcp 65001 > nul 2>&1')
    except:
        pass
    
    print("✓ Configuración UTF-8 aplicada")


def run_script(script_path: str) -> tuple[int, str, str]:
    """
    Ejecuta un script Python como subproceso y captura stdout/stderr con configuración UTF-8.
    Returns: (returncode, stdout, stderr)
    """
    try:
        completed = subprocess.run(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',  # Reemplazar caracteres problemáticos
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
            check=False,
            timeout=300  # 5 minutos máximo por script
        )
        return completed.returncode, completed.stdout, completed.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout: {script_path} tardó más de 5 minutos en ejecutarse"
    except Exception as e:
        return 1, "", f"Error al ejecutar {script_path}: {e}"


def log_run(step: str, returncode: int, stdout: str, stderr: str, log_dir: str) -> str:
    """
    Guarda un log por paso con timestamp y devuelve la ruta del archivo de log.
    """
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{ts}_{step}.log")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"STEP: {step}\n")
            f.write(f"RETURNCODE: {returncode}\n\n")
            f.write("STDOUT:\n")
            f.write(stdout or "")
            f.write("\n\nSTDERR:\n")
            f.write(stderr or "")
        return log_path
    except Exception:
        return ""


def main():
    print(">>> Iniciando el proceso de orquestación con configuración UTF-8 <<<")
    
    # Configurar entorno UTF-8
    configure_utf8_environment()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "logs")

    steps = [
        ("api_youtube", os.path.join(base_dir, "api_youtube.py")),
        ("financial_api", os.path.join(base_dir, "financial_api.py")),
    ]

    overall_success = True
    for step_name, script in steps:
        print(f"\n=== Ejecutando: {step_name} ===")
        code, out, err = run_script(script)
        log_file = log_run(step_name, code, out, err, log_dir)
        if log_file:
            print(f"Log guardado en: {log_file}")
        if code != 0:
            overall_success = False
            print(f"✗ ERROR en {step_name} (returncode={code}). Se continúa con el siguiente paso.")
        else:
            print(f"✓ {step_name} ejecutado exitosamente")

    print("\n" + "="*60)
    if overall_success:
        print("✓ Orquestación completada con éxito.")
        sys.exit(0)
    else:
        print("⚠️  Orquestación completada con errores. Revisa los logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()


