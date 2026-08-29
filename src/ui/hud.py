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
        self._fonte_xp = None

    def _obter_fonte_xp(self):
        if self._fonte_xp is None:
            self._fonte_xp = pygame.font.SysFont("Arial", 10, bold=True)
        return self._fonte_xp

    def desenhar_barra_xp(self, screen, sistema_xp, visivel: bool = True):
        """
        Renderiza a barra de experiência centralizada na tela logo abaixo do HUD superior.
        Dimensões: 360x10 px, top=62, border_radius=3.
        """
        if not visivel or sistema_xp is None:
            return

        largura_barra = 360
        altura_barra = 10
        pos_x = (LARGURA_TELA - largura_barra) // 2
        pos_y = 62
        raio_borda = 3

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
        sombra_rect = sombra_surf.get_rect(centerx=LARGURA_TELA // 2 + 1, centery=pos_y + altura_barra // 2 + 1)
        screen.blit(sombra_surf, sombra_rect)

        texto_surf = fonte.render(texto_str, True, cor_texto)
        texto_rect = texto_surf.get_rect(centerx=LARGURA_TELA // 2, centery=pos_y + altura_barra // 2)
        screen.blit(texto_surf, texto_rect)
