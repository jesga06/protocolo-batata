"""
Inimigo Padrão (Estagiário) — Protocolo: Batata
Inimigo básico que persegue o jogador em linha reta e causa dano por contato.
"""

from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_PADRAO_HP, INIMIGO_PADRAO_VELOCIDADE,
    INIMIGO_PADRAO_DANO, INIMIGO_PADRAO_COOLDOWN_ATAQUE,
    INIMIGO_PADRAO_XP
)
from src.utils.traducao import t


class InimigoPadrao(InimigoBase):
    """
    Inimigo rastejante padrão (Gabinete de Firma) com HP baixo, velocidade média e dano de contato moderado.
    """
    nome_exibicao = t("combate_entidades", "inim_padrao")

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_PADRAO_HP,
        velocidade: float = INIMIGO_PADRAO_VELOCIDADE,
        dano_contato: int = INIMIGO_PADRAO_DANO,
        cooldown_contato: float = INIMIGO_PADRAO_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_PADRAO_XP,
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
            score_valor=100,
            largura=28,
            altura=28,
            sprite_key="inimigo_padrao",
            is_elite=is_elite,
            nome_elite=nome_elite
        )

