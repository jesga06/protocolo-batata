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
    AMARELO_XP, DOURADO, CINZA_BORDA, AZUL_CIANO, DASH_COOLDOWN,
    SMG_ZONA_IDEAL_MIN, SMG_ZONA_IDEAL_MAX,
)
from src.utils.math_utils import clamp
from src.utils.fontes import carregar_fonte_sans, carregar_fonte_mono
from src.utils.traducao import t
from src.sistemas.conquistas_dados import (
    CHIPS_FIRMWARE,
    CONQUISTAS_CONTINUAS,
    CONQUISTAS_UNICAS,
)

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


_RECOMPENSA_CHAVES = {
    ("habilidade", "dash"): "recomp_dash",
    ("arma", "smg_compacta"): "recomp_smg_compacta",
    ("arma", "bastao_choque"): "recomp_bastao_choque",
    ("arma", "rifle_arco"): "recomp_rifle_arco",
    ("arma", "lanca_chamas"): "recomp_lanca_chamas",
    ("configuracao", "latencia_ping"): "recomp_latencia_ping",
    ("slot_firmware", "+1"): "recomp_slot_firmware",
    ("opcao_config", "precisao_parry:postura_riposte"): "recomp_postura_riposte",
    ("opcao_config", "dash_rastro:thread_fantasma"): "recomp_thread_fantasma",
    ("opcao_config", "dash_protocolo:sombra_espelho"): "recomp_sombra_espelho",
    ("opcao_config", "dash_protocolo:rollback_estado"): "recomp_rollback_estado",
}


def formatar_recompensas_conquista(recompensas: list[tuple[str, str]]) -> str:
    """Converte lista de tuplas (tipo, id) em texto legível de desbloqueio."""
    if not recompensas:
        return t("ui_geral", "recomp_trofeu_permanente")
    partes: list[str] = []
    for tipo, rid in recompensas:
        chave = (tipo, rid)
        if chave in _RECOMPENSA_CHAVES:
            partes.append(t("ui_geral", _RECOMPENSA_CHAVES[chave]))
        elif tipo == "modificador_run":
            chip = CHIPS_FIRMWARE.get(rid)
            partes.append(t("ui_geral", "recomp_firmware_prefixo", nome=chip.nome if chip else rid))
        elif tipo == "trofeu":
            partes.append(t("ui_geral", "recomp_trofeu"))
        else:
            partes.append(str(rid).replace("_", " ").title())
    return " + ".join(partes)


def _quebrar_texto_hud(fonte: pygame.font.Font, texto: str, max_largura: int, max_linhas: int = 3) -> list[str]:
    """Quebra texto em múltiplas linhas respeitando max_largura sem truncar nomes."""
    palavras = str(texto or "").split()
    if not palavras:
        return [""]
    linhas: list[str] = []
    atual = palavras[0]
    for idx, pal in enumerate(palavras[1:], start=1):
        teste = f"{atual} {pal}"
        if fonte.size(teste)[0] <= max_largura:
            atual = teste
        else:
            linhas.append(atual)
            if len(linhas) >= max_linhas - 1:
                linhas.append(" ".join(palavras[idx:]))
                return linhas
            atual = pal
    linhas.append(atual)
    return linhas[:max_linhas]


def _criar_fonte(nomes: tuple[str, ...], tamanho: int, bold: bool = False) -> pygame.font.Font:
    eh_mono = any("mono" in n.lower() or "consolas" in n.lower() or "courier" in n.lower() for n in nomes)
    if eh_mono:
        return carregar_fonte_mono(tamanho, bold=bold)
    return carregar_fonte_sans(tamanho, bold=bold)


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
        self._fonte_card_nome = self._obter_fonte_nativa("sans", 10, bold=True)
        self._fonte_card_mono = self._obter_fonte_nativa("mono", 8, bold=True)
        self._fonte_pin_nome = self._obter_fonte_nativa("sans", 10, bold=True)
        self._fonte_pin_sub = self._obter_fonte_nativa("sans", 8, bold=False)
        self._fonte_pin_recomp = self._obter_fonte_nativa("sans", 8, bold=True)
        self._fonte_pin_num = self._obter_fonte_nativa("mono", 9, bold=True)
        self._fonte_banner_sub = self._obter_fonte_nativa("sans", 9, bold=False)
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
            if familia == "mono":
                self._fontes_nativas[chave] = carregar_fonte_mono(px, bold=bool(bold))
            else:
                self._fontes_nativas[chave] = carregar_fonte_sans(px, bold=bool(bold))
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

    def desenhar_painel_vitais(self, screen, jogador, visivel: bool = True, arma_melee=None):
        """
        Renderiza o painel compacto de Vitais no topo esquerdo projetado em DPI nativo:
        - Barra de HP com leitura numérica monospace + segmento Overshield ciano
        - Barra compacta de prontidão do Dash quando jogador.dash_desbloqueado estiver ativo
        - Barra/timer compacto de recarga do Quick-Parry (PARRY PRONTO / PARRY X.Xs)
        """
        if not visivel or jogador is None:
            return

        arma_parry = arma_melee
        if arma_parry is None:
            armas_j = getattr(jogador, "armas", None) or []
            if armas_j and hasattr(armas_j[0], "parry_duracao"):
                arma_parry = armas_j[0]

        ox, oy, _vw, _vh, s = self._calcular_viewport(screen)
        dash_ativo = bool(getattr(jogador, "dash_desbloqueado", False))
        tem_parry = arma_parry is not None
        x = ox + int(round(16 * s))
        y = oy + int(round(72 * s))
        largura = max(1, int(round(114 * s)))
        altura_l = 28 + (18 if dash_ativo else 0) + (17 if tem_parry else 0)
        altura = max(1, int(round(altura_l * s)))
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
        texto_hp = (
            t("ui_geral", "hud_hp_escudo", hp_atual=hp_atual, hp_max=hp_max, escudo=escudo_val)
            if escudo_val > 0
            else t("ui_geral", "hud_hp_padrao", hp_atual=hp_atual, hp_max=hp_max)
        )
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
            txt_d = t("ui_geral", "hud_dash_pronto") if pronto else t("ui_geral", "hud_dash_cd", segundos=cd_rest)
            cor_txt_d = (8, 14, 24) if pronto else COR_TEXTO_SUAVE
            surf_d = fonte_dash.render(txt_d, True, cor_txt_d)
            rect_d = surf_d.get_rect(centerx=bar_x + bar_w // 2, centery=dash_y + dash_h // 2)
            screen.blit(surf_d, rect_d)

        # Barra compacta de prontidão/timer do Quick-Parry
        if tem_parry:
            parry_y = (bar_y + bar_h + max(2, int(round(4 * s)))) + (max(4, int(round(13 * s))) + max(2, int(round(4 * s))) if dash_ativo else 0)
            parry_h = max(4, int(round(13 * s)))
            cd_p = max(0.0, float(getattr(arma_parry, "tempo_recarga_restante", 0.0)))
            cd_max_p = max(
                0.01,
                float(getattr(arma_parry, "ultimo_parry_cd_total", getattr(arma_parry, "cooldown", 0.6))),
            )
            parry_ativo = bool(getattr(arma_parry, "parry_ativo", False))
            pronto_p = (cd_p <= 0.0 and not parry_ativo)
            prog_p = 1.0 if pronto_p else (1.0 if parry_ativo else clamp(1.0 - (cd_p / cd_max_p), 0.0, 1.0))

            pygame.draw.rect(screen, COR_CARD_BG, (bar_x, parry_y, bar_w, parry_h), border_radius=raio_bar)
            fill_p = int(bar_w * prog_p)
            if fill_p > 0:
                cor_parry = COR_CIANO if parry_ativo else (COR_OURO if pronto_p else (130, 94, 24))
                pygame.draw.rect(screen, cor_parry, (bar_x, parry_y, fill_p, parry_h), border_radius=raio_bar)
            borda_p = COR_OURO if pronto_p else (COR_CIANO if parry_ativo else COR_BORDA_SUTIL)
            pygame.draw.rect(screen, borda_p, (bar_x, parry_y, bar_w, parry_h), width=borda_w, border_radius=raio_bar)

            fonte_parry = self._obter_fonte_nativa("mono", 9, bold=True, scale=s)
            txt_p = (
                t("ui_geral", "hud_parry_ativo")
                if parry_ativo
                else (t("ui_geral", "hud_parry_pronto") if pronto_p else t("ui_geral", "hud_parry_cd", segundos=cd_p))
            )
            cor_txt_p = (14, 12, 8) if (pronto_p or parry_ativo) else COR_TEXTO_SUAVE
            surf_p = fonte_parry.render(txt_p, True, cor_txt_p)
            rect_p = surf_p.get_rect(centerx=bar_x + bar_w // 2, centery=parry_y + parry_h // 2)
            screen.blit(surf_p, rect_p)

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
            texto_str = t("ui_geral", "hud_xp_max", nivel=sistema_xp.nivel)
            cor_texto = COR_OURO
        else:
            proximo_custo = sistema_xp.xp_para_proximo_nivel(sistema_xp.nivel)
            texto_str = t("ui_geral", "hud_xp_progresso", nivel=sistema_xp.nivel, xp_atual=sistema_xp.xp_atual, xp_prox=proximo_custo)
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
        nome = getattr(boss, "nome_elite", "") or getattr(boss, "nome", "") or t("ui_geral", "hud_miniboss_fallback")
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
                prefixo = t("ui_geral", "hud_boss_timer_fast")
            elif t_val >= 15.0:
                cor_badge_bg = (64, 42, 12)
                cor_badge_txt = COR_AMBAR
                prefixo = t("ui_geral", "hud_boss_timer_heat")
            else:
                cor_badge_bg = (75, 16, 22)
                cor_badge_txt = COR_CARMESIM
                prefixo = t("ui_geral", "hud_boss_timer_crit")

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

    @staticmethod
    def _resolver_detalhes_pin(item: dict) -> tuple[str, str, str]:
        """Resolve (nome_completo, texto_desbloqueio, texto_acao) dinâmico para o pin."""
        cid = str(item.get("id", ""))
        nome = str(item.get("nome", ""))
        atual = int(item.get("atual", 0))
        meta = max(1, int(item.get("meta", 1)))
        concluida = bool(item.get("concluida", False))

        texto_desbloqueio = str(item.get("recompensa_texto", ""))
        texto_acao = str(item.get("acao", ""))

        if cid in CONQUISTAS_CONTINUAS:
            cdef = CONQUISTAS_CONTINUAS[cid]
            if not nome:
                nome = cdef.nome
            if not texto_acao:
                texto_acao = cdef.descricao
            if concluida:
                texto_desbloqueio = t("ui_geral", "hud_pin_todos_marcos")
            else:
                alvo_ms = None
                for ms in cdef.milestones:
                    if atual < ms.meta or ms.meta >= meta:
                        alvo_ms = ms
                        break
                if alvo_ms is None and cdef.milestones:
                    alvo_ms = cdef.milestones[-1]
                if alvo_ms is not None:
                    texto_desbloqueio = t("ui_geral", "hud_pin_desbloqueia", recompensa=formatar_recompensas_conquista(alvo_ms.recompensas))
        elif cid in CONQUISTAS_UNICAS:
            cdef = CONQUISTAS_UNICAS[cid]
            if not nome:
                nome = cdef.nome
            if not texto_acao:
                texto_acao = cdef.descricao
            if concluida:
                texto_desbloqueio = t("ui_geral", "hud_pin_desbloqueada")
            else:
                texto_desbloqueio = t("ui_geral", "hud_pin_desbloqueia", recompensa=formatar_recompensas_conquista(cdef.recompensas))

        return nome, texto_desbloqueio, texto_acao

    def desenhar_pins_conquistas(self, screen, resumo_fixadas: list[dict], visivel: bool = True):
        """
        Renderiza 0..3 cards compactos no canto superior direito com as conquistas fixadas:
        nome completo (sem reticências), recompensa dinâmica do próximo marco, instrução e barra.
        100% ocultas quando visivel=False (hud='desligado') ou lista vazia.
        """
        if not visivel or not resumo_fixadas:
            return

        ox, oy, vw, _vh, s = self._calcular_viewport(screen)
        fonte_nome = self._obter_fonte_nativa("sans", 10, bold=True, scale=s)
        fonte_recomp = self._obter_fonte_nativa("sans", 8, bold=True, scale=s)
        fonte_sub = self._obter_fonte_nativa("sans", 8, bold=False, scale=s)
        fonte_num = self._obter_fonte_nativa("mono", 9, bold=True, scale=s)

        largura = max(168, int(round(244 * s)))
        gap = max(4, int(round(5 * s)))
        pad_x = max(6, int(round(8 * s)))
        pad_y = max(4, int(round(5 * s)))
        raio = max(2, int(round(4 * s)))
        borda_w = max(1, int(round(1 * s)))
        bar_h = max(3, int(round(3 * s)))
        line_gap = max(1, int(round(2 * s)))

        x = ox + vw - int(round(16 * s)) - largura
        y_cursor = oy + int(round(72 * s))

        for item in resumo_fixadas[:3]:
            concluida = bool(item.get("concluida", False))
            atual = int(item.get("atual", 0))
            meta = max(1, int(item.get("meta", 1)))
            progresso = clamp(float(item.get("progresso", 0.0)), 0.0, 1.0)

            nome, texto_recomp, texto_acao = self._resolver_detalhes_pin(item)
            txt_num = t("ui_geral", "hud_pin_ok") if concluida else f"{atual}/{meta}"
            surf_num = fonte_num.render(txt_num, True, COR_VERDE if concluida else COR_TEXTO_SUAVE)

            max_w_nome = max(60, largura - pad_x * 2 - surf_num.get_width() - int(round(6 * s)))
            linhas_nome = _quebrar_texto_hud(fonte_nome, nome, max_w_nome, max_linhas=2)
            max_w_sub = max(60, largura - pad_x * 2)
            linhas_recomp = _quebrar_texto_hud(fonte_recomp, texto_recomp, max_w_sub, max_linhas=2) if texto_recomp else []
            linhas_acao = _quebrar_texto_hud(fonte_sub, texto_acao, max_w_sub, max_linhas=2) if texto_acao else []

            h_nome = len(linhas_nome) * fonte_nome.get_linesize()
            h_recomp = len(linhas_recomp) * fonte_recomp.get_linesize() + (line_gap if linhas_recomp else 0)
            h_acao = len(linhas_acao) * fonte_sub.get_linesize() + (line_gap if linhas_acao else 0)
            altura_item = pad_y * 2 + h_nome + h_recomp + h_acao + bar_h + max(4, int(round(5 * s)))

            y = y_cursor
            y_cursor += altura_item + gap

            painel = self._obter_painel_translucido(largura, altura_item, raio=raio)
            screen.blit(painel, (x, y))
            cor_borda = COR_VERDE if concluida else COR_BORDA_SUTIL
            pygame.draw.rect(screen, cor_borda, (x, y, largura, altura_item), width=borda_w, border_radius=raio)

            cy = y + pad_y
            cor_nome = COR_OURO if concluida else BRANCO
            for i_ln, ln in enumerate(linhas_nome):
                s_ln = fonte_nome.render(ln, True, cor_nome)
                screen.blit(s_ln, (x + pad_x, cy))
                if i_ln == 0:
                    screen.blit(surf_num, (x + largura - pad_x - surf_num.get_width(), cy + 1))
                cy += fonte_nome.get_linesize()

            if linhas_recomp:
                cy += line_gap
                cor_rec = COR_VERDE if concluida else COR_CIANO
                for ln in linhas_recomp:
                    s_rec = fonte_recomp.render(ln, True, cor_rec)
                    screen.blit(s_rec, (x + pad_x, cy))
                    cy += fonte_recomp.get_linesize()

            if linhas_acao:
                cy += line_gap
                for ln in linhas_acao:
                    s_ac = fonte_sub.render(ln, True, COR_TEXTO_SUAVE)
                    screen.blit(s_ac, (x + pad_x, cy))
                    cy += fonte_sub.get_linesize()

            bar_x = x + pad_x
            bar_y = y + altura_item - pad_y - bar_h
            bar_w = max(10, largura - pad_x * 2)
            pygame.draw.rect(screen, COR_CARD_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=1)
            fill_w = int(bar_w * progresso)
            if fill_w > 0:
                cor_fill = COR_VERDE if concluida else COR_CIANO
                pygame.draw.rect(screen, cor_fill, (bar_x, bar_y, fill_w, bar_h), border_radius=1)

    def desenhar_barra_calor_in_world(self, screen, x: float, y: float, largura: float, arma) -> None:
        """Renderiza barra compacta de calor da SMG Compacta (0..100%, zona ideal 60%..92% âmbar)."""
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
        # Marcador da zona ideal (60%..92%)
        z_ini = bx + int(bw * (SMG_ZONA_IDEAL_MIN / 100.0))
        z_fim = bx + int(bw * (SMG_ZONA_IDEAL_MAX / 100.0))
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
        y = oy + int(round(142 * s))
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
        txt = t("ui_geral", "hud_ram_flush") if travado else t("ui_geral", "hud_ram_uso", pct=int(prog * 100))
        surf = fonte.render(txt, True, COR_CARMESIM if travado else COR_TEXTO_SUAVE)
        screen.blit(surf, (x + pad_x, y + max(1, int(round(2 * s)))))

    def desenhar_banners_desbloqueio(self, screen, banners: list[dict]) -> None:
        """
        Renderiza cards estilo Steam / Cyber-Office empilhados no canto inferior direito
        para notificar conquistas e desbloqueios em tempo real (zero alocação de fontes).
        """
        if screen is None or not banners:
            return

        ox, oy, vw, vh, s = self._calcular_viewport(screen)
        f_badge = self._obter_fonte_nativa("mono", 9, bold=True, scale=s)
        f_titulo = self._obter_fonte_nativa("sans", 11, bold=True, scale=s)
        f_sub = self._obter_fonte_nativa("sans", 9, bold=False, scale=s)

        card_w = max(180, int(round(304 * s)))
        card_h = max(48, int(round(72 * s)))
        gap = max(4, int(round(8 * s)))
        margem_r = max(8, int(round(18 * s)))
        margem_b = max(8, int(round(18 * s)))
        raio = max(2, int(round(6 * s)))
        pad_x = max(6, int(round(12 * s)))
        pad_y = max(4, int(round(7 * s)))

        ativos = [b for b in banners if float(b.get("tempo", 0.0)) > 0.0]
        if not ativos:
            return

        for idx, banner in enumerate(ativos[:4]):
            tempo = float(banner.get("tempo", 0.0))
            tempo_max = max(0.01, float(banner.get("tempo_max", 4.0)))
            decorrido = max(0.0, tempo_max - tempo)

            slide_ratio = 0.0
            if decorrido < 0.25:
                t_in = clamp(decorrido / 0.25, 0.0, 1.0)
                slide_ratio = (1.0 - t_in) ** 2
            elif tempo < 0.30:
                t_out = clamp(tempo / 0.30, 0.0, 1.0)
                slide_ratio = (1.0 - t_out) ** 2

            slide_px = int(round(slide_ratio * (card_w + margem_r)))
            x = ox + vw - card_w - margem_r + slide_px
            y = oy + vh - margem_b - card_h - idx * (card_h + gap)

            cor_destaque = banner.get("cor", COR_OURO)
            if not isinstance(cor_destaque, tuple) or len(cor_destaque) < 3:
                cor_destaque = COR_OURO

            painel = self._obter_painel_translucido(card_w, card_h, raio=raio)
            screen.blit(painel, (x, y))

            rect_card = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(screen, cor_destaque, rect_card, width=max(1, int(round(1 * s))), border_radius=raio)

            # Filete lateral brilhante
            barra_w = max(3, int(round(4 * s)))
            pygame.draw.rect(
                screen,
                cor_destaque,
                pygame.Rect(x, y + max(2, int(round(4 * s))), barra_w, card_h - max(4, int(round(8 * s)))),
                border_radius=max(1, int(round(2 * s))),
            )

            # Badge brilhante "DESBLOQUEADO!"
            badge_surf = f_badge.render(t("ui_geral", "hud_banner_desbloqueado"), True, cor_destaque)
            badge_pad_x = max(4, int(round(6 * s)))
            badge_pad_y = max(1, int(round(2 * s)))
            badge_rect = pygame.Rect(
                x + pad_x,
                y + pad_y,
                badge_surf.get_width() + badge_pad_x * 2,
                badge_surf.get_height() + badge_pad_y * 2,
            )
            pygame.draw.rect(screen, COR_ELEVADO, badge_rect, border_radius=max(2, int(round(3 * s))))
            pygame.draw.rect(screen, cor_destaque, badge_rect, width=1, border_radius=max(2, int(round(3 * s))))
            screen.blit(badge_surf, (badge_rect.x + badge_pad_x, badge_rect.y + badge_pad_y))

            # Título completo da conquista/desbloqueio
            titulo = str(banner.get("titulo", t("ui_geral", "hud_banner_titulo_fallback")))
            titulo_surf = f_titulo.render(titulo, True, BRANCO)
            screen.blit(titulo_surf, (x + pad_x, badge_rect.bottom + max(3, int(round(4 * s)))))

            # Subtítulo da recompensa
            subtitulo = str(banner.get("subtitulo", ""))
            if subtitulo:
                sub_surf = f_sub.render(subtitulo, True, COR_CIANO)
                screen.blit(sub_surf, (x + pad_x, y + card_h - sub_surf.get_height() - pad_y))


