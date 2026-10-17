"""Aísla toda la suite antes de importar la configuración del servidor."""
import os
import sys
import tempfile

import pytest


# test_costos también importa CONFIG durante la recolección. Preparar aquí
# el entorno evita que el orden de los archivos seleccione la base de la demo.
_VAR_PRUEBAS = tempfile.TemporaryDirectory(prefix="kauta-test-")
os.environ["KAUTA_VAR"] = _VAR_PRUEBAS.name
os.environ["KAUTA_BD"] = f"sqlite:///{_VAR_PRUEBAS.name}/prueba.db"


@pytest.fixture(scope="session", autouse=True)
def entorno_aislado():
    yield
    modulo_bd = sys.modules.get("servidor.db")
    if modulo_bd is not None:
        modulo_bd.motor_bd.dispose()
    _VAR_PRUEBAS.cleanup()
