"""
Cubo Criogênico — Goon de Gelo da Geladeira Tsunami
Patina em direção ao jogador e dispara fragmentos criogênicos.
"""

from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.utils.constantes import (
    INIMIGO_CUBO_CRIOGENICO_HP,
    INIMIGO_CUBO_CRIOGENICO_VELOCIDADE,
    INIMIGO_CUBO_CRIOGENICO_DANO,
    INIMIGO_CUBO_CRIOGENICO_XP,
)
from src.utils.math_utils import distancia, vetor_direcao, lerp
from src.utils.traducao import t


class CuboCriogenico(InimigoBase):
    nome_exibicao = t("combate_entidades", "inim_cubo_criogenico")

    def __init__(self, x: float, y: float):
        super().__init__(
            x=x,
            y=y,
            hp=INIMIGO_CUBO_CRIOGENICO_HP,
            velocidade=INIMIGO_CUBO_CRIOGENICO_VELOCIDADE,
            dano_contato=INIMIGO_CUBO_CRIOGENICO_DANO,
            cooldown_contato=0.5,
            xp_valor=INIMIGO_CUBO_CRIOGENICO_XP,
            score_valor=120,
            largura=34,
            altura=34,
            sprite_key="cubo_criogenico",
        )
        self.timer_tiro = 0.6
        self.cooldown_tiro = 2.4
        self.projeteis_pendentes: list[Projetil] = []

    def update(self, dt: float, pos_alvo: tuple[float, float], vel_alvo: tuple[float, float] = None):
        if not self.vivo:
            return
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo
        dist = distancia(cx, cy, tx, ty)
        ux, uy = vetor_direcao(cx, cy, tx, ty)

        self.x += (ux * self.velocidade + self.vx_knockback) * dt
        self.y += (uy * self.velocidade + self.vy_knockback) * dt
        self.vx_knockback = lerp(self.vx_knockback, 0.0, min(1.0, 10.0 * dt))
        self.vy_knockback = lerp(self.vy_knockback, 0.0, min(1.0, 10.0 * dt))

        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        self.timer_tiro += dt
        if self.timer_tiro >= self.cooldown_tiro and dist <= 420.0:
            self.timer_tiro = 0.0
            proj = Projetil(
                x=cx - 7.0,
                y=cy - 7.0,
                dir_x=ux,
                dir_y=uy,
                velocidade=310.0,
                dano=14,
                tempo_vida=3.0,
                dono="inimigo",
                largura=14,
                altura=14,
                sprite_key="projetil_inimigo",
                criogenico=True,
            )
            self.projeteis_pendentes.append(proj)

    def obter_projeteis_pendentes(self) -> list[Projetil]:
        lista = list(self.projeteis_pendentes)
        self.projeteis_pendentes.clear()
        return lista
