"""
Inimigo Ranged (Atirador Blaster) — Protocolo: Batata
Inimigo com canhão frontal de disparo de projéteis e chassi ferrugem.
"""

from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_RANGED_HP, INIMIGO_RANGED_VELOCIDADE,
    INIMIGO_RANGED_DANO, INIMIGO_RANGED_COOLDOWN_ATAQUE,
    INIMIGO_RANGED_XP
)


class InimigoRanged(InimigoBase):
    """
    Inimigo armado com canhão balístico.
    """

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_RANGED_HP,
        velocidade: float = INIMIGO_RANGED_VELOCIDADE,
        dano_contato: int = INIMIGO_RANGED_DANO,
        cooldown_contato: float = INIMIGO_RANGED_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_RANGED_XP
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
            sprite_key="inimigo_ranged"
        )
