"""
Cena de Gameplay Principal — Protocolo: Batata
Gerencia o loop completo do jogo: jogador, câmera 2D com letterbox, armas,
projéteis, hordas de inimigos, colisões, HUD in-world e HUD em screen-space.
"""

import os
import pygame
from src.cenas.base_scene import BaseScene
from src.entidades.jogador import Jogador
from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.sistemas.sistema_spawn import SistemaSpawn
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

        # Sistemas de combate e spawn
        self.spawner = SistemaSpawn(max_ativos=60)
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
                        afetados = arma_ativa.executar_ataque(
                            centro_jogador_x, centro_jogador_y,
                            self.inimigos
                        )
                        if isinstance(afetados, (list, tuple)):
                            for inim in afetados:
                                if not getattr(inim, "vivo", True):
                                    self.abates += 1
                                    self.pontos += getattr(inim, "score_valor", 100)
                        self.buffer_tiro = 0.0
                        self.efeitos_melee.append({
                            "x": centro_jogador_x,
                            "y": centro_jogador_y,
                            "alcance": getattr(arma_ativa, "alcance", 140.0),
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

                    break

        # Limpeza de entidades destruídas / inativas
        self.projeteis = [p for p in self.projeteis if p.ativo]
        self.inimigos = [e for e in self.inimigos if e.vivo]

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

        # Indicador de alcance Melee quando empunhada (Antes do golpe)
        arma_ativa = self.jogador.obter_arma_ativa()
        if (isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1) and self.jogador.vivo:
            raio = int(getattr(arma_ativa, "alcance", 140))
            cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
            cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
            surf_alcance = pygame.Surface((raio * 2 + 4, raio * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf_alcance, (0, 220, 255, 20), (raio + 2, raio + 2), raio)
            pygame.draw.circle(surf_alcance, (0, 220, 255, 70), (raio + 2, raio + 2), raio, width=1)
            screen.blit(surf_alcance, (cx - raio - 2, cy - raio - 2))

        # Efeitos visuais de golpe Melee (Depois / Durante o golpe)
        for ef in self.efeitos_melee:
            raio = int(ef["alcance"])
            cx = int(self.camera.transform_x(ef["x"]))
            cy = int(self.camera.transform_y(ef["y"]))
            progresso = 1.0 - max(0.0, ef["tempo"] / ef["tempo_total"])
            alpha = int(220 * (1.0 - progresso))
            
            surf_golpe = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            raio_atual = int(raio * (0.5 + 0.5 * progresso))
            pygame.draw.circle(surf_golpe, (255, 215, 0, alpha // 4), (raio + 4, raio + 4), raio_atual)
            pygame.draw.circle(surf_golpe, (255, 255, 255, alpha), (raio + 4, raio + 4), raio_atual, width=3)
            screen.blit(surf_golpe, (cx - raio - 4, cy - raio - 4))

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

        # 3. Botão de Engrenagem e FPS (Top-Right)
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
