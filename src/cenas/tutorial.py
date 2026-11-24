"""
Cena de Tutorial e Guia de Combate — Protocolo: Batata
Explica os controles, HUD, tipos de drops, arquétipos de inimigos e mecânicas de jogo sem uso de emojis.
"""

import pygame
from src.cenas.base_scene import BaseScene
from src.ui.banner_dicas import BannerDica
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, BRANCO, PRETO, DOURADO,
    AZUL_CIANO, AMARELO_XP, VERDE_CURA, VERMELHO_HP, LARANJA_ALERTA,
    CINZA_BORDA, CINZA_PAINEL, CINZA_FUNDO, CINZA_TEXTO
)

_C_BACKDROP = (7, 9, 14)
_C_HUD_PANEL = (11, 14, 23)
_C_CARD = (17, 24, 39)
_C_BORDER = (51, 65, 85)
_C_CYAN = (34, 211, 238)
_C_PURPLE = (168, 85, 247)
_C_GOLD = (251, 191, 36)
_C_TEXT_PRIMARY = (241, 245, 249)
_C_TEXT_SECONDARY = (148, 163, 184)
_C_TEXT_MUTED = (100, 116, 139)

_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}


def _obter_fonte(familia: str, tamanho: int, bold: bool = False) -> pygame.font.Font:
    px_sz = max(8, int(tamanho))
    chave = (familia, px_sz, bold)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    candidatos = ("jetbrainsmono", "firacode", "consolas", "dejavusansmono") if familia == "mono" else ("notosans", "dejavusans", "liberationsans", "arial")
    for nome in candidatos:
        f = pygame.font.SysFont(nome, px_sz, bold=bold)
        if f is not None:
            _FONT_CACHE[chave] = f
            return f
    f = pygame.font.SysFont("Arial", px_sz, bold=bold)
    _FONT_CACHE[chave] = f
    return f


class TutorialScene(BaseScene):
    """
    Tela de Tutorial interativo em formato de painel com guias visuais.
    """

    def __init__(
        self):
        super().__init__()
        self.tempo_acumulado = 0.0
        self.pagina_atual = 0  # 0: Controles, 1: Projéteis & Música, 2: Arsenal & Drops, 3: Inimigos & Sistemas
        self.total_paginas = 4
        self.banner_dicas = BannerDica()

        # Debounce de entrada e proteção contra sangramento de teclas de cenas anteriores
        self.tempo_entrada = 0.0
        self._teclas_bloqueadas_entrada = True
        self._tab_pressionado_anterior = False
        self._kp6_pressionado_anterior = False
        self._kp4_pressionado_anterior = False

        # Cache de fontes para alta performance
        self._fonte_tit = pygame.font.SysFont("Arial", 22, bold=True)
        self._fonte_tab = pygame.font.SysFont("Arial", 12, bold=True)
        self._fonte_sec = pygame.font.SysFont("Arial", 14, bold=True)
        self._fonte_corpo = pygame.font.SysFont("Arial", 12)
        self._fonte_destaque = pygame.font.SysFont("Arial", 12, bold=True)
        self._fonte_rod = pygame.font.SysFont("Arial", 11, bold=True)

    def loop(self):
        dt = min(self.janela.delta_time(), 0.1)
        self.tempo_acumulado += dt
        self.tempo_entrada += dt
        if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
            self.banner_dicas.atualizar(dt)

        # Checa estado físico das teclas brutas no Pygame
        tab_pressionado = False
        kp6_pressionado = False
        kp4_pressionado = False
        teclas_acao_seguradas = False
        try:
            keys = pygame.key.get_pressed()
            tab_pressionado = bool(keys[pygame.K_TAB])
            kp6_pressionado = bool(keys[pygame.K_KP6] or keys[pygame.K_KP_6])
            kp4_pressionado = bool(keys[pygame.K_KP4] or keys[pygame.K_KP_4])
            if (keys[pygame.K_t] or keys[pygame.K_RETURN] or keys[pygame.K_ESCAPE] or
                keys[pygame.K_SPACE] or keys[pygame.K_m] or keys[pygame.K_TAB]):
                teclas_acao_seguradas = True
        except Exception:
            pass

        # Proteção contra sangramento de input: só aceita ações após soltar as teclas de ação ou após 0.25s
        if self._teclas_bloqueadas_entrada:
            if not teclas_acao_seguradas or self.tempo_entrada >= 0.25:
                self._teclas_bloqueadas_entrada = False
            else:
                self._tab_pressionado_anterior = tab_pressionado
                self._kp6_pressionado_anterior = kp6_pressionado
                self._kp4_pressionado_anterior = kp4_pressionado
                return

        # Detecção de borda de subida (edge detection) para teclas especiais
        tab_edge = tab_pressionado and not self._tab_pressionado_anterior
        self._tab_pressionado_anterior = tab_pressionado

        kp6_edge = kp6_pressionado and not self._kp6_pressionado_anterior
        self._kp6_pressionado_anterior = kp6_pressionado

        kp4_edge = kp4_pressionado and not self._kp4_pressionado_anterior
        self._kp4_pressionado_anterior = kp4_pressionado

        # Retorno ao menu principal via edge detection (key_down)
        tecla_voltar = (
            hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("ESC") or
                self.teclado.key_down("ENTER") or
                self.teclado.key_down("SPACE") or
                self.teclado.key_down("m") or self.teclado.key_down("M") or
                self.teclado.key_down("t") or self.teclado.key_down("T")
            )
        )
        if tecla_voltar:
            from PPlay.scenemanager import SceneManager
            from src.cenas.menu_principal import MenuPrincipalScene
            SceneManager.change_scene(MenuPrincipalScene())
            return

        # Navegação direta para abas via teclas numéricas '1'..'4'
        tecla_num1 = (
            hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("1") or self.teclado.key_down("KP_1") or self.teclado.key_down("KP1")
            )
        )
        tecla_num2 = (
            hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("2") or self.teclado.key_down("KP_2") or self.teclado.key_down("KP2")
            )
        )
        tecla_num3 = (
            hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("3") or self.teclado.key_down("KP_3") or self.teclado.key_down("KP3")
            )
        )
        tecla_num4 = (
            hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("4") or self.teclado.key_down("KP_4") or self.teclado.key_down("KP4")
            )
        )

        if tecla_num1:
            self.pagina_atual = 0
            return
        elif tecla_num2:
            self.pagina_atual = 1
            return
        elif tecla_num3:
            self.pagina_atual = 2
            return
        elif tecla_num4:
            self.pagina_atual = 3
            return

        # Navegação com clique do mouse nas abas superiores
        if self.mouse is not None and hasattr(self.mouse, "get_position") and hasattr(self.mouse, "button_down"):
            try:
                if self.mouse.button_down(1):
                    mx, my = self.mouse.get_position()
                    ox = (LARGURA_TELA - 800) // 2
                    oy = (ALTURA_TELA - 600) // 2
                    for i in range(self.total_paginas):
                        tx = ox + 60 + i * 172
                        rect_tab = pygame.Rect(tx, oy + 75, 166, 30)
                        if rect_tab.collidepoint(mx, my):
                            self.pagina_atual = i
                            return
            except Exception:
                pass

        # Navegação de páginas (Direita / Esquerda)
        tecla_dir = (
            (hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("RIGHT") or self.teclado.key_down("d") or self.teclado.key_down("D") or
                self.teclado.key_down("TAB") or self.teclado.key_down("KP_6") or self.teclado.key_down("KP6")
            )) or tab_edge or kp6_edge
        )
        tecla_esq = (
            (hasattr(self.teclado, "key_down") and (
                self.teclado.key_down("LEFT") or self.teclado.key_down("a") or self.teclado.key_down("A") or
                self.teclado.key_down("KP_4") or self.teclado.key_down("KP4")
            )) or kp4_edge
        )

        if tecla_dir:
            self.pagina_atual = (self.pagina_atual + 1) % self.total_paginas
        elif tecla_esq:
            self.pagina_atual = (self.pagina_atual - 1) % self.total_paginas

    def draw(self):
        screen = self.janela.screen
        sw, sh = screen.get_size()
        scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
        vx = (sw - int(round(LARGURA_TELA * scale))) // 2
        vy = (sh - int(round(ALTURA_TELA * scale))) // 2

        def px(val: float) -> int:
            return vx + int(round(val * scale))

        def py(val: float) -> int:
            return vy + int(round(val * scale))

        def ps(val: float) -> int:
            return max(1, int(round(val * scale)))

        screen.fill(_C_BACKDROP)

        ox = (LARGURA_TELA - 800) // 2
        oy = (ALTURA_TELA - 600) // 2

        # Painel central estilizado (projetado em DPI nativo)
        painel_rect = pygame.Rect(px(ox + 40), py(oy + 30), ps(720), ps(540))
        pygame.draw.rect(screen, _C_HUD_PANEL, painel_rect, border_radius=ps(10))
        pygame.draw.rect(screen, _C_BORDER, painel_rect, width=max(1, ps(2)), border_radius=ps(10))
        meio_w = (painel_rect.width - ps(28)) // 2
        pygame.draw.rect(screen, _C_PURPLE, (painel_rect.x + ps(14), painel_rect.y + 1, meio_w, max(2, ps(2))))
        pygame.draw.rect(screen, _C_GOLD, (painel_rect.x + ps(14) + meio_w, painel_rect.y + 1, meio_w, max(2, ps(2))))

        # Fontes nativas cacheadas por escala
        fonte_tit = _obter_fonte("sans", max(8, int(round(22 * scale))), bold=True)
        fonte_tab = _obter_fonte("mono", max(8, int(round(12 * scale))), bold=True)
        fonte_sec = _obter_fonte("sans", max(8, int(round(14 * scale))), bold=True)
        fonte_corpo = _obter_fonte("sans", max(8, int(round(12 * scale))), bold=False)
        fonte_destaque = _obter_fonte("sans", max(8, int(round(12 * scale))), bold=True)
        fonte_rod = _obter_fonte("mono", max(8, int(round(11 * scale))), bold=False)

        # Cabeçalho
        tit_surf = fonte_tit.render("GUIA DE SOBREVIVÊNCIA - PROTOCOLO: BATATA", True, _C_GOLD)
        tit_rect = tit_surf.get_rect(centerx=px(LARGURA_TELA // 2), top=py(oy + 45))
        screen.blit(tit_surf, tit_rect)

        try:
            pygame.mouse.set_visible(True)
        except Exception:
            pass

        # Indicador de abas / páginas
        tabs = ["[1] CONTROLES", "[2] PROJÉTEIS & RITMO", "[3] ARSENAL & DROPS", "[4] INIMIGOS & SISTEMAS"]
        fonte_tab_sm = _obter_fonte("mono", max(8, int(round(10 * scale))), bold=True)
        for i, nome_tab in enumerate(tabs):
            tx = px(ox + 60 + i * 172)
            cor_tab = _C_GOLD if i == self.pagina_atual else _C_TEXT_MUTED
            tab_surf = fonte_tab_sm.render(nome_tab, True, cor_tab)
            screen.blit(tab_surf, (tx, py(oy + 80)))
            if i == self.pagina_atual:
                pygame.draw.line(screen, _C_GOLD, (tx, py(oy + 98)), (tx + tab_surf.get_width(), py(oy + 98)), max(2, ps(2)))

        pygame.draw.line(screen, _C_BORDER, (px(ox + 60), py(oy + 105)), (px(ox + 740), py(oy + 105)), max(1, ps(1)))

        if self.pagina_atual == 0:
            sec1_surf = fonte_sec.render("CONTROLES PRINCIPAIS", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 116)))

            controles = [
                ("W, A, S, D", "Move Cleiton pelo escritório."),
                ("LMB (ESQ.)", "Ataca com a arma equipada (Melee na Chave/Bastão)."),
                ("RMB (DIR.)", "Parry Rápido instantâneo (sem precisar trocar para o Slot 1!)."),
                ("SHIFT / ESPAÇO", "Dash com invencibilidade; Just-Dodge mantém seu Combo ativo."),
                ("TECLAS 1, 2, 3 / F", "Troca Slots [1..3]; [F] alterna Auto-Fire; [ESC] abre Configs."),
            ]

            y_pos = oy + 140
            for tecla, desc in controles:
                kc_r = pygame.Rect(px(ox + 70), py(y_pos), ps(155), ps(24))
                pygame.draw.rect(screen, _C_CARD, kc_r, border_radius=ps(5))
                pygame.draw.rect(screen, _C_BORDER, kc_r, width=max(1, ps(1)), border_radius=ps(5))
                t_surf = fonte_tab_sm.render(tecla, True, _C_GOLD)
                screen.blit(t_surf, t_surf.get_rect(center=kc_r.center))

                d_surf = fonte_corpo.render(desc, True, _C_TEXT_PRIMARY)
                screen.blit(d_surf, (px(ox + 238), py(y_pos + 4)))
                y_pos += 30

            sec2_surf = fonte_sec.render("HUD, COMBO & CONQUISTAS FIXADAS", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 8)))
            y_pos += 32

            hud_itens = [
                ("Topo Central", "Cronômetro, abates, barra de XP, vida dos chefes e Combo (Ranks D->S)."),
                ("Canto Superior Direito", "Exibe até 3 Conquistas Fixadas com progresso e recompensa ao vivo."),
                ("Canto Superior Esquerdo", "4 slots (Melee, Pistola/SMG, Especial, Drones) + calor/munição."),
            ]
            for tit_h, desc_h in hud_itens:
                h_surf = fonte_destaque.render(f"- {tit_h}:", True, _C_TEXT_PRIMARY)
                screen.blit(h_surf, (px(ox + 70), py(y_pos)))
                d_surf = fonte_corpo.render(desc_h, True, _C_TEXT_SECONDARY)
                screen.blit(d_surf, (px(ox + 70), py(y_pos + 16)))
                y_pos += 36

        elif self.pagina_atual == 1:
            sec1_surf = fonte_sec.render("3 TIPOS DE PROJÉTEIS INIMIGOS (LEGENDA VISUAL)", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 116)))

            tipos_proj = [
                (
                    "comum",
                    "Projétil Comum (Vermelho)",
                    "Pode ser rebatido com Parry (RMB) OU atravessado com Dash.",
                    (239, 68, 68),
                ),
                (
                    "shuriken",
                    "Shuriken Ninja (Roxo-Magenta) — NÃO-DESVIÁVEL",
                    "Ignora i-frames do Dash! Exige PARRY (RMB). Exclusivo do Ninja Corporativo.",
                    (217, 70, 239),
                ),
                (
                    "seta",
                    "Seta de Perigo (Amarela-Preta) — NÃO-PARRIÁVEL",
                    "Ignora Parry! Exige DASH / Just-Dodge. Exclusivo de Ranged (config ativa).",
                    (250, 204, 21),
                ),
            ]
            y_pos = oy + 144
            for kind, tit_p, desc_p, cor_p in tipos_proj:
                card_r = pygame.Rect(px(ox + 70), py(y_pos), ps(660), ps(54))
                pygame.draw.rect(screen, _C_CARD, card_r, border_radius=ps(6))
                pygame.draw.rect(screen, _C_BORDER, card_r, width=max(1, ps(1)), border_radius=ps(6))

                ic_cx = px(ox + 102)
                ic_cy = py(y_pos + 27)
                if kind == "comum":
                    pygame.draw.circle(screen, (239, 68, 68), (ic_cx, ic_cy), ps(9))
                    pygame.draw.circle(screen, (254, 202, 202), (ic_cx - ps(2), ic_cy - ps(2)), ps(3))
                elif kind == "shuriken":
                    pygame.draw.circle(screen, (147, 51, 234), (ic_cx, ic_cy), ps(13), width=max(1, ps(2)))
                    pts = [
                        (ic_cx, ic_cy - ps(11)), (ic_cx + ps(3), ic_cy - ps(3)),
                        (ic_cx + ps(11), ic_cy), (ic_cx + ps(3), ic_cy + ps(3)),
                        (ic_cx, ic_cy + ps(11)), (ic_cx - ps(3), ic_cy + ps(3)),
                        (ic_cx - ps(11), ic_cy), (ic_cx - ps(3), ic_cy - ps(3)),
                    ]
                    pygame.draw.polygon(screen, (217, 70, 239), pts)
                    pygame.draw.polygon(screen, (255, 255, 255), pts, width=max(1, ps(1)))
                else:
                    pts_s = [
                        (ic_cx + ps(12), ic_cy),
                        (ic_cx - ps(8), ic_cy - ps(9)),
                        (ic_cx - ps(4), ic_cy),
                        (ic_cx - ps(8), ic_cy + ps(9)),
                    ]
                    pygame.draw.polygon(screen, (250, 204, 21), pts_s)
                    pygame.draw.polygon(screen, (20, 20, 20), pts_s, width=max(1, ps(2)))

                screen.blit(fonte_destaque.render(tit_p, True, cor_p), (px(ox + 132), py(y_pos + 8)))
                screen.blit(fonte_corpo.render(desc_p, True, _C_TEXT_PRIMARY), (px(ox + 132), py(y_pos + 28)))
                y_pos += 64

            sec2_surf = fonte_sec.render("RITMO MÚSICA-ONDA & DESBLOQUEIOS", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 6)))
            y_pos += 30
            ritmo_info = [
                ("Fases Música-Onda", "ANTICIPATION (preparo) -> HOLD (respiro) -> ASSAULT_INTRO -> ASSAULT (ataque intenso)."),
                ("15 Parries = Dash + SMG", "Complete 15 Parries para liberar Dash e SMG Compacta (mira na zona 60%-92%)."),
            ]
            for tit_r, desc_r in ritmo_info:
                screen.blit(fonte_destaque.render(f"- {tit_r}:", True, _C_GOLD), (px(ox + 70), py(y_pos)))
                screen.blit(fonte_corpo.render(desc_r, True, _C_TEXT_SECONDARY), (px(ox + 70), py(y_pos + 16)))
                y_pos += 36

        elif self.pagina_atual == 2:
            sec1_surf = fonte_sec.render("ARSENAL V2.0 (SLOTS 1, 2 E 3)", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 116)))

            armas_info = [
                ("Slot 1: Chave Inglesa / Bastão de Choque", "LMB golpeia de perto; RMB dá Parry. Bastão aplica corrente elétrica."),
                ("Slot 2: Pistola / SMG Compacta", "Pistola: 4º tiro sobrecarregado. SMG: zona ideal de calor (60%-92%) dá +25% cadência."),
                ("Slot 3: Escopeta, Rifle, Minigun, Foguetes, Granadas, Railgun", "Armas pesadas com munição limitada obtidas em Caixas de Arma."),
                ("Slot 3 (Novas): Rifle de Arco & Lança-Chamas", "Arco elétrico em cadeia (Rifle de Arco) e cone contínuo de fogo (Lança-Chamas)."),
            ]
            y_pos = oy + 140
            for nome_a, desc_a in armas_info:
                screen.blit(fonte_destaque.render(f"- {nome_a}:", True, _C_GOLD), (px(ox + 70), py(y_pos)))
                screen.blit(fonte_corpo.render(desc_a, True, _C_TEXT_PRIMARY), (px(ox + 70), py(y_pos + 15)))
                y_pos += 34

            sec2_surf = fonte_sec.render("ITENS E COLETÁVEIS NO CHÃO", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 6)))
            y_pos += 30
            drops_info = [
                ("Gema XP / Caixa Reparo", "Sobe até Nível 12 ou cura +35 HP. Drops por >10s podem ser roubados pelo Scavenger!"),
                ("Módulo Drone / Núcleo Overclock", "Evolui Drones (MK-I a MK-III) ou instala BIOS Overclock ao vencer Mini-Boss (<60s)."),
            ]
            for nome_d, desc_d in drops_info:
                screen.blit(fonte_destaque.render(f"* {nome_d}:", True, _C_GOLD), (px(ox + 70), py(y_pos)))
                screen.blit(fonte_corpo.render(desc_d, True, _C_TEXT_SECONDARY), (px(ox + 70), py(y_pos + 15)))
                y_pos += 34

        elif self.pagina_atual == 3:
            sec1_surf = fonte_sec.render("INIMIGOS DO ESCRITÓRIO", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 116)))

            inimigos_info = [
                ("Gabinete / Mouse / Xerox / CRT / Blindado", "Clássicos: CRT fica intangível a cada 3s; Blindado reduz 30% do dano frontal."),
                ("Projetor Laser (Ranged)", "Atira projéteis vermelhos ou Setas Amarelas (Não-Parriáveis) com config ativa."),
                ("Impressora Térmica", "Dispara projéteis grandes de alto impacto (sem aura dourada)."),
                ("Ninja Corporativo", "Lança Shurikens Roxas (Não-Desviáveis) e inicia Duelos de Parry!"),
            ]
            y_pos = oy + 140
            for nome_i, desc_i in inimigos_info:
                screen.blit(fonte_destaque.render(f"* {nome_i}:", True, (252, 165, 165)), (px(ox + 70), py(y_pos)))
                screen.blit(fonte_corpo.render(desc_i, True, _C_TEXT_PRIMARY), (px(ox + 70), py(y_pos + 15)))
                y_pos += 33

            sec2_surf = fonte_sec.render("CONQUISTAS, FIRMWARE & 28 CONFIGURAÇÕES", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 6)))
            y_pos += 30

            regras_info = [
                ("Conquistas & Chips de Firmware", "Desbloqueie armas, habilidades e até 3 Slots de Firmware equipáveis no Menu Principal."),
                ("28 Configurações de Gameplay", "Cada config combina um Benefício e um Sacrifício mecânico; ative várias para desafios."),
                ("Mini-Bosses & Geladeira Tsunami", "Mini-Bosses a cada 1 min (superaquecem em 60s); Chefe Final entra no Nível 12."),
            ]
            for nome_r, desc_r in regras_info:
                screen.blit(fonte_destaque.render(f"- {nome_r}:", True, _C_GOLD), (px(ox + 70), py(y_pos)))
                screen.blit(fonte_corpo.render(desc_r, True, _C_TEXT_SECONDARY), (px(ox + 70), py(y_pos + 15)))
                y_pos += 33

        # Rodapé de Instruções
        rodape_txt = "[1, 2, 3, 4] / [A / D] / [SETAS] ou CLIQUE para trocar de página   •   [ESC / ENTER] Voltar"
        rod_surf = fonte_rod.render(rodape_txt, True, _C_TEXT_MUTED)
        screen.blit(rod_surf, rod_surf.get_rect(centerx=px(LARGURA_TELA // 2), bottom=painel_rect.bottom - ps(12)))

        if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
            dica_rect = pygame.Rect(painel_rect.x, painel_rect.bottom + ps(10), painel_rect.width, ps(54))
            self.banner_dicas.desenhar(screen, dica_rect, scale=scale)
