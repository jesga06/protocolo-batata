"""
Re-export do Chefe Final: Geladeira Tsunami ("The Perfect Sound™") — Protocolo: Batata
Localização canônica: src/entidades/inimigos/geladeira_tsunami.py
"""

from src.entidades.inimigos.geladeira_tsunami import (
    GeladeiraTsunami,
    ESTADO_INTRO,
    ESTADO_FASE1,
    ESTADO_FASE2,
    ESTADO_FASE3,
    ESTADO_MORTE
)

__all__ = [
    "GeladeiraTsunami",
    "ESTADO_INTRO",
    "ESTADO_FASE1",
    "ESTADO_FASE2",
    "ESTADO_FASE3",
    "ESTADO_MORTE"
]
