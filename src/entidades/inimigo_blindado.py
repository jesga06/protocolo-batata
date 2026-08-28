"""
Inimigo Blindado (Ballistic Enthusiast) — Protocolo: Batata
Inimigo com escudo reforçado e placa balística resistente em X.
"""

from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_BLINDADO_HP, INIMIGO_BLINDADO_VELOCIDADE,
    INIMIGO_BLINDADO_DANO, INIMIGO_BLINDADO_COOLDOWN_ATAQUE,
    INIMIGO_BLINDADO_XP
)


class InimigoBlindado(InimigoBase):
    """
    Inimigo com couraça protetora pesada de 47x47px.
    """

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_BLINDADO_HP,
        velocidade: float = INIMIGO_BLINDADO_VELOCIDADE,
        dano_contato: int = INIMIGO_BLINDADO_DANO,
        cooldown_contato: float = INIMIGO_BLINDADO_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_BLINDADO_XP
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=250,
            largura=47,
            altura=47,
            sprite_key="inimigo_blindado"
        )
