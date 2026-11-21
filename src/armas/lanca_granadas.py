"""
Lança-Granadas — Protocolo: Batata
Arma especial de Slot 3: dispara granadas explosivas com raio de ação de 65px e boa cadência de disparo.
Escalado com modificadores de dano explosivo (Config 5: Tremor de Tela).
"""

from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao
from src.utils.constantes import (
    GRANADAS_DANO, GRANADAS_COOLDOWN, GRANADAS_VELOCIDADE_PROJETIL,
    GRANADAS_RAIO_EXPLOSAO, GRANADAS_MUNICIAO_MAX, obter_caminho_asset
)


class LancaGranadas(ArmaBase):
    """
    Lança-Granadas com 24 projéteis explosivos de raio 65px.
    """

    def __init__(
        self,
        dano: int = GRANADAS_DANO,
        cooldown: float = GRANADAS_COOLDOWN,
        velocidade_projetil: float = GRANADAS_VELOCIDADE_PROJETIL,
        raio_explosao: float = GRANADAS_RAIO_EXPLOSAO,
        municao_max: int = GRANADAS_MUNICIAO_MAX
    ):
        super().__init__(
            nome="Lança-Granadas",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_granadas"
        )
        self.velocidade_projetil = float(velocidade_projetil)
        self.raio_explosao = float(raio_explosao)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara 1 granada explosiva e consome 1 munição.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown
        self.municao_atual -= 1

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        projetil = Projetil(
            x=origem_x - 6.0,
            y=origem_y - 6.0,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=1.0,
            dono="jogador",
            largura=12,
            altura=12,
            sprite_key="projetil_granada",
            explosivo=True,
            raio_explosao=self.raio_explosao,
            desaceleracao=self.velocidade_projetil,
            arco_parabolico=True,
            fragmentar=True
        )

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_granada"))
            sfx.play()
        except Exception:
            pass

        return [projetil]
