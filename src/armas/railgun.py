"""
Railgun (Canhão Eletromagnético) — Protocolo: Batata
Arma especial de Slot 3 (port 1:1 da v2): disparo instantâneo em feixe hitscan de 1800 px,
165 de dano, 10 cargas e penetração total em linha reta.
"""

from src.armas.arma_base import ArmaBase
from src.utils.math_utils import vetor_direcao
from src.utils.constantes import (
    RAILGUN_DANO, RAILGUN_COOLDOWN,
    RAILGUN_VELOCIDADE_PROJETIL, RAILGUN_MUNICIAO_MAX,
)
from src.utils.traducao import t


class Railgun(ArmaBase):
    """
    Railgun eletromagnética instantânea (165 de dano, 10 de munição, alcance 1800 px).
    """

    def __init__(
        self,
        dano: int = RAILGUN_DANO,
        cooldown: float = RAILGUN_COOLDOWN,
        velocidade_projetil: float = RAILGUN_VELOCIDADE_PROJETIL,
        municao_max: int = RAILGUN_MUNICIAO_MAX
    ):
        super().__init__(
            nome=t("combate_entidades", "arma_railgun"),
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_railgun"
        )
        self.velocidade_projetil = float(velocidade_projetil)

    def disparar_feixe(
        self,
        origem_x: float,
        origem_y: float,
        destino_x: float,
        destino_y: float,
        alcance: float = 1800.0
    ) -> dict | None:
        """Dispara o feixe hitscan instantâneo de 1800 px e consome 1 carga."""
        if not self.pode_atirar():
            return None

        self.tempo_recarga_restante = self.cooldown
        self.municao_atual -= 1

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        return {
            "x1": float(origem_x),
            "y1": float(origem_y),
            "x2": float(origem_x + dir_x * alcance),
            "y2": float(origem_y + dir_y * alcance),
            "dir_x": float(dir_x),
            "dir_y": float(dir_y),
            "dano": int(self.dano),
            "raio": 14.0,
        }

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list:
        """Railgun usa exclusivamente disparar_feixe() no pipeline hitscan."""
        return []
