"""
Escopeta (Shotgun) — Protocolo: Batata
Arma especial de Slot 3: disparo de múltiplos projéteis (pellets) em leque cônico com alto impacto a curta distância.
"""

import math
from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao, rotacionar_vetor
from src.utils.constantes import (
    SHOTGUN_DANO, SHOTGUN_COOLDOWN, SHOTGUN_VELOCIDADE_PROJETIL,
    SHOTGUN_PELLETS, SHOTGUN_SPREAD_ANGULO, SHOTGUN_MUNICIAO_MAX,
    obter_caminho_asset
)


class Shotgun(ArmaBase):
    """
    Escopeta de 30 cartuchos com dispersão de 5 pellets em um cone de 0.35 rad.
    """

    def __init__(
        self,
        dano: int = SHOTGUN_DANO,
        cooldown: float = SHOTGUN_COOLDOWN,
        velocidade_projetil: float = SHOTGUN_VELOCIDADE_PROJETIL,
        pellets: int = SHOTGUN_PELLETS,
        spread_angulo: float = SHOTGUN_SPREAD_ANGULO,
        municao_max: int = SHOTGUN_MUNICIAO_MAX
    ):
        super().__init__(
            nome="Escopeta",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_shotgun"
        )
        self.velocidade_projetil = float(velocidade_projetil)
        self.pellets = int(pellets)
        self.spread_angulo = float(spread_angulo)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara 5 pellets distribuídos simetricamente no arco angular de 0.35 rad e consome 1 cartucho.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown
        self.municao_atual -= 1

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        projeteis = []
        if self.pellets <= 1:
            offsets = [0.0]
        else:
            meio_leque = self.spread_angulo / 2.0
            passo = self.spread_angulo / (self.pellets - 1)
            offsets = [-meio_leque + i * passo for i in range(self.pellets)]

        for offset in offsets:
            p_dx, p_dy = rotacionar_vetor(dir_x, dir_y, offset)
            proj = Projetil(
                x=origem_x,
                y=origem_y,
                dir_x=p_dx,
                dir_y=p_dy,
                velocidade=self.velocidade_projetil,
                dano=self.dano,
                tempo_vida=1.2,
                dono="jogador",
                sprite_key="projetil_shotgun"
            )
            projeteis.append(proj)

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_shotgun"))
            sfx.play()
        except Exception:
            pass

        return projeteis
