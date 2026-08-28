"""
Inimigo Phasing (Warranty Void) — Protocolo: Batata
Inimigo fantasma ciano translúcido com alternância periódica de fase.
"""

from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_PHASING_HP, INIMIGO_PHASING_VELOCIDADE,
    INIMIGO_PHASING_DANO, INIMIGO_PHASING_COOLDOWN_ATAQUE,
    INIMIGO_PHASING_XP, INIMIGO_PHASING_CICLO
)


class InimigoPhasing(InimigoBase):
    """
    Inimigo etéreo que atravessa o campo e persegue a batata com sprite semi-transparente.
    """

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_PHASING_HP,
        velocidade: float = INIMIGO_PHASING_VELOCIDADE,
        dano_contato: int = INIMIGO_PHASING_DANO,
        cooldown_contato: float = INIMIGO_PHASING_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_PHASING_XP
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=200,
            largura=42,
            altura=42,
            sprite_key="inimigo_phasing"
        )
