"""
Pistola (Padrão de Fábrica) — Protocolo: Batata
Arma de Slot 2 permanente do jogador com munição infinita e disparo direto.
"""

from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao
from src.utils.constantes import (
    PISTOLA_DANO, PISTOLA_COOLDOWN, PISTOLA_VELOCIDADE_PROJETIL,
    obter_caminho_asset
)


class Pistola(ArmaBase):
    """
    Pistola inicial com munição infinita e cadência média de tiro.
    """

    def __init__(
        self,
        dano: int = PISTOLA_DANO,
        cooldown: float = 0.33,
        velocidade_projetil: float = 420.0,
        tempo_vida_projetil: float = 2.5
    ):
        super().__init__(
            nome="Padrão de Fábrica",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=True,
            slot=2,
            icone_asset="arma_pistola"
        )
        self.velocidade_projetil = float(velocidade_projetil)
        self.tempo_vida_projetil = float(tempo_vida_projetil)

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara um projétil em direção ao ponto de destino (mira do mouse).
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0  # Direção padrão para a direita se coincidirem

        projetil = Projetil(
            x=origem_x,
            y=origem_y,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=self.tempo_vida_projetil,
            dono="jogador"
        )

        # Tenta reproduzir efeito sonoro de tiro de forma segura
        try:
            from PPlay.sound import Sound
            sfx_path = obter_caminho_asset("sfx_tiro_pistola")
            sfx = Sound(sfx_path)
            sfx.play()
        except Exception:
            pass

        return [projetil]
