"""
Inimigo Impressora Térmica — Protocolo: Batata
Artilharia pesada que dispara Núcleos de Sobrecarga (22x22, 240 px/s, 25 dano).
Parry em seus núcleos desencadeia Contra-Detonação em área com estilhaços teleguiados.
"""

import math
from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.utils.constantes import (
    INIMIGO_IMPRESSORA_HP,
    INIMIGO_IMPRESSORA_VELOCIDADE,
    INIMIGO_IMPRESSORA_DANO,
    INIMIGO_IMPRESSORA_XP,
)
from src.utils.math_utils import distancia, vetor_direcao, lerp


class InimigoImpressoraTermica(InimigoBase):
    nome_exibicao = "Impressora Térmica"

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_IMPRESSORA_HP,
        velocidade: float = INIMIGO_IMPRESSORA_VELOCIDADE,
        dano_contato: int = INIMIGO_IMPRESSORA_DANO,
        xp_valor: int = INIMIGO_IMPRESSORA_XP,
        is_elite: bool = False,
        nome_elite: str = "",
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=0.6,
            xp_valor=xp_valor,
            score_valor=260,
            largura=48,
            altura=48,
            sprite_key="inimigo_impressora",
            is_elite=is_elite,
            nome_elite=nome_elite,
        )
        self.distancia_standoff = 320.0
        self.distancia_tiro_max = 500.0
        self.cooldown_tiro = 2.2
        self.timer_tiro = 0.8
        self.dano_projetil = 25
        self.vel_projetil = 240.0
        self.projeteis_pendentes: list[Projetil] = []

    def update(self, dt: float, pos_alvo: tuple[float, float], vel_alvo: tuple[float, float] = None):
        if not self.vivo:
            return
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo
        dist = distancia(cx, cy, tx, ty)
        ux, uy = vetor_direcao(cx, cy, tx, ty)

        if dist > self.distancia_standoff:
            vx = ux * self.velocidade + self.vx_knockback
            vy = uy * self.velocidade + self.vy_knockback
        else:
            vx = self.vx_knockback
            vy = self.vy_knockback

        self.x += vx * dt
        self.y += vy * dt
        self.vx_knockback = lerp(self.vx_knockback, 0.0, min(1.0, 10.0 * dt))
        self.vy_knockback = lerp(self.vy_knockback, 0.0, min(1.0, 10.0 * dt))

        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        self.timer_tiro += dt
        if self.timer_tiro >= self.cooldown_tiro and dist <= self.distancia_tiro_max:
            self.timer_tiro = 0.0
            dir_x, dir_y = vetor_direcao(cx, cy, tx, ty)
            if dir_x == 0.0 and dir_y == 0.0:
                dir_x = 1.0
            proj = Projetil(
                x=cx - 14.0,
                y=cy - 14.0,
                dir_x=dir_x,
                dir_y=dir_y,
                velocidade=self.vel_projetil,
                dano=self.dano_projetil,
                tempo_vida=4.0,
                dono="inimigo",
                largura=28,
                altura=28,
                sprite_key="projetil_inimigo",
                sobrecarga_termica=True,
                eh_impressora=True,
            )
            self.projeteis_pendentes.append(proj)

    def obter_projeteis_pendentes(self) -> list[Projetil]:
        lista = list(self.projeteis_pendentes)
        self.projeteis_pendentes.clear()
        return lista
