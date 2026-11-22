"""
Railgun (Canhão Eletromagnético) — Protocolo: Batata
Arma especial de Slot 3 (port 1:1 da v2): disparo instantâneo em feixe hitscan de 1800 px,
165 de dano, 10 cargas e penetração total em linha reta.
"""

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
    Railgun eletromagnética instantânea (165 de dano, 10 de munição, alcance 1800 px).
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
            icone_asset="arma_railgun"
        )
        self.tempo_carga = float(tempo_carga)
        self.carga_acumulada = 0.0
        self.carregando = False
        self.velocidade_projetil = float(velocidade_projetil)

    @property
    def progresso_carga(self) -> float:
        return 1.0 if self.tempo_carga <= 0.0 else 0.0

    def iniciar_carga(self):
        self.carregando = False
        self.carga_acumulada = 0.0

    def update_carga(self, dt: float) -> bool:
        return True

    def cancelar_carga(self):
        self.carregando = False
        self.carga_acumulada = 0.0

    def _tocar_sfx_disparo(self):
        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_railgun"))
            sfx.play()
        except Exception:
            pass

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
        self.carregando = False
        self.carga_acumulada = 0.0
        self._tocar_sfx_disparo()

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

    def disparar(self, origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> list[Projetil]:
        """Fallback de compatibilidade para retornos baseados em Projetil."""
        feixe = self.disparar_feixe(origem_x, origem_y, destino_x, destino_y)
        if not feixe:
            return []

        return [Projetil(
            x=origem_x - 6,
            y=origem_y - 6,
            dir_x=feixe["dir_x"],
            dir_y=feixe["dir_y"],
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=2.0,
            dono="jogador",
            largura=12,
            altura=12,
            sprite_key="projetil_pistola",
            explosivo=False,
            perfurante=True,
            trilha_plasma=True,
            origem_trilha=(origem_x, origem_y)
        )]
