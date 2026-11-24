"""
Menu de Debug / Console de Desenvolvedor — Protocolo: Batata
Painel de depuração em tempo real acionado por F1 / ~ com navegação por teclado
e geração de entidades (drops e inimigos) via clique do mouse no mundo do jogo.
"""

import math
import os
import pygame
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    ROXO_ACENTO, ROXO_CLARO, ROXO_ESCURO,
    DOURADO, VERDE_CURA, VERMELHO_DANO, LARANJA_ALERTA, BRANCO, CINZA_TEXTO,
    DROP_TEMPO_DESAPARECER, DROP_TEMPO_SCAVENGER_ATIVAR, DROP_CURA_VALOR_BASE
)
from src.entidades.drop import ItemDrop

_FONT_CACHE: dict[tuple[int, bool], pygame.font.Font] = {}


def _obter_fonte_debug(tamanho: int, bold: bool = False) -> pygame.font.Font:
    px_sz = max(8, int(tamanho))
    chave = (px_sz, bold)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in ("jetbrainsmono", "firacode", "consolas", "dejavusansmono"):
        f = pygame.font.SysFont(nome, px_sz, bold=bold)
        if f is not None:
            _FONT_CACHE[chave] = f
            return f
    f = pygame.font.SysFont("consolas", px_sz, bold=bold)
    _FONT_CACHE[chave] = f
    return f


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
            ("Caixa Equipamento", "equipamento", 1),
            ("Núcleo Overclock", "overclock", 1)
        ]
        self.idx_tipo_drop = 0

        self.opcoes_armas = [
            ("Minigun", "Minigun"),
            ("Shotgun", "Shotgun"),
            ("Rifle Assalto", "RifleAssalto"),
            ("Lanca-Foguetes", "LancaFoguetes"),
            ("Lanca-Granadas", "LancaGranadas"),
            ("Railgun", "Railgun"),
            ("Bastao de Choque", "BastaoChoque"),
            ("SMG Compacta", "SMGCompacta"),
            ("Rifle de Arco", "RifleArco"),
            ("Lanca-Chamas", "LancaChamas"),
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
            ("Impressora Termica", "impressora"),
            ("Ninja Corporativo", "ninja"),
            ("Chefe de Elite", "elite"),
            ("Geladeira Tsunami (Boss)", "boss")
        ]
        self.idx_inimigo = 0

        self.opcoes_level_up = [1, 3, 5, 10]
        self.idx_level_up = 0

        self.opcoes_overclock = [
            ("Multithreading", "multithreading"),
            ("Refrigeração", "refrigeracao"),
            ("Overvolt", "overvolt"),
            ("BIOS Modding", "bios_modding"),
            ("Proteção Surtos", "protecao_surtos"),
            ("Upgrade Barramento", "upgrade_barramento")
        ]
        self.idx_overclock = 0

        self.opcoes_pular_tempo = [10, 20, 30]
        self.idx_pular_tempo = 0

        self.opcoes_fases_musica = [
            ("ANTICIPATION", "anticipation"),
            ("HOLD", "hold"),
            ("ASSAULT_INTRO", "assault_intro"),
            ("ASSAULT", "assault"),
        ]
        self.idx_fase_musica = 0

        # Índice do menu focado
        self.indice_foco = 0
        self.total_itens = 18

        # Retângulo do painel de Debug centralizado / com offset adaptado para 1280x720
        self.offset_x = (LARGURA_TELA - 800) // 2
        self.offset_y = (ALTURA_TELA - 600) // 2
        self.rect_painel = pygame.Rect(self.offset_x + 16, self.offset_y + 16, 340, 560)
        self._painel_surf = pygame.Surface((self.rect_painel.width, self.rect_painel.height), pygame.SRCALPHA)
        self._painel_surf.fill((12, 10, 22, 235))
        self._tecla_f1_anterior = False
        self._tecla_tilde_anterior = False
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

        # Checa tecla de atalho F1 ou ~ (crase / tilde) para abrir/fechar com edge-trigger
        tecla_f1_atual = False
        tecla_tilde_atual = False

        if teclado is not None:
            if hasattr(teclado, "key_down"):
                if teclado.key_down("F1"):
                    tecla_f1_atual = True
                if teclado.key_down("`") or teclado.key_down("~"):
                    tecla_tilde_atual = True
            if hasattr(teclado, "key_pressed"):
                if teclado.key_pressed("F1"):
                    tecla_f1_atual = True
                if teclado.key_pressed("`") or teclado.key_pressed("~") or teclado.key_pressed("GRAVE"):
                    tecla_tilde_atual = True

        # Checagem direta via Pygame para redundância
        chaves_pressionadas = pygame.key.get_pressed()
        if chaves_pressionadas[pygame.K_F1]:
            tecla_f1_atual = True
        if chaves_pressionadas[pygame.K_BACKQUOTE]:
            tecla_tilde_atual = True

        f1_edge = tecla_f1_atual and not self._tecla_f1_anterior
        tilde_edge = tecla_tilde_atual and not self._tecla_tilde_anterior
        self._tecla_f1_anterior = tecla_f1_atual
        self._tecla_tilde_anterior = tecla_tilde_atual

        if (f1_edge or tilde_edge) and self.cooldown_input <= 0.0:
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
            if self.cena and getattr(self.cena, "mouse", None):
                try:
                    mx, my = self.cena.mouse.get_position()
                except Exception:
                    mx, my = pygame.mouse.get_pos() if pygame.mouse.get_focused() else (400, 300)
            elif mouse is not None and hasattr(mouse, "get_position"):
                try:
                    mx, my = mouse.get_position()
                except Exception:
                    mx, my = pygame.mouse.get_pos() if pygame.mouse.get_focused() else (400, 300)
            else:
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
                    else:
                        if self.indice_foco in (0, 1, 2, 3):
                            self._alterar_opcao(-1)
                        elif self.indice_foco in (4, 5, 6, 7):
                            self._alterar_opcao(-1)
                        elif self.indice_foco in (8, 9, 10, 11, 12, 14):
                            self._executar_acao_selecionada()
                        elif self.indice_foco == 13:
                            self._alterar_opcao(-1)
                    self.cooldown_input = 0.20
            else:
                # Clique fora do painel: gera spawn nas coordenadas do mundo do jogo
                cam_x = getattr(self.cena.camera, "x", 0.0) if (self.cena and hasattr(self.cena, "camera")) else 0.0
                cam_y = getattr(self.cena.camera, "y", 0.0) if (self.cena and hasattr(self.cena, "camera")) else 0.0
                largura_arena = getattr(self.cena, "largura_arena", LARGURA_ARENA)
                altura_arena = getattr(self.cena, "altura_arena", ALTURA_ARENA)
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
        elif self.indice_foco == 13:  # Overclock
            self.idx_overclock = (self.idx_overclock + direcao) % len(self.opcoes_overclock)
        elif self.indice_foco == 15:  # Pular Tempo + Kit Debug
            self.idx_pular_tempo = (self.idx_pular_tempo + direcao) % len(self.opcoes_pular_tempo)
        elif self.indice_foco == 16:  # Fase Música-Onda
            self.idx_fase_musica = (self.idx_fase_musica + direcao) % len(self.opcoes_fases_musica)

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
                sys_conq = getattr(config_sys, "sistema_conquistas", None) or getattr(self.cena, "sistema_conquistas", None)
                if sys_conq is not None and hasattr(sys_conq, "recompensas"):
                    sys_conq.recompensas.setdefault("configuracao", set()).add("latencia_ping")
                self._definir_status(f"TODAS AS {len(CONFIGURACOES_GAMEPLAY)} CONFIGS DESBLOQUEADAS!")
        elif self.indice_foco == 12:  # Boss Cutscene
            if self.cena and hasattr(self.cena, "iniciar_boss_cutscene"):
                self.fechar()
                self.cena.iniciar_boss_cutscene()
                self._definir_status("BOSS CUTSCENE INICIADA!")
        elif self.indice_foco == 13:  # Conceder Overclock
            nome_ov, id_ov = self.opcoes_overclock[self.idx_overclock]
            if self.cena and hasattr(self.cena, "jogador") and self.cena.jogador:
                self.cena.jogador.aplicar_overclock(id_ov)
                if hasattr(self.cena, "aplicar_modificadores"):
                    self.cena.aplicar_modificadores()
                self._definir_status(f"OVERCLOCK CONCEDIDO: {nome_ov}")
        elif self.indice_foco == 14:  # Matar Chefe
            if self.cena and hasattr(self.cena, "chefe_final") and self.cena.chefe_final:
                chefe = self.cena.chefe_final
                if getattr(chefe, "estado", None) == "intro":
                    chefe.intro_concluida = True
                chefe.receber_dano(chefe.hp + 9999)
                if hasattr(self.cena, "_registrar_abate_inimigo"):
                    self.cena._registrar_abate_inimigo(chefe)
                self._definir_status("GELADEIRA TSUNAMI DESTRUÍDA!")
            elif self.cena and hasattr(self.cena, "inimigos"):
                for inim in self.cena.inimigos:
                    if getattr(inim, "is_elite", False):
                        inim.receber_dano(inim.hp + 999)
                        if hasattr(self.cena, "_registrar_abate_inimigo"):
                            self.cena._registrar_abate_inimigo(inim)
                self._definir_status("MINI-BOSSES DESTRUÍDOS!")
        elif self.indice_foco == 15:  # Pular Tempo + Kit Debug
            self._aplicar_kit_debug()
        elif self.indice_foco == 16:  # Forçar Fase Música-Onda
            nome_fase, estado_fase = self.opcoes_fases_musica[self.idx_fase_musica]
            sys_mus = getattr(self.cena, "sistema_musica", None) if self.cena else None
            if sys_mus is None:
                try:
                    from src.sistemas.sistema_musica import obter_sistema_musica
                    sys_mus = obter_sistema_musica()
                except Exception:
                    sys_mus = None
            if sys_mus is not None:
                loops = -1 if estado_fase in ("hold", "assault") else 0
                if hasattr(sys_mus, "_tocar_par_estado"):
                    sys_mus._tocar_par_estado(estado_fase, loops=loops)
                else:
                    sys_mus.estado = estado_fase
                self._definir_status(f"MUSICA-ONDA: {nome_fase}")
        elif self.indice_foco == 17:  # Desbloquear Todas Conquistas & Firmware
            sys_conq = getattr(self.cena, "sistema_conquistas", None) if self.cena else None
            if sys_conq is None and self.cena:
                cfg = getattr(self.cena, "config_sistema", None) or getattr(self.cena, "gerenciador_config", None)
                sys_conq = getattr(cfg, "sistema_conquistas", None) if cfg is not None else None
            if sys_conq is not None:
                from src.sistemas.conquistas_dados import (
                    CHIPS_FIRMWARE,
                    CONQUISTAS_CONTINUAS,
                    CONQUISTAS_UNICAS,
                )
                for cid, cdef in CONQUISTAS_CONTINUAS.items():
                    max_meta = cdef.milestones[-1].meta if cdef.milestones else 999
                    sys_conq.continuas[cid] = {
                        "valor": max_meta,
                        "milestones_concluidos": list(range(len(cdef.milestones))),
                    }
                    for ms in cdef.milestones:
                        if hasattr(sys_conq, "_conceder_recompensas"):
                            sys_conq._conceder_recompensas(ms.recompensas)
                for cid, cdef in CONQUISTAS_UNICAS.items():
                    sys_conq.unicas_concluidas.add(cid)
                    if hasattr(sys_conq, "_conceder_recompensas"):
                        sys_conq._conceder_recompensas(cdef.recompensas)
                if hasattr(sys_conq, "recompensas"):
                    sys_conq.recompensas.setdefault("modificador_run", set()).update(CHIPS_FIRMWARE.keys())
                sys_conq.slots_firmware_max = 3
                self._definir_status("CONQUISTAS & FIRMWARE DESBLOQUEADOS!")

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
                Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun,
                BastaoChoque, SMGCompacta, RifleArco, LancaChamas,
            )
            jog = getattr(self.cena, "jogador", None)
            if jog is not None:
                if classe_str == "BastaoChoque":
                    if hasattr(jog, "aplicar_loadout"):
                        jog.aplicar_loadout("bastao_choque", getattr(jog, "slot2_id", "pistola"))
                    elif hasattr(jog, "armas") and len(jog.armas) >= 1:
                        jog.armas[0] = BastaoChoque()
                    if hasattr(jog, "selecionar_slot"):
                        jog.selecionar_slot(1)
                    self._definir_status(f"ARMA EQUIPADA: {nome_a}")
                elif classe_str == "SMGCompacta":
                    if hasattr(jog, "aplicar_loadout"):
                        jog.aplicar_loadout(getattr(jog, "slot1_id", "chave_manutencao"), "smg_compacta")
                    elif hasattr(jog, "armas") and len(jog.armas) >= 2:
                        jog.armas[1] = SMGCompacta()
                    if hasattr(jog, "selecionar_slot"):
                        jog.selecionar_slot(2)
                    self._definir_status(f"ARMA EQUIPADA: {nome_a}")
                else:
                    armas_map = {
                        "Minigun": Minigun,
                        "Shotgun": Shotgun,
                        "RifleAssalto": RifleAssalto,
                        "LancaFoguetes": LancaFoguetes,
                        "LancaGranadas": LancaGranadas,
                        "Railgun": Railgun,
                        "RifleArco": RifleArco,
                        "LancaChamas": LancaChamas,
                    }
                    if classe_str in armas_map:
                        nova_arma = armas_map[classe_str]()
                        if hasattr(jog, "equipar_arma_especial"):
                            jog.equipar_arma_especial(nova_arma)
                        else:
                            jog.arma_especial = nova_arma
                        if hasattr(jog, "selecionar_slot"):
                            jog.selecionar_slot(3)
                        elif hasattr(jog, "slot_ativo"):
                            jog.slot_ativo = 3
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
            from src.entidades.inimigo_impressora import InimigoImpressoraTermica
            from src.entidades.inimigo_ninja import InimigoNinja
            from src.entidades.geladeira_tsunami import GeladeiraTsunami
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
            elif tipo_i == "impressora":
                inimigo = InimigoImpressoraTermica(x=x, y=y)
            elif tipo_i == "ninja":
                inimigo = InimigoNinja(x=x, y=y)
            elif tipo_i == "elite":
                inimigo = InimigoPadrao(x=x, y=y, is_elite=True, nome_elite="CHEFE DE ELITE (DEBUG)")
                inimigo.hp_max = 120
                inimigo.hp = 120
                inimigo.score_valor = 500
            elif tipo_i == "boss":
                inimigo = GeladeiraTsunami(x=x - 56, y=y - 78)
                inimigo.estado = "fase1"
                inimigo.subestado_fase2 = "stalk"
                inimigo.intro_concluida = True
                if hasattr(self.cena, "chefe_final"):
                    self.cena.chefe_final = inimigo

            if inimigo is not None and hasattr(self.cena, "inimigos"):
                # Posiciona o CENTRO do inimigo exatamente nas coordenadas do clique
                if tipo_i != "boss":
                    inimigo.x = x - getattr(inimigo, "largura", 28) / 2.0
                    inimigo.y = y - getattr(inimigo, "altura", 28) / 2.0
                self.cena.inimigos.append(inimigo)
                self._definir_status(f"INIMIGO SPAWNADO: {nome_i}")

    def _aplicar_kit_debug(self):
        """Avança 10/20/30s, equipa arma especial (sem Railgun), aplica consumíveis e 1 mod de BIOS."""
        if not self.cena:
            return
        import random
        segs = float(self.opcoes_pular_tempo[self.idx_pular_tempo])
        if hasattr(self.cena, "tempo_sobrevivencia"):
            self.cena.tempo_sobrevivencia += segs
        if hasattr(self.cena, "spawner") and self.cena.spawner is not None:
            self.cena.spawner.tempo_decorrido += segs
            self.cena.spawner.tempo_elite += segs

        jog = getattr(self.cena, "jogador", None)
        if jog is not None:
            from src.armas import Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas
            arma_cls = random.choice([Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas])
            nova_arma = arma_cls()
            if hasattr(jog, "equipar_arma_especial"):
                jog.equipar_arma_especial(nova_arma)
            else:
                jog.arma_especial = nova_arma
                if hasattr(jog, "selecionar_slot"):
                    jog.selecionar_slot(3)

            jog.buff_dano_timer = 15.0
            jog.buff_vel_timer = 15.0
            jog.buff_cadencia_timer = 15.0
            jog.escudo_ativo = True

            adquiridos = getattr(jog, "overclocks_adquiridos", set())
            disponiveis = [cid for _, cid in self.opcoes_overclock if cid not in adquiridos]
            mod_id = random.choice(disponiveis) if disponiveis else self.opcoes_overclock[self.idx_overclock][1]
            if hasattr(jog, "aplicar_overclock"):
                jog.aplicar_overclock(mod_id)

            # Desbloqueia Dash / meta de parries para testes completos
            from src.utils.constantes import DASH_PARRY_META
            jog.dash_desbloqueado = True
            cfg = getattr(self.cena, "config_sistema", None) or getattr(self.cena, "gerenciador_config", None)
            if cfg is not None and hasattr(cfg, "estatisticas"):
                cfg.estatisticas["dash_desbloqueado"] = True
                cfg.estatisticas["parries_total"] = max(int(cfg.estatisticas.get("parries_total", 0)), int(DASH_PARRY_META))
                if hasattr(cfg, "salvar_arquivo"):
                    cfg.salvar_arquivo()

        if hasattr(self.cena, "aplicar_modificadores"):
            self.cena.aplicar_modificadores()
        self._definir_status(f"+{int(segs)}s + ARMA + CONSUMIVEIS + BIOS + DASH!")

    def _definir_status(self, texto: str):
        self._mensagem_status = str(texto)
        self._timer_status = 2.5

    def draw(self, screen: pygame.Surface):
        """Renderiza o HUD do console de debug e mira de spawn do mouse em DPI nativo."""
        if not self.ativo or screen is None:
            return

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

        fonte_tit = _obter_fonte_debug(max(8, int(round(14 * scale))), bold=True)
        fonte_item = _obter_fonte_debug(max(8, int(round(12 * scale))), bold=True)
        fonte_val = _obter_fonte_debug(max(8, int(round(12 * scale))), bold=False)
        fonte_hint = _obter_fonte_debug(max(8, int(round(11 * scale))), bold=False)

        painel_px = pygame.Rect(
            px(self.rect_painel.x),
            py(self.rect_painel.y),
            ps(self.rect_painel.width),
            ps(self.rect_painel.height),
        )
        if self._painel_surf.get_size() != (painel_px.width, painel_px.height):
            self._painel_surf = pygame.Surface((painel_px.width, painel_px.height), pygame.SRCALPHA)
            self._painel_surf.fill((11, 14, 23, 236))

        # 1. Fundo Escuro do Painel Translúcido
        screen.blit(self._painel_surf, painel_px.topleft)
        pygame.draw.rect(screen, (168, 85, 247), painel_px, width=max(1, ps(2)), border_radius=ps(8))

        # 2. Cabeçalho do Console
        tit_surf = fonte_tit.render("CONSOLE DEBUG (F1 / ~)", True, DOURADO)
        screen.blit(tit_surf, (painel_px.x + ps(12), painel_px.y + ps(12)))
        pygame.draw.line(
            screen,
            (51, 65, 85),
            (painel_px.x + ps(10), painel_px.y + ps(32)),
            (painel_px.right - ps(10), painel_px.y + ps(32)),
            max(1, ps(1)),
        )

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
            ("12. Destravar Configs", "[ENTER DESTRAVA 28]", DOURADO),
            ("13. Boss Cutscene (Lvl 20)", "[ENTER CUTSCENE]", DOURADO),
            ("14. Conceder Overclock", f"< {self.opcoes_overclock[self.idx_overclock][0]} >", ROXO_CLARO),
            ("15. Matar Chefe", "[ENTER PARA MATAR]", VERMELHO_DANO),
            ("16. Kit Debug (+Tempo)", f"< +{self.opcoes_pular_tempo[self.idx_pular_tempo]}s +Kit >", (34, 211, 238)),
            ("17. Fase Musica-Onda", f"< {self.opcoes_fases_musica[self.idx_fase_musica][0]} >", (168, 85, 247)),
            ("18. Destravar Conq/FW", "[ENTER DESTRAVA TUDO]", DOURADO),
        ]

        for i, (label, val_txt, val_cor) in enumerate(itens_config):
            is_focado = (i == self.indice_foco)
            item_rect = pygame.Rect(
                px(self.rect_painel.x + 8),
                py(y_cursor - 2),
                ps(self.rect_painel.width - 16),
                ps(22),
            )

            if is_focado:
                pygame.draw.rect(screen, (30, 41, 59), item_rect, border_radius=ps(4))
                pygame.draw.rect(screen, DOURADO, item_rect, width=max(1, ps(1)), border_radius=ps(4))
                marcador = fonte_item.render(">", True, DOURADO)
                screen.blit(marcador, (item_rect.x + ps(4), py(y_cursor + 2)))

            cor_lbl = DOURADO if is_focado else BRANCO
            lbl_surf = fonte_item.render(label, True, cor_lbl)
            screen.blit(lbl_surf, (item_rect.x + ps(16), py(y_cursor + 2)))

            val_surf = fonte_val.render(val_txt, True, val_cor if not is_focado else DOURADO)
            val_rect = val_surf.get_rect(right=item_rect.right - ps(6), centery=item_rect.centery)
            screen.blit(val_surf, val_rect)

            y_cursor += 24

        # 4. Mensagem de Feedback / Status
        pygame.draw.line(
            screen,
            (51, 65, 85),
            (painel_px.x + ps(10), py(y_cursor + 4)),
            (painel_px.right - ps(10), py(y_cursor + 4)),
            max(1, ps(1)),
        )
        y_cursor += 12

        if self._mensagem_status:
            status_surf = fonte_hint.render(self._mensagem_status, True, DOURADO)
            screen.blit(status_surf, (painel_px.x + ps(12), py(y_cursor)))
        else:
            hint_txt = "SETAS: Navegar | ENTER: Acao | CLIQUE: Spawn"
            hint_surf = fonte_hint.render(hint_txt, True, CINZA_TEXTO)
            screen.blit(hint_surf, (painel_px.x + ps(12), py(y_cursor)))

        # 5. Mira Visual no Cursor do Mouse para Spawn no Mundo (projetada em DPI nativo)
        if self.cena and getattr(self.cena, "mouse", None):
            try:
                mx, my = self.cena.mouse.get_position()
            except Exception:
                mx, my = pygame.mouse.get_pos() if pygame.mouse.get_focused() else (400, 300)
        else:
            mx, my = pygame.mouse.get_pos() if pygame.mouse.get_focused() else (400, 300)
        if not self.rect_painel.collidepoint(mx, my):
            smx, smy = px(mx), py(my)
            r_mira = ps(10)
            l_mira = ps(14)
            w_mira = max(1, ps(1))
            pygame.draw.circle(screen, DOURADO, (smx, smy), r_mira, width=w_mira)
            pygame.draw.line(screen, DOURADO, (smx - l_mira, smy), (smx + l_mira, smy), w_mira)
            pygame.draw.line(screen, DOURADO, (smx, smy - l_mira), (smx, smy + l_mira), w_mira)
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
                mira_txt = fonte_hint.render(entidade_spawn_label, True, DOURADO)
                screen.blit(mira_txt, (smx + ps(14), smy - ps(8)))