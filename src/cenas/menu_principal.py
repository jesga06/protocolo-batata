"""
Cena do Menu Principal — Protocolo: Batata
Tela inicial do jogo com opções de Jogar, Configurações, Créditos e Sair.
"""

import sys
import os
import pygame
from src.cenas.base_scene import BaseScene
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, TITULO_JOGO,
    BRANCO, AZUL_CIANO, AMARELO_XP, CINZA_PAINEL, DOURADO,
    obter_caminho_asset
)


class MenuPrincipalScene(BaseScene):
    def __init__(self):
        super().__init__()
        self.tempo_acumulado = 0.0
        self.opcao_selecionada = 0
        self.opcoes = ["JOGAR [ENTER]", "CONFIGURAÇÕES [C]", "CRÉDITOS [K]", "SAIR [ESC]"]

        # Inicia a trilha sonora em loop contínuo
        try:
            caminho_musica = obter_caminho_asset("musica_fase")
            if os.path.isfile(caminho_musica):
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(caminho_musica)
                    pygame.mixer.music.set_volume(0.4)
                    pygame.mixer.music.play(-1)
        except Exception:
            pass

    def loop(self):
        dt = self.janela.delta_time()
        self.tempo_acumulado += dt

        # Navegação com Teclado
        if self.teclado.key_down("UP") or self.teclado.key_down("w"):
            self.opcao_selecionada = (self.opcao_selecionada - 1) % len(self.opcoes)
        elif self.teclado.key_down("DOWN") or self.teclado.key_down("s"):
            self.opcao_selecionada = (self.opcao_selecionada + 1) % len(self.opcoes)

        # Seleção de opções
        if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE"):
            if self.opcao_selecionada == 0:
                self.iniciar_jogo()
            elif self.opcao_selecionada == 3:
                self.sair_jogo()

        if self.teclado.key_down("ESC"):
            self.sair_jogo()

    def draw(self):
        # Fundo do menu com grade sutil
        screen = self.janela.screen
        screen.fill((18, 22, 30))

        # Título principal perfeitamente centralizado com pygame.font e rect.centerx
        fonte_titulo = pygame.font.SysFont("Arial", 36, bold=True)
        titulo_surf = fonte_titulo.render(TITULO_JOGO, True, DOURADO)
        titulo_rect = titulo_surf.get_rect(centerx=LARGURA_TELA // 2, top=110)
        screen.blit(titulo_surf, titulo_rect)

        # Painel central das opções
        inicio_y = 260
        espacamento = 50
        fonte_opcoes = pygame.font.SysFont("Arial", 18, bold=True)

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
        fonte_rodape = pygame.font.SysFont("Arial", 14)
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
