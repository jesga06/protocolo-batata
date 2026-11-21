"""
Drone de Suporte — Protocolo: Batata
Equipamento de Slot 4: concede +15% de velocidade de movimento ao jogador e atração magnética de drops em um raio de 150px.
"""

from src.equipamentos.drone_base import DroneBase
from src.utils.math_utils import distancia


class DroneSuporte(DroneBase):
    """
    Drone utilitário que amplifica a mobilidade da batata e atrai itens e gemas de XP.
    """

    def __init__(
        self,
        tempo_vida: float = 30.0,
        bonus_velocidade: float = 0.15,
        raio_magnetico: float = 150.0,
        velocidade_magnetica: float = 250.0,
        raio_orbita: float = 48.0,
        velocidade_angular: float = 2.5
    ):
        super().__init__(
            nome="Drone de Suporte",
            icone_asset="drone_suporte",
            sprite_key="drone_suporte",
            tempo_vida=tempo_vida,
            raio_orbita=raio_orbita,
            velocidade_angular=velocidade_angular,
            hp=1
        )
        self.bonus_velocidade = float(bonus_velocidade)
        self.raio_magnetico = float(raio_magnetico)
        self.velocidade_magnetica = float(velocidade_magnetica)
        self.timer_estase: float = 0.0
        self.intervalo_estase: float = 3.5
        self.zonas_estase_pendentes: list = []

    def update(self, dt: float, jogador=None, drops: list = None, *args, **kwargs):
        """
        Atualiza física orbital e atrai todos os drops no chão dentro do raio magnético de 150px em direção ao jogador.
        """
        super().update(dt, jogador=jogador, *args, **kwargs)
        if not self.ativo:
            return

        raio_efetivo = self.raio_magnetico + (getattr(self, "nivel_mk", 1) - 1) * 35.0

        if jogador is not None and drops:
            j_cx = jogador.x + getattr(jogador, "largura", 32) / 2.0
            j_cy = jogador.y + getattr(jogador, "altura", 32) / 2.0

            for drop in drops:
                if not getattr(drop, "ativo", True) or getattr(drop, "coletado", False):
                    continue
                if getattr(drop, "tipo", "") == "capsula_powerup":
                    continue

                d_cx = drop.x + getattr(drop, "largura", 42) / 2.0
                d_cy = drop.y + getattr(drop, "altura", 42) / 2.0
                dist = distancia(j_cx, j_cy, d_cx, d_cy)

                if dist <= raio_efetivo and dist > 0.1:
                    # Move o drop em direção ao centro do jogador sem ultrapassá-lo (evita overshoot)
                    dx = (j_cx - d_cx) / dist
                    dy = (j_cy - d_cy) / dist
                    passo = min(self.velocidade_magnetica * dt, dist)
                    drop.x += dx * passo
                    drop.y += dy * passo

        self.timer_estase += dt
        if self.timer_estase >= self.intervalo_estase:
            inimigos = kwargs.get("inimigos", None)
            if inimigos and jogador is not None:
                j_cx = jogador.x + getattr(jogador, "largura", 32) / 2.0
                j_cy = jogador.y + getattr(jogador, "altura", 32) / 2.0
                for inim in inimigos:
                    if getattr(inim, "vivo", True):
                        i_cx = inim.x + getattr(inim, "largura", 28) / 2.0
                        i_cy = inim.y + getattr(inim, "altura", 28) / 2.0
                        if distancia(j_cx, j_cy, i_cx, i_cy) <= 320.0:
                            self.timer_estase = 0.0
                            self.zonas_estase_pendentes.append({
                                "x": inim.x + getattr(inim, "largura", 28) / 2.0,
                                "y": inim.y + getattr(inim, "altura", 28) / 2.0,
                                "raio": 85.0 + (getattr(self, "nivel_mk", 1) - 1) * 20.0,
                                "tempo": 3.0,
                                "tempo_max": 3.0
                            })
                            break
