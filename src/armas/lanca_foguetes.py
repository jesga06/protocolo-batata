"""
Lança-Foguetes — Protocolo: Batata
Arma especial de Slot 3: dispara ogivas de alto impacto com grande raio de explosão (AoE de 80px).
Escalado com modificadores de dano explosivo (Config 5: Tremor de Tela).
"""

from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao
from src.utils.constantes import (
    FOGUETES_DANO, FOGUETES_COOLDOWN, FOGUETES_VELOCIDADE_PROJETIL,
    FOGUETES_RAIO_EXPLOSAO, FOGUETES_MUNICIAO_MAX, obter_caminho_asset
)


class LancaFoguetes(ArmaBase):
    """
    Lança-Foguetes com 18 munições e detonação AoE de 80px.
    """

    def __init__(
        self,
        dano: int = FOGUETES_DANO,
        cooldown: float = FOGUETES_COOLDOWN,
        velocidade_projetil: float = FOGUETES_VELOCIDADE_PROJETIL,
        raio_explosao: float = FOGUETES_RAIO_EXPLOSAO,
        municao_max: int = FOGUETES_MUNICIAO_MAX
    ):
        super().__init__(
            nome="Lança-Foguetes",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_foguetes"
        )
        self.velocidade_projetil = float(velocidade_projetil)
        self.raio_explosao = float(raio_explosao)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara 1 foguete balístico pesado e consome 1 munição.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown
        self.municao_atual -= 1

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        projetil = Projetil(
            x=origem_x - 7.0,
            y=origem_y - 7.0,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=3.0,
            dono="jogador",
            largura=14,
            altura=14,
            sprite_key="projetil_foguete",
            explosivo=True,
            raio_explosao=self.raio_explosao,
            aceleracao=680.0,
            chao_em_chamas=True
        )

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_foguete"))
            sfx.play()
        except Exception:
            pass

        return [projetil]
