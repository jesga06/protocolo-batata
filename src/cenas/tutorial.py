"""
Cena de Tutorial e Guia de Combate — Protocolo: Batata
Explica os controles, HUD, tipos de drops, arquétipos de inimigos e mecânicas de jogo sem uso de emojis.
"""

import pygame
from src.cenas.base_scene import BaseScene
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
        self.pagina_atual = 0  # 0: Controles e HUD, 1: Drops e Armas, 2: Inimigos e Regras
        self.total_paginas = 3

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

        # Navegação direta para abas via teclas numéricas '1', '2', '3' (teclado principal ou numérico)
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

        if tecla_num1:
            self.pagina_atual = 0
            return
        elif tecla_num2:
            self.pagina_atual = 1
            return
        elif tecla_num3:
            self.pagina_atual = 2
            return

        # Navegação com clique do mouse nas abas superiores
        if self.mouse is not None and hasattr(self.mouse, "get_position") and hasattr(self.mouse, "button_down"):
            try:
                if self.mouse.button_down(1):
                    mx, my = self.mouse.get_position()
                    ox = (LARGURA_TELA - 800) // 2
                    oy = (ALTURA_TELA - 600) // 2
                    for i in range(self.total_paginas):
                        tx = ox + 75 + i * 220
                        rect_tab = pygame.Rect(tx, oy + 75, 205, 30)
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

        # Indicador de abas / páginas
        tabs = ["[1] CONTROLES & HUD", "[2] DROPS & ARMAS", "[3] INIMIGOS & MECÂNICAS"]
        for i, nome_tab in enumerate(tabs):
            tx = px(ox + 80 + i * 220)
            cor_tab = _C_GOLD if i == self.pagina_atual else _C_TEXT_MUTED
            tab_surf = fonte_tab.render(nome_tab, True, cor_tab)
            screen.blit(tab_surf, (tx, py(oy + 80)))
            if i == self.pagina_atual:
                pygame.draw.line(screen, _C_GOLD, (tx, py(oy + 98)), (tx + tab_surf.get_width(), py(oy + 98)), max(2, ps(2)))

        pygame.draw.line(screen, _C_BORDER, (px(ox + 60), py(oy + 105)), (px(ox + 740), py(oy + 105)), max(1, ps(1)))

        if self.pagina_atual == 0:
            sec1_surf = fonte_sec.render("CONTROLES PRINCIPAIS", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 120)))

            controles = [
                ("W, A, S, D", "Move Cleiton pelo escritório."),
                ("MOUSE (MIRA)", "Aponta os disparos e o alcance da Chave de Manutenção."),
                ("BOTÃO ESQUERDO", "Ataca com a arma equipada (segure para disparo contínuo)."),
                ("TECLAS 1, 2, 3", "Alterna entre Chave [1], Pistola [2] e Arma Especial [3]."),
                ("TECLA ESC / C", "Abre as Configurações para ligar modificadores e ajustar áudio.")
            ]

            y_pos = oy + 145
            for tecla, desc in controles:
                kc_r = pygame.Rect(px(ox + 70), py(y_pos), ps(150), ps(24))
                pygame.draw.rect(screen, _C_CARD, kc_r, border_radius=ps(5))
                pygame.draw.rect(screen, _C_BORDER, kc_r, width=max(1, ps(1)), border_radius=ps(5))
                t_surf = fonte_tab.render(tecla, True, _C_GOLD)
                screen.blit(t_surf, t_surf.get_rect(center=kc_r.center))

                d_surf = fonte_corpo.render(desc, True, _C_TEXT_PRIMARY)
                screen.blit(d_surf, (px(ox + 235), py(y_pos + 4)))
                y_pos += 32

            sec2_surf = fonte_sec.render("ELEMENTOS DA INTERFACE (HUD)", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 10)))
            y_pos += 35

            hud_itens = [
                ("Topo Central", "Mostra o cronômetro, os abates, a barra de XP e a vida dos chefes."),
                ("Canto Superior Esquerdo", "Exibe os 4 slots de armas/drones, munição restante e buffs ativos."),
                ("Abaixo de Cleiton", "Barra verde de vida e barreira azul de sobrevida, quando ativa.")
            ]
            for tit_h, desc_h in hud_itens:
                h_surf = fonte_destaque.render(f"- {tit_h}:", True, _C_TEXT_PRIMARY)
                screen.blit(h_surf, (px(ox + 70), py(y_pos)))
                d_surf = fonte_corpo.render(desc_h, True, _C_TEXT_SECONDARY)
                screen.blit(d_surf, (px(ox + 70), py(y_pos + 16)))
                y_pos += 34

        elif self.pagina_atual == 1:
            sec1_surf = fonte_sec.render("ITENS E COLETÁVEIS (DURAM 60 SEGUNDOS NO CHÃO)", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 120)))

            drops_info = [
                ("Gema Amarela de XP", "Dá experiência para subir até o nível 12."),
                ("Caixa de Reparo", "Recupera 35 de vida na hora."),
                ("Caixa de Arma Especial", "Equipa uma das 6 armas pesadas no Slot 3 com munição limitada."),
                ("Módulo de Drone", "Ativa um drone no Slot 4 por 30s ou evolui um ativo (MK-I até MK-III)."),
                ("Núcleo de Overclock", "Cai de Mini-Bosses derrotados em até 60s e instala uma melhoria de BIOS.")
            ]
            y_pos = oy + 145
            for nome_d, desc_d in drops_info:
                d_surf = fonte_destaque.render(f"* {nome_d}:", True, _C_GOLD)
                screen.blit(d_surf, (px(ox + 70), py(y_pos)))
                desc_s = fonte_corpo.render(desc_d, True, _C_TEXT_PRIMARY)
                screen.blit(desc_s, (px(ox + 70), py(y_pos + 15)))
                y_pos += 30

            sec2_surf = fonte_sec.render("ARSENAL DISPONÍVEL", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 4)))
            y_pos += 26

            armas_info = [
                ("Chave de Manutenção [1]", "Empurra inimigos de perto e rebate tiros inimigos de volta (Parry)."),
                ("Pistola [2]", "Munição infinita. Todo 4º disparo sai mais forte e atravessa inimigos."),
                ("Escopeta / Rifle [3]", "Escopeta dispara 9 chumbos com empurrão; Rifle garante crítico a cada 3º tiro."),
                ("Minigun / Foguetes / Granadas [3]", "Giro acelerado, piso em chamas ou granadas com sub-explosões."),
                ("Railgun [3]", "Carrega por 1s com mira laser e atravessa a fila inteira deixando plasma.")
            ]
            for nome_a, desc_a in armas_info:
                a_surf = fonte_destaque.render(f"- {nome_a}:", True, _C_GOLD)
                screen.blit(a_surf, (px(ox + 70), py(y_pos)))
                desc_a_s = fonte_corpo.render(desc_a, True, _C_TEXT_SECONDARY)
                screen.blit(desc_a_s, (px(ox + 70), py(y_pos + 14)))
                y_pos += 28

        elif self.pagina_atual == 2:
            sec1_surf = fonte_sec.render("MÁQUINAS DO ESCRITÓRIO", True, _C_CYAN)
            screen.blit(sec1_surf, (px(ox + 70), py(oy + 120)))

            inimigos_info = [
                ("Gabinete de Firma", "Perseguidor padrão do escritório (40 HP)."),
                ("Mouse Óptico", "Corre rápido, mas cai com poucos tiros (20 HP)."),
                ("Copiadora Xerox", "Lenta, resistente (120 HP) e causa bastante dano de contato."),
                ("Monitor CRT", "Fica translúcido e imune a qualquer dano por 1,2s a cada 3s."),
                ("Triturador Blindado", "Corta 30% do dano pela frente; ataque pelos lados ou costas."),
                ("Projetor Laser", "Mantém distância e atira feixes que podem ser rebatidos com a Chave [1].")
            ]
            y_pos = oy + 145
            for nome_i, desc_i in inimigos_info:
                i_surf = fonte_destaque.render(f"* {nome_i}:", True, (252, 165, 165))
                screen.blit(i_surf, (px(ox + 70), py(y_pos)))
                desc_i_s = fonte_corpo.render(desc_i, True, _C_TEXT_PRIMARY)
                screen.blit(desc_i_s, (px(ox + 70), py(y_pos + 14)))
                y_pos += 29

            sec2_surf = fonte_sec.render("PROGRESSÃO, MINI-BOSSES E CHEFE FINAL", True, _C_CYAN)
            screen.blit(sec2_surf, (px(ox + 70), py(y_pos + 4)))
            y_pos += 25

            regras_info = [
                ("Níveis Normais (Sem Pausa)", "Curam 10 HP, empurram inimigos e soltam 2 Cápsulas para escolher uma."),
                ("Níveis 5 e 11 (Configurações)", "Pausam o jogo para desbloquear 1 Configuração (que começa desligada)."),
                ("Mini-Bosses (1 a 4 min)", "Superaquecem em 60s sem deixar prêmio; abater em menos de 30s dá bônus."),
                ("Geladeira Tsunami", "Entra no nível 12 (ou após os Mini-Bosses) depois de um aviso de 10s.")
            ]
            for nome_r, desc_r in regras_info:
                r_surf = fonte_destaque.render(f"- {nome_r}:", True, _C_GOLD)
                screen.blit(r_surf, (px(ox + 70), py(y_pos)))
                desc_r_s = fonte_corpo.render(desc_r, True, _C_TEXT_SECONDARY)
                screen.blit(desc_r_s, (px(ox + 70), py(y_pos + 14)))
                y_pos += 27

        # Rodapé de Instruções
        rodape_txt = "[1, 2, 3] / [A / D] / [SETAS] ou CLIQUE para trocar de página   •   [ESC / ENTER] Voltar"
        rod_surf = fonte_rod.render(rodape_txt, True, _C_TEXT_MUTED)
        screen.blit(rod_surf, rod_surf.get_rect(centerx=px(LARGURA_TELA // 2), bottom=painel_rect.bottom - ps(12)))
