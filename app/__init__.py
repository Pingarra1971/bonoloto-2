"""
Bonoloto 2.0 — sistema cuantitativo de análisis aplicado a la Bonoloto.

Estructura:
  app/api              endpoints HTTP (FastAPI)
  app/domain           lógica de dominio (algoritmos, modelos)
  app/services         orquestación (pipeline, calibración, cálculo)
  app/infrastructure   adaptadores (BD, autenticación, scheduler)
  tests                pruebas unitarias e integración
"""
__version__ = "2.0.0"
