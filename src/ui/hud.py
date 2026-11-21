"""
Componentes de HUD e Interface de Usuário — Protocolo: Batata
Gerencia a renderização de elementos de tela, incluindo a barra de progresso de XP do jogador.
"""

import pygame
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, BRANCO, PRETO,
    AMARELO_XP, DOURADO, CINZA_BORDA, AZUL_CIANO
)
from src.utils.math_utils import clamp


class HUD:
    """
    Controlador de interface visual fixa na tela (Screen-Space HUD).
    """

    def __init__(self):
        self._fonte_xp = pygame.font.SysFont("Arial", 12, bold=True)
        self._fonte_nome = pygame.font.SysFont("Arial", 14, bold=True)
        self._fonte_hp = pygame.font.SysFont("Arial", 11, bold=True)

    def _obter_fonte_xp(self):
        if self._fonte_xp is None:
            self._fonte_xp = pygame.font.SysFont("Arial", 12, bold=True)
        return self._fonte_xp

    def desenhar_barra_xp(self, screen, sistema_xp, visivel: bool = True):
        """
        Renderiza a barra de experiência centralizada na tela logo abaixo do HUD superior.
        Dimensões: 520x14 px, top=66, border_radius=4.
        """
        if not visivel or sistema_xp is None:
            return

        largura_barra = 520
        altura_barra = 14
        centro_x = screen.get_width() // 2 if hasattr(screen, "get_width") else LARGURA_TELA // 2
        pos_x = centro_x - largura_barra // 2
        pos_y = 66
        raio_borda = 4

        # 1. Fundo da barra
        bg_rect = (pos_x, pos_y, largura_barra, altura_barra)
        pygame.draw.rect(screen, (20, 25, 35), bg_rect, border_radius=raio_borda)

        # 2. Preenchimento proporcional
        progresso = sistema_xp.progresso_normalizado()
        fill_w = int(largura_barra * progresso)
        if fill_w > 0:
            fill_rect = (pos_x, pos_y, fill_w, altura_barra)
            pygame.draw.rect(screen, (255, 215, 0), fill_rect, border_radius=raio_borda)
            # Destaque superior sutil
            if fill_w > 4 and altura_barra >= 4:
                highlight_rect = (pos_x + 2, pos_y + 1, fill_w - 4, 2)
                pygame.draw.rect(screen, (255, 245, 160), highlight_rect, border_radius=1)

        # 3. Borda metálica
        pygame.draw.rect(screen, (50, 65, 85), bg_rect, width=1, border_radius=raio_borda)

        # 4. Texto de nível e progresso
        fonte = self._obter_fonte_xp()
        if sistema_xp.nivel >= sistema_xp.nivel_max:
            texto_str = f"NÍVEL {sistema_xp.nivel} (MÁXIMO)"
            cor_texto = DOURADO
        else:
            proximo_custo = sistema_xp.xp_para_proximo_nivel(sistema_xp.nivel)
            texto_str = f"Nv. {sistema_xp.nivel} - {sistema_xp.xp_atual}/{proximo_custo} XP"
            cor_texto = BRANCO

        # Sombra de texto para alta legibilidade
        sombra_surf = fonte.render(texto_str, True, (10, 10, 15))
        sombra_rect = sombra_surf.get_rect(centerx=centro_x + 1, centery=pos_y + altura_barra // 2 + 1)
        screen.blit(sombra_surf, sombra_rect)

        texto_surf = fonte.render(texto_str, True, cor_texto)
        texto_rect = texto_surf.get_rect(centerx=centro_x, centery=pos_y + altura_barra // 2)
        screen.blit(texto_surf, texto_rect)

    def desenhar_barra_boss(self, screen, boss, visivel: bool = True):
        """
        Renderiza a barra de vida dedicada para o Mini-Boss / Chefe Elite no topo da tela.
        Dimensões: 400x12 px em y=90 com moldura dourada e preenchimento roxo/magenta.
        """
        if not visivel or boss is None or not getattr(boss, "vivo", True):
            return

        largura_barra = 560
        altura_barra = 16
        centro_x = screen.get_width() // 2 if hasattr(screen, "get_width") else LARGURA_TELA // 2
        pos_x = centro_x - largura_barra // 2
        pos_y = 106
        raio_borda = 4

        # 1. Nome do Mini-Boss / Chefe (posicionado acima da barra em y=86 sem sobrepor a barra de XP)
        nome = getattr(boss, "nome_elite", "") or "MINI-BOSS ELITE"
        fonte_nome = self._fonte_nome
        nome_sombra = fonte_nome.render(nome, True, (10, 5, 20))
        nome_rect = nome_sombra.get_rect(centerx=centro_x + 1, top=87)
        screen.blit(nome_sombra, nome_rect)

        nome_surf = fonte_nome.render(nome, True, DOURADO)
        nome_rect_main = nome_surf.get_rect(centerx=centro_x, top=86)
        screen.blit(nome_surf, nome_rect_main)

        # 2. Fundo da barra (container roxo escuro)
        bg_rect = (pos_x, pos_y, largura_barra, altura_barra)
        pygame.draw.rect(screen, (35, 20, 50), bg_rect, border_radius=raio_borda)

        # 3. Preenchimento proporcional
        hp_max = max(1, getattr(boss, "hp_max", 100))
        hp_atual = max(0, getattr(boss, "hp", 0))
        progresso = clamp(hp_atual / hp_max, 0.0, 1.0)
        fill_w = int(largura_barra * progresso)

        if fill_w > 0:
            fill_rect = (pos_x, pos_y, fill_w, altura_barra)
            pygame.draw.rect(screen, (215, 140, 255), fill_rect, border_radius=raio_borda)
            if fill_w > 4 and altura_barra >= 4:
                highlight_rect = (pos_x + 2, pos_y + 1, fill_w - 4, 3)
                pygame.draw.rect(screen, (245, 200, 255), highlight_rect, border_radius=1)

        # 4. Borda dourada
        pygame.draw.rect(screen, DOURADO, bg_rect, width=2, border_radius=raio_borda)

        # 5. Texto de HP numérico
        texto_hp = f"{hp_atual}/{hp_max} HP"
        fonte_hp = self._fonte_hp
        sombra_hp = fonte_hp.render(texto_hp, True, (10, 5, 20))
        sombra_rect = sombra_hp.get_rect(centerx=centro_x + 1, centery=pos_y + altura_barra // 2 + 1)
        screen.blit(sombra_hp, sombra_rect)

        hp_surf = fonte_hp.render(texto_hp, True, BRANCO)
        hp_rect = hp_surf.get_rect(centerx=centro_x, centery=pos_y + altura_barra // 2)
        screen.blit(hp_surf, hp_rect)


