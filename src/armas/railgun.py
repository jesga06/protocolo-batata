"""
Railgun (Canhão Eletromagnético) — Protocolo: Batata
Arma especial de Slot 3: requer 1.0s de carga energética e dispara um projétil linear perfurante de 50 de dano.
"""

import math
from src.armas.arma_base import ArmaBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import vetor_direcao
from src.utils.constantes import (
    RAILGUN_DANO, RAILGUN_COOLDOWN, RAILGUN_CHARGE_TIME,
    RAILGUN_VELOCIDADE_PROJETIL, RAILGUN_MUNICIAO_MAX,
    obter_caminho_asset
)


class Railgun(ArmaBase):
    """
    Railgun com carga de 1.0s antes do disparo, 50 de dano linear e penetração infinita de inimigos.
    """

    def __init__(
        self,
        dano: int = RAILGUN_DANO,
        cooldown: float = RAILGUN_COOLDOWN,
        tempo_carga: float = RAILGUN_CHARGE_TIME,
        velocidade_projetil: float = RAILGUN_VELOCIDADE_PROJETIL,
        municao_max: int = RAILGUN_MUNICIAO_MAX
    ):
        super().__init__(
            nome="Railgun",
            dano=dano,
            cooldown=cooldown,
            municao_infinita=False,
            municao_max=municao_max,
            slot=3,
            icone_asset="arma_rifle"
        )
        self.tempo_carga = float(tempo_carga)
        self.carga_acumulada = 0.0
        self.carregando = False
        self.velocidade_projetil = float(velocidade_projetil)

    @property
    def progresso_carga(self) -> float:
        """Retorna o percentual de carga de 0.0 a 1.0."""
        return min(1.0, self.carga_acumulada / max(0.01, self.tempo_carga)) if self.carregando else 0.0

    def iniciar_carga(self):
        """Inicia o ciclo de carga da arma com feedback sonoro."""
        if not self.carregando and self.pode_atirar():
            self.carregando = True
            self.carga_acumulada = 0.0
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_tiro_foguete"))
                sfx.play()
            except Exception:
                pass

    def update_carga(self, dt: float) -> bool:
        """
        Avança a carga se a arma estiver sendo preparada.
        Retorna True no instante exato em que a carga atinge 100% (1.0s).
        """
        if self.carregando:
            self.carga_acumulada += dt
            if self.carga_acumulada >= self.tempo_carga:
                self.carregando = False
                self.carga_acumulada = 0.0
                return True
        return False

    def cancelar_carga(self):
        """Cancela a carga atual se o jogador soltar o gatilho."""
        self.carregando = False
        self.carga_acumulada = 0.0

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """
        Dispara o projétil hipersônico perfurante de 50 de dano.
        """
        if not self.pode_atirar():
            return []

        self.tempo_recarga_restante = self.cooldown
        self.municao_atual -= 1
        self.carregando = False
        self.carga_acumulada = 0.0

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_rifle"))
            sfx.play()
        except Exception:
            pass

        dir_x, dir_y = vetor_direcao(origem_x, origem_y, destino_x, destino_y)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        projetil_perfurante = Projetil(
            x=origem_x - 6,
            y=origem_y - 6,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=2.0,
            dono="jogador",
            largura=12,
            altura=12,
            sprite_key="projetil_pistola",
            explosivo=False,
            perfurante=True
        )

        return [projetil_perfurante]
