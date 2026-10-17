# TODOS

## Infrastructure

### Integración continua de Kauta en GitHub Actions

**What:** Un workflow que en cada push y PR a `main` corra `pytest -q` en `kauta/` y `npm ci && npm run typecheck && npm run build` en `kauta/web/`.

**Why:** Cada push a `main` se despliega solo en Vercel; sin CI, una prueba en rojo llega a la URL del jurado sin aviso previo.

**Context:** Surgió en /plan-eng-review del 2026-10-17 (registro R13 de `docs/designs/kauta-finops-rediseno.md`). Kauta usa Python 3.12 y Node con Vite 8; la suite tarda unos 18 s y no necesita clave de IA. Pros: aviso en rojo antes de abrir la demo y protección del contrato de regresión D8 en cada push. Contras: un archivo más que mantener; no bloquea el despliegue de Vercel salvo que se configure como verificación requerida. Para empezar: `.github/workflows/kauta.yml` con dos jobs (python y web).

**Effort:** S
**Priority:** P2
**Depends on:** que `kauta/` exista en el repositorio (paso 1 del plan).

## Completed
