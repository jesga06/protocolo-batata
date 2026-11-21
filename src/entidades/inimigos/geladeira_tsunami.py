"""
Geladeira Tsunami — Protocolo: Batata
Chefe Final ("The Perfect Sound™") com FSM de 3 Fases, Balão de Fala e Ataques Sônicos.
Dimensões: estritamente 112 x 156 px (sprite e hitbox física).
"""

import math
import os
import random
import pygame

from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.utils.constantes import (
    ASSETS_DIR, ASSET_PATHS, obter_caminho_asset,
    BOSS_GELADEIRA_LARGURA, BOSS_GELADEIRA_ALTURA,
    BOSS_GELADEIRA_HP_BASE, BOSS_GELADEIRA_DANO_CONTATO,
    BOSS_GELADEIRA_VELOCIDADE, BOSS_GELADEIRA_NOME,
    BOSS_GELADEIRA_FLAVOR, LARGURA_ARENA, ALTURA_ARENA,
    LARGURA_TELA, ALTURA_TELA,
    BRANCO, PRETO, DOURADO, ROXO_ACENTO, ROXO_CLARO, VERMELHO_DANO,
    AZUL_CIANO, LARANJA_ALERTA
)
from src.utils.math_utils import distancia, vetor_direcao, normalizar_vetor, clamp, lerp, colisao_aabb


ESTADO_INTRO = "intro"
ESTADO_FASE1 = "fase1"
ESTADO_FASE2 = "fase2"
ESTADO_FASE3 = "fase3"
ESTADO_MORTE = "morte"


class CaixaDeSomBoss(InimigoBase):
    """
    Caixa de Som (Subwoofer Totem destrutível) lançada pela Geladeira Tsunami.
    Permanece fixa na arena emitindo ondas sonoras cruzadas até ser destruída pelos tiros do jogador.
    Cria a pressão espacial natural para builds sem configurações, sem usar timers artificiais de morte.
    """
    def __init__(self, x: float, y: float, hp: int = 240):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=0.0,
            dano_contato=12,
            cooldown_contato=0.6,
            xp_valor=0,
            score_valor=150,
            largura=40,
            altura=40,
            sprite_key="caixa_som_boss",
            is_elite=False,
            nome_elite="CAIXA DE SOM"
        )
        self.is_caixa_som = True
        self.timer_onda = 0.8
        self.intervalo_onda = 2.4
        self.projeteis_pendentes: list[Projetil] = []
        self.angulo_onda = 0.0

    def update(self, dt: float, pos_alvo: tuple[float, float]):
        if not self.vivo:
            return
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)

        self.timer_onda += dt
        if self.timer_onda >= self.intervalo_onda:
            self.timer_onda = 0.0
            self.angulo_onda = (self.angulo_onda + 0.45) % (2.0 * math.pi)
            cx = self.x + self.largura / 2.0
            cy = self.y + self.altura / 2.0
            for i in range(6):
                ang = self.angulo_onda + i * (2.0 * math.pi / 6.0)
                self.projeteis_pendentes.append(Projetil(
                    x=cx - 5.0,
                    y=cy - 5.0,
                    dir_x=math.cos(ang),
                    dir_y=math.sin(ang),
                    velocidade=175.0,
                    dano=10,
                    tempo_vida=3.2,
                    dono="inimigo",
                    largura=10,
                    altura=10,
                    sprite_key="projetil_inimigo",
                    cor=ROXO_CLARO
                ))

    def desenhar(self, janela, camera=None):
        if not self.vivo:
            return
        super().desenhar(janela, camera)
        try:
            screen = getattr(janela, "screen", janela)
            dx = camera.transform_x(self.x) if camera else self.x
            dy = camera.transform_y(self.y) if camera else self.y
            pct = clamp(self.hp / max(1, self.hp_max), 0.0, 1.0)
            pygame.draw.rect(screen, (15, 18, 26), (int(dx), int(dy - 8), self.largura, 5), border_radius=2)
            pygame.draw.rect(screen, ROXO_ACENTO, (int(dx + 1), int(dy - 7), int((self.largura - 2) * pct), 3), border_radius=2)
        except Exception:
            pass


class GeladeiraTsunami(InimigoBase):
    """
    Entidade do Chefe Final: Geladeira Tsunami ("The Perfect Sound™").
    FSM de 3 fases dinâmicas baseadas em limites de vida (100%-66%, 66%-33%, <=33%),
    intro cinematográfica com balão de fala cômico de 3.5s e sequência de morte de 1.5s.
    """

    ESTADO_INTRO = ESTADO_INTRO
    ESTADO_FASE1 = ESTADO_FASE1
    ESTADO_FASE2 = ESTADO_FASE2
    ESTADO_FASE3 = ESTADO_FASE3
    ESTADO_MORTE = ESTADO_MORTE

    _sprite_tsunami_cache = None
    _balao_fonte_cache = None
    _aura_cache = {}
    _flash_cache = {}

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = BOSS_GELADEIRA_HP_BASE,
        velocidade: float = BOSS_GELADEIRA_VELOCIDADE,
        dano_contato: int = BOSS_GELADEIRA_DANO_CONTATO,
        cooldown_contato: float = 0.5,
        xp_valor: int = 0,
        score_valor: int = 5000,
        largura: int = BOSS_GELADEIRA_LARGURA,
        altura: int = BOSS_GELADEIRA_ALTURA,
        sprite_key: str = "boss_geladeira_tsunami",
        is_elite: bool = True,
        nome_elite: str = f"{BOSS_GELADEIRA_NOME} — {BOSS_GELADEIRA_FLAVOR}",
        y_destino: float = None,
        y_origem: float = None,
        **kwargs
    ):
        # Inicia a classe base sem passar is_elite=True para evitar duplicar largura/altura
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=score_valor,
            largura=largura,
            altura=altura,
            sprite_key=sprite_key,
            is_elite=False,
            nome_elite=nome_elite
        )

        # Enforce rigoroso de dimensões e atributos de Boss
        self.is_elite = True
        self.is_boss = True
        self.largura = int(largura)   # 112 px
        self.altura = int(altura)     # 156 px
        self.width = self.largura
        self.height = self.altura
        self.hp_max = int(hp)         # 2500 HP
        self.hp = int(hp)
        self.nome_elite = nome_elite
        self.nome = BOSS_GELADEIRA_NOME
        self.flavor = BOSS_GELADEIRA_FLAVOR
        self.tempo_vida_restante = None  # Imune a sobreaquecimento térmico
        self.superaqueceu = False
        self.morreu = False
        self.derrotado = False

        # FSM e Timers
        self.estado = ESTADO_INTRO
        self._intro_concluida = False
        self.timer_intro = 3.5
        self.tempo_intro_total = 3.5
        if y_destino is not None:
            self.y_intro_destino = float(y_destino)
        elif "y_destino" in kwargs:
            self.y_intro_destino = float(kwargs["y_destino"])
        elif y > 700:
            self.y_intro_destino = float(ALTURA_ARENA / 2.0 - self.altura / 2.0 - 50.0)
        else:
            self.y_intro_destino = float(y)

        if y_origem is not None:
            self.y_intro_origem = float(y_origem)
        elif "y_origem" in kwargs:
            self.y_intro_origem = float(kwargs["y_origem"])
        elif "y_intro_origem" in kwargs:
            self.y_intro_origem = float(kwargs["y_intro_origem"])
        elif y > 700:
            self.y_intro_origem = 940.0
        else:
            self.y_intro_origem = float(y + 250.0)

        self.y = self.y_intro_origem

        # Balão de fala
        self.balao_fala_texto = "Você já passou da validade.\nSente a pressão, neném."
        self.fala_intro = self.balao_fala_texto
        self.mostrar_balao_fala = True
        self.timer_balao_fala = 3.5

        # Fase 1: Heavy Stalk + Subwoofer Pulse (anéis sônicos com brecha de esquiva)
        self.timer_pulso_fase1 = 0.0
        self.intervalo_pulso_fase1 = 1.45

        # Fase 2: Telegraphed Bass Rush Dash (500 px/s) + Subwoofer Totems
        self.subestado_fase2 = "stalk"  # "stalk", "telegraph", "dash"
        self.timer_ciclo_fase2 = 0.0
        self.intervalo_dash_fase2 = 2.6
        self.timer_telegraph_fase2 = 0.0
        self.duracao_telegraph = 0.65
        self.timer_dash_fase2 = 0.0
        self.duracao_dash_max = 0.90
        self.dash_dir_x = 0.0
        self.dash_dir_y = 0.0
        self.dash_velocidade = 500.0
        self.timer_totem_fase2 = 0.0
        self.intervalo_totem_fase2 = 2.2

        # Fase 3: Center Stage Anchor + Sonic Tsunami Helix
        self.angulo_helix = 0.0
        self.timer_tiro_helix = 0.0
        self.intervalo_tiro_helix = 0.09
        self.timer_bass_blast = 0.0
        self.intervalo_bass_blast = 1.40
        self.centro_arena_x = (LARGURA_ARENA - self.largura) / 2.0
        self.centro_arena_y = (ALTURA_ARENA - self.altura) / 2.0

        # Fase Morte: cascata de explosões (1.5s), tremor e drop de vitória
        self.timer_morte = 1.5
        self.duracao_morte_total = 1.5
        self.gerar_drop_vitoria = False
        self.shake_screen = False
        self.shake_intensidade = 0.0
        self.particulas_explosao: list[dict] = []

        # Filas de saída e mecânicas espaciais (Bass Push, Poças de Gelo, Caixas de Som, Drift Duplo, Sucção)
        self.projeteis_pendentes: list[Projetil] = []
        self.caixas_som_pendentes: list[CaixaDeSomBoss] = []
        self.pocas_gelo_pendentes: list[dict] = []
        self.pulso_empurrao_pendente: bool = False
        self.timer_cubo_gelo: float = 0.0
        self.dashes_restantes_ciclo: int = 2
        self.vortice_succao_ativo: bool = False
        self.timer_vortice_fase3: float = 0.0

    @property
    def intro_concluida(self) -> bool:
        return (self.estado != ESTADO_INTRO) or (self.timer_intro <= 0.0)

    @intro_concluida.setter
    def intro_concluida(self, val: bool):
        if val:
            self.timer_intro = 0.0
            self.mostrar_balao_fala = False
            if self.estado == ESTADO_INTRO:
                self.estado = ESTADO_FASE1

    @property
    def rect(self) -> pygame.Rect:
        """Hitbox física AABB estrita de 112 x 156 px (colapso para zero na morte)."""
        if self.estado == ESTADO_MORTE:
            return pygame.Rect(int(self.x), int(self.y), 0, 0)
        return pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    def get_rect(self) -> tuple[float, float, int, int]:
        if self.estado == ESTADO_MORTE:
            return (self.x, self.y, 0, 0)
        return (self.x, self.y, self.largura, self.altura)

    @classmethod
    def _obter_sprite_boss(cls, largura: int = 112, altura: int = 156):
        """Carrega e escala o sprite da Geladeira Tsunami para 112x156 px com fallback procedural."""
        if cls._sprite_tsunami_cache is None:
            caminho = obter_caminho_asset("boss_geladeira_tsunami")
            if os.path.isfile(caminho) and pygame.display.get_init():
                try:
                    img = pygame.image.load(caminho).convert_alpha()
                    cls._sprite_tsunami_cache = pygame.transform.scale(img, (largura, altura))
                except Exception:
                    pass
            elif pygame.display.get_init():
                cls._sprite_tsunami_cache = cls._criar_superficie_fallback(largura, altura)
        if cls._sprite_tsunami_cache is not None:
            return cls._sprite_tsunami_cache
        return cls._criar_superficie_fallback(largura, altura)

    @classmethod
    def _criar_superficie_fallback(cls, largura: int = 112, altura: int = 156) -> pygame.Surface:
        """Gera uma superfície procedural estilizada caso o asset gráfico não esteja disponível."""
        surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
        # Corpo metálico azul marinho escuro
        pygame.draw.rect(surf, (25, 35, 50), (0, 0, largura, altura), border_radius=8)
        pygame.draw.rect(surf, (55, 95, 145), (4, 4, largura - 8, altura - 8), border_radius=6)

        # Divisória do congelador
        div_y = int(altura * 0.36)
        pygame.draw.line(surf, (15, 20, 30), (4, div_y), (largura - 4, div_y), 4)

        # Subwoofer Superior (porta do congelador)
        cx_sub = largura // 2
        cy_sub1 = int(altura * 0.18)
        pygame.draw.circle(surf, (15, 20, 30), (cx_sub, cy_sub1), 22)
        pygame.draw.circle(surf, ROXO_ACENTO, (cx_sub, cy_sub1), 16, width=3)
        pygame.draw.circle(surf, DOURADO, (cx_sub, cy_sub1), 8)

        # Subwoofer Principal Gigante (porta inferior)
        cy_sub2 = int(altura * 0.68)
        pygame.draw.circle(surf, (15, 20, 30), (cx_sub, cy_sub2), 36)
        pygame.draw.circle(surf, ROXO_ACENTO, (cx_sub, cy_sub2), 28, width=4)
        pygame.draw.circle(surf, (0, 220, 255), (cx_sub, cy_sub2), 18, width=3)
        pygame.draw.circle(surf, DOURADO, (cx_sub, cy_sub2), 8)

        # Puxadores cromados
        pygame.draw.rect(surf, (220, 230, 245), (largura - 12, int(altura * 0.12), 6, int(altura * 0.18)), border_radius=2)
        pygame.draw.rect(surf, (220, 230, 245), (largura - 12, int(altura * 0.44), 6, int(altura * 0.32)), border_radius=2)

        # Borda dourada brilhante
        pygame.draw.rect(surf, DOURADO, (0, 0, largura, altura), width=3, border_radius=8)
        return surf

    def receber_dano(self, quantidade: int, *args, **kwargs):
        """Aplica dano à Geladeira Tsunami, aciona flash e faz a transição de fases da FSM."""
        if not self.vivo or self.estado == ESTADO_MORTE:
            return 0
        if self.estado == ESTADO_INTRO:
            return 0

        self.hp -= int(quantidade)
        self.flash_timer = 0.12

        if self.hp <= 0:
            self.hp = 0
            self._iniciar_estado_morte()
        else:
            self._atualizar_fase_por_hp()
        return quantidade

    def tentar_causar_dano_contato(self, jogador) -> bool:
        """
        Bloqueia estritamente dano de contato durante ESTADO_MORTE ou ESTADO_INTRO.
        Caso contrário, delega para a lógica base de InimigoBase.
        """
        if self.estado in (ESTADO_MORTE, ESTADO_INTRO) or not self.vivo:
            return False
        return super().tentar_causar_dano_contato(jogador)

    def _atualizar_fase_por_hp(self):
        """Avalia a transição entre Fase 1 (>66%), Fase 2 (33-66%) e Fase 3 (<=33%)."""
        if self.estado in (ESTADO_INTRO, ESTADO_MORTE):
            return

        pct_hp = self.hp / max(1, self.hp_max)
        if pct_hp <= 0.35:
            if self.estado != ESTADO_FASE3:
                self.estado = ESTADO_FASE3
        elif pct_hp <= 0.70:
            if self.estado != ESTADO_FASE2:
                self.estado = ESTADO_FASE2
                self.subestado_fase2 = "stalk"
                self.timer_ciclo_fase2 = 0.0
        else:
            if self.estado != ESTADO_FASE1:
                self.estado = ESTADO_FASE1

    def _iniciar_estado_morte(self):
        """Inicia a sequência final de destruição e vitória (1.5s de cascata)."""
        self.estado = ESTADO_MORTE
        self.timer_morte = 1.5
        self.shake_screen = True
        self.shake_intensidade = 10.0
        self.mostrar_balao_fala = False

    def update(self, dt: float, pos_alvo: tuple[float, float], **kwargs):
        """
        Atualiza a FSM do chefe, movimentação, ataques por fase e contadores de efeito.
        """
        if not self.vivo and self.estado != ESTADO_MORTE:
            return

        # Atualiza flash visual de dano e cooldown de contato
        if self.flash_timer > 0.0:
            self.flash_timer = max(0.0, self.flash_timer - dt)
        if self.cooldown_contato_atual > 0.0:
            self.cooldown_contato_atual = max(0.0, self.cooldown_contato_atual - dt)

        # Atualiza partículas de explosão ativas
        if self.particulas_explosao:
            for part in self.particulas_explosao:
                part["tempo"] -= dt
                part["x"] += part["vx"] * dt
                part["y"] += part["vy"] * dt
            self.particulas_explosao = [p for p in self.particulas_explosao if p["tempo"] > 0.0]

        # FSM: ESTADO_INTRO
        if self.estado == ESTADO_INTRO:
            self._update_intro(dt)
            return

        # FSM: ESTADO_MORTE
        if self.estado == ESTADO_MORTE:
            self._update_morte(dt)
            return

        # Verifica mudança de fase com base no HP atual
        self._atualizar_fase_por_hp()

        # FSM: ESTADO_FASE1 (HP > 66%)
        if self.estado == ESTADO_FASE1:
            self._update_fase1(dt, pos_alvo)

        # FSM: ESTADO_FASE2 (33% < HP <= 66%)
        elif self.estado == ESTADO_FASE2:
            self._update_fase2(dt, pos_alvo, **kwargs)

        # FSM: ESTADO_FASE3 (HP <= 33%)
        elif self.estado == ESTADO_FASE3:
            self._update_fase3(dt, pos_alvo)

    def _update_intro(self, dt: float):
        """Ascensão suave da borda inferior e exibição do balão de fala por 3.5s."""
        self.timer_intro -= dt
        progresso = 1.0 - max(0.0, self.timer_intro / self.tempo_intro_total)
        # Interpolação suave de subida
        self.y = lerp(self.y_intro_origem, self.y_intro_destino, min(1.0, progresso * 1.25))
        self.mostrar_balao_fala = True

        if self.timer_intro <= 0.0:
            self.timer_intro = 0.0
            self.y = self.y_intro_destino
            self.mostrar_balao_fala = False
            self.estado = ESTADO_FASE1
            self._atualizar_fase_por_hp()
            self.timer_pulso_fase1 = 0.5

    def _update_fase1(self, dt: float, pos_alvo: tuple[float, float]):
        """Fase 1: Heavy Stalk em direção ao jogador + Subwoofer Pulse periódico."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo

        # Movimento de perseguição pesada (85 px/s)
        ux, uy = vetor_direcao(cx, cy, tx, ty)
        self.x += ux * self.velocidade * dt
        self.y += uy * self.velocidade * dt

        # Ataque: Subwoofer Pulse (anéis sônicos com brecha para esquiva + Bass Push)
        self.timer_pulso_fase1 += dt
        if self.timer_pulso_fase1 >= self.intervalo_pulso_fase1:
            self._disparar_pulso_subwoofer(pos_alvo)
            self.pulso_empurrao_pendente = True
            self.timer_pulso_fase1 = 0.0

        # Cubos de Gelo que geram poças congeladas no chão
        self.timer_cubo_gelo = getattr(self, "timer_cubo_gelo", 0.0) + dt
        if self.timer_cubo_gelo >= 4.2:
            self.timer_cubo_gelo = 0.0
            self.pocas_gelo_pendentes.append({
                "x": clamp(tx + random.uniform(-60.0, 60.0), 80.0, float(LARGURA_ARENA - 80.0)),
                "y": clamp(ty + random.uniform(-60.0, 60.0), 80.0, float(ALTURA_ARENA - 80.0)),
                "raio": 68.0,
                "tempo": 6.0,
                "tempo_max": 6.0
            })

    def _update_fase2(self, dt: float, pos_alvo: tuple[float, float], **kwargs):
        """Fase 2: Telegraphed Bass Rush Dash (420 px/s) + Subwoofer Totems."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo

        limite = kwargs.get("limite_arena", (float(LARGURA_ARENA), float(ALTURA_ARENA)))
        lim_w = float(limite[0]) if isinstance(limite, (tuple, list)) and len(limite) >= 2 else float(LARGURA_ARENA)
        lim_h = float(limite[1]) if isinstance(limite, (tuple, list)) and len(limite) >= 2 else float(ALTURA_ARENA)

        if self.subestado_fase2 == "stalk":
            # Perseguição com velocidade ligeiramente elevada (95 px/s)
            ux, uy = vetor_direcao(cx, cy, tx, ty)
            self.x += ux * (self.velocidade * 1.15) * dt
            self.y += uy * (self.velocidade * 1.15) * dt

            # Totems sônicos periódicos
            self.timer_totem_fase2 += dt
            if self.timer_totem_fase2 >= self.intervalo_totem_fase2:
                self._disparar_totem_acustico()
                self.timer_totem_fase2 = 0.0

            # Timer para iniciar o telegrafo do Bass Rush Dash
            self.timer_ciclo_fase2 += dt
            if self.timer_ciclo_fase2 >= self.intervalo_dash_fase2:
                self.subestado_fase2 = "telegraph"
                self.timer_telegraph_fase2 = self.duracao_telegraph
                self.dash_dir_x, self.dash_dir_y = vetor_direcao(cx, cy, tx, ty)
                if self.dash_dir_x == 0.0 and self.dash_dir_y == 0.0:
                    self.dash_dir_x = 1.0

        elif self.subestado_fase2 == "telegraph":
            # Parado carregando o rush sonoro (linha de telegrafo ativa)
            self.timer_telegraph_fase2 -= dt
            if self.timer_telegraph_fase2 <= 0.0:
                self.subestado_fase2 = "dash"
                self.timer_dash_fase2 = self.duracao_dash_max

        elif self.subestado_fase2 == "dash":
            # Investida em alta velocidade (420 px/s)
            self.x += self.dash_dir_x * self.dash_velocidade * dt
            self.y += self.dash_dir_y * self.dash_velocidade * dt
            self.timer_dash_fase2 -= dt

            # Evita colisão espúria no frame 1 de dash se iniciado exatamente sobre a borda
            tolerancia_frame1 = (self.timer_dash_fase2 > (self.duracao_dash_max - dt * 1.5))
            bateu_parede = False
            if not tolerancia_frame1 or self.x < -1.0 or self.x + self.largura > lim_w + 1.0 or self.y < -1.0 or self.y + self.altura > lim_h + 1.0:
                bateu_parede = (
                    (self.x <= 0 and self.dash_dir_x < 0) or
                    (self.x + self.largura >= lim_w and self.dash_dir_x > 0) or
                    (self.y <= 0 and self.dash_dir_y < 0) or
                    (self.y + self.altura >= lim_h and self.dash_dir_y > 0) or
                    self.x < -10.0 or self.x + self.largura > lim_w + 10.0 or
                    self.y < -10.0 or self.y + self.altura > lim_h + 10.0
                )

            if bateu_parede or self.timer_dash_fase2 <= 0.0:
                # Clamp na arena
                self.x = clamp(self.x, 0.0, float(lim_w - self.largura))
                self.y = clamp(self.y, 0.0, float(lim_h - self.altura))

                # Impacto na parede: screen shake e 4 estilhaços acústicos
                self.shake_screen = True
                self.shake_intensidade = 12.0
                self._disparar_estilhacos_acusticos()

                # Drift Duplo: se ainda resta o segundo dash do par, recalcula curva para o jogador
                if getattr(self, "dashes_restantes_ciclo", 1) > 1 and not bateu_parede:
                    self.dashes_restantes_ciclo = 1
                    self.dash_dir_x, self.dash_dir_y = vetor_direcao(
                        self.x + self.largura / 2.0,
                        self.y + self.altura / 2.0,
                        tx,
                        ty
                    )
                    if self.dash_dir_x == 0.0 and self.dash_dir_y == 0.0:
                        self.dash_dir_x = 1.0
                    self.timer_dash_fase2 = self.duracao_dash_max * 0.65
                else:
                    self.dashes_restantes_ciclo = 2
                    self.subestado_fase2 = "stalk"
                    self.timer_ciclo_fase2 = 0.0

    def _update_fase3(self, dt: float, pos_alvo: tuple[float, float]):
        """Fase 3: Center Stage Anchor + Sonic Tsunami Helix + Radial Bass Blasts."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0

        # Movimento de ancoragem no centro do palco (800x600)
        dist_centro = distancia(self.x, self.y, self.centro_arena_x, self.centro_arena_y)
        if dist_centro > 10.0:
            ux, uy = vetor_direcao(self.x, self.y, self.centro_arena_x, self.centro_arena_y)
            self.x += ux * 120.0 * dt
            self.y += uy * 120.0 * dt
        else:
            self.x = self.centro_arena_x
            self.y = self.centro_arena_y

        # Sonic Tsunami Helix (feixes em espiral tripla rotativa contínua)
        self.angulo_helix += 4.2 * dt
        self.timer_tiro_helix += dt
        if self.timer_tiro_helix >= self.intervalo_tiro_helix:
            self._disparar_helix_tsunami()
            self.timer_tiro_helix = 0.0

        # Radial Bass Blasts periódicos + Vórtice de Sucção do Subwoofer
        self.timer_vortice_fase3 = getattr(self, "timer_vortice_fase3", 0.0) + dt
        self.vortice_succao_ativo = (4.5 <= (self.timer_vortice_fase3 % 7.5) <= 7.0)

        self.timer_bass_blast += dt
        if self.timer_bass_blast >= self.intervalo_bass_blast:
            self._disparar_blast_radial()
            self.timer_bass_blast = 0.0
            self.shake_screen = True
            self.shake_intensidade = 8.0

    def _update_morte(self, dt: float):
        """Sequência de morte: 1.5s de cascata de explosões, tremor e sinal de vitória."""
        self.timer_morte -= dt
        self.shake_screen = True
        self.shake_intensidade = 6.0

        # Gera partículas e explosões aleatórias pelo corpo do chefe
        for _ in range(3):
            px = self.x + random.uniform(0, self.largura)
            py = self.y + random.uniform(0, self.altura)
            self.particulas_explosao.append({
                "x": px,
                "y": py,
                "vx": random.uniform(-120, 120),
                "vy": random.uniform(-120, 120),
                "raio": random.uniform(6, 18),
                "cor": random.choice([DOURADO, ROXO_ACENTO, BRANCO, LARANJA_ALERTA]),
                "tempo": random.uniform(0.2, 0.5)
            })

        if self.timer_morte <= 0.0:
            self.timer_morte = 0.0
            self.vivo = False
            self.morreu = True
            self.derrotado = True
            self.gerar_drop_vitoria = True

    # -------------------------------------------------------------------------
    # Geradores de Ataques Balísticos e Sônicos
    # -------------------------------------------------------------------------

    def _disparar_pulso_subwoofer(self, pos_alvo: tuple[float, float]):
        """Dispara um anel concêntrico de 14 projéteis com 2 brechas de esquiva."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = pos_alvo
        ang_jogador = math.atan2(ty - cy, tx - cx)

        num_tiros = 18
        for i in range(num_tiros):
            ang = i * (2.0 * math.pi / num_tiros)
            # Cria brechas nos ângulos diretamente alinhados com o jogador (+-16 graus)
            diff_ang = abs((ang - ang_jogador + math.pi) % (2.0 * math.pi) - math.pi)
            if diff_ang < 0.25:
                continue  # Brecha para esquiva habilidosa

            dir_x = math.cos(ang)
            dir_y = math.sin(ang)
            proj = Projetil(
                x=cx - 6.0,
                y=cy - 6.0,
                dir_x=dir_x,
                dir_y=dir_y,
                velocidade=250.0,
                dano=15,
                tempo_vida=3.8,
                dono="inimigo",
                largura=12,
                altura=12,
                sprite_key="projetil_inimigo"
            )
            self.projeteis_pendentes.append(proj)

    def _disparar_estilhacos_acusticos(self):
        """Gera 4 estilhaços acústicos em leque perpendicular após bater na parede."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0

        for ang_deg in (45, 135, 225, 315):
            rad = math.radians(ang_deg)
            proj = Projetil(
                x=cx - 5.0,
                y=cy - 5.0,
                dir_x=math.cos(rad),
                dir_y=math.sin(rad),
                velocidade=260.0,
                dano=12,
                tempo_vida=3.0,
                dono="inimigo",
                largura=10,
                altura=10,
                sprite_key="projetil_inimigo"
            )
            self.projeteis_pendentes.append(proj)

    def _disparar_totem_acustico(self):
        """Gera pulso radial concêntrico de 8 projéteis e instala uma Caixa de Som destrutível na arena."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0

        for i in range(8):
            ang = i * (2.0 * math.pi / 8.0)
            proj = Projetil(
                x=cx - 5.0,
                y=cy - 5.0,
                dir_x=math.cos(ang),
                dir_y=math.sin(ang),
                velocidade=180.0,
                dano=10,
                tempo_vida=3.5,
                dono="inimigo",
                largura=10,
                altura=10,
                sprite_key="projetil_inimigo"
            )
            self.projeteis_pendentes.append(proj)

        ang_t = random.uniform(0.0, 2.0 * math.pi)
        tx = clamp(cx + math.cos(ang_t) * 210.0 - 20.0, 60.0, float(LARGURA_ARENA - 100.0))
        ty = clamp(cy + math.sin(ang_t) * 210.0 - 20.0, 60.0, float(ALTURA_ARENA - 100.0))
        self.caixas_som_pendentes.append(CaixaDeSomBoss(x=tx, y=ty))

    def _disparar_helix_tsunami(self):
        """Dispara feixe triplo helicoidal rotativo a partir do centro do palco."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0

        for offset in (0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0):
            ang = self.angulo_helix + offset
            proj = Projetil(
                x=cx - 5.0,
                y=cy - 5.0,
                dir_x=math.cos(ang),
                dir_y=math.sin(ang),
                velocidade=255.0,
                dano=10,
                tempo_vida=4.5,
                dono="inimigo",
                largura=10,
                altura=10,
                sprite_key="projetil_inimigo"
            )
            self.projeteis_pendentes.append(proj)

    def _disparar_blast_radial(self):
        """Dispara uma explosão omnidirecional de 20 ondas de choque de alta velocidade."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0

        num_blast = 20
        for i in range(num_blast):
            ang = i * (2.0 * math.pi / num_blast)
            proj = Projetil(
                x=cx - 6.0,
                y=cy - 6.0,
                dir_x=math.cos(ang),
                dir_y=math.sin(ang),
                velocidade=320.0,
                dano=12,
                tempo_vida=3.5,
                dono="inimigo",
                largura=12,
                altura=12,
                sprite_key="projetil_inimigo"
            )
            self.projeteis_pendentes.append(proj)

    def obter_projeteis_pendentes(self) -> list[Projetil]:
        """Retorna e esvazia a fila de novos projéteis disparados."""
        projeteis = list(self.projeteis_pendentes)
        self.projeteis_pendentes.clear()
        return projeteis

    def obter_shake_pendente(self) -> float:
        """Consome o impulso pendente de tremor de tela."""
        if self.shake_screen:
            intensidade = self.shake_intensidade
            self.shake_screen = False
            self.shake_intensidade = 0.0
            return intensidade
        return 0.0

    # -------------------------------------------------------------------------
    # Renderização Gráfica e Balão de Fala
    # -------------------------------------------------------------------------

    def desenhar_balao_fala(self, screen, draw_x: float, draw_y: float):
        """
        Renderiza o balão de quadrinhos acima do topo da Geladeira Tsunami
        com o texto: 'Você já passou da validade.\nSente a pressão, neném.'
        e ponteiro triangular apontando para baixo.
        """
        if not pygame.font.get_init():
            try:
                pygame.font.init()
            except Exception:
                return

        if self._balao_fonte_cache is None:
            try:
                self._balao_fonte_cache = pygame.font.SysFont("arial", 13, bold=True)
            except Exception:
                self._balao_fonte_cache = pygame.font.Font(None, 18)

        fonte = self._balao_fonte_cache
        linhas = self.balao_fala_texto.split("\n")
        surfs_linhas = [fonte.render(linha, True, (25, 25, 35)) for linha in linhas]

        largura_max = max(s.get_width() for s in surfs_linhas)
        altura_total = sum(s.get_height() for s in surfs_linhas)

        pad_x = 12
        pad_y = 8
        balao_w = largura_max + pad_x * 2
        balao_h = altura_total + pad_y * 2 + 4

        # Posição centralizada acima do chefe
        balao_x = draw_x + self.largura / 2.0 - balao_w / 2.0
        balao_y = draw_y - balao_h - 16

        # Clamping na janela visível (1280x720 ou dimensão da surface)
        sw_max = float(screen.get_width() if hasattr(screen, "get_width") else LARGURA_TELA)
        sh_max = float(screen.get_height() if hasattr(screen, "get_height") else ALTURA_TELA)
        balao_x = clamp(balao_x, 10.0, sw_max - balao_w - 10.0)
        balao_y = clamp(balao_y, 10.0, sh_max - balao_h - 10.0)

        # 1. Caixa arredondada do balão
        balao_rect = pygame.Rect(int(balao_x), int(balao_y), int(balao_w), int(balao_h))
        pygame.draw.rect(screen, (248, 248, 255), balao_rect, border_radius=8)
        pygame.draw.rect(screen, (30, 35, 50), balao_rect, width=2, border_radius=8)

        # 2. Ponteiro triangular apontando para o topo central da Geladeira
        ponta_alvo_x = draw_x + self.largura / 2.0
        ponta_alvo_y = draw_y - 2.0
        p1 = (balao_x + balao_w / 2.0 - 8, balao_y + balao_h)
        p2 = (balao_x + balao_w / 2.0 + 8, balao_y + balao_h)
        p3 = (ponta_alvo_x, min(ponta_alvo_y, balao_y + balao_h + 14))

        pygame.draw.polygon(screen, (248, 248, 255), [p1, p2, p3])
        pygame.draw.line(screen, (30, 35, 50), p1, p3, 2)
        pygame.draw.line(screen, (30, 35, 50), p2, p3, 2)

        # 3. Renderização do texto
        curr_y = balao_y + pad_y
        for s in surfs_linhas:
            sx = balao_x + (balao_w - s.get_width()) / 2.0
            screen.blit(s, (int(sx), int(curr_y)))
            curr_y += s.get_height() + 2

    def desenhar(self, janela_ou_superficie, camera=None):
        """
        Renderiza o chefe, efeitos de aura, linha de telegrafo, sprite e balão de fala.
        Compatível com instâncias de Janela, Surface e offsets de câmera.
        """
        if not self.vivo and self.estado != ESTADO_MORTE:
            return

        screen = getattr(janela_ou_superficie, "screen", janela_ou_superficie)
        if not isinstance(screen, pygame.Surface):
            return

        if hasattr(camera, "transform_x"):
            draw_x = camera.transform_x(self.x)
            draw_y = camera.transform_y(self.y)
        elif isinstance(camera, (tuple, list)) and len(camera) >= 2:
            draw_x = self.x - camera[0]
            draw_y = self.y - camera[1]
        else:
            draw_x = self.x
            draw_y = self.y

        # Não renderiza se fora da tela virtual visível (exceto durante ESTADO_INTRO com balão de fala visível)
        sw_vis = screen.get_width() if hasattr(screen, "get_width") else LARGURA_TELA
        sh_vis = screen.get_height() if hasattr(screen, "get_height") else ALTURA_TELA
        if draw_x < -150 or draw_x > sw_vis + 150 or draw_y < -180 or draw_y > sh_vis + 180:
            if self.estado == ESTADO_INTRO and self.mostrar_balao_fala:
                self.desenhar_balao_fala(screen, draw_x, draw_y)
            return

        # 1. Linha de telégrafo do Bass Rush Dash (Fase 2)
        if self.estado == ESTADO_FASE2 and self.subestado_fase2 == "telegraph":
            cx = draw_x + self.largura / 2.0
            cy = draw_y + self.altura / 2.0
            f_x = cx + self.dash_dir_x * 350.0
            f_y = cy + self.dash_dir_y * 350.0
            pygame.draw.line(screen, (255, 80, 80), (cx, cy), (f_x, f_y), 3)

        display_inited = pygame.display.get_init()

        # 2. Aura sônica pulsante (Fase 1, 2, 3)
        if self.estado in (ESTADO_FASE1, ESTADO_FASE2, ESTADO_FASE3):
            try:
                ticks = pygame.time.get_ticks() if display_inited else 0
                pulso = math.sin(ticks / 100.0) * 6.0
                raio_aura = max(self.largura, self.altura) / 2.0 + 10.0 + pulso
                centro_x = int(draw_x + self.largura / 2.0)
                centro_y = int(draw_y + self.altura / 2.0)

                dim_aura = max(10, int((raio_aura + 6.0) * 2))
                is_fase3 = (self.estado == ESTADO_FASE3)
                aura_key = (dim_aura, is_fase3)

                if display_inited:
                    if aura_key not in self._aura_cache:
                        aura_surf = pygame.Surface((dim_aura, dim_aura), pygame.SRCALPHA)
                        acx = dim_aura // 2
                        acy = dim_aura // 2
                        cor_aura = (175, 75, 255, 70) if not is_fase3 else (255, 80, 180, 90)
                        pygame.draw.circle(aura_surf, cor_aura, (acx, acy), max(1, int(raio_aura)))
                        pygame.draw.circle(aura_surf, (255, 215, 0, 200), (acx, acy), max(1, int(raio_aura)), width=2)
                        self._aura_cache[aura_key] = aura_surf
                    else:
                        aura_surf = self._aura_cache[aura_key]
                else:
                    aura_surf = pygame.Surface((dim_aura, dim_aura), pygame.SRCALPHA)
                    acx = dim_aura // 2
                    acy = dim_aura // 2
                    cor_aura = (175, 75, 255, 70) if not is_fase3 else (255, 80, 180, 90)
                    pygame.draw.circle(aura_surf, cor_aura, (acx, acy), max(1, int(raio_aura)))
                    pygame.draw.circle(aura_surf, (255, 215, 0, 200), (acx, acy), max(1, int(raio_aura)), width=2)

                acx = dim_aura // 2
                acy = dim_aura // 2
                screen.blit(aura_surf, (centro_x - acx, centro_y - acy))
            except Exception:
                pass

        # 3. Renderização do Sprite do Boss (112x156)
        sprite = self._obter_sprite_boss(self.largura, self.altura)
        if sprite is not None:
            if self.flash_timer > 0.0 or (self.estado == ESTADO_MORTE and int(self.timer_morte * 15) % 2 == 0):
                if display_inited:
                    flash_key = (id(sprite), self.largura, self.altura)
                    if flash_key not in self._flash_cache:
                        sprite_flash = sprite.copy()
                        sprite_flash.fill((255, 220, 220, 200), special_flags=pygame.BLEND_ADD)
                        self._flash_cache[flash_key] = sprite_flash
                    else:
                        sprite_flash = self._flash_cache[flash_key]
                else:
                    sprite_flash = sprite.copy()
                    sprite_flash.fill((255, 220, 220, 200), special_flags=pygame.BLEND_ADD)
                screen.blit(sprite_flash, (int(draw_x), int(draw_y)))
            else:
                screen.blit(sprite, (int(draw_x), int(draw_y)))
        else:
            cor = (255, 255, 255) if self.flash_timer > 0.0 else (0, 180, 220)
            pygame.draw.rect(screen, cor, (int(draw_x), int(draw_y), self.largura, self.altura), border_radius=6)

        # 4. Partículas da cascata de explosões (Estado Morte)
        if self.particulas_explosao:
            for part in self.particulas_explosao:
                px = (camera.transform_x(part["x"]) if hasattr(camera, "transform_x") else part["x"])
                py = (camera.transform_y(part["y"]) if hasattr(camera, "transform_y") else part["y"])
                pygame.draw.circle(screen, part["cor"], (int(px), int(py)), max(1, int(part["raio"])))

        # 5. Balão de fala durante ESTADO_INTRO
        if self.mostrar_balao_fala:
            self.desenhar_balao_fala(screen, draw_x, draw_y)
