"""
Inimigo Ninja Corporativo — Protocolo: Batata
Inimigo raro (máximo 2 ativos, cooldown mínimo de 20s entre spawns) que realiza
telegrafo de 0.55s antes de dash e pode aparar tiros do jogador, iniciando Duelos de Parry em 3 estágios.
"""

import math
import pygame
from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.utils.constantes import (
    INIMIGO_NINJA_HP,
    INIMIGO_NINJA_VELOCIDADE,
    INIMIGO_NINJA_DANO,
    INIMIGO_NINJA_XP,
)
from src.utils.math_utils import distancia, vetor_direcao, lerp


class InimigoNinja(InimigoBase):
    nome_exibicao = "Ninja Corporativo"

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_NINJA_HP,
        velocidade: float = INIMIGO_NINJA_VELOCIDADE,
        dano_contato: int = INIMIGO_NINJA_DANO,
        xp_valor: int = INIMIGO_NINJA_XP,
        is_elite: bool = False,
        nome_elite: str = "",
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=0.45,
            xp_valor=xp_valor,
            score_valor=350,
            largura=38,
            altura=38,
            sprite_key="inimigo_ninja",
            is_elite=is_elite,
            nome_elite=nome_elite,
        )
        self.is_ninja = True
        self.dano_projetil = 18
        self.vel_projetil = 340.0
        self.cooldown_tiro = 2.0
        self.timer_tiro = 0.6
        self.projeteis_pendentes: list[Projetil] = []

        # Dash com telegrafo de 0.55s
        self.estado_dash = "stalk"  # stalk | telegraph | dash
        self.timer_dash_cd = 2.4
        self.timer_telegraph = 0.0
        self.timer_dash_ativo = 0.0
        self.dash_dir_x = 1.0
        self.dash_dir_y = 0.0

        # Postura de Parry contra tiros do jogador
        self.parry_cooldown = 0.0
        self.parry_telegraph_timer = 0.0

    def receber_dano(self, quantidade: int, *args, **kwargs):
        """Ninjas só sofrem dano de projéteis diretos do jogador ou de seu próprio projétil aparado."""
        fonte = kwargs.pop("fonte", "")
        if fonte not in ("projetil_jogador", "parry_ninja_proprio"):
            return 0
        return super().receber_dano(quantidade, *args, **kwargs)

    def pode_aparar_projetil(self) -> bool:
        return self.vivo and self.parry_cooldown <= 0.0

    def aparar_projetil_jogador(self, proj: Projetil, pos_alvo: tuple[float, float]) -> Projetil | None:
        """Reflete um projétil do jogador de volta como Estágio 1 de Duelo de Parry."""
        if not self.pode_aparar_projetil():
            return None
        self.parry_cooldown = 3.5
        self.parry_telegraph_timer = 0.55
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        dx, dy = vetor_direcao(cx, cy, pos_alvo[0], pos_alvo[1])
        if dx == 0.0 and dy == 0.0:
            dx = 1.0
        proj.dono = "inimigo"
        proj.dir_x = dx
        proj.dir_y = dy
        proj.velocidade = max(340.0, float(getattr(proj, "velocidade", 340.0)) * 0.9)
        proj.dano = self.dano_projetil
        proj.duel_stage = 1
        proj.duel_owner = self
        proj.cor = (244, 63, 94)
        proj.tempo_vida = max(float(getattr(proj, "tempo_vida", 2.5)), 3.0)
        proj.tempo_vida_restante = proj.tempo_vida
        if hasattr(proj, "alvos_atingidos"):
            proj.alvos_atingidos.clear()
        return proj

    def disparar_contra_ataque_duelo(self, proximo_stage: int, pos_alvo: tuple[float, float]) -> Projetil:
        """Dispara imediatamente a devolução do Duelo de Parry (Stage 2 = 1.35x, Stage 3 = 1.75x)."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        dx, dy = vetor_direcao(cx, cy, pos_alvo[0], pos_alvo[1])
        if dx == 0.0 and dy == 0.0:
            dx = 1.0
        mult_vel = 1.35 if int(proximo_stage) == 2 else 1.75
        proj = Projetil(
            x=cx - 7.0,
            y=cy - 7.0,
            dir_x=dx,
            dir_y=dy,
            velocidade=self.vel_projetil * mult_vel,
            dano=self.dano_projetil,
            tempo_vida=3.2,
            dono="inimigo",
            largura=14,
            altura=14,
            sprite_key="projetil_inimigo",
            duel_stage=int(proximo_stage),
            duel_owner=self,
        )
        self.projeteis_pendentes.append(proj)
        return proj

    def update(self, dt: float, pos_alvo: tuple[float, float], vel_alvo: tuple[float, float] = None):
        if not self.vivo:
            return
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo
        dist = distancia(cx, cy, tx, ty)
        ux, uy = vetor_direcao(cx, cy, tx, ty)

        if self.parry_cooldown > 0.0:
            self.parry_cooldown = max(0.0, self.parry_cooldown - dt)
        if self.parry_telegraph_timer > 0.0:
            self.parry_telegraph_timer = max(0.0, self.parry_telegraph_timer - dt)

        if self.estado_dash == "stalk":
            self.x += (ux * self.velocidade + self.vx_knockback) * dt
            self.y += (uy * self.velocidade + self.vy_knockback) * dt
            self.timer_dash_cd -= dt
            if self.timer_dash_cd <= 0.0 and dist < 440.0:
                self.estado_dash = "telegraph"
                self.timer_telegraph = 0.55
                self.dash_dir_x, self.dash_dir_y = ux, uy
        elif self.estado_dash == "telegraph":
            self.timer_telegraph -= dt
            if self.timer_telegraph <= 0.0:
                self.estado_dash = "dash"
                self.timer_dash_ativo = 0.24
                self.dash_dir_x, self.dash_dir_y = vetor_direcao(cx, cy, tx, ty)
                if self.dash_dir_x == 0.0 and self.dash_dir_y == 0.0:
                    self.dash_dir_x = 1.0
        elif self.estado_dash == "dash":
            self.x += self.dash_dir_x * 540.0 * dt
            self.y += self.dash_dir_y * 540.0 * dt
            self.timer_dash_ativo -= dt
            if self.timer_dash_ativo <= 0.0:
                self.estado_dash = "stalk"
                self.timer_dash_cd = 2.8

        self.vx_knockback = lerp(self.vx_knockback, 0.0, min(1.0, 10.0 * dt))
        self.vy_knockback = lerp(self.vy_knockback, 0.0, min(1.0, 10.0 * dt))
        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        self.timer_tiro += dt
        if self.timer_tiro >= self.cooldown_tiro and dist <= 480.0:
            self.timer_tiro = 0.0
            proj = Projetil(
                x=cx - 6.0,
                y=cy - 6.0,
                dir_x=ux,
                dir_y=uy,
                velocidade=self.vel_projetil,
                dano=self.dano_projetil,
                tempo_vida=3.0,
                dono="inimigo",
                largura=12,
                altura=12,
                sprite_key="projetil_inimigo",
                duel_stage=1,
                duel_owner=self,
            )
            self.projeteis_pendentes.append(proj)

    def obter_projeteis_pendentes(self) -> list[Projetil]:
        lista = list(self.projeteis_pendentes)
        self.projeteis_pendentes.clear()
        return lista

    def desenhar(self, janela, camera=None):
        super().desenhar(janela, camera)
        if not self.vivo:
            return
        if self.estado_dash == "telegraph" or self.parry_telegraph_timer > 0.0:
            screen = getattr(janela, "screen", janela)
            dx = camera.transform_x(self.x + self.largura / 2.0) if camera else (self.x + self.largura / 2.0)
            dy = camera.transform_y(self.y + self.altura / 2.0) if camera else (self.y + self.altura / 2.0)
            cor = (56, 189, 248) if self.estado_dash == "telegraph" else (192, 132, 252)
            pygame.draw.circle(screen, cor, (int(dx), int(dy)), 26, 2)
