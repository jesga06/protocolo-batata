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
from src.utils.traducao import t


FONTES_DANO_VALIDAS_NINJA = frozenset({
    "projetil_jogador",
    "parry_ninja_proprio",
    "railgun",
    "rifle_arco_direto",
    "lanca_chamas",
})

# Parâmetros de homing por estágio do duelo (taxa_rad/s, radar_dot):
# progressivamente mais fechados para que o dash básico (0.22s / 2.6x) não quebre o lock facilmente.
NINJA_HOMING_POR_ESTAGIO: dict[int, tuple[float, float]] = {
    1: (3.4, -0.35),
    2: (4.6, -0.65),
    3: (6.0, -0.85),
}


class InimigoNinja(InimigoBase):
    nome_exibicao = t("combate_entidades", "inim_ninja")

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
        self.dano_projetil = 28
        self.vel_projetil = 380.0
        self.cooldown_tiro = 2.0
        self.timer_tiro = 0.6
        self.projeteis_pendentes: list[Projetil] = []
        self._duelo_windups_pendentes: list[dict] = []
        self.duelo_windup_duracao: float = 0.25

        # Dash com telegrafo de 0.55s (mais frequente) e rastro visual
        self.estado_dash = "stalk"  # stalk | telegraph | dash
        self.timer_dash_cd = 0.8
        self.timer_telegraph = 0.0
        self.timer_dash_ativo = 0.0
        self.dash_dir_x = 1.0
        self.dash_dir_y = 0.0
        self.rastro_dash: list[tuple[float, float]] = []

        # Postura de Parry contra tiros do jogador
        self.parry_cooldown = 0.0
        self.parry_telegraph_timer = 0.0

    def receber_dano(self, quantidade: int, *args, **kwargs):
        """Ninjas só sofrem dano de projéteis diretos do jogador, Railgun, Rifle de Arco (direto), Lança-Chamas ou próprio shuriken aparado."""
        fonte = kwargs.pop("fonte", "")
        if fonte not in FONTES_DANO_VALIDAS_NINJA:
            return 0
        return super().receber_dano(quantidade, *args, **kwargs)

    def pode_aparar_projetil(self) -> bool:
        return self.vivo and self.parry_cooldown <= 0.0

    def aparar_projetil_jogador(self, proj: Projetil, pos_alvo: tuple[float, float]) -> Projetil | None:
        """Reflete um projétil do jogador de volta como Estágio 1 de Duelo de Parry."""
        if not self.pode_aparar_projetil():
            return None
        self.parry_cooldown = 1.2
        self.parry_telegraph_timer = 0.55
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        dx, dy = vetor_direcao(cx, cy, pos_alvo[0], pos_alvo[1])
        if dx == 0.0 and dy == 0.0:
            dx = 1.0
        proj.dono = "inimigo"
        proj.dir_x = dx
        proj.dir_y = dy
        proj.velocidade = max(self.vel_projetil, float(getattr(proj, "velocidade", self.vel_projetil)) * 0.95)
        proj.dano = self.dano_projetil
        proj.largura = 20
        proj.altura = 20
        proj.width = proj.largura
        proj.height = proj.altura
        proj.duel_stage = 1
        proj.duel_owner = self
        proj.nao_desviavel = True
        taxa_h, dot_h = NINJA_HOMING_POR_ESTAGIO[1]
        proj.homing_ativo = True
        proj.homing_taxa_rad = taxa_h
        proj.homing_radar_dot = dot_h
        proj.homing_alvo_cursor = False
        proj.cor = (168, 85, 247)
        proj.tempo_vida = max(float(getattr(proj, "tempo_vida", 2.5)), 5.5)
        proj.tempo_vida_restante = proj.tempo_vida
        if hasattr(proj, "alvos_atingidos"):
            proj.alvos_atingidos.clear()
        return proj

    def disparar_contra_ataque_duelo(self, proximo_stage: int, pos_alvo: tuple[float, float]) -> Projetil | None:
        """Agenda o contra-ataque de Duelo de Parry com wind-up telegrafado (~0.25s) antes do disparo."""
        self.parry_telegraph_timer = max(self.parry_telegraph_timer, self.duelo_windup_duracao)
        self._duelo_windups_pendentes.append({
            "stage": int(proximo_stage),
            "pos_alvo": (float(pos_alvo[0]), float(pos_alvo[1])),
            "tempo": float(self.duelo_windup_duracao),
        })
        return None

    def _emitir_projetil_duelo(self, proximo_stage: int, pos_alvo: tuple[float, float]) -> Projetil:
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        dx, dy = vetor_direcao(cx, cy, pos_alvo[0], pos_alvo[1])
        if dx == 0.0 and dy == 0.0:
            dx = 1.0
        estagio = int(proximo_stage)
        vel = 470.0 if estagio == 2 else 560.0
        taxa_h, dot_h = NINJA_HOMING_POR_ESTAGIO.get(estagio, NINJA_HOMING_POR_ESTAGIO[3])
        proj = Projetil(
            x=cx - 10.0,
            y=cy - 10.0,
            dir_x=dx,
            dir_y=dy,
            velocidade=vel,
            dano=self.dano_projetil,
            tempo_vida=6.0,
            dono="inimigo",
            largura=20,
            altura=20,
            sprite_key="projetil_inimigo",
            cor=(168, 85, 247),
            duel_stage=estagio,
            duel_owner=self,
            nao_desviavel=True,
            homing_ativo=True,
            homing_taxa_rad=taxa_h,
            homing_radar_dot=dot_h,
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

        if self._duelo_windups_pendentes:
            restantes_duelo: list[dict] = []
            for item in self._duelo_windups_pendentes:
                item["tempo"] -= dt
                if item["tempo"] <= 0.0:
                    self._emitir_projetil_duelo(item["stage"], pos_alvo)
                else:
                    restantes_duelo.append(item)
            self._duelo_windups_pendentes = restantes_duelo

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
            self.rastro_dash.append((self.x, self.y))
            if len(self.rastro_dash) > 5:
                self.rastro_dash.pop(0)
            self.x += self.dash_dir_x * 620.0 * dt
            self.y += self.dash_dir_y * 620.0 * dt
            self.timer_dash_ativo -= dt
            if self.timer_dash_ativo <= 0.0:
                self.estado_dash = "stalk"
                self.timer_dash_cd = 1.1
        if self.estado_dash != "dash" and self.rastro_dash:
            self.rastro_dash.pop(0)

        self.vx_knockback = lerp(self.vx_knockback, 0.0, min(1.0, 10.0 * dt))
        self.vy_knockback = lerp(self.vy_knockback, 0.0, min(1.0, 10.0 * dt))
        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)

        self.timer_tiro += dt
        if self.timer_tiro >= self.cooldown_tiro and dist <= 680.0:
            self.timer_tiro = 0.0
            taxa_h, dot_h = NINJA_HOMING_POR_ESTAGIO[1]
            proj = Projetil(
                x=cx - 10.0,
                y=cy - 10.0,
                dir_x=ux,
                dir_y=uy,
                velocidade=self.vel_projetil,
                dano=self.dano_projetil,
                tempo_vida=5.5,
                dono="inimigo",
                largura=20,
                altura=20,
                sprite_key="projetil_inimigo",
                cor=(168, 85, 247),
                duel_stage=1,
                duel_owner=self,
                nao_desviavel=True,
                homing_ativo=True,
                homing_taxa_rad=taxa_h,
                homing_radar_dot=dot_h,
            )
            self.projeteis_pendentes.append(proj)

    def obter_projeteis_pendentes(self) -> list[Projetil]:
        lista = list(self.projeteis_pendentes)
        self.projeteis_pendentes.clear()
        return lista

    def desenhar(self, janela, camera=None):
        screen = getattr(janela, "screen", janela)
        if self.vivo and getattr(self, "rastro_dash", None):
            for idx_r, (rx, ry) in enumerate(self.rastro_dash):
                rdx = camera.transform_x(rx + self.largura / 2.0) if camera else (rx + self.largura / 2.0)
                rdy = camera.transform_y(ry + self.altura / 2.0) if camera else (ry + self.altura / 2.0)
                pygame.draw.circle(screen, (56, 189, 248), (int(rdx), int(rdy)), 14 + idx_r * 2, 2)
        super().desenhar(janela, camera)
        if not self.vivo:
            return
        dx = camera.transform_x(self.x + self.largura / 2.0) if camera else (self.x + self.largura / 2.0)
        dy = camera.transform_y(self.y + self.altura / 2.0) if camera else (self.y + self.altura / 2.0)
        if self.pode_aparar_projetil():
            pygame.draw.circle(screen, (192, 132, 252), (int(dx), int(dy)), 25, 2)
        if self.estado_dash == "telegraph":
            pygame.draw.circle(screen, (56, 189, 248), (int(dx), int(dy)), 30, 3)
            fim_x = dx + self.dash_dir_x * 95.0
            fim_y = dy + self.dash_dir_y * 95.0
            pygame.draw.line(screen, (56, 189, 248), (int(dx), int(dy)), (int(fim_x), int(fim_y)), 3)
        if self.parry_telegraph_timer > 0.0:
            pygame.draw.circle(screen, (232, 121, 249), (int(dx), int(dy)), 34, 3)
