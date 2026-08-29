"""
Inimigo Rápido (Viciado em Cafeína) — Protocolo: Batata
Inimigo ágil em forma de cunha verde neon com alta velocidade e baixo HP.
"""

from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_RAPIDO_HP, INIMIGO_RAPIDO_VELOCIDADE,
    INIMIGO_RAPIDO_DANO, INIMIGO_RAPIDO_COOLDOWN_ATAQUE,
    INIMIGO_RAPIDO_XP
)


class InimigoRapido(InimigoBase):
    """
    Inimigo veloz de assédio que persegue o jogador em ritmo frenético.
    """

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_RAPIDO_HP,
        velocidade: float = INIMIGO_RAPIDO_VELOCIDADE,
        dano_contato: int = INIMIGO_RAPIDO_DANO,
        cooldown_contato: float = INIMIGO_RAPIDO_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_RAPIDO_XP,
        is_elite: bool = False,
        nome_elite: str = ""
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=150,
            largura=31,
            altura=31,
            sprite_key="inimigo_rapido",
            is_elite=is_elite,
            nome_elite=nome_elite
        )

