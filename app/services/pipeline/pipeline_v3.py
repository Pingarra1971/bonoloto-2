"""
Alias de compatibilidad: PipelineV3 ahora apunta a PipelineV4 (v7.0).
Si tu código importa `from app.services.pipeline.pipeline_v3 import PipelineV3`, sigue funcionando.
"""
from app.services.pipeline.pipeline_v4 import PipelineV4 as PipelineV3
from app.services.pipeline.pipeline_v4 import ResultadoPipeline

__all__ = ["PipelineV3", "ResultadoPipeline"]
