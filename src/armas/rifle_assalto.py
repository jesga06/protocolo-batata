"""
Rifle de Assalto — Protocolo: Batata
Arma especial de Slot 3: disparos precisos em linha reta com projéteis de altíssima velocidade e dano moderado.
"""

from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao
from src.utils.constantes import (
    RIFLE_DANO, RIFLE_COOLDOWN, RIFLE_VELOCIDADE_PROJETIL,
    RIFLE_MUNICIAO_MAX, obter_caminho_asset
)


class RifleAssalto(ArmaBase):
    """
    Rifle de assalto com 60 tiros, alta cadência e máxima precisão linear.
    """

    def __init__(
        self,
        dano: int = RIFLE_DANO,
        cooldown: float = RIFLE_COOLDOWN,
        velocidade_projetil: float = RIFLE_VELOCIDADE_PROJETIL,
        municao_max: int = RIFLE_MUNICIAO_MAX
    ):
        super().__init__(
            nome="Rifle de Assalto",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_rifle"
        )
        self.velocidade_projetil = float(velocidade_projetil)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara 1 projétil retilíneo veloz e consome 1 munição.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown
        self.municao_atual -= 1

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        projetil = Projetil(
            x=origem_x,
            y=origem_y,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=2.5,
            dono="jogador",
            sprite_key="projetil_rifle"
        )

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_rifle"))
            sfx.play()
        except Exception:
            pass

        return [projetil]
