"""
Drone de Cura — Protocolo: Batata
Equipamento de Slot 4: orbita o jogador e restaura 5 HP periodicamente a cada 3.0s até o teto de vida máxima.
"""

from src.equipamentos.drone_base import DroneBase


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
            nome="Drone de Cura",
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

    def update(self, dt: float, jogador=None, *args, **kwargs):
        """
        Atualiza física orbital e pulsa cura de 5 HP a cada 3.0 segundos.
        """
        super().update(dt, jogador=jogador, *args, **kwargs)
        if not self.ativo:
            return

        self.timer_cura += dt
        if self.timer_cura >= self.intervalo_cura:
            self.timer_cura -= self.intervalo_cura
            if jogador is not None and getattr(jogador, "vivo", True):
                if hasattr(jogador, "curar"):
                    jogador.curar(self.valor_cura)
