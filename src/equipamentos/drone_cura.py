"""
Drone de Cura — Protocolo: Batata
Equipamento de Slot 4: orbita o jogador e restaura 5 HP periodicamente a cada 3.0s até o teto de vida máxima.
"""

from src.equipamentos.drone_base import DroneBase
from src.utils.traducao import t


class DroneCura(DroneBase):
    """
    Drone companheiro médico que pulsa cura a cada 3.0 segundos.
    """

    def __init__(
        self,
        tempo_vida: float = 30.0,
        intervalo_cura: float = 3.0,
        valor_cura: int = 5,
        raio_orbita: float = 48.0,
        velocidade_angular: float = 2.5
    ):
        super().__init__(
            nome=t("combate_entidades", "drone_cura"),
            icone_asset="drone_cura",
            sprite_key="drone_cura",
            tempo_vida=tempo_vida,
            raio_orbita=raio_orbita,
            velocidade_angular=velocidade_angular,
            hp=1
        )
        self.intervalo_cura = float(intervalo_cura)
        self.valor_cura = int(valor_cura)
        self.timer_cura = 0.0
        self.feixe_cura_timer: float = 0.0
        self.ultimo_valor_curado: int = 0

    def update(self, dt: float, jogador=None, *args, **kwargs):
        """
        Atualiza física orbital e pulsa cura de 5 HP a cada 3.0 segundos.
        """
        super().update(dt, jogador=jogador, *args, **kwargs)
        if not self.ativo:
            return

        self.feixe_cura_timer = max(0.0, self.feixe_cura_timer - dt)

        self.timer_cura += dt
        if self.timer_cura >= self.intervalo_cura:
            self.timer_cura -= self.intervalo_cura
            if jogador is not None and getattr(jogador, "vivo", True):
                cura_mk = self.valor_cura + (getattr(self, "nivel_mk", 1) - 1) * 3
                hp_antes = getattr(jogador, "hp", 0)
                hp_max = getattr(jogador, "hp_max", 150)
                if hasattr(jogador, "curar"):
                    jogador.curar(cura_mk)
                excedente = max(0, (hp_antes + cura_mk) - hp_max)
                if excedente > 0 and hasattr(jogador, "escudo_sobrevida"):
                    jogador.escudo_sobrevida = min(25, getattr(jogador, "escudo_sobrevida", 0) + excedente)
                self.feixe_cura_timer = 0.45
                self.ultimo_valor_curado = cura_mk
                jogador.evento_cura_drone = cura_mk

    def desenhar(self, janela, camera=None):
        super().desenhar(janela, camera)
