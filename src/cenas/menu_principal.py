"""
Cena do Menu Principal — Protocolo: Batata
Tela inicial do jogo com opções de Jogar, Configurações, Créditos e Sair.
"""

import sys
import os
import pygame
from src.cenas.base_scene import BaseScene
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.menu_configs import MenuConfigs
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, TITULO_JOGO,
    BRANCO, AZUL_CIANO, AMARELO_XP, CINZA_PAINEL, DOURADO,
    obter_caminho_asset, SAVE_FILE_PATH
)


class MenuPrincipalScene(BaseScene):
    def __init__(self):
        super().__init__()
        self.tempo_acumulado = 0.0
        self.opcao_selecionada = 0
        self.opcoes = ["JOGAR [ENTER]", "CONFIGURAÇÕES [C]", "TUTORIAL [T]", "SAIR [ESC]"]
        self.cooldown_input = 0.0

        # Sistema de configurações e Menu de Configurações
        self.gerenciador_config = GerenciadorConfiguracoes()
        self.gerenciador_config.carregar_arquivo(SAVE_FILE_PATH)
        self.menu_configs = MenuConfigs(self.gerenciador_config, em_jogo=False, cena=self)

        # Cache de fontes para alta performance
        self._fonte_titulo = pygame.font.SysFont("Arial", 36, bold=True)
        self._fonte_badge = pygame.font.SysFont("Arial", 13, bold=True)
        self._fonte_opcoes = pygame.font.SysFont("Arial", 18, bold=True)
        self._fonte_rodape = pygame.font.SysFont("Arial", 14)

        # Inicia a trilha sonora e sincroniza volumes com as configurações salvas
        try:
            from PPlay.sound import SoundManager
            SoundManager.inicializar()
            vol_master = self.gerenciador_config.obter_valor("volume_master")
            if vol_master is None:
                vol_master = 100
            vol_musica = self.gerenciador_config.obter_valor("volume_musica")
            if vol_musica is None:
                vol_musica = 100
            vol_sfx = self.gerenciador_config.obter_valor("volume_sfx")
            if vol_sfx is None:
                vol_sfx = 100

            # Aplica volume de SFX
            sfx_efetivo = int(round(vol_sfx * (vol_master / 100.0)))
            SoundManager.set_sfx_volume(sfx_efetivo)

            # Aplica volume de Música e toca faixa da fase se necessário
            caminho_musica = obter_caminho_asset("musica_fase")
            if os.path.isfile(caminho_musica):
                musica_volume_efetivo = (vol_musica / 100.0) * (vol_master / 100.0) * 0.4
                pygame.mixer.music.set_volume(musica_volume_efetivo)

                current_track = getattr(pygame.mixer.music, "_current_track", None)
                if current_track != caminho_musica or not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(caminho_musica)
                    pygame.mixer.music._current_track = caminho_musica
                    pygame.mixer.music.play(-1)
        except Exception:
            pass

    def loop(self):
        dt = min(self.janela.delta_time(), 0.1)
        self.tempo_acumulado += dt

        # Se o Menu de Configurações estiver aberto, delega o loop para ele
        if self.menu_configs.ativo:
            self.menu_configs.update(dt, self.teclado, self.mouse)
            if not self.menu_configs.ativo:
                self.cooldown_input = 0.18
            return

        if self.cooldown_input > 0.0:
            self.cooldown_input = max(0.0, self.cooldown_input - dt)
            return

        # Atalho direto para Configurações via tecla 'C'
        abrir_configs = False
        if hasattr(self.teclado, "key_down") and (self.teclado.key_down("c") or self.teclado.key_down("C")):
            abrir_configs = True

        if abrir_configs:
            self.menu_configs.abrir()
            return

        # Atalho direto para Tutorial via tecla 'T'
        abrir_tut = False
        if hasattr(self.teclado, "key_down") and (self.teclado.key_down("t") or self.teclado.key_down("T")):
            abrir_tut = True

        if abrir_tut:
            self.abrir_tutorial()
            return

        # Suporte a mouse (hover e clique nos botões do menu)
        inicio_y = 250
        espacamento = 50
        mx, my = None, None
        if self.mouse is not None and hasattr(self.mouse, "get_position"):
            try:
                mx, my = self.mouse.get_position()
            except Exception:
                mx, my = None, None

        mouse_clicado = False
        if self.mouse is not None and hasattr(self.mouse, "button_down"):
            try:
                if self.mouse.button_down(1):
                    mouse_clicado = True
            except Exception:
                pass

        if mx is not None and my is not None:
            for i in range(len(self.opcoes)):
                y = inicio_y + i * espacamento
                rect_opcao = pygame.Rect(0, y - 5, 280, 35)
                rect_opcao.centerx = LARGURA_TELA // 2
                if rect_opcao.collidepoint(mx, my):
                    self.opcao_selecionada = i
                    if mouse_clicado:
                        self._executar_opcao_selecionada()
                        return

        # Navegação com Teclado
        if self.teclado.key_down("UP") or self.teclado.key_down("w"):
            self.opcao_selecionada = (self.opcao_selecionada - 1) % len(self.opcoes)
        elif self.teclado.key_down("DOWN") or self.teclado.key_down("s"):
            self.opcao_selecionada = (self.opcao_selecionada + 1) % len(self.opcoes)

        # Seleção de opções
        if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE"):
            self._executar_opcao_selecionada()

        if self.teclado.key_down("ESC"):
            self.sair_jogo()

    def _executar_opcao_selecionada(self):
        if self.opcao_selecionada == 0:
            self.iniciar_jogo()
        elif self.opcao_selecionada == 1:
            self.menu_configs.abrir()
        elif self.opcao_selecionada == 2:
            self.abrir_tutorial()
        elif self.opcao_selecionada == 3:
            self.sair_jogo()

    def abrir_tutorial(self):
        from PPlay.scenemanager import SceneManager
        from src.cenas.tutorial import TutorialScene
        SceneManager.change_scene(TutorialScene())

    def draw(self):
        screen = self.janela.screen

        # Se o Menu de Configurações estiver ativo, desenha-o
        if self.menu_configs.ativo:
            self.menu_configs.draw(screen)
            return

        # Fundo do menu com grade sutil
        screen.fill((18, 22, 30))

        # Título principal perfeitamente centralizado com pygame.font e rect.centerx
        fonte_titulo = self._fonte_titulo
        titulo_surf = fonte_titulo.render(TITULO_JOGO, True, DOURADO)
        titulo_rect = titulo_surf.get_rect(centerx=LARGURA_TELA // 2, top=100)
        screen.blit(titulo_surf, titulo_rect)

        # Badge de Recorde e Melhor Tempo (Estatísticas Globais)
        estatisticas = self.gerenciador_config.obter_estatisticas()
        high_score = estatisticas.get("high_score", 0)
        melhor_tempo = estatisticas.get("melhor_tempo", 0.0)
        m_tempo = int(melhor_tempo // 60)
        s_tempo = int(melhor_tempo % 60)

        badge_rect = pygame.Rect(0, 160, 480, 32)
        badge_rect.centerx = LARGURA_TELA // 2
        pygame.draw.rect(screen, (25, 32, 45), badge_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 75, 95), badge_rect, width=1, border_radius=6)

        fonte_badge = self._fonte_badge
        texto_badge = f"RECORDE: {high_score:,} PTS   |   MELHOR TEMPO: {m_tempo:02d}:{s_tempo:02d}"
        badge_surf = fonte_badge.render(texto_badge, True, (215, 230, 250))
        badge_text_rect = badge_surf.get_rect(center=badge_rect.center)
        screen.blit(badge_surf, badge_text_rect)

        # Painel central das opções
        inicio_y = 250
        espacamento = 50
        fonte_opcoes = self._fonte_opcoes

        for i, texto in enumerate(self.opcoes):
            y = inicio_y + i * espacamento
            selecionado = (i == self.opcao_selecionada)

            cor_texto = DOURADO if selecionado else BRANCO
            prefixo = "> " if selecionado else "  "
            texto_opcao = f"{prefixo}{texto}"

            # Desenha destaque do botão selecionado perfeitamente centralizado
            if selecionado:
                caixa_destaque = pygame.Rect(0, y - 5, 280, 35)
                caixa_destaque.centerx = LARGURA_TELA // 2
                pygame.draw.rect(screen, (35, 48, 68), caixa_destaque, border_radius=6)
                pygame.draw.rect(screen, AZUL_CIANO, caixa_destaque, width=2, border_radius=6)

            opcao_surf = fonte_opcoes.render(texto_opcao, True, cor_texto)
            opcao_rect = opcao_surf.get_rect(centerx=LARGURA_TELA // 2, centery=y + 12)
            screen.blit(opcao_surf, opcao_rect)

        # Rodapé com instruções perfeitamente centralizado
        fonte_rodape = self._fonte_rodape
        rodape_surf = fonte_rodape.render(
            "PPlay 2.0 Engine | Use [W/S] ou [Setas] para navegar e [ENTER] para confirmar",
            True,
            (120, 135, 155)
        )
        rodape_rect = rodape_surf.get_rect(centerx=LARGURA_TELA // 2, bottom=ALTURA_TELA - 25)
        screen.blit(rodape_surf, rodape_rect)

    def iniciar_jogo(self):
        from PPlay.scenemanager import SceneManager
        from src.cenas.gameplay import GameplayScene
        SceneManager.change_scene(GameplayScene())

    def sair_jogo(self):
        self.janela.close()
