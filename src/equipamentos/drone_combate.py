"""
Drone de Combate — Protocolo: Batata
Equipamento de Slot 4: orbita o jogador, rastreia o inimigo mais próximo em um raio de 350px e dispara a cada 1.0s (dano 8).
"""

from src.equipamentos.drone_base import DroneBase
from src.entidades.projetil import Projetil
from src.utils.math_utils import distancia, vetor_direcao
from src.utils.constantes import obter_caminho_asset


class DroneCombate(DroneBase):
    """
    Drone de suporte balístico com mira automática e disparos periódicos.
    """

    def __init__(
        self,
        tempo_vida: float = 30.0,
        cooldown_tiro: float = 1.0,
        dano: int = 8,
        alcance_deteccao: float = 350.0,
        velocidade_projetil: float = 480.0,
        raio_orbita: float = 48.0,
        velocidade_angular: float = 2.5
    ):
        super().__init__(
            nome="Drone de Combate",
            icone_asset="drone_combate",
            sprite_key="drone_combate",
            tempo_vida=tempo_vida,
            raio_orbita=raio_orbita,
            velocidade_angular=velocidade_angular,
            hp=1
        )
        self.cooldown_tiro = float(cooldown_tiro)
        self.timer_tiro = 0.0
        self.dano = int(dano)
        self.alcance_deteccao = float(alcance_deteccao)
        self.velocidade_projetil = float(velocidade_projetil)

    def disparar_no_alvo(self, alvo) -> list[Projetil]:
        """Gera um projétil apontado do centro do drone para o alvo."""
        d_cx = self.x + self.largura / 2.0
        d_cy = self.y + self.altura / 2.0
        a_cx = alvo.x + getattr(alvo, "largura", 28) / 2.0
        a_cy = alvo.y + getattr(alvo, "altura", 28) / 2.0

        dir_x, dir_y = vetor_direcao(d_cx, d_cy, a_cx, a_cy)
        if dir_x == 0.0 and dir_y == 0.0:
            dir_x = 1.0

        proj = Projetil(
            x=d_cx,
            y=d_cy,
            dir_x=dir_x,
            dir_y=dir_y,
            velocidade=self.velocidade_projetil,
            dano=self.dano,
            tempo_vida=1.8,
            dono="jogador",
            sprite_key="projetil_pistola"
        )

        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_tiro_pistola"))
            sfx.play()
        except Exception:
            pass

        return [proj]

    def update(self, dt: float, jogador=None, inimigos: list = None, *args, **kwargs) -> list[Projetil]:
        """
        Atualiza órbita e executa aquisição de alvos dentro de 350px para disparo a cada 1.0s.
        Retorna lista de novos projéteis gerados.
        """
        super().update(dt, jogador=jogador, *args, **kwargs)
        if not self.ativo:
            return []

        self.timer_tiro += dt
        if self.timer_tiro >= self.cooldown_tiro:
            if inimigos:
                d_cx = self.x + self.largura / 2.0
                d_cy = self.y + self.altura / 2.0

                melhor_alvo = None
                menor_dist = self.alcance_deteccao

                for inimigo in inimigos:
                    if not getattr(inimigo, "vivo", True):
                        continue
                    e_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                    e_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                    dist = distancia(d_cx, d_cy, e_cx, e_cy)

                    if dist <= menor_dist:
                        menor_dist = dist
                        melhor_alvo = inimigo

                if melhor_alvo is not None:
                    self.timer_tiro = 0.0
                    return self.disparar_no_alvo(melhor_alvo)

        return []
