"""
Componentes de HUD e Interface de Usuário — Protocolo: Batata
Gerencia a renderização de elementos de tela em estética Cyber-Office:
- Painel compacto de Vitais (HP numérico, Overshield ciano e prontidão de Dash)
- Barra compacta de XP e Barra compacta de Mini-Boss / Chefe com timer vivo de superaquecimento
"""

import math
import pygame
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, BRANCO, PRETO,
    AMARELO_XP, DOURADO, CINZA_BORDA, AZUL_CIANO, DASH_COOLDOWN
)
from src.utils.math_utils import clamp

# Paleta Cyber-Office aprovada (Stage 2)
COR_HUD_BG = (11, 14, 23, 220)       # #0b0e17 translúcido
COR_CARD_BG = (17, 24, 39)           # #111827
COR_ELEVADO = (30, 41, 59)           # #1e293b
COR_BORDA_SUTIL = (51, 65, 85)       # #334155
COR_CIANO = (34, 211, 238)           # #22d3ee
COR_ROXO = (168, 85, 247)            # #a855f7
COR_VERDE = (16, 185, 129)           # #10b981
COR_OURO = (251, 191, 36)            # #fbbf24
COR_AMBAR = (245, 158, 11)           # #f59e0b
COR_CARMESIM = (239, 68, 68)         # #ef4444
COR_TEXTO_SUAVE = (148, 163, 184)    # #94a3b8


def _criar_fonte(nomes: tuple[str, ...], tamanho: int, bold: bool = False) -> pygame.font.Font:
    for nome in nomes:
        try:
            f = pygame.font.SysFont(nome, tamanho, bold=bold)
            if f is not None:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, tamanho)


class HUD:
    """
    Controlador de interface visual fixa na tela (Screen-Space HUD) — Estilo Cyber-Office compacto.
    """

    def __init__(self):
        self._fontes_nativas: dict[tuple[str, int, bool], pygame.font.Font] = {}
        self._fonte_xp = self._obter_fonte_nativa("mono", 10, bold=True)
        self._fonte_nome = self._obter_fonte_nativa("sans", 11, bold=True)
        self._fonte_hp = self._obter_fonte_nativa("mono", 11, bold=True)
        self._fonte_timer_boss = self._obter_fonte_nativa("mono", 10, bold=True)
        self._fonte_vitais = self._obter_fonte_nativa("mono", 11, bold=True)
        self._fonte_dash = self._obter_fonte_nativa("mono", 9, bold=True)
        self._painel_surf_cache: dict[tuple[int, int, int], pygame.Surface] = {}

    @staticmethod
    def _calcular_viewport(screen) -> tuple[int, int, int, int, float]:
        sw, sh = screen.get_size() if hasattr(screen, "get_size") else (LARGURA_TELA, ALTURA_TELA)
        if sw < 1 or sh < 1:
            return 0, 0, LARGURA_TELA, ALTURA_TELA, 1.0
        scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
        vw = max(1, int(round(LARGURA_TELA * scale)))
        vh = max(1, int(round(ALTURA_TELA * scale)))
        ox = (sw - vw) // 2
        oy = (sh - vh) // 2
        return ox, oy, vw, vh, scale

    def _obter_fonte_nativa(self, familia: str, tamanho_logico: float, bold: bool = True, scale: float = 1.0) -> pygame.font.Font:
        px = max(8, int(round(float(tamanho_logico) * float(scale))))
        chave = (familia, px, bool(bold))
        if chave not in self._fontes_nativas:
            nomes = ("DejaVu Sans Mono", "Consolas", "Courier New", "Arial") if familia == "mono" else ("DejaVu Sans", "Arial")
            self._fontes_nativas[chave] = _criar_fonte(nomes, px, bold=bold)
        return self._fontes_nativas[chave]

    def _obter_painel_translucido(self, w: int, h: int, raio: int = 5) -> pygame.Surface:
        chave = (max(1, int(w)), max(1, int(h)), max(0, int(raio)))
        if chave not in self._painel_surf_cache:
            surf = pygame.Surface((chave[0], chave[1]), pygame.SRCALPHA)
            pygame.draw.rect(surf, COR_HUD_BG, (0, 0, chave[0], chave[1]), border_radius=chave[2])
            self._painel_surf_cache[chave] = surf
        return self._painel_surf_cache[chave]

    def _obter_fonte_xp(self, scale: float = 1.0):
        return self._obter_fonte_nativa("mono", 10, bold=True, scale=scale)

    def desenhar_painel_vitais(self, screen, jogador, visivel: bool = True):
        """
        Renderiza o painel compacto de Vitais no topo esquerdo projetado em DPI nativo:
        - Barra de HP com leitura numérica monospace + segmento Overshield ciano
        - Barra compacta de prontidão do Dash quando jogador.dash_desbloqueado estiver ativo
        """
        if not visivel or jogador is None:
            return

        ox, oy, _vw, _vh, s = self._calcular_viewport(screen)
        dash_ativo = bool(getattr(jogador, "dash_desbloqueado", False))
        x = ox + int(round(16 * s))
        y = oy + int(round(72 * s))
        largura = max(1, int(round(114 * s)))
        altura = max(1, int(round((46 if dash_ativo else 28) * s)))
        raio_painel = max(2, int(round(5 * s)))
        raio_bar = max(1, int(round(3 * s)))
        borda_w = max(1, int(round(1 * s)))

        # Fundo translúcido Cyber-Office
        painel = self._obter_painel_translucido(largura, altura, raio=raio_painel)
        screen.blit(painel, (x, y))
        pygame.draw.rect(screen, COR_BORDA_SUTIL, (x, y, largura, altura), width=borda_w, border_radius=raio_painel)

        # Barra de HP
        hp_max = max(1, int(getattr(jogador, "hp_max", 150)))
        hp_atual = max(0, int(getattr(jogador, "hp", 0)))
        pct_hp = clamp(hp_atual / float(hp_max), 0.0, 1.0)
        escudo_val = max(0, int(getattr(jogador, "escudo_sobrevida", 0)))

        pad_x = max(2, int(round(5 * s)))
        bar_x = x + pad_x
        bar_y = y + max(2, int(round(6 * s)))
        bar_w = max(1, largura - pad_x * 2)
        bar_h = max(4, int(round(16 * s)))

        pygame.draw.rect(screen, COR_CARD_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=raio_bar)

        if pct_hp > 0.45:
            cor_hp = COR_VERDE
        elif pct_hp > 0.25:
            cor_hp = COR_AMBAR
        else:
            cor_hp = COR_CARMESIM

        fill_w = int(bar_w * pct_hp)
        if fill_w > 0:
            pygame.draw.rect(screen, cor_hp, (bar_x, bar_y, fill_w, bar_h), border_radius=raio_bar)
            if fill_w > max(4, int(round(4 * s))):
                pygame.draw.rect(screen, (255, 255, 255), (bar_x + max(1, int(round(2 * s))), bar_y + 1, fill_w - max(2, int(round(4 * s))), max(1, int(round(1 * s)))))

        # Overshield ciano (Barreira de Sobrevida)
        if escudo_val > 0:
            pct_esc = clamp(escudo_val / float(max(25, hp_max // 3)), 0.0, 1.0)
            esc_w = max(4, int(bar_w * pct_esc))
            esc_h = max(2, int(round(3 * s)))
            pygame.draw.rect(screen, COR_CIANO, (bar_x, bar_y + bar_h - esc_h, esc_w, esc_h), border_radius=1)

        pygame.draw.rect(screen, COR_BORDA_SUTIL, (bar_x, bar_y, bar_w, bar_h), width=borda_w, border_radius=raio_bar)

        fonte_vitais = self._obter_fonte_nativa("mono", 11, bold=True, scale=s)
        texto_hp = f"{hp_atual}/{hp_max}" if escudo_val > 0 else f"HP {hp_atual}/{hp_max}"
        if escudo_val > 0:
            texto_hp += f" +{escudo_val}"
        sombra_hp = fonte_vitais.render(texto_hp, True, (6, 8, 14))
        surf_hp = fonte_vitais.render(texto_hp, True, BRANCO if escudo_val == 0 else COR_CIANO)
        rect_hp = surf_hp.get_rect(centerx=bar_x + bar_w // 2, centery=bar_y + bar_h // 2)
        screen.blit(sombra_hp, (rect_hp.x + max(1, int(round(s))), rect_hp.y + max(1, int(round(s)))))
        screen.blit(surf_hp, rect_hp)

        # Barra compacta de prontidão do Dash (quando desbloqueado)
        if dash_ativo:
            dash_y = bar_y + bar_h + max(2, int(round(4 * s)))
            dash_h = max(4, int(round(13 * s)))
            cd_rest = max(0.0, float(getattr(jogador, "dash_cooldown_restante", 0.0)))
            ativo_t = max(0.0, float(getattr(jogador, "dash_ativo_timer", 0.0)))
            pronto = (cd_rest <= 0.0 and ativo_t <= 0.0)
            prog_dash = 1.0 if pronto else clamp(1.0 - (cd_rest / max(0.01, float(DASH_COOLDOWN))), 0.0, 1.0)

            pygame.draw.rect(screen, COR_CARD_BG, (bar_x, dash_y, bar_w, dash_h), border_radius=raio_bar)
            fill_d = int(bar_w * prog_dash)
            if fill_d > 0:
                cor_dash = COR_CIANO if pronto else (30, 110, 140)
                pygame.draw.rect(screen, cor_dash, (bar_x, dash_y, fill_d, dash_h), border_radius=raio_bar)
            borda_d = COR_CIANO if pronto else COR_BORDA_SUTIL
            pygame.draw.rect(screen, borda_d, (bar_x, dash_y, bar_w, dash_h), width=borda_w, border_radius=raio_bar)

            fonte_dash = self._obter_fonte_nativa("mono", 9, bold=True, scale=s)
            txt_d = "DASH PRONTO" if pronto else f"DASH {cd_rest:.1f}s"
            cor_txt_d = (8, 14, 24) if pronto else COR_TEXTO_SUAVE
            surf_d = fonte_dash.render(txt_d, True, cor_txt_d)
            rect_d = surf_d.get_rect(centerx=bar_x + bar_w // 2, centery=dash_y + dash_h // 2)
            screen.blit(surf_d, rect_d)

    def desenhar_card_parry(self, screen, jogador, parries_total: int = 0, visivel: bool = True):
        """
        Renderiza um card compacto no canto superior direito incentivando o desbloqueio do Dash
        via parries acumulados quando jogador.dash_desbloqueado ainda for False.
        """
        if not visivel or jogador is None or bool(getattr(jogador, "dash_desbloqueado", False)):
            return

        ox, oy, vw, _vh, s = self._calcular_viewport(screen)
        fonte_titulo = self._obter_fonte_nativa("sans", 11, bold=True, scale=s)
        fonte_cont = self._obter_fonte_nativa("mono", 11, bold=True, scale=s)

        linha_1 = "Dê parry 50 vezes para desbloquear o dash"
        linha_2 = f"Quantidade de Parries: {max(0, int(parries_total))}"

        surf_1 = fonte_titulo.render(linha_1, True, COR_TEXTO_SUAVE)
        surf_2 = fonte_cont.render(linha_2, True, COR_OURO)

        pad_x = max(6, int(round(10 * s)))
        pad_y = max(4, int(round(6 * s)))
        gap_y = max(2, int(round(3 * s)))
        largura = max(surf_1.get_width(), surf_2.get_width()) + pad_x * 2
        altura = surf_1.get_height() + surf_2.get_height() + gap_y + pad_y * 2

        x = ox + vw - int(round(16 * s)) - largura
        y = oy + int(round(72 * s))
        raio_painel = max(2, int(round(5 * s)))
        borda_w = max(1, int(round(1 * s)))

        painel = self._obter_painel_translucido(largura, altura, raio=raio_painel)
        screen.blit(painel, (x, y))
        pygame.draw.rect(screen, COR_BORDA_SUTIL, (x, y, largura, altura), width=borda_w, border_radius=raio_painel)

        screen.blit(surf_1, (x + largura - pad_x - surf_1.get_width(), y + pad_y))
        screen.blit(surf_2, (x + largura - pad_x - surf_2.get_width(), y + pad_y + surf_1.get_height() + gap_y))

    def desenhar_barra_xp(self, screen, sistema_xp, visivel: bool = True):
        """
        Renderiza a barra de experiência compacta centralizada no topo da tela em DPI nativo.
        Dimensões lógicas: 420x11 px em y=30 (logo abaixo da faixa de telemetria).
        """
        if not visivel or sistema_xp is None:
            return

        ox, oy, vw, _vh, s = self._calcular_viewport(screen)
        largura_barra = max(1, int(round(420 * s)))
        altura_barra = max(4, int(round(11 * s)))
        centro_x = ox + vw // 2
        pos_x = centro_x - largura_barra // 2
        pos_y = oy + int(round(30 * s))
        raio_borda = max(1, int(round(3 * s)))
        borda_w = max(1, int(round(1 * s)))

        # 1. Fundo da barra Cyber-Office
        bg_rect = (pos_x, pos_y, largura_barra, altura_barra)
        pygame.draw.rect(screen, COR_CARD_BG, bg_rect, border_radius=raio_borda)

        # 2. Preenchimento proporcional dourado
        progresso = clamp(sistema_xp.progresso_normalizado(), 0.0, 1.0)
        fill_w = int(largura_barra * progresso)
        if fill_w > 0:
            fill_rect = (pos_x, pos_y, fill_w, altura_barra)
            pygame.draw.rect(screen, COR_OURO, fill_rect, border_radius=raio_borda)
            if fill_w > max(4, int(round(4 * s))) and altura_barra >= 4:
                highlight_rect = (pos_x + max(1, int(round(2 * s))), pos_y + 1, fill_w - max(2, int(round(4 * s))), max(1, int(round(2 * s))))
                pygame.draw.rect(screen, (254, 243, 199), highlight_rect, border_radius=1)

        # 3. Borda metálica sutil
        pygame.draw.rect(screen, COR_BORDA_SUTIL, bg_rect, width=borda_w, border_radius=raio_borda)

        # 4. Texto monospace compacto inline
        fonte = self._obter_fonte_xp(scale=s)
        if sistema_xp.nivel >= sistema_xp.nivel_max:
            texto_str = f"NV.{sistema_xp.nivel} MAX"
            cor_texto = COR_OURO
        else:
            proximo_custo = sistema_xp.xp_para_proximo_nivel(sistema_xp.nivel)
            texto_str = f"NV.{sistema_xp.nivel}  {sistema_xp.xp_atual}/{proximo_custo} XP"
            cor_texto = BRANCO

        off_sh = max(1, int(round(s)))
        sombra_surf = fonte.render(texto_str, True, (8, 10, 16))
        sombra_rect = sombra_surf.get_rect(centerx=centro_x + off_sh, centery=pos_y + altura_barra // 2 + off_sh)
        screen.blit(sombra_surf, sombra_rect)

        texto_surf = fonte.render(texto_str, True, cor_texto)
        texto_rect = texto_surf.get_rect(centerx=centro_x, centery=pos_y + altura_barra // 2)
        screen.blit(texto_surf, texto_rect)

    def desenhar_barra_boss(self, screen, boss, visivel: bool = True):
        """
        Renderiza a barra compacta de Mini-Boss / Chefe Final diretamente abaixo da barra de XP em DPI nativo.
        Dimensões lógicas: 480x18 px em y=45..63 com nome, HP numérico e timer vivo 60.0s inline.
        """
        if not visivel or boss is None or not getattr(boss, "vivo", True):
            return

        ox, oy, vw, _vh, s = self._calcular_viewport(screen)
        largura_barra = max(1, int(round(480 * s)))
        altura_barra = max(6, int(round(18 * s)))
        centro_x = ox + vw // 2
        pos_x = centro_x - largura_barra // 2
        pos_y = oy + int(round(45 * s))
        raio_borda = max(2, int(round(4 * s)))
        borda_w = max(1, int(round(1 * s)))

        # 1. Fundo translúcido / roxo escuro Cyber-Office
        bg_rect = (pos_x, pos_y, largura_barra, altura_barra)
        pygame.draw.rect(screen, (24, 14, 38), bg_rect, border_radius=raio_borda)

        # 2. Preenchimento proporcional
        hp_max = max(1, getattr(boss, "hp_max", 100))
        hp_atual = max(0, getattr(boss, "hp", 0))
        progresso = clamp(hp_atual / hp_max, 0.0, 1.0)
        fill_w = int(largura_barra * progresso)

        if fill_w > 0:
            fill_rect = (pos_x, pos_y, fill_w, altura_barra)
            pygame.draw.rect(screen, COR_ROXO, fill_rect, border_radius=raio_borda)
            if fill_w > max(4, int(round(4 * s))) and altura_barra >= 4:
                highlight_rect = (pos_x + max(1, int(round(2 * s))), pos_y + 1, fill_w - max(2, int(round(4 * s))), max(1, int(round(2 * s))))
                pygame.draw.rect(screen, (233, 213, 255), highlight_rect, border_radius=1)

        # 3. Timer vivo de superaquecimento (60.0s -> XX.Xs) para Mini-Bosses
        tempo_restante = getattr(boss, "tempo_vida_restante", None)
        borda_cor = COR_OURO
        if tempo_restante is not None:
            t_val = max(0.0, float(tempo_restante))
            if t_val < 15.0:
                ticks = pygame.time.get_ticks() if pygame.display.get_init() else 0
                borda_cor = COR_CARMESIM if (ticks // 180) % 2 == 0 else COR_AMBAR
            elif t_val < 30.0:
                borda_cor = COR_AMBAR

        pygame.draw.rect(screen, borda_cor, bg_rect, width=borda_w, border_radius=raio_borda)

        # 4. Nome inline à esquerda
        nome = getattr(boss, "nome_elite", "") or getattr(boss, "nome", "") or "MINI-BOSS"
        if len(nome) > 26:
            nome = nome[:25] + "…"
        cy_bar = pos_y + altura_barra // 2
        off_sh = max(1, int(round(s)))

        fonte_nome = self._obter_fonte_nativa("sans", 11, bold=True, scale=s)
        nome_sombra = fonte_nome.render(nome, True, (8, 4, 16))
        nome_surf = fonte_nome.render(nome, True, COR_OURO)
        nome_rect = nome_surf.get_rect(left=pos_x + max(4, int(round(8 * s))), centery=cy_bar)
        screen.blit(nome_sombra, (nome_rect.x + off_sh, nome_rect.y + off_sh))
        screen.blit(nome_surf, nome_rect)

        # 5. HP numérico inline ao centro
        fonte_hp = self._obter_fonte_nativa("mono", 11, bold=True, scale=s)
        texto_hp = f"{hp_atual}/{hp_max}"
        sombra_hp = fonte_hp.render(texto_hp, True, (8, 4, 16))
        hp_surf = fonte_hp.render(texto_hp, True, BRANCO)
        hp_rect = hp_surf.get_rect(centerx=centro_x + int(round(16 * s)), centery=cy_bar)
        screen.blit(sombra_hp, (hp_rect.x + off_sh, hp_rect.y + off_sh))
        screen.blit(hp_surf, hp_rect)

        # 6. Badge inline do timer de superaquecimento à direita (destaque janela 30s e urgente <15s)
        if tempo_restante is not None:
            t_val = max(0.0, float(tempo_restante))
            if t_val >= 30.0:
                cor_badge_bg = (14, 48, 62)
                cor_badge_txt = COR_CIANO
                prefixo = "FAST "
            elif t_val >= 15.0:
                cor_badge_bg = (64, 42, 12)
                cor_badge_txt = COR_AMBAR
                prefixo = "HEAT "
            else:
                cor_badge_bg = (75, 16, 22)
                cor_badge_txt = COR_CARMESIM
                prefixo = "CRIT "

            fonte_timer = self._obter_fonte_nativa("mono", 10, bold=True, scale=s)
            txt_t = f"{prefixo}{t_val:04.1f}s"
            t_surf = fonte_timer.render(txt_t, True, cor_badge_txt)
            badge_w = t_surf.get_width() + max(6, int(round(10 * s)))
            badge_h = max(4, altura_barra - max(2, int(round(4 * s))))
            badge_x = pos_x + largura_barra - badge_w - max(2, int(round(3 * s)))
            badge_y = pos_y + max(1, int(round(2 * s)))
            raio_badge = max(1, int(round(3 * s)))
            pygame.draw.rect(screen, cor_badge_bg, (badge_x, badge_y, badge_w, badge_h), border_radius=raio_badge)
            pygame.draw.rect(screen, cor_badge_txt, (badge_x, badge_y, badge_w, badge_h), width=borda_w, border_radius=raio_badge)
            t_rect = t_surf.get_rect(centerx=badge_x + badge_w // 2, centery=cy_bar)
            screen.blit(t_surf, t_rect)

    def desenhar_pins_conquistas(self, screen, resumo_fixadas: list[dict], visivel: bool = True):
        """
        Renderiza 0..3 barras finas discretas no canto superior direito com as conquistas fixadas.
        100% ocultas quando visivel=False (hud='desligado') ou lista vazia.
        """
        if not visivel or not resumo_fixadas:
            return

        ox, oy, vw, _vh, s = self._calcular_viewport(screen)
        fonte_nome = self._obter_fonte_nativa("sans", 10, bold=True, scale=s)
        fonte_num = self._obter_fonte_nativa("mono", 9, bold=True, scale=s)

        largura = max(120, int(round(188 * s)))
        altura_item = max(18, int(round(24 * s)))
        gap = max(3, int(round(4 * s)))
        pad_x = max(5, int(round(7 * s)))
        pad_y = max(3, int(round(4 * s)))
        raio = max(2, int(round(4 * s)))
        borda_w = max(1, int(round(1 * s)))

        x = ox + vw - int(round(16 * s)) - largura
        y_base = oy + int(round(72 * s))

        for idx, item in enumerate(resumo_fixadas[:3]):
            y = y_base + idx * (altura_item + gap)
            painel = self._obter_painel_translucido(largura, altura_item, raio=raio)
            screen.blit(painel, (x, y))
            concluida = bool(item.get("concluida", False))
            cor_borda = COR_VERDE if concluida else COR_BORDA_SUTIL
            pygame.draw.rect(screen, cor_borda, (x, y, largura, altura_item), width=borda_w, border_radius=raio)

            nome = str(item.get("nome", ""))
            if len(nome) > 18:
                nome = nome[:17] + "…"
            atual = int(item.get("atual", 0))
            meta = max(1, int(item.get("meta", 1)))
            progresso = clamp(float(item.get("progresso", 0.0)), 0.0, 1.0)

            surf_nome = fonte_nome.render(nome, True, COR_OURO if concluida else BRANCO)
            txt_num = "OK" if concluida else f"{atual}/{meta}"
            surf_num = fonte_num.render(txt_num, True, COR_VERDE if concluida else COR_TEXTO_SUAVE)

            screen.blit(surf_nome, (x + pad_x, y + pad_y - 1))
            screen.blit(surf_num, (x + largura - pad_x - surf_num.get_width(), y + pad_y))

            bar_x = x + pad_x
            bar_y = y + altura_item - max(4, int(round(6 * s)))
            bar_w = max(10, largura - pad_x * 2)
            bar_h = max(2, int(round(3 * s)))
            pygame.draw.rect(screen, COR_CARD_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=1)
            fill_w = int(bar_w * progresso)
            if fill_w > 0:
                cor_fill = COR_VERDE if concluida else COR_CIANO
                pygame.draw.rect(screen, cor_fill, (bar_x, bar_y, fill_w, bar_h), border_radius=1)

    def desenhar_indicador_combo(self, screen, sistema_combo, visivel: bool = True):
        """
        Renderiza o contador Nx COMBO + barra de janela no topo central e,
        quando modo_estilo estiver ativo, o badge de Rank (D/C/B/A/S) + Overdrive.
        """
        if not visivel or sistema_combo is None:
            return
        combo_atual = int(getattr(sistema_combo, "combo_atual", 0))
        overdrive = bool(getattr(sistema_combo, "overdrive_ativo", False))
        modo_estilo = bool(getattr(sistema_combo, "modo_estilo", False))
        if combo_atual <= 0 and not overdrive:
            return

        ox, oy, vw, _vh, s = self._calcular_viewport(screen)
        centro_x = ox + vw // 2
        y = oy + int(round(68 * s))

        fonte_combo = self._obter_fonte_nativa("mono", 12, bold=True, scale=s)
        fonte_rank = self._obter_fonte_nativa("sans", 13, bold=True, scale=s)

        rank = getattr(sistema_combo, "rank", "D")
        cores_rank = {
            "D": COR_TEXTO_SUAVE,
            "C": COR_CIANO,
            "B": COR_VERDE,
            "A": COR_AMBAR,
            "S": COR_OURO,
        }
        cor_rank = cores_rank.get(rank, BRANCO)
        if overdrive:
            cor_rank = COR_OURO

        txt_combo = f"{combo_atual}x COMBO"
        if overdrive:
            txt_combo += " · OVERDRIVE"
        surf_combo = fonte_combo.render(txt_combo, True, COR_OURO if overdrive else BRANCO)

        badge_w = int(round(22 * s)) if modo_estilo else 0
        gap_badge = int(round(6 * s)) if modo_estilo else 0
        pad_x = max(6, int(round(10 * s)))
        pad_y = max(3, int(round(4 * s)))
        largura = surf_combo.get_width() + pad_x * 2 + badge_w + gap_badge
        altura = max(20, surf_combo.get_height() + pad_y * 2 + max(3, int(round(4 * s))))
        x = centro_x - largura // 2
        raio = max(2, int(round(5 * s)))
        borda_w = max(1, int(round(1 * s)))

        painel = self._obter_painel_translucido(largura, altura, raio=raio)
        screen.blit(painel, (x, y))
        pygame.draw.rect(screen, cor_rank if overdrive or modo_estilo else COR_BORDA_SUTIL, (x, y, largura, altura), width=borda_w, border_radius=raio)

        tx = x + pad_x
        if modo_estilo:
            b_rect = pygame.Rect(tx, y + pad_y, badge_w, max(12, surf_combo.get_height()))
            pygame.draw.rect(screen, COR_ELEVADO, b_rect, border_radius=3)
            pygame.draw.rect(screen, cor_rank, b_rect, width=1, border_radius=3)
            s_rank = fonte_rank.render(rank, True, cor_rank)
            screen.blit(s_rank, s_rank.get_rect(center=b_rect.center))
            tx += badge_w + gap_badge

        screen.blit(surf_combo, (tx, y + pad_y))

        # Barra de janela de decaimento
        janela_max = max(0.01, float(getattr(sistema_combo, "janela_max", 4.0)))
        janela_rest = max(0.0, float(getattr(sistema_combo, "janela_timer", 0.0)))
        prog = clamp(janela_rest / janela_max, 0.0, 1.0)
        bar_x = x + pad_x
        bar_y = y + altura - max(3, int(round(5 * s)))
        bar_w = max(10, largura - pad_x * 2)
        bar_h = max(2, int(round(2 * s)))
        pygame.draw.rect(screen, COR_CARD_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=1)
        if prog > 0.0:
            pygame.draw.rect(screen, cor_rank, (bar_x, bar_y, int(bar_w * prog), bar_h), border_radius=1)

    def desenhar_barra_calor_in_world(self, screen, x: float, y: float, largura: float, arma) -> None:
        """Renderiza barra compacta de calor da SMG Compacta (0..100%, zona ideal 65%..95% âmbar)."""
        if arma is None or not getattr(arma, "usa_calor", False):
            return
        calor = clamp(float(getattr(arma, "calor_atual", 0.0)), 0.0, 100.0)
        superaquecida = bool(getattr(arma, "superaquecida", False))
        em_ideal = bool(getattr(arma, "em_zona_ideal", False))

        bx = int(round(x))
        by = int(round(y))
        bw = max(20, int(round(largura)))
        bh = 5

        pygame.draw.rect(screen, (14, 18, 28), (bx - 1, by - 1, bw + 2, bh + 2), border_radius=2)
        # Marcador da zona ideal (65%..95%)
        z_ini = bx + int(bw * 0.65)
        z_fim = bx + int(bw * 0.95)
        pygame.draw.rect(screen, (95, 62, 14), (z_ini, by, max(2, z_fim - z_ini), bh))

        fill_w = int(bw * (calor / 100.0))
        if fill_w > 0:
            if superaquecida:
                ticks = pygame.time.get_ticks() if pygame.display.get_init() else 0
                cor = COR_CARMESIM if (ticks // 90) % 2 == 0 else (255, 180, 180)
            elif em_ideal:
                cor = COR_AMBAR
            else:
                cor = COR_CIANO
            pygame.draw.rect(screen, cor, (bx, by, fill_w, bh), border_radius=1)
        pygame.draw.rect(screen, COR_BORDA_SUTIL, (bx - 1, by - 1, bw + 2, bh + 2), width=1, border_radius=2)

    def desenhar_barra_ram_gc(self, screen, efeito_gc, visivel: bool = True) -> None:
        """Renderiza indicador discreto de memória RAM do Garbage Collector abaixo do painel de Vitais."""
        if not visivel or efeito_gc is None:
            return
        ox, oy, _vw, _vh, s = self._calcular_viewport(screen)
        x = ox + int(round(16 * s))
        y = oy + int(round(124 * s))
        largura = max(90, int(round(114 * s)))
        altura = max(14, int(round(18 * s)))
        raio = max(2, int(round(4 * s)))

        painel = self._obter_painel_translucido(largura, altura, raio=raio)
        screen.blit(painel, (x, y))
        travado = bool(getattr(efeito_gc, "disparos_travados", False))
        prog = clamp(float(getattr(efeito_gc, "ram_progresso", 0.0)), 0.0, 1.0)
        cor_borda = COR_CARMESIM if travado else COR_VERDE
        pygame.draw.rect(screen, cor_borda, (x, y, largura, altura), width=1, border_radius=raio)

        pad_x = max(4, int(round(5 * s)))
        bar_w = max(8, largura - pad_x * 2)
        bar_h = max(3, int(round(4 * s)))
        bar_y = y + altura - bar_h - max(2, int(round(3 * s)))
        pygame.draw.rect(screen, COR_CARD_BG, (x + pad_x, bar_y, bar_w, bar_h), border_radius=1)
        if prog > 0.0:
            pygame.draw.rect(screen, cor_borda, (x + pad_x, bar_y, int(bar_w * prog), bar_h), border_radius=1)

        fonte = self._obter_fonte_nativa("mono", 8, bold=True, scale=s)
        txt = "GC FLUSH!" if travado else f"RAM {int(prog * 100)}%"
        surf = fonte.render(txt, True, COR_CARMESIM if travado else COR_TEXTO_SUAVE)
        screen.blit(surf, (x + pad_x, y + max(1, int(round(2 * s)))))


