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
from src.utils.traducao import t


class Pistola(ArmaBase):
    """
    Pistola inicial com munição infinita e cadência média de tiro.
    """

    def __init__(
        self,
        dano: int = PISTOLA_DANO,
        cooldown: float = PISTOLA_COOLDOWN,
        velocidade_projetil: float = PISTOLA_VELOCIDADE_PROJETIL,
        tempo_vida_projetil: float = 2.5
    ):
        super().__init__(
            nome=t("combate_entidades", "arma_pistola"),
            dano=dano,
            cooldown=cooldown,
            municao_infinita=True,
            slot=2,
            icone_asset="arma_pistola"
        )
        self.velocidade_projetil = float(velocidade_projetil)
        self.tempo_vida_projetil = float(tempo_vida_projetil)
        self.contador_tiros: int = 0

    @property
    def pips_carga(self) -> int:
        """Retorna a carga atual do ciclo de 4 disparos (0..3)."""
        return self.contador_tiros % 4

    @property
    def esta_carregada(self) -> bool:
        """Retorna True quando o próximo disparo será o 4º tiro sobrecarregado."""
        return self.pips_carga == 3

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

        self.contador_tiros += 1
        if self.contador_tiros % 4 == 0:
            projetil = Projetil(
                x=origem_x - 6.0,
                y=origem_y - 6.0,
                dir_x=dir_x,
                dir_y=dir_y,
                velocidade=self.velocidade_projetil,
                dano=int(round(self.dano * 2.2)),
                tempo_vida=self.tempo_vida_projetil,
                dono="jogador",
                largura=12,
                altura=12,
                perfurante=True,
                cor=(0, 230, 255),
                sobrecarregado=True
            )
        else:
            projetil = Projetil(
                x=origem_x - 4.0,
                y=origem_y - 4.0,
                dir_x=dir_x,
                dir_y=dir_y,
                velocidade=self.velocidade_projetil,
                dano=self.dano,
                tempo_vida=self.tempo_vida_projetil,
                dono="jogador",
                largura=8,
                altura=8
            )

        return [projetil]
