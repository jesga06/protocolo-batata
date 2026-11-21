"""
Inimigo Tanque (Geladeira Industrial) — Protocolo: Batata
Inimigo pesado de grande porte com alta resistência, velocidade lenta e alto dano de contato.
"""

from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_TANK_HP, INIMIGO_TANK_VELOCIDADE,
    INIMIGO_TANK_DANO, INIMIGO_TANK_COOLDOWN_ATAQUE,
    INIMIGO_TANK_XP
)


class InimigoTank(InimigoBase):
    """
    Inimigo tanque (Copiadora Xerox) com carcaça de 62x62px e alta barra de vida.
    """
    nome_exibicao = "Copiadora Xerox"

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_TANK_HP,
        velocidade: float = INIMIGO_TANK_VELOCIDADE,
        dano_contato: int = INIMIGO_TANK_DANO,
        cooldown_contato: float = INIMIGO_TANK_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_TANK_XP,
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
            score_valor=300,
            largura=62,
            altura=62,
            sprite_key="inimigo_tank",
            is_elite=is_elite,
            nome_elite=nome_elite
        )

