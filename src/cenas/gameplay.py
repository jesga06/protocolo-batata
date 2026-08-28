"""
Cena de Gameplay Principal — Protocolo: Batata
Gerencia o loop completo do jogo: jogador, câmera 2D com letterbox, armas,
projéteis, hordas de inimigos, colisões, HUD in-world e HUD em screen-space.
"""

import math
import os
import pygame
from src.cenas.base_scene import BaseScene
from src.entidades.jogador import Jogador
from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.ui.hud import HUD
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    BRANCO, PRETO, CINZA_FUNDO, CINZA_PAINEL, CINZA_BORDA,
    VERMELHO_HP, VERDE_CURA, AMARELO_XP, AZUL_CIANO, DOURADO,
    obter_caminho_asset
)
from src.utils.math_utils import colisao_aabb, clamp


class GameplayScene(BaseScene):
    """
    Cena principal de combate e sobrevivência na arena.
    """
    _tile_piso = None
    _btn_gear_img = None
    _slot_inv_img = None

    def __init__(self):
        super().__init__()
        self.largura_arena = LARGURA_ARENA
        self.altura_arena = ALTURA_ARENA

        # Jogador posicionado no centro da arena
        self.jogador = Jogador(
            x=self.largura_arena / 2.0 - 16,
            y=self.altura_arena / 2.0 - 16
        )

        # Câmera 2D vinculada às dimensões virtuais
        self.camera = Camera(LARGURA_TELA, ALTURA_TELA)
        self.camera.set_world_bounds(self.largura_arena, self.altura_arena)

        # Sistemas de combate, spawn, drops e progressão
        self.spawner = SistemaSpawn(max_ativos=60)
        self.sistema_drops = SistemaDrops()
        self.sistema_scavenger = SistemaScavenger()
        self.hud = HUD()
        self.projeteis: list[Projetil] = []
        self.inimigos: list[InimigoBase] = []

        # Métricas de partida
        self.tempo_sobrevivencia = 0.0
        self.abates = 0
        self.pontos = 0
        self.pausado = False
        self.game_over = False

        # Input buffer e efeitos visuais
        self.buffer_tiro = 0.0
        self.efeitos_melee: list[dict] = []

    @classmethod
    def _carregar_assets_cenario(cls):
        if cls._tile_piso is None:
            try:
                caminho = obter_caminho_asset("tile_piso")
                if os.path.isfile(caminho):
                    cls._tile_piso = pygame.image.load(caminho).convert()
            except Exception:
                cls._tile_piso = None

        if cls._btn_gear_img is None:
            try:
                caminho = obter_caminho_asset("btn_gear")
                if os.path.isfile(caminho):
                    cls._btn_gear_img = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._btn_gear_img = None

        if cls._slot_inv_img is None:
            try:
                caminho = obter_caminho_asset("slot_inventario")
                if os.path.isfile(caminho):
                    cls._slot_inv_img = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._slot_inv_img = None

    def loop(self):
        dt = self.janela.delta_time()
        # Se dt for 0 ou excessivamente baixo (em testes headless ultra-rápidos), usa 1/60s
        if dt < 0.005:
            dt = 1.0 / 60.0
        # Clampa dt para evitar saltos quânticos em frames atípicos (máximo 100ms)
        dt = min(dt, 0.1)

        # Controle de Pausa via Teclado (ESC)
        if self.teclado.key_down("ESC"):
            if not self.game_over:
                self.pausado = not self.pausado
            else:
                self._voltar_menu()
                return

        # Comportamento no estado de Game Over
        if self.game_over:
            if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE"):
                self._reiniciar_partida()
            return

        # Comportamento no estado Pausado
        if self.pausado:
            if self.teclado.key_down("m") or self.teclado.key_down("M"):
                self._voltar_menu()
            return

        # =========================================================================
        # 1. ATUALIZAÇÃO DO JOGADOR E INPUTS
        # =========================================================================
        self.tempo_sobrevivencia += dt

        self.jogador.processar_input(
            self.teclado,
            self.mouse,
            dt,
            limite_arena=(self.largura_arena, self.altura_arena)
        )
        self.jogador.update(dt)

        # Atualiza a posição da câmera para seguir o jogador suavemente
        self.camera.follow(self.jogador, suavizacao=0.15)

        # =========================================================================
        # 2. DISPARO DE ARMAS (PISTOLA E MELEE)
        # =========================================================================
        # =========================================================================
        # 2. DISPARO DE ARMAS (PISTOLA E MELEE COM BUFFER DE INPUT)
        # =========================================================================
        centro_jogador_x = self.jogador.x + self.jogador.largura / 2.0
        centro_jogador_y = self.jogador.y + self.jogador.altura / 2.0

        # Posição virtual do cursor convertida para espaço do mundo
        try:
            mx, my = self.mouse.get_position()
        except Exception:
            mx, my = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)

        mouse_mundo_x = mx + self.camera.x
        mouse_mundo_y = my + self.camera.y

        # Detecta clique no botão de engrenagem (752, 16, 32x32)
        if self.mouse.button_down(1):
            if 752 <= mx <= 784 and 16 <= my <= 48:
                self.pausado = True
                return

        # Input buffer: se o mouse estiver pressionado neste frame, alimenta o buffer
        mouse_pressionado = pygame.mouse.get_pressed()[0]
        if mouse_pressionado:
            self.buffer_tiro = 0.15  # Buffer de 150ms para garantir que cliques rápidos nunca sejam perdidos
        else:
            self.buffer_tiro = max(0.0, self.buffer_tiro - dt)

        disparar_agora = (self.buffer_tiro > 0.0)

        if disparar_agora and self.jogador.vivo:
            arma_ativa = self.jogador.obter_arma_ativa()
            if arma_ativa is not None:
                if isinstance(arma_ativa, Pistola) or getattr(arma_ativa, "slot", None) == 2:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        novos_tiros = arma_ativa.disparar(
                            centro_jogador_x, centro_jogador_y,
                            mouse_mundo_x, mouse_mundo_y
                        )
                        if novos_tiros:
                            self.projeteis.extend(novos_tiros)
                            self.buffer_tiro = 0.0
                elif isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        ang_mira = math.atan2(mouse_mundo_y - centro_jogador_y, mouse_mundo_x - centro_jogador_x)
                        afetados = arma_ativa.executar_ataque(
                            centro_jogador_x, centro_jogador_y,
                            self.inimigos,
                            mira_x=mouse_mundo_x,
                            mira_y=mouse_mundo_y,
                            angulo_mira=ang_mira
                        )
                        if isinstance(afetados, (list, tuple)):
                            for inim in afetados:
                                if not getattr(inim, "vivo", True):
                                    self.abates += 1
                                    self.pontos += getattr(inim, "score_valor", 100)
                                    self.sistema_drops.gerar_drop_morte_inimigo(
                                        inim.x + getattr(inim, "largura", 28) / 2.0,
                                        inim.y + getattr(inim, "altura", 28) / 2.0,
                                        xp_base=getattr(inim, "xp_valor", 10)
                                    )
                        self.buffer_tiro = 0.0
                        self.efeitos_melee.append({
                            "x": centro_jogador_x,
                            "y": centro_jogador_y,
                            "angulo": ang_mira,
                            "alcance": getattr(arma_ativa, "alcance", 84.0),
                            "arco_graus": getattr(arma_ativa, "arco_graus", 45.0),
                            "tempo": 0.15,
                            "tempo_total": 0.15
                        })
                else:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        if hasattr(arma_ativa, "disparar"):
                            novos_tiros = arma_ativa.disparar(
                                centro_jogador_x, centro_jogador_y,
                                mouse_mundo_x, mouse_mundo_y
                            )
                            if novos_tiros:
                                self.projeteis.extend(novos_tiros)
                                self.buffer_tiro = 0.0

        # Atualiza o tempo de vida dos efeitos visuais de Melee
        for ef in self.efeitos_melee:
            ef["tempo"] -= dt
        self.efeitos_melee = [ef for ef in self.efeitos_melee if ef["tempo"] > 0]

        # =========================================================================
        # 3. SPAWNER DE INIMIGOS
        # =========================================================================
        novos_inimigos = self.spawner.update(
            dt=dt,
            camera_x=self.camera.x,
            camera_y=self.camera.y,
            total_inimigos_vivos=len(self.inimigos),
            view_w=LARGURA_TELA,
            view_h=ALTURA_TELA,
            arena_w=self.largura_arena,
            arena_h=self.altura_arena
        )
        self.inimigos.extend(novos_inimigos)

        # =========================================================================
        # 4. FÍSICA DOS PROJÉTEIS
        # =========================================================================
        for proj in self.projeteis:
            proj.update(dt)
            # Desativa projéteis que saíram muito longe dos limites da arena
            if (proj.x < -100 or proj.x > self.largura_arena + 100 or
                proj.y < -100 or proj.y > self.altura_arena + 100):
                proj.ativo = False

        # =========================================================================
        # 5. IA DOS INIMIGOS E DANO DE CONTATO NO JOGADOR
        # =========================================================================
        for inimigo in self.inimigos:
            inimigo.update(dt, (centro_jogador_x, centro_jogador_y))
            inimigo.tentar_causar_dano_contato(self.jogador)

        # =========================================================================
        # 6. COLISÕES: PROJÉTEIS VS INIMIGOS
        # =========================================================================
        for proj in self.projeteis:
            if not proj.ativo:
                continue

            for inimigo in self.inimigos:
                if not inimigo.vivo:
                    continue

                if colisao_aabb(
                    proj.x, proj.y, proj.largura, proj.altura,
                    inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                ):
                    inimigo.receber_dano(proj.dano)
                    proj.ativo = False

                    if not inimigo.vivo:
                        self.abates += 1
                        self.pontos += inimigo.score_valor
                        self.sistema_drops.gerar_drop_morte_inimigo(
                            inimigo.x + inimigo.largura / 2.0,
                            inimigo.y + inimigo.altura / 2.0,
                            xp_base=getattr(inimigo, "xp_valor", 10)
                        )

                    break

        # Limpeza de entidades destruídas / inativas
        self.projeteis = [p for p in self.projeteis if p.ativo]
        self.inimigos = [e for e in self.inimigos if e.vivo]

        # =========================================================================
        # 7. SISTEMA DE DROPS E PROGRESSÃO DE XP
        # =========================================================================
        self.sistema_drops.update(dt)
        eventos_coleta = self.sistema_drops.coletar_jogador(self.jogador)
        for ev in eventos_coleta:
            if ev["tipo"] == "xp":
                self.jogador.ganhar_xp(ev["valor"])

        # Atualiza IA do Scavenger se houver drops elegíveis
        self.sistema_scavenger.update(dt, self.inimigos, self.sistema_drops.drops)

        # Verifica morte do jogador
        if not self.jogador.vivo:
            self.game_over = True

    def draw(self):
        screen = self.janela.screen
        self._carregar_assets_cenario()

        # =========================================================================
        # CAMADA 1: ESPAÇO DO MUNDO (TRANSFORMADO PELA CÂMERA)
        # =========================================================================
        # Fundo da arena
        screen.fill(CINZA_FUNDO)

        # Renderização do piso ladrilhado visível
        tile_tam = 32
        inicio_tx = max(0, int(self.camera.x // tile_tam))
        fim_tx = min(int(self.largura_arena // tile_tam), int((self.camera.x + LARGURA_TELA) // tile_tam) + 1)
        inicio_ty = max(0, int(self.camera.y // tile_tam))
        fim_ty = min(int(self.altura_arena // tile_tam), int((self.camera.y + ALTURA_TELA) // tile_tam) + 1)

        if self._tile_piso is not None:
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    screen.blit(self._tile_piso, (self.camera.transform_x(wx), self.camera.transform_y(wy)))
        else:
            # Grade fallback caso textura não esteja em RAM
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    dx = self.camera.transform_x(wx)
                    dy = self.camera.transform_y(wy)
                    pygame.draw.rect(screen, (28, 32, 42), (dx, dy, tile_tam, tile_tam), 1)

        # Linhas delimitadoras da arena
        borda_x0 = self.camera.transform_x(0)
        borda_y0 = self.camera.transform_y(0)
        borda_x1 = self.camera.transform_x(self.largura_arena)
        borda_y1 = self.camera.transform_y(self.altura_arena)
        pygame.draw.rect(screen, AZUL_CIANO, (borda_x0, borda_y0, self.largura_arena, self.altura_arena), width=3)

        # Posição virtual do cursor do mouse em coordenadas de mundo
        try:
            mx, my = self.mouse.get_position()
        except Exception:
            mx, my = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)
        mouse_mundo_x = mx + self.camera.x
        mouse_mundo_y = my + self.camera.y

        # Indicador de alcance Melee quando empunhada (Antes do golpe - Cone direcional de 45°)
        arma_ativa = self.jogador.obter_arma_ativa()
        if (isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1) and self.jogador.vivo:
            raio = getattr(arma_ativa, "alcance", 84.0)
            arco = getattr(arma_ativa, "arco_graus", 45.0)
            cx_mundo = self.jogador.x + self.jogador.largura / 2.0
            cy_mundo = self.jogador.y + self.jogador.altura / 2.0
            cx_tela = int(self.camera.transform_x(cx_mundo))
            cy_tela = int(self.camera.transform_y(cy_mundo))

            ang_centro = math.atan2(mouse_mundo_y - cy_mundo, mouse_mundo_x - cx_mundo)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio * 2 + 16)
            surf_alcance = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            s_cx = surf_dim // 2
            s_cy = surf_dim // 2

            pontos_setor = [(s_cx, s_cy)]
            num_seg = 12
            for step in range(num_seg + 1):
                ang = ang_centro - meio_arco + (2.0 * meio_arco * step / num_seg)
                px = s_cx + math.cos(ang) * raio
                py = s_cy + math.sin(ang) * raio
                pontos_setor.append((px, py))

            pygame.draw.polygon(surf_alcance, (0, 220, 255, 25), pontos_setor)
            pygame.draw.polygon(surf_alcance, (0, 220, 255, 80), pontos_setor, width=1)
            screen.blit(surf_alcance, (cx_tela - s_cx, cy_tela - s_cy))

        # Efeitos visuais de golpe Melee (Depois / Durante o golpe - Slash Fan de 45°)
        for ef in self.efeitos_melee:
            raio_base = ef["alcance"]
            arco = ef.get("arco_graus", 45.0)
            ang_centro = ef.get("angulo", 0.0)
            cx_tela = int(self.camera.transform_x(ef["x"]))
            cy_tela = int(self.camera.transform_y(ef["y"]))

            progresso = 1.0 - max(0.0, ef["tempo"] / ef["tempo_total"])
            alpha = int(240 * (1.0 - progresso))
            raio_atual = raio_base * (0.4 + 0.6 * progresso)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio_base * 2 + 16)
            surf_golpe = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            s_cx = surf_dim // 2
            s_cy = surf_dim // 2

            pontos_fan = [(s_cx, s_cy)]
            num_seg = 12
            for step in range(num_seg + 1):
                ang = ang_centro - meio_arco + (2.0 * meio_arco * step / num_seg)
                px = s_cx + math.cos(ang) * raio_atual
                py = s_cy + math.sin(ang) * raio_atual
                pontos_fan.append((px, py))

            pygame.draw.polygon(surf_golpe, (255, 215, 0, alpha // 3), pontos_fan)
            pygame.draw.polygon(surf_golpe, (255, 255, 255, alpha), pontos_fan, width=2)
            screen.blit(surf_golpe, (cx_tela - s_cx, cy_tela - s_cy))

        # Drops de itens e gemas de XP no chão da arena
        self.sistema_drops.desenhar(self.janela, self.camera)

        # Inimigos
        for inimigo in self.inimigos:
            inimigo.desenhar(self.janela, self.camera)

        # Jogador
        self.jogador.desenhar(self.janela, self.camera)

        # Projéteis
        for proj in self.projeteis:
            proj.desenhar(self.janela, self.camera)

        # Barra de HP in-world flutuando abaixo do jogador
        self._desenhar_hp_in_world()

        # =========================================================================
        # CAMADA 2: ESPAÇO DA TELA (SCREEN-SPACE HUD)
        # =========================================================================
        self._desenhar_hud_tela()

        # Overlays modais de Pausa e Game Over
        if self.game_over:
            self._desenhar_overlay_game_over()
        elif self.pausado:
            self._desenhar_overlay_pausa()

    def _desenhar_hp_in_world(self):
        """Desenha a barra de HP diretamente abaixo da batata."""
        if not self.jogador.vivo:
            return

        centro_x = self.jogador.x + self.jogador.largura / 2.0
        base_y = self.jogador.y + self.jogador.altura + 6

        bar_x = self.camera.transform_x(centro_x - 20)
        bar_y = self.camera.transform_y(base_y)

        bar_w = 40
        bar_h = 6

        # Fundo vermelho
        pygame.draw.rect(self.janela.screen, (160, 30, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=2)

        # Preenchimento verde
        proporcao = clamp(self.jogador.hp / float(self.jogador.hp_max), 0.0, 1.0)
        fill_w = int(bar_w * proporcao)
        if fill_w > 0:
            pygame.draw.rect(self.janela.screen, VERDE_CURA, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

        # Borda escura
        pygame.draw.rect(self.janela.screen, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=2)

    def _desenhar_hud_tela(self):
        """Renderiza o HUD fixo na tela: inventário, métricas e botão de engrenagem."""
        screen = self.janela.screen

        # 1. Slots de inventário (Top-Left: 16, 16) com destaque para o slot ativo
        slot_tam = 38
        slot_ativo = getattr(self.jogador, "slot_ativo", 2)

        fonte_slots = pygame.font.SysFont("Arial", 10, bold=True)
        for i in range(4):
            sx = 16 + i * (slot_tam + 6)
            sy = 16
            slot_num = i + 1
            is_ativo = (slot_num == slot_ativo)

            # Cor de fundo e borda destacada para o slot selecionado
            bg_cor = (40, 50, 70) if is_ativo else (25, 30, 42)
            borda_cor = DOURADO if is_ativo else CINZA_BORDA
            borda_largura = 3 if is_ativo else 2

            pygame.draw.rect(screen, bg_cor, (sx, sy, slot_tam, slot_tam), border_radius=4)
            pygame.draw.rect(screen, borda_cor, (sx, sy, slot_tam, slot_tam), width=borda_largura, border_radius=4)

            # Rótulo de cada slot
            if i == 0:
                texto_slot = "1:Melee"
                cor_slot = DOURADO if is_ativo else CINZA_BORDA
            elif i == 1:
                texto_slot = "2:Pistol"
                cor_slot = DOURADO if is_ativo else CINZA_BORDA
            elif i == 2:
                texto_slot = "3:Espec"
                cor_slot = DOURADO if is_ativo else (80, 90, 110)
            elif i == 3:
                texto_slot = "4:Drone"
                cor_slot = (80, 90, 110)

            lbl_surf = fonte_slots.render(texto_slot, True, cor_slot)
            lbl_rect = lbl_surf.get_rect(centerx=sx + slot_tam // 2, centery=sy + slot_tam // 2)
            screen.blit(lbl_surf, lbl_rect)

        # 2. Cronômetro de Sobrevivência e Contador de Abates (Top-Center) perfeitamente centralizados
        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)
        texto_tempo = f"{minutos:02d}:{segundos:02d}"

        fonte_tempo = pygame.font.SysFont("Arial", 22, bold=True)
        tempo_surf = fonte_tempo.render(texto_tempo, True, BRANCO)
        tempo_rect = tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=14)
        screen.blit(tempo_surf, tempo_rect)

        texto_abates = f"Abates: {self.abates}"
        fonte_abates = pygame.font.SysFont("Arial", 14, bold=True)
        abates_surf = fonte_abates.render(texto_abates, True, AMARELO_XP)
        abates_rect = abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=40)
        screen.blit(abates_surf, abates_rect)

        # 3. Barra de Progresso de XP (Top-Center: top=62, 360x10 px)
        if hasattr(self, "hud") and self.hud is not None:
            self.hud.desenhar_barra_xp(screen, self.jogador.sistema_xp)

        # 4. Botão de Engrenagem e FPS (Top-Right)
        fps_val = int(self.janela.get_fps())
        fonte_fps = pygame.font.SysFont("Arial", 14)
        fps_surf = fonte_fps.render(f"FPS: {fps_val}", True, AZUL_CIANO)
        fps_rect = fps_surf.get_rect(right=LARGURA_TELA - 60, centery=32)
        screen.blit(fps_surf, fps_rect)

        if self._btn_gear_img is not None:
            screen.blit(self._btn_gear_img, (752, 16))
        else:
            pygame.draw.rect(screen, (45, 55, 75), (752, 16, 32, 32), border_radius=4)
            gear_surf = fonte_fps.render("[⚙]", True, DOURADO)
            gear_rect = gear_surf.get_rect(centerx=768, centery=32)
            screen.blit(gear_surf, gear_rect)

    def _desenhar_overlay_pausa(self):
        """Overlay modal de pausa com textos perfeitamente centralizados."""
        screen = self.janela.screen
        dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        dark_surf.fill((10, 15, 22, 180))
        screen.blit(dark_surf, (0, 0))

        fonte_titulo = pygame.font.SysFont("Arial", 34, bold=True)
        fonte_sub = pygame.font.SysFont("Arial", 18, bold=True)

        t_surf = fonte_titulo.render("JOGO PAUSADO", True, DOURADO)
        t_rect = t_surf.get_rect(centerx=LARGURA_TELA // 2, top=200)
        screen.blit(t_surf, t_rect)

        c_surf = fonte_sub.render("[ESC] Continuar Partida", True, BRANCO)
        c_rect = c_surf.get_rect(centerx=LARGURA_TELA // 2, top=280)
        screen.blit(c_surf, c_rect)

        m_surf = fonte_sub.render("[M] Menu Principal", True, CINZA_BORDA)
        m_rect = m_surf.get_rect(centerx=LARGURA_TELA // 2, top=325)
        screen.blit(m_surf, m_rect)

    def _desenhar_overlay_game_over(self):
        """Overlay de fim de jogo com estatísticas perfeitamente centralizadas."""
        screen = self.janela.screen
        dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        dark_surf.fill((20, 5, 5, 210))
        screen.blit(dark_surf, (0, 0))

        fonte_tit = pygame.font.SysFont("Arial", 36, bold=True)
        fonte_sub = pygame.font.SysFont("Arial", 16)
        fonte_stat = pygame.font.SysFont("Arial", 18, bold=True)
        fonte_prompt = pygame.font.SysFont("Arial", 16, bold=True)

        tit_surf = fonte_tit.render("PROTOCOLO FALHOU", True, VERMELHO_HP)
        screen.blit(tit_surf, tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=160))

        sub_surf = fonte_sub.render("A Batata sucumbiu aos bugs e estagiários.", True, (200, 180, 180))
        screen.blit(sub_surf, sub_surf.get_rect(centerx=LARGURA_TELA // 2, top=210))

        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)

        tempo_surf = fonte_stat.render(f"Tempo de Sobrevivência: {minutos:02d}:{segundos:02d}", True, BRANCO)
        screen.blit(tempo_surf, tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=270))

        abates_surf = fonte_stat.render(f"Total de Abates: {self.abates}", True, AMARELO_XP)
        screen.blit(abates_surf, abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=305))

        pontos_surf = fonte_stat.render(f"Pontuação Final: {self.pontos}", True, AZUL_CIANO)
        screen.blit(pontos_surf, pontos_surf.get_rect(centerx=LARGURA_TELA // 2, top=340))

        prompt_surf = fonte_prompt.render("Pressione [ENTER] para Jogar Novamente ou [ESC] para o Menu", True, DOURADO)
        screen.blit(prompt_surf, prompt_surf.get_rect(centerx=LARGURA_TELA // 2, top=420))

    def _reiniciar_partida(self):
        SceneManager.change_scene(GameplayScene())

    def _voltar_menu(self):
        from src.cenas.menu_principal import MenuPrincipalScene
        SceneManager.change_scene(MenuPrincipalScene())
