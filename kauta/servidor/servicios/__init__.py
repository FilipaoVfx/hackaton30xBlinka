"""Lógica de negocio del servidor. Las rutas HTTP solo validan, autorizan y llaman a estos servicios."""
import threading

# Las operaciones que mueven dinero o escriben en la cadena de auditoría se serializan.
# En PostgreSQL se reemplaza por un bloqueo transaccional (pg_advisory_xact_lock) y SELECT … FOR UPDATE.
BLOQUEO = threading.RLock()
