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

    def __init__(self):
        super().__init__()
        self.tempo_acumulado = 0.0
        self.pagina_atual = 0  # 0: Controles e HUD, 1: Drops e Armas, 2: Inimigos e Regras
        self.total_paginas = 3

    def loop(self):
        dt = self.janela.delta_time()
        self.tempo_acumulado += dt

        # Navegação de páginas e retorno
        if self.teclado.key_down("ESCAPE") or self.teclado.key_down("RETURN") or self.teclado.key_down("SPACE"):
            from PPlay.scenemanager import SceneManager
            from src.cenas.menu_principal import MenuPrincipalScene
            SceneManager.change_scene(MenuPrincipalScene())
            return

        if self.teclado.key_down("RIGHT") or self.teclado.key_down("d") or self.teclado.key_down("TAB"):
            self.pagina_atual = (self.pagina_atual + 1) % self.total_paginas
        elif self.teclado.key_down("LEFT") or self.teclado.key_down("a"):
            self.pagina_atual = (self.pagina_atual - 1) % self.total_paginas

    def draw(self):
        screen = self.janela.screen
        screen.fill(CINZA_FUNDO)

        # Painel central estilizado
        painel_rect = pygame.Rect(40, 30, 720, 540)
        pygame.draw.rect(screen, CINZA_PAINEL, painel_rect, border_radius=8)
        pygame.draw.rect(screen, CINZA_BORDA, painel_rect, width=2, border_radius=8)

        # Cabeçalho
        fonte_tit = pygame.font.SysFont("Arial", 22, bold=True)
        tit_surf = fonte_tit.render("GUIA DE SOBREVIVÊNCIA — PROTOCOLO: BATATA", True, DOURADO)
        tit_rect = tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=45)
        screen.blit(tit_surf, tit_rect)

        # Indicador de abas / páginas
        fonte_tab = pygame.font.SysFont("Arial", 12, bold=True)
        tabs = ["[1] CONTROLES & HUD", "[2] DROPS & ARMAS", "[3] INIMIGOS & MECÂNICAS"]
        for i, nome_tab in enumerate(tabs):
            tx = 80 + i * 220
            cor_tab = DOURADO if i == self.pagina_atual else (120, 135, 155)
            tab_surf = fonte_tab.render(nome_tab, True, cor_tab)
            screen.blit(tab_surf, (tx, 80))
            if i == self.pagina_atual:
                pygame.draw.line(screen, DOURADO, (tx, 98), (tx + tab_surf.get_width(), 98), 2)

        pygame.draw.line(screen, (45, 55, 75), (60, 105), (740, 105), 1)

        fonte_sec = pygame.font.SysFont("Arial", 14, bold=True)
        fonte_corpo = pygame.font.SysFont("Arial", 12)
        fonte_destaque = pygame.font.SysFont("Arial", 12, bold=True)

        if self.pagina_atual == 0:
            # Página 1: Controles e HUD
            sec1_surf = fonte_sec.render("CONTROLES PRINCIPAIS", True, AZUL_CIANO)
            screen.blit(sec1_surf, (70, 120))

            controles = [
                ("W, A, S, D", "Movimentação da Batata com normalização diagonal."),
                ("MOUSE (MIRA)", "Aponta a mira das armas e a direção do cone de ataque."),
                ("BOTÃO ESQUERDO", "Dispara a arma equipada. Segure para disparo contínuo."),
                ("TECLAS 1, 2, 3, 4", "Alterna entre Melee [1], Pistola [2], Especial [3] e Drone [4]."),
                ("TECLA ESC / C", "Abre o Menu de Configurações para ligar/desligar modificadores.")
            ]

            y_pos = 145
            for tecla, desc in controles:
                pygame.draw.rect(screen, (20, 26, 38), (70, y_pos, 150, 24), border_radius=4)
                pygame.draw.rect(screen, (50, 65, 90), (70, y_pos, 150, 24), width=1, border_radius=4)
                t_surf = fonte_destaque.render(tecla, True, AMARELO_XP)
                screen.blit(t_surf, t_surf.get_rect(centerx=145, centery=y_pos + 12))

                d_surf = fonte_corpo.render(desc, True, BRANCO)
                screen.blit(d_surf, (235, y_pos + 4))
                y_pos += 32

            sec2_surf = fonte_sec.render("ELEMENTOS DA INTERFACE (HUD)", True, AZUL_CIANO)
            screen.blit(sec2_surf, (70, y_pos + 10))
            y_pos += 35

            hud_itens = [
                ("Barra Superior Central", "Exibe o Cronômetro de Sobrevivência e o Contador de Abates."),
                ("Barra de Experiência", "Mostra o nível atual e a barra amarela de progresso para o próximo nível."),
                ("Slots no Canto Superior", "Indicam as armas e drones equipados, com destaque no slot ativo e munição.")
            ]
            for tit_h, desc_h in hud_itens:
                h_surf = fonte_destaque.render(f"- {tit_h}:", True, (200, 220, 240))
                screen.blit(h_surf, (70, y_pos))
                d_surf = fonte_corpo.render(desc_h, True, CINZA_TEXTO)
                screen.blit(d_surf, (70, y_pos + 16))
                y_pos += 34

        elif self.pagina_atual == 1:
            # Página 2: Drops e Armas
            sec1_surf = fonte_sec.render("DROPS E COLETÁVEIS (DURAM 60 SEGUNDOS NO CHÃO)", True, AZUL_CIANO)
            screen.blit(sec1_surf, (70, 120))

            drops_info = [
                ("Gema Amarela de XP", "Concede experiência. Inimigos padrão dão 5 XP; inimigos maiores concedem mais."),
                ("Caixa Vermelha de Cura", "Restaura imediatamente 35 pontos de vida (HP) da Batata."),
                ("Caixa Dourada de Arma", "Equipa uma arma especial no Slot 3 com munição limitada."),
                ("Caixa Laranja de Drone", "Ativa um drone de suporte orbital no Slot 4 com duração de 30 segundos.")
            ]
            y_pos = 145
            for nome_d, desc_d in drops_info:
                d_surf = fonte_destaque.render(f"* {nome_d}:", True, AMARELO_XP)
                screen.blit(d_surf, (70, y_pos))
                desc_s = fonte_corpo.render(desc_d, True, BRANCO)
                screen.blit(desc_s, (70, y_pos + 16))
                y_pos += 36

            sec2_surf = fonte_sec.render("ARSENAL DISPONÍVEL", True, AZUL_CIANO)
            screen.blit(sec2_surf, (70, y_pos + 10))
            y_pos += 35

            armas_info = [
                ("Chave de Manutenção [1]", "Golpe melee em cone direcional de 45 graus com forte repulsão (knockback)."),
                ("Pistola [2]", "Arma permanente de disparo contínuo (10 de dano por tiro, munição infinita)."),
                ("Escopeta [3]", "Dispara 9 projéteis simultâneos com dispersão (10 de dano por projétil)."),
                ("Railgun [3]", "Carrega por 1.0s e dispara um projétil de 50 de dano que atravessa todos os alvos."),
                ("Minigun / Lança-Foguetes [3]", "Armas de alta cadência ou dano em área com munição finita.")
            ]
            for nome_a, desc_a in armas_info:
                a_surf = fonte_destaque.render(f"- {nome_a}:", True, DOURADO)
                screen.blit(a_surf, (70, y_pos))
                desc_a_s = fonte_corpo.render(desc_a, True, CINZA_TEXTO)
                screen.blit(desc_a_s, (70, y_pos + 15))
                y_pos += 32

        elif self.pagina_atual == 2:
            # Página 3: Inimigos e Mecânicas
            sec1_surf = fonte_sec.render("ARQUÉTIPOS DE INIMIGOS", True, AZUL_CIANO)
            screen.blit(sec1_surf, (70, 120))

            inimigos_info = [
                ("Estagiário (Robô Azul)", "Inimigo padrão de perseguição beeline (40 HP, cede 5 XP)."),
                ("Viciado em Cafeína (Verde)", "Inimigo ultra-rápido, morre com exatamente 2 tiros (20 HP, cede 8 XP)."),
                ("Warranty Void (Fantasma Ciano)", "Alterna para forma etérea: projéteis e golpes passam direto sem dano."),
                ("Ballistic Enthusiast (Blindado)", "Chassi reforçado com escudo que reduz dano frontal."),
                ("Atirador Blaster (Ferrugem)", "Mantém distância tática e dispara projéteis vermelhos no jogador."),
                ("Geladeira Industrial (Tanque)", "Monstro maciço com 120 HP que exige múltiplos disparos para ser destruído.")
            ]
            y_pos = 145
            for nome_i, desc_i in inimigos_info:
                i_surf = fonte_destaque.render(f"* {nome_i}:", True, (255, 120, 120))
                screen.blit(i_surf, (70, y_pos))
                desc_i_s = fonte_corpo.render(desc_i, True, BRANCO)
                screen.blit(desc_i_s, (70, y_pos + 16))
                y_pos += 34

            sec2_surf = fonte_sec.render("PROGRESSÃO E LEVEL UP POR MARCOS", True, AZUL_CIANO)
            screen.blit(sec2_surf, (70, y_pos + 8))
            y_pos += 30

            regras_info = [
                ("Níveis Regulares", "Oferecem 3 opções de buffs ou utilitários consumíveis escalados para o nível."),
                ("Níveis de Marco (a cada 5 níveis)", "A opção central é substituída por uma Configuração Amaldiçoada."),
                ("Buffer de Pity", "Se não escolher a Configuração no nível 5, ela reaparece no nível seguinte.")
            ]
            for nome_r, desc_r in regras_info:
                r_surf = fonte_destaque.render(f"- {nome_r}:", True, DOURADO)
                screen.blit(r_surf, (70, y_pos))
                desc_r_s = fonte_corpo.render(desc_r, True, CINZA_TEXTO)
                screen.blit(desc_r_s, (70, y_pos + 15))
                y_pos += 30

        # Rodapé de Instruções
        rodape_txt = "Pressione [A / D] ou [SETAS] para trocar de página | Pressione [ESC] ou [ENTER] para voltar"
        fonte_rod = pygame.font.SysFont("Arial", 11, bold=True)
        rod_surf = fonte_rod.render(rodape_txt, True, (150, 165, 185))
        screen.blit(rod_surf, rod_surf.get_rect(centerx=LARGURA_TELA // 2, bottom=painel_rect.bottom - 12))
