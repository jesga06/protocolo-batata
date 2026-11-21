"""
Minigun — Protocolo: Batata
Arma especial de Slot 3: altíssima cadência de tiro, leve dispersão e grande capacidade de munição.
"""

import random
from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao, rotacionar_vetor
from src.utils.constantes import (
    MINIGUN_DANO, MINIGUN_COOLDOWN, MINIGUN_VELOCIDADE_PROJETIL,
    MINIGUN_MUNICIAO_MAX, obter_caminho_asset
)


class Minigun(ArmaBase):
    """
    Minigun de alta cadência com 225 tiros e leve dispersão angular.
    """

    def __init__(
        self,
        dano: int = MINIGUN_DANO,
        cooldown: float = MINIGUN_COOLDOWN,
        velocidade_projetil: float = MINIGUN_VELOCIDADE_PROJETIL,
        municao_max: int = MINIGUN_MUNICIAO_MAX,
        spread_max_rad: float = 0.06
    ):
        super().__init__(
            nome="Minigun",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_minigun"
        )
        self.velocidade_projetil = float(velocidade_projetil)
        self.spread_max_rad = float(spread_max_rad)
        self.fator_spin: float = 0.0
        self.tempo_sem_atirar: float = 0.0

    def update(self, dt: float):
        super().update(dt)
        self.tempo_sem_atirar += dt
        if self.tempo_sem_atirar > 0.22:
            self.fator_spin = max(0.0, self.fator_spin - dt * 1.4)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara 1 projétil rápido com leve dispersão e consome 1 munição.
        """
        if not self.pode_atirar():
            return []

        self.tempo_sem_atirar = 0.0
        self.fator_spin = min(1.0, self.fator_spin + 0.08)
        self.tempo_recarga_restante = self.cooldown * (1.0 - 0.45 * self.fator_spin)
        self.municao_atual -= 1

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        # Aplica dispersão angular sutil
        desvio = random.uniform(-self.spread_max_rad, self.spread_max_rad)
        if desvio != 0.0:
            dir_x, dir_y = rotacionar_vetor(dir_x, dir_y, desvio)

        projetil = Projetil(
            x=origem_x - 3.0,
            y=origem_y - 3.0,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=2.2,
            dono="jogador",
            largura=6,
            altura=6,
            sprite_key="projetil_minigun",
            recuo_autor=16.0
        )

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_minigun"))
            sfx.play()
        except Exception:
            pass

        return [projetil]
