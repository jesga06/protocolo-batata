"""
Menu de Debug / Console de Desenvolvedor — Protocolo: Batata
Painel de depuração em tempo real acionado por F1 / ~ com navegação por teclado
e geração de entidades (drops e inimigos) via clique do mouse no mundo do jogo.
"""

import math
import os
import pygame
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA,
    ROXO_ACENTO, ROXO_CLARO, ROXO_ESCURO,
    DOURADO, VERDE_CURA, VERMELHO_DANO, LARANJA_ALERTA, BRANCO, CINZA_TEXTO,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR, DROP_CURA_VALOR_BASE
)
from src.entidades.drop import ItemDrop


class MenuDebug:
    """
    Console de depuração in-game com pausa total do mundo e controles rápidos.
    """

    def __init__(self, cena_gameplay=None):
        self.cena = cena_gameplay
        self.ativo = False
        self.cooldown_input = 0.0

        # Toggles de estado de gameplay
        self.spawn_natural_ativo = True
        self.timer_congelado = False
        self.municao_infinita = False
        self.modo_deus = False

        # Catálogos de opções de spawn
        self.opcoes_tipo_drop = [
            ("XP (+5)", "xp", 5),
            ("XP (+50)", "xp", 50),
            ("Cura (+35)", "cura", DROP_CURA_VALOR_BASE),
            ("Caixa de Arma", "arma", 1),
            ("Caixa Equipamento", "equipamento", 1)
        ]
        self.idx_tipo_drop = 0

        self.opcoes_armas = [
            ("Minigun", "Minigun"),
            ("Shotgun", "Shotgun"),
            ("Rifle Assalto", "RifleAssalto"),
            ("Lanca-Foguetes", "LancaFoguetes"),
            ("Lanca-Granadas", "LancaGranadas"),
            ("Railgun", "Railgun")
        ]
        self.idx_arma = 0

        self.opcoes_drones = [
            ("Drone Cura", "DroneCura"),
            ("Drone Combate", "DroneCombate"),
            ("Drone Suporte", "DroneSuporte")
        ]
        self.idx_drone = 0

        self.opcoes_inimigos = [
            ("Padrao (Estagiario)", "padrao"),
            ("Rapido (Cafeina)", "rapido"),
            ("Phasing (Warranty)", "phasing"),
            ("Blindado", "blindado"),
            ("Ranged (Atirador)", "ranged"),
            ("Tanque (Geladeira)", "tank"),
            ("Chefe de Elite", "elite")
        ]
        self.idx_inimigo = 0

        self.opcoes_level_up = [1, 3, 5, 10]
        self.idx_level_up = 0

        # Índice do menu focado
        self.indice_foco = 0
        self.total_itens = 12

        # Retângulo do painel de Debug (Top-Left)
        self.rect_painel = pygame.Rect(16, 16, 330, 530)
        self._fonte_tit = None
        self._fonte_item = None
        self._fonte_val = None
        self._fonte_hint = None
        self._mensagem_status = ""
        self._timer_status = 0.0

    def _inicializar_fontes(self):
        if self._fonte_tit is None:
            self._fonte_tit = pygame.font.SysFont("consolas", 14, bold=True)
            self._fonte_item = pygame.font.SysFont("consolas", 12, bold=True)
            self._fonte_val = pygame.font.SysFont("consolas", 12, bold=False)
            self._fonte_hint = pygame.font.SysFont("consolas", 11, bold=False)

    def alternar(self):
        """Abre ou fecha o menu de debug."""
        if self.ativo:
            self.fechar()
        else:
            self.abrir()

    def abrir(self):
        """Abre o menu de debug e congela a partida."""
        self.ativo = True
        self.cooldown_input = 0.25
        self._mensagem_status = "DEBUG MENU ATIVADO"
        self._timer_status = 2.0
        if self.cena and hasattr(self.cena, "pausado"):
            self.cena.pausado = True

    def fechar(self):
        """Fecha o menu de debug e descongela a partida (se modal level up ou configs não estiverem abertos)."""
        self.ativo = False
        self.cooldown_input = 0.25
        if self.cena:
            level_up_ativo = getattr(self.cena.modal_level_up, "ativo", False) if hasattr(self.cena, "modal_level_up") else False
            configs_ativo = getattr(self.cena.menu_configs, "ativo", False) if hasattr(self.cena, "menu_configs") else False
            if not level_up_ativo and not configs_ativo and hasattr(self.cena, "pausado"):
                self.cena.pausado = False

    def update(self, dt: float, teclado=None, mouse=None):
        """Processa inputs de teclado (navegação) e clique de mouse no mundo (spawn)."""
        if self.cooldown_input > 0.0:
            self.cooldown_input = max(0.0, self.cooldown_input - dt)

        if self._timer_status > 0.0:
            self._timer_status = max(0.0, self._timer_status - dt)
            if self._timer_status <= 0.0:
                self._mensagem_status = ""

        # Checa tecla de atalho F1 ou ~ (crase / tilde) para abrir/fechar
        tecla_f1 = False
        tecla_tilde = False

        if teclado is not None:
            if hasattr(teclado, "key_pressed"):
                tecla_f1 = teclado.key_pressed("F1")
                tecla_tilde = teclado.key_pressed("`") or teclado.key_pressed("~") or teclado.key_pressed("GRAVE")
            elif hasattr(teclado, "key_down"):
                tecla_f1 = teclado.key_down("F1")
                tecla_tilde = teclado.key_down("`") or teclado.key_down("~")

        # Checagem direta via Pygame para redundância
        chaves_pressionadas = pygame.key.get_pressed()
        if chaves_pressionadas[pygame.K_F1] or chaves_pressionadas[pygame.K_BACKQUOTE]:
            tecla_f1 = True

        if (tecla_f1 or tecla_tilde) and self.cooldown_input <= 0.0:
            self.alternar()
            return

        if not self.ativo:
            return

        # Se ativo, tecla ESC também fecha o debug menu
        if chaves_pressionadas[pygame.K_ESCAPE] and self.cooldown_input <= 0.0:
            self.fechar()
            return

        # 1. Navegação de Menu por Teclado (Setas CIMA / BAIXO)
        if self.cooldown_input <= 0.0:
            if chaves_pressionadas[pygame.K_UP]:
                self.indice_foco = (self.indice_foco - 1) % self.total_itens
                self.cooldown_input = 0.15
            elif chaves_pressionadas[pygame.K_DOWN]:
                self.indice_foco = (self.indice_foco + 1) % self.total_itens
                self.cooldown_input = 0.15
            elif chaves_pressionadas[pygame.K_LEFT]:
                self._alterar_opcao(direcao=-1)
                self.cooldown_input = 0.15
            elif chaves_pressionadas[pygame.K_RIGHT]:
                self._alterar_opcao(direcao=1)
                self.cooldown_input = 0.15
            elif chaves_pressionadas[pygame.K_RETURN] or chaves_pressionadas[pygame.K_SPACE]:
                self._executar_acao_selecionada()
                self.cooldown_input = 0.20

        # 2. Spawn pelo Clique do Mouse no Mundo
        # 2. Interação via Mouse (Clique no painel para selecionar/executar ou no mundo para spawn)
        mouse_clicado = False
        try:
            if mouse is not None and hasattr(mouse, "button_down") and mouse.button_down(1):
                mouse_clicado = True
        except Exception:
            pass

        if pygame.mouse.get_pressed()[0]:
            mouse_clicado = True

        if mouse_clicado and self.cooldown_input <= 0.0:
            mx, my = pygame.mouse.get_pos() if pygame.mouse.get_focused() else (400, 300)
            if self.rect_painel.collidepoint(mx, my):
                # Clique dentro do painel do menu de debug
                y_rel = my - (self.rect_painel.y + 40)
                if 0 <= y_rel < self.total_itens * 24:
                    item_clicado = y_rel // 24
                    self.indice_foco = item_clicado
                    item_rect = pygame.Rect(self.rect_painel.x + 8, self.rect_painel.y + 40 + item_clicado * 24 - 2, self.rect_painel.width - 16, 22)
                    if mx > item_rect.centerx:
                        self._alterar_opcao(1)
                    elif self.indice_foco in (8, 9, 10, 11):
                        self._executar_acao_selecionada()
                    self.cooldown_input = 0.20
            else:
                # Clique fora do painel: gera spawn nas coordenadas do mundo do jogo
                cam_x = getattr(self.cena.camera, "x", 0.0) if (self.cena and hasattr(self.cena, "camera")) else 0.0
                cam_y = getattr(self.cena.camera, "y", 0.0) if (self.cena and hasattr(self.cena, "camera")) else 0.0
                largura_arena = getattr(self.cena, "largura_arena", 2400)
                altura_arena = getattr(self.cena, "altura_arena", 1800)
                mundo_x = max(20.0, min(float(largura_arena) - 20.0, mx + cam_x))
                mundo_y = max(20.0, min(float(altura_arena) - 20.0, my + cam_y))
                self._spawnar_item_ou_inimigo_no_mundo(mundo_x, mundo_y)
                self.cooldown_input = 0.25

    def _alterar_opcao(self, direcao: int):
        """Altera valores de toggles e opções com as setas esquerda/direita."""
        if self.indice_foco == 0:  # Spawn Natural
            self.spawn_natural_ativo = not self.spawn_natural_ativo
        elif self.indice_foco == 1:  # Congelar Timer
            self.timer_congelado = not self.timer_congelado
        elif self.indice_foco == 2:  # Munição Infinita
            self.municao_infinita = not self.municao_infinita
        elif self.indice_foco == 3:  # Modo Deus
            self.modo_deus = not self.modo_deus
        elif self.indice_foco == 4:  # Tipo de Drop
            self.idx_tipo_drop = (self.idx_tipo_drop + direcao) % len(self.opcoes_tipo_drop)
        elif self.indice_foco == 5:  # Arma Específica
            self.idx_arma = (self.idx_arma + direcao) % len(self.opcoes_armas)
        elif self.indice_foco == 6:  # Drone Específico
            self.idx_drone = (self.idx_drone + direcao) % len(self.opcoes_drones)
        elif self.indice_foco == 7:  # Inimigo
            self.idx_inimigo = (self.idx_inimigo + direcao) % len(self.opcoes_inimigos)
        elif self.indice_foco == 10:  # Subir Nível (+X)
            self.idx_level_up = (self.idx_level_up + direcao) % len(self.opcoes_level_up)

    def _executar_acao_selecionada(self):
        """Executa ações com a tecla ENTER / ESPAÇO."""
        if self.indice_foco in (0, 1, 2, 3):
            self._alterar_opcao(1)
        elif self.indice_foco in (4, 5, 6, 7):
            # Spawna na frente do jogador se apertou ENTER
            if self.cena and hasattr(self.cena, "jogador") and self.cena.jogador:
                px = self.cena.jogador.x + 40.0
                py = self.cena.jogador.y
                self._spawnar_item_ou_inimigo_no_mundo(px, py)
        elif self.indice_foco == 8:  # Curar Vida Completa
            if self.cena and hasattr(self.cena, "jogador") and self.cena.jogador:
                self.cena.jogador.hp = self.cena.jogador.hp_max
                self._definir_status("VIDA RESTAURADA AO MAXIMO!")
        elif self.indice_foco == 9:  # Tomar Dano (1/8 HP)
            if self.cena and hasattr(self.cena, "jogador") and self.cena.jogador:
                dano = max(1, self.cena.jogador.hp_max // 8)
                self.cena.jogador.receber_dano(dano)
                self._definir_status(f"DANO RECEBIDO: -{dano} HP")
        elif self.indice_foco == 10:  # Subir Nível (+X)
            qtd = self.opcoes_level_up[self.idx_level_up]
            if self.cena and hasattr(self.cena, "jogador") and self.cena.jogador:
                sistema_xp = getattr(self.cena.jogador, "sistema_xp", None)
                if sistema_xp is not None:
                    for _ in range(qtd):
                        xp_req = getattr(sistema_xp, "xp_necessario", None)
                        if xp_req is None and hasattr(sistema_xp, "xp_para_proximo_nivel"):
                            xp_req = sistema_xp.xp_para_proximo_nivel()
                        xp_req = xp_req if xp_req is not None else 35
                        xp_faltante = max(1, xp_req - getattr(sistema_xp, "xp_atual", 0))
                        if hasattr(self.cena.jogador, "ganhar_xp"):
                            self.cena.jogador.ganhar_xp(xp_faltante)
                        elif hasattr(sistema_xp, "adicionar_xp"):
                            sistema_xp.adicionar_xp(xp_faltante)
                self.fechar()
                self._definir_status(f"LEVEL UP (+{qtd}) ATIVADO!")
        elif self.indice_foco == 11:  # Desbloquear Todas Configurações
            config_sys = getattr(self.cena, "config_sistema", None) or getattr(self.cena, "gerenciador_config", None)
            if config_sys is not None:
                from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
                for cid in CONFIGURACOES_GAMEPLAY.keys():
                    config_sys.desbloquear_config(cid)
                if hasattr(config_sys, "salvar_progresso"):
                    config_sys.salvar_progresso()
                self._definir_status("TODAS AS 20 CONFIGS DESBLOQUEADAS!")

    def _spawnar_item_ou_inimigo_no_mundo(self, x: float, y: float):
        """Gera a entidade selecionada com o CENTRO posicionado exatamente nas coordenadas (x, y)."""
        if not self.cena:
            return

        if self.indice_foco == 4:  # Spawn Categoria Drop
            nome_d, tipo_d, val_d = self.opcoes_tipo_drop[self.idx_tipo_drop]
            from src.utils.constantes import DROP_LARGURA, DROP_ALTURA, DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR
            drop = ItemDrop(
                x=x - float(DROP_LARGURA) / 2.0,
                y=y - float(DROP_ALTURA) / 2.0,
                tipo=tipo_d,
                valor=val_d,
                tempo_vida=DROP_TEMPO_DESAPARECER,
                tempo_scavenger=DROP_TEMPO_SCAVENGER_ATIVAR
            )
            if hasattr(self.cena, "sistema_drops") and hasattr(self.cena.sistema_drops, "drops"):
                self.cena.sistema_drops.drops.append(drop)
            elif hasattr(self.cena, "drops"):
                self.cena.drops.append(drop)
            self._definir_status(f"DROP SPAWNADO: {nome_d}")

        elif self.indice_foco == 5:  # Spawn Arma Específica
            nome_a, classe_str = self.opcoes_armas[self.idx_arma]
            from src.armas import (
                Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun
            )
            armas_map = {
                "Minigun": Minigun,
                "Shotgun": Shotgun,
                "RifleAssalto": RifleAssalto,
                "LancaFoguetes": LancaFoguetes,
                "LancaGranadas": LancaGranadas,
                "Railgun": Railgun
            }
            if classe_str in armas_map and hasattr(self.cena, "jogador") and self.cena.jogador:
                nova_arma = armas_map[classe_str]()
                self.cena.jogador.arma_especial = nova_arma
                if hasattr(self.cena.jogador, "selecionar_slot"):
                    self.cena.jogador.selecionar_slot(3)
                elif hasattr(self.cena.jogador, "slot_ativo"):
                    self.cena.jogador.slot_ativo = 3
                self._definir_status(f"ARMA EQUIPADA: {nome_a}")

        elif self.indice_foco == 6:  # Spawn Drone Específico
            nome_dr, classe_str = self.opcoes_drones[self.idx_drone]
            from src.equipamentos import DroneCura, DroneCombate, DroneSuporte
            drones_map = {
                "DroneCura": DroneCura,
                "DroneCombate": DroneCombate,
                "DroneSuporte": DroneSuporte
            }
            if classe_str in drones_map and hasattr(self.cena, "jogador") and self.cena.jogador:
                novo_drone = drones_map[classe_str](tempo_vida=30.0)
                if hasattr(self.cena.jogador, "adicionar_drone"):
                    self.cena.jogador.adicionar_drone(novo_drone)
                elif hasattr(self.cena.jogador, "drone"):
                    self.cena.jogador.drone = novo_drone
                self._definir_status(f"DRONE ATIVADO: {nome_dr}")

        elif self.indice_foco == 7:  # Spawn Inimigo (Centro alinhado com o clique)
            nome_i, tipo_i = self.opcoes_inimigos[self.idx_inimigo]
            from src.entidades import (
                InimigoPadrao, InimigoRapido, InimigoPhasing,
                InimigoBlindado, InimigoRanged, InimigoTank
            )
            inimigo = None
            if tipo_i == "padrao":
                inimigo = InimigoPadrao(x=x, y=y)
            elif tipo_i == "rapido":
                inimigo = InimigoRapido(x=x, y=y)
            elif tipo_i == "phasing":
                inimigo = InimigoPhasing(x=x, y=y)
            elif tipo_i == "blindado":
                inimigo = InimigoBlindado(x=x, y=y)
            elif tipo_i == "ranged":
                inimigo = InimigoRanged(x=x, y=y)
            elif tipo_i == "tank":
                inimigo = InimigoTank(x=x, y=y)
            elif tipo_i == "elite":
                inimigo = InimigoPadrao(x=x, y=y, is_elite=True, nome_elite="CHEFE DE ELITE (DEBUG)")
                inimigo.hp_max = 120
                inimigo.hp = 120
                inimigo.score_valor = 500

            if inimigo is not None and hasattr(self.cena, "inimigos"):
                # Posiciona o CENTRO do inimigo exatamente nas coordenadas do clique
                inimigo.x = x - getattr(inimigo, "largura", 28) / 2.0
                inimigo.y = y - getattr(inimigo, "altura", 28) / 2.0
                self.cena.inimigos.append(inimigo)
                self._definir_status(f"INIMIGO SPAWNADO: {nome_i}")

    def _definir_status(self, texto: str):
        self._mensagem_status = str(texto)
        self._timer_status = 2.5

    def draw(self, screen: pygame.Surface):
        """Renderiza o HUD do console de debug e mira de spawn do mouse."""
        if not self.ativo or screen is None:
            return

        self._inicializar_fontes()

        # 1. Fundo Escuro do Painel Translúcido
        painel_surf = pygame.Surface((self.rect_painel.width, self.rect_painel.height), pygame.SRCALPHA)
        painel_surf.fill((12, 10, 22, 235))
        screen.blit(painel_surf, (self.rect_painel.x, self.rect_painel.y))
        pygame.draw.rect(screen, ROXO_ACENTO, self.rect_painel, width=2, border_radius=6)

        # 2. Cabeçalho do Console
        tit_surf = self._fonte_tit.render("CONSOLE DEBUG (F1 / ~)", True, DOURADO)
        screen.blit(tit_surf, (self.rect_painel.x + 12, self.rect_painel.y + 12))
        pygame.draw.line(screen, (80, 60, 120), (self.rect_painel.x + 10, self.rect_painel.y + 32), (self.rect_painel.right - 10, self.rect_painel.y + 32), 1)

        # 3. Lista de Itens e Toggles
        y_cursor = self.rect_painel.y + 40
        itens_config = [
            ("1. Spawn Natural", "LIGADO" if self.spawn_natural_ativo else "DESLIGADO", VERDE_CURA if self.spawn_natural_ativo else VERMELHO_DANO),
            ("2. Congelar Timer", "LIGADO" if self.timer_congelado else "DESLIGADO", LARANJA_ALERTA if self.timer_congelado else CINZA_TEXTO),
            ("3. Municao Infinita", "LIGADO" if self.municao_infinita else "DESLIGADO", DOURADO if self.municao_infinita else CINZA_TEXTO),
            ("4. Modo Deus (HP Inf)", "LIGADO" if self.modo_deus else "DESLIGADO", DOURADO if self.modo_deus else CINZA_TEXTO),
            ("5. Spawn Drop", f"< {self.opcoes_tipo_drop[self.idx_tipo_drop][0]} >", ROXO_CLARO),
            ("6. Equipar Arma", f"< {self.opcoes_armas[self.idx_arma][0]} >", ROXO_CLARO),
            ("7. Ativar Drone", f"< {self.opcoes_drones[self.idx_drone][0]} >", ROXO_CLARO),
            ("8. Spawn Inimigo", f"< {self.opcoes_inimigos[self.idx_inimigo][0]} >", ROXO_CLARO),
            ("9. Curar Vida Max", "[ENTER PARA CURAR]", VERDE_CURA),
            ("10. Tomar Dano 1/8", "[ENTER PARA DANO]", VERMELHO_DANO),
            ("11. Level Up (+X)", f"< +{self.opcoes_level_up[self.idx_level_up]} Nivel >", DOURADO),
            ("12. Destravar Configs", "[ENTER DESTRAVA 20]", DOURADO)
        ]

        for i, (label, val_txt, val_cor) in enumerate(itens_config):
            is_focado = (i == self.indice_foco)
            item_rect = pygame.Rect(self.rect_painel.x + 8, y_cursor - 2, self.rect_painel.width - 16, 22)

            if is_focado:
                pygame.draw.rect(screen, (55, 35, 80), item_rect, border_radius=4)
                pygame.draw.rect(screen, DOURADO, item_rect, width=1, border_radius=4)
                marcador = self._fonte_item.render(">", True, DOURADO)
                screen.blit(marcador, (item_rect.x + 4, y_cursor + 2))

            cor_lbl = DOURADO if is_focado else BRANCO
            lbl_surf = self._fonte_item.render(label, True, cor_lbl)
            screen.blit(lbl_surf, (item_rect.x + 16, y_cursor + 2))

            val_surf = self._fonte_val.render(val_txt, True, val_cor if not is_focado else DOURADO)
            val_rect = val_surf.get_rect(right=item_rect.right - 6, centery=item_rect.centery)
            screen.blit(val_surf, val_rect)

            y_cursor += 24

        # 4. Mensagem de Feedback / Status
        pygame.draw.line(screen, (80, 60, 120), (self.rect_painel.x + 10, y_cursor + 4), (self.rect_painel.right - 10, y_cursor + 4), 1)
        y_cursor += 12

        if self._mensagem_status:
            status_surf = self._fonte_hint.render(self._mensagem_status, True, DOURADO)
            screen.blit(status_surf, (self.rect_painel.x + 12, y_cursor))
        else:
            hint_txt = "SETAS: Navegar | ENTER: Acao | CLIQUE: Spawn"
            hint_surf = self._fonte_hint.render(hint_txt, True, CINZA_TEXTO)
            screen.blit(hint_surf, (self.rect_painel.x + 12, y_cursor))

        # 5. Mira Visual no Cursor do Mouse para Spawn no Mundo
        mx, my = pygame.mouse.get_pos() if pygame.mouse.get_focused() else (400, 300)
        if not self.rect_painel.collidepoint(mx, my):
            # Desenha retículo de mira
            pygame.draw.circle(screen, DOURADO, (mx, my), 10, width=1)
            pygame.draw.line(screen, DOURADO, (mx - 14, my), (mx + 14, my), 1)
            pygame.draw.line(screen, DOURADO, (mx, my - 14), (mx, my + 14), 1)
            # Texto da entidade que será gerada
            entidade_spawn_label = ""
            if self.indice_foco == 4:
                entidade_spawn_label = f"Spawn: {self.opcoes_tipo_drop[self.idx_tipo_drop][0]}"
            elif self.indice_foco == 5:
                entidade_spawn_label = f"Equipar: {self.opcoes_armas[self.idx_arma][0]}"
            elif self.indice_foco == 6:
                entidade_spawn_label = f"Drone: {self.opcoes_drones[self.idx_drone][0]}"
            elif self.indice_foco == 7:
                entidade_spawn_label = f"Spawn: {self.opcoes_inimigos[self.idx_inimigo][0]}"

            if entidade_spawn_label:
                mira_txt = self._fonte_hint.render(entidade_spawn_label, True, DOURADO)
                screen.blit(mira_txt, (mx + 14, my - 8))