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
        screen.fill(CINZA_FUNDO)

        ox = (LARGURA_TELA - 800) // 2
        oy = (ALTURA_TELA - 600) // 2

        # Painel central estilizado
        painel_rect = pygame.Rect(ox + 40, oy + 30, 720, 540)
        pygame.draw.rect(screen, CINZA_PAINEL, painel_rect, border_radius=8)
        pygame.draw.rect(screen, CINZA_BORDA, painel_rect, width=2, border_radius=8)

        # Cabeçalho
        fonte_tit = self._fonte_tit
        tit_surf = fonte_tit.render("GUIA DE SOBREVIVÊNCIA - PROTOCOLO: BATATA", True, DOURADO)
        tit_rect = tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 45)
        screen.blit(tit_surf, tit_rect)

        # Indicador de abas / páginas
        fonte_tab = self._fonte_tab
        tabs = ["[1] CONTROLES & HUD", "[2] DROPS & ARMAS", "[3] INIMIGOS & MECÂNICAS"]
        for i, nome_tab in enumerate(tabs):
            tx = ox + 80 + i * 220
            cor_tab = DOURADO if i == self.pagina_atual else (120, 135, 155)
            tab_surf = fonte_tab.render(nome_tab, True, cor_tab)
            screen.blit(tab_surf, (tx, oy + 80))
            if i == self.pagina_atual:
                pygame.draw.line(screen, DOURADO, (tx, oy + 98), (tx + tab_surf.get_width(), oy + 98), 2)

        pygame.draw.line(screen, (45, 55, 75), (ox + 60, oy + 105), (ox + 740, oy + 105), 1)

        fonte_sec = self._fonte_sec
        fonte_corpo = self._fonte_corpo
        fonte_destaque = self._fonte_destaque

        if self.pagina_atual == 0:
            # Página 1: Controles e HUD
            sec1_surf = fonte_sec.render("CONTROLES PRINCIPAIS", True, AZUL_CIANO)
            screen.blit(sec1_surf, (ox + 70, oy + 120))

            controles = [
                ("W, A, S, D", "Move a Batata pela arena."),
                ("MOUSE (MIRA)", "Aponta a mira das armas e o cone da Chave de Manutenção."),
                ("BOTÃO ESQUERDO", "Atira com a arma equipada."),
                ("TECLAS 1, 2, 3", "Alterna entre Chave Inglesa [1], Pistola [2] e Arma Especial [3]."),
                ("TECLA ESC / C", "Abre o Menu de Configurações para ligar ou desligar modificadores.")
            ]

            y_pos = oy + 145
            for tecla, desc in controles:
                pygame.draw.rect(screen, (20, 26, 38), (ox + 70, y_pos, 150, 24), border_radius=4)
                pygame.draw.rect(screen, (50, 65, 90), (ox + 70, y_pos, 150, 24), width=1, border_radius=4)
                t_surf = fonte_destaque.render(tecla, True, AMARELO_XP)
                screen.blit(t_surf, t_surf.get_rect(centerx=ox + 145, centery=y_pos + 12))

                d_surf = fonte_corpo.render(desc, True, BRANCO)
                screen.blit(d_surf, (ox + 235, y_pos + 4))
                y_pos += 32

            sec2_surf = fonte_sec.render("ELEMENTOS DA INTERFACE (HUD)", True, AZUL_CIANO)
            screen.blit(sec2_surf, (ox + 70, y_pos + 10))
            y_pos += 35

            hud_itens = [
                ("Barra Superior Central", "Mostra o tempo de partida e o total de abates."),
                ("Barra de Experiência", "Indica o nível atual e o progresso até o próximo nível."),
                ("Slots no Canto Superior", "Mostram a arma ativa, a munição restante e os drones em órbita.")
            ]
            for tit_h, desc_h in hud_itens:
                h_surf = fonte_destaque.render(f"- {tit_h}:", True, (200, 220, 240))
                screen.blit(h_surf, (ox + 70, y_pos))
                d_surf = fonte_corpo.render(desc_h, True, CINZA_TEXTO)
                screen.blit(d_surf, (ox + 70, y_pos + 16))
                y_pos += 34

        elif self.pagina_atual == 1:
            # Página 2: Drops e Armas
            sec1_surf = fonte_sec.render("ITENS E COLETÁVEIS (DURAM 60 SEGUNDOS NO CHÃO)", True, AZUL_CIANO)
            screen.blit(sec1_surf, (ox + 70, oy + 120))

            drops_info = [
                ("Gema Amarela de XP", "Dá experiência para subir de nível."),
                ("Caixa de Reparo", "Recupera 35 de vida na hora."),
                ("Caixa de Arma Especial", "Equipa uma arma pesada no Slot 3 com munição limitada."),
                ("Módulo de Drone", "Ativa um drone no Slot 4 por 30s ou evolui um drone ativo até MK-III."),
                ("Núcleo de Overclock", "Drop de Mini-Boss que instala um módulo tático de BIOS.")
            ]
            y_pos = oy + 145
            for nome_d, desc_d in drops_info:
                d_surf = fonte_destaque.render(f"* {nome_d}:", True, AMARELO_XP)
                screen.blit(d_surf, (ox + 70, y_pos))
                desc_s = fonte_corpo.render(desc_d, True, BRANCO)
                screen.blit(desc_s, (ox + 70, y_pos + 15))
                y_pos += 30

            sec2_surf = fonte_sec.render("ARSENAL DISPONÍVEL", True, AZUL_CIANO)
            screen.blit(sec2_surf, (ox + 70, y_pos + 4))
            y_pos += 26

            armas_info = [
                ("Chave de Manutenção [1]", "Golpe em arco que empurra inimigos e rebate projéteis inimigos (Parry)."),
                ("Pistola [2]", "Munição infinita. Todo 4º disparo sai sobrecarregado e atravessa alvos."),
                ("Escopeta [3]", "Dispara 9 chumbos em leque com alto empurrão a queima-roupa."),
                ("Railgun [3]", "Carrega por 1.0s com mira laser e rasga a arena deixando trilha elétrica."),
                ("Minigun / Foguetes / Granadas [3]", "Aceleração de giro, chão em chamas ou arco com fragmentação.")
            ]
            for nome_a, desc_a in armas_info:
                a_surf = fonte_destaque.render(f"- {nome_a}:", True, DOURADO)
                screen.blit(a_surf, (ox + 70, y_pos))
                desc_a_s = fonte_corpo.render(desc_a, True, CINZA_TEXTO)
                screen.blit(desc_a_s, (ox + 70, y_pos + 14))
                y_pos += 28

        elif self.pagina_atual == 2:
            # Página 3: Inimigos e Mecânicas
            sec1_surf = fonte_sec.render("MÁQUINAS DO ESCRITÓRIO", True, AZUL_CIANO)
            screen.blit(sec1_surf, (ox + 70, oy + 120))

            inimigos_info = [
                ("Gabinete de Firma", "Perseguidor padrão do escritório (40 de vida)."),
                ("Mouse Óptico", "Rápido e frágil, avança em alta velocidade (20 de vida)."),
                ("Monitor de Tubo", "Entra em fase estática e fica temporariamente intangível."),
                ("Triturador de Papel", "Chassi blindado que reduz dano recebido pela frente."),
                ("Projetor Laser", "Mantém distância e dispara feixes que podem ser rebatidos na Chave Inglesa."),
                ("Mini-Bosses e Geladeira Tsunami", "Abata Mini-Bosses em menos de 30s para bônus extra antes de encarar a Geladeira.")
            ]
            y_pos = oy + 145
            for nome_i, desc_i in inimigos_info:
                i_surf = fonte_destaque.render(f"* {nome_i}:", True, (255, 120, 120))
                screen.blit(i_surf, (ox + 70, y_pos))
                desc_i_s = fonte_corpo.render(desc_i, True, BRANCO)
                screen.blit(desc_i_s, (ox + 70, y_pos + 15))
                y_pos += 31

            sec2_surf = fonte_sec.render("PROGRESSÃO, CÁPSULAS E CONFIGURAÇÕES", True, AZUL_CIANO)
            screen.blit(sec2_surf, (ox + 70, y_pos + 4))
            y_pos += 26

            regras_info = [
                ("Níveis Normais (Sem Pausa)", "Soltam uma onda de choque, curam 10 de vida e derrubam 2 Cápsulas no chão."),
                ("Marcos de Configuração (Níveis 5 e 11)", "Abrem o painel para desbloquear uma Configuração permanente."),
                ("Buffer de Misericórdia", "Se pular uma Configuração no marco, ela continua disponível no marco seguinte."),
                ("Núcleos de Overclock", "Derrote Mini-Bosses antes de 60s para instalar módulos táticos de BIOS.")
            ]
            for nome_r, desc_r in regras_info:
                r_surf = fonte_destaque.render(f"- {nome_r}:", True, DOURADO)
                screen.blit(r_surf, (ox + 70, y_pos))
                desc_r_s = fonte_corpo.render(desc_r, True, CINZA_TEXTO)
                screen.blit(desc_r_s, (ox + 70, y_pos + 14))
                y_pos += 27

        # Rodapé de Instruções
        rodape_txt = "Pressione [1, 2, 3], [A / D], [SETAS] ou CLIQUE para trocar de página | [ESC / ENTER] para voltar"
        fonte_rod = self._fonte_rod
        rod_surf = fonte_rod.render(rodape_txt, True, (150, 165, 185))
        screen.blit(rod_surf, rod_surf.get_rect(centerx=LARGURA_TELA // 2, bottom=painel_rect.bottom - 12))
