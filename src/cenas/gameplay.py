import math
import os
import random
import pygame
from src.cenas.base_scene import BaseScene
from src.entidades.jogador import Jogador
from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_particulas import SistemaParticulas
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.hud import HUD
from src.ui.modal_level_up import ModalLevelUp
from src.ui.menu_configs import MenuConfigs
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    BRANCO, PRETO, CINZA_FUNDO, CINZA_PAINEL, CINZA_BORDA,
    VERMELHO_HP, VERDE_CURA, AMARELO_XP, AZUL_CIANO, DOURADO,
    TEMPO_VITORIA,
    obter_caminho_asset, SAVE_FILE_PATH
)
from src.utils.math_utils import colisao_aabb, clamp, distancia


class GameplayScene(BaseScene):
    """
    Cena principal de combate e sobrevivência na arena.
    """
    _tile_piso = None
    _btn_gear_img = None
    _slot_inv_img = None

    def __init__(self):
        super().__init__()
        self.largura_arena = LARGURA_ARENA
        self.altura_arena = ALTURA_ARENA

        # Jogador posicionado no centro da arena
        self.jogador = Jogador(
            x=self.largura_arena / 2.0 - 16,
            y=self.altura_arena / 2.0 - 16
        )

        # Câmera 2D vinculada às dimensões virtuais
        self.camera = Camera(LARGURA_TELA, ALTURA_TELA)
        self.camera.set_world_bounds(self.largura_arena, self.altura_arena)

        # Sistema de Configurações e Modificadores
        self.gerenciador_config = GerenciadorConfiguracoes()
        self.gerenciador_config.carregar_arquivo(SAVE_FILE_PATH)
        self.modal_level_up = ModalLevelUp(self.gerenciador_config, self.jogador, cena=self)
        self.menu_configs = MenuConfigs(self.gerenciador_config, em_jogo=True, cena=self)

        # Registra callback de level-up no SistemaXP do jogador
        self.jogador.sistema_xp.registrar_callback_level_up(self._ao_subir_nivel)

        # Sistemas de combate, spawn, drops, partículas e progressão
        self.config_sistema = self.gerenciador_config
        self.spawner = SistemaSpawn(max_ativos=400)
        self.sistema_drops = SistemaDrops()
        self.sistema_scavenger = SistemaScavenger()
        self.sistema_particulas = SistemaParticulas()
        self.hud = HUD()

        from src.ui.menu_debug import MenuDebug
        self.menu_debug = MenuDebug(cena_gameplay=self)

        self.projeteis: list[Projetil] = []
        self.inimigos: list[InimigoBase] = []

        # Métricas de partida e condição de vitória
        self.tempo_sobrevivencia = 0.0
        self.abates = 0
        self.pontos = 0
        self.dano_total_causado = 0
        self.pausado = False
        self.game_over = False
        self.vitoria = False
        self.partida_registrada = False
        self.estatisticas_partida_resultado = {}

        # Toasts de itens coletados, Screen Shake e Efeitos
        self.toasts_coleta: list[dict] = []
        self._fonte_toast = None
        self.shake_intensidade: float = 0.0
        self.shake_timer: float = 0.0

        # Input buffer e efeitos visuais
        self.buffer_tiro = 0.0
        self.efeitos_melee: list[dict] = []

        # Aplica modificadores iniciais
        self.aplicar_modificadores()

        # Inicialização da trilha sonora em loop contínuo
        try:
            caminho_musica = obter_caminho_asset("musica_fase")
            if os.path.isfile(caminho_musica):
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(caminho_musica)
                    pygame.mixer.music.set_volume(0.4)
                    pygame.mixer.music.play(-1)
        except Exception:
            pass

    def aplicar_shake(self, intensidade: float, duracao: float):
        """Ativa tremor de tela se a configuração 5 'screen_shake' estiver ligada."""
        val_shake = self.gerenciador_config.obter_valor("screen_shake")
        if val_shake in (True, "Ligado", "ligado", "1"):
            self.shake_intensidade = max(self.shake_intensidade, float(intensidade))
            self.shake_timer = max(self.shake_timer, float(duracao))


    _icones_slots: dict = {}

    @classmethod
    def _obter_sprite_icone(cls, chave: str):
        if chave not in cls._icones_slots:
            caminho = obter_caminho_asset(chave)
            if caminho and os.path.isfile(caminho):
                try:
                    img = pygame.image.load(caminho).convert_alpha()
                    cls._icones_slots[chave] = pygame.transform.scale(img, (26, 26))
                except Exception:
                    cls._icones_slots[chave] = None
            else:
                cls._icones_slots[chave] = None
        return cls._icones_slots.get(chave)

    @classmethod
    def _carregar_assets_cenario(cls):
        if cls._tile_piso is None:
            try:
                caminho = obter_caminho_asset("tile_piso")
                if os.path.isfile(caminho):
                    cls._tile_piso = pygame.image.load(caminho).convert()
            except Exception:
                cls._tile_piso = None

        if cls._btn_gear_img is None:
            try:
                caminho = obter_caminho_asset("btn_gear")
                if os.path.isfile(caminho):
                    cls._btn_gear_img = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._btn_gear_img = None
                cls._btn_gear_img = None

        if cls._slot_inv_img is None:
            try:
                caminho = obter_caminho_asset("slot_inventario")
                if os.path.isfile(caminho):
                    cls._slot_inv_img = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._slot_inv_img = None

    def _ao_subir_nivel(self, novo_nivel: int):
        """Callback acionado pelo SistemaXP ao subir de nível."""
        self.modal_level_up.enfileirar_level_up(novo_nivel)
        self.pausado = True

    def aplicar_modificadores(self):
        """Aplica os modificadores matemáticos calculados às entidades ativas."""
        mods = self.gerenciador_config.obter_modificadores()
        # 1. Velocidade do jogador
        self.jogador.velocidade_atual = self.jogador.velocidade_base * mods.vel_jogador_mult

        # 2. Dano das armas do jogador
        for arma in self.jogador.armas:
            if not hasattr(arma, "_dano_original"):
                arma._dano_original = arma.dano
            arma.dano = int(round(arma._dano_original * mods.dano_armas_mult))
        if getattr(self.jogador, "arma_especial", None) is not None:
            if not hasattr(self.jogador.arma_especial, "_dano_original"):
                self.jogador.arma_especial._dano_original = self.jogador.arma_especial.dano
            self.jogador.arma_especial.dano = int(round(self.jogador.arma_especial._dano_original * mods.dano_armas_mult))

    def loop(self):
        dt = self.janela.delta_time()
        # Se dt for 0 ou excessivamente baixo (em testes headless ultra-rápidos), usa 1/60s
        if dt < 0.005:
            dt = 1.0 / 60.0
        # Clampa dt para evitar saltos quânticos em frames atípicos (máximo 100ms)
        dt = min(dt, 0.1)

        # 0. Se o Menu de Debug estiver ativo, processa seus inputs e congela o jogo
        if hasattr(self, "menu_debug"):
            self.menu_debug.update(dt, self.teclado, self.mouse)
            if self.menu_debug.ativo:
                self.pausado = True
                return
            elif not self.modal_level_up.ativo and not self.menu_configs.ativo and not self.game_over and not self.vitoria:
                self.pausado = False

        # Sincroniza estado de Modo Deus e Munição Infinita
        if hasattr(self, "menu_debug"):
            self.jogador.modo_deus = getattr(self.menu_debug, "modo_deus", False)
            if getattr(self.menu_debug, "municao_infinita", False) and self.jogador.arma_especial:
                self.jogador.arma_especial.municao_atual = self.jogador.arma_especial.municao_max

        # 1. Se o Modal de Level Up estiver ativo, processa seus inputs e congela o jogo
        if self.modal_level_up.ativo:
            self.modal_level_up.update(dt, self.teclado, self.mouse)
            if not self.modal_level_up.ativo and not self.menu_configs.ativo and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                self.pausado = False
            return

        # 2. Se o Menu de Configurações estiver ativo, processa seus inputs e congela o jogo
        if self.menu_configs.ativo:
            self.menu_configs.update(dt, self.teclado, self.mouse)
            if not self.menu_configs.ativo and not self.modal_level_up.ativo and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                self.pausado = False
            return

        # 3. Tecla 'C' para abrir o menu de configurações
        if (hasattr(self.teclado, "key_down") and (self.teclado.key_down("c") or self.teclado.key_down("C"))) or \
           (hasattr(self.teclado, "key_pressed") and (self.teclado.key_pressed("c") or self.teclado.key_pressed("C"))):
            self.menu_configs.abrir()
            self.pausado = True
            return

        # 4. Controle de Pausa / Menu via Teclado (ESC)
        if self.teclado.key_down("ESC"):
            if self.game_over or self.vitoria:
                self._voltar_menu()
                return
            else:
                if not self.pausado:
                    self.menu_configs.abrir()
                    self.pausado = True
                else:
                    self.pausado = False
                return

        # Comportamento no estado de Vitória
        if self.vitoria:
            if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE"):
                self._reiniciar_partida()
                return
            if self.teclado.key_down("m") or self.teclado.key_down("M"):
                self._voltar_menu()
                return
            return

        # Comportamento no estado de Game Over
        if self.game_over:
            if self.teclado.key_down("ENTER") or self.teclado.key_down("SPACE"):
                self._reiniciar_partida()
                return
            if self.teclado.key_down("m") or self.teclado.key_down("M"):
                self._voltar_menu()
                return
            return

        # Comportamento no estado Pausado
        if self.pausado:
            if self.teclado.key_down("m") or self.teclado.key_down("M"):
                self._voltar_menu()
            return

        # =========================================================================
        # 1. ATUALIZAÇÃO DO JOGADOR E INPUTS
        # =========================================================================
        timer_congelado = getattr(self.menu_debug, "timer_congelado", False) if hasattr(self, "menu_debug") else False
        if not timer_congelado:
            self.tempo_sobrevivencia += dt

        # Atualiza temporizador de Screen Shake
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            if self.shake_timer == 0.0:
                self.shake_intensidade = 0.0

        # Atualiza sistema de partículas
        self.sistema_particulas.update(dt)

        # Verificação da Condição de Vitória (600.0 segundos / 10 Minutos)
        if self.tempo_sobrevivencia >= TEMPO_VITORIA and self.jogador.vivo and not self.vitoria:
            self.vitoria = True
            self._acionar_vitoria()
            return

        # Atualiza e limpa toasts de coleta
        for t in self.toasts_coleta:
            t["tempo"] -= dt
            t["y"] -= 22.0 * dt
        self.toasts_coleta = [t for t in self.toasts_coleta if t["tempo"] > 0]

        self.jogador.processar_input(
            self.teclado,
            self.mouse,
            dt,
            limite_arena=(self.largura_arena, self.altura_arena)
        )
        tiros_drone = self.jogador.update(
            dt,
            drops=self.sistema_drops.drops,
            inimigos=self.inimigos
        )
        if tiros_drone:
            self.projeteis.extend(tiros_drone)

        # Atualiza a posição da câmera para seguir o jogador suavemente
        self.camera.follow(self.jogador, suavizacao=0.15)

        # =========================================================================
        # 2. DISPARO DE ARMAS (PISTOLA, MELEE E ESPECIAIS COM BUFFER DE INPUT)
        # =========================================================================
        centro_jogador_x = self.jogador.x + self.jogador.largura / 2.0
        centro_jogador_y = self.jogador.y + self.jogador.altura / 2.0

        # Posição virtual do cursor convertida para espaço do mundo
        try:
            mx, my = self.mouse.get_position()
        except Exception:
            mx, my = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)

        mouse_mundo_x = mx + self.camera.x
        mouse_mundo_y = my + self.camera.y

        # Detecta clique no botão de engrenagem (752, 16, 32x32)
        if self.mouse.button_down(1):
            if 752 <= mx <= 784 and 16 <= my <= 48:
                self.menu_configs.abrir()
                self.pausado = True
                return

        # Input buffer: se o mouse estiver pressionado neste frame, alimenta o buffer
        mouse_pressionado = pygame.mouse.get_pressed()[0]
        if mouse_pressionado:
            self.buffer_tiro = 0.15  # Buffer de 150ms para garantir que cliques rápidos nunca sejam perdidos
        else:
            self.buffer_tiro = max(0.0, self.buffer_tiro - dt)

        disparar_agora = (self.buffer_tiro > 0.0)

        if disparar_agora and self.jogador.vivo:
            arma_ativa = self.jogador.obter_arma_ativa()
            if arma_ativa is not None:
                if isinstance(arma_ativa, Pistola) or getattr(arma_ativa, "slot", None) == 2:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        novos_tiros = arma_ativa.disparar(
                            centro_jogador_x, centro_jogador_y,
                            mouse_mundo_x, mouse_mundo_y
                        )
                        if novos_tiros:
                            self.projeteis.extend(novos_tiros)
                            self.buffer_tiro = 0.0
                elif isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        ang_mira = math.atan2(mouse_mundo_y - centro_jogador_y, mouse_mundo_x - centro_jogador_x)
                        afetados = arma_ativa.executar_ataque(
                            centro_jogador_x, centro_jogador_y,
                            self.inimigos,
                            mira_x=mouse_mundo_x,
                            mira_y=mouse_mundo_y,
                            angulo_mira=ang_mira
                        )
                        if isinstance(afetados, (list, tuple)):
                            for inim in afetados:
                                dano_melee = getattr(arma_ativa, "dano", 10)
                                self.dano_total_causado += dano_melee
                                self.sistema_particulas.emitir_faiscas(
                                    inim.x + getattr(inim, "largura", 28) / 2.0,
                                    inim.y + getattr(inim, "altura", 28) / 2.0,
                                    dir_x=math.cos(ang_mira),
                                    dir_y=math.sin(ang_mira),
                                    cor=(255, 240, 150),
                                    qtd=5
                                )
                                if not getattr(inim, "vivo", True):
                                    self.abates += 1
                                    self.pontos += getattr(inim, "score_valor", 100)
                                    if getattr(inim, "is_elite", False):
                                        self.aplicar_shake(14.0, 0.35)
                                        self.sistema_particulas.emitir_debris(inim.x + 14, inim.y + 14, cor=(255, 215, 0), qtd=16)
                                    self.sistema_drops.gerar_drop_morte_inimigo(
                                        inim.x + getattr(inim, "largura", 28) / 2.0,
                                        inim.y + getattr(inim, "altura", 28) / 2.0,
                                        xp_base=getattr(inim, "xp_valor", 5),
                                        is_elite=getattr(inim, "is_elite", False)
                                    )
                        self.buffer_tiro = 0.0
                        self.efeitos_melee.append({
                            "x": centro_jogador_x,
                            "y": centro_jogador_y,
                            "angulo": ang_mira,
                            "alcance": getattr(arma_ativa, "alcance", 84.0),
                            "arco_graus": getattr(arma_ativa, "arco_graus", 45.0),
                            "tempo": 0.15,
                            "tempo_total": 0.15
                        })
                else:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        if hasattr(arma_ativa, "disparar"):
                            novos_tiros = arma_ativa.disparar(
                                centro_jogador_x, centro_jogador_y,
                                mouse_mundo_x, mouse_mundo_y
                            )
                            if novos_tiros:
                                self.projeteis.extend(novos_tiros)
                                self.buffer_tiro = 0.0

        # Atualiza o tempo de vida dos efeitos visuais de Melee
        for ef in self.efeitos_melee:
            ef["tempo"] -= dt
        self.efeitos_melee = [ef for ef in self.efeitos_melee if ef["tempo"] > 0]

        # =========================================================================
        # 3. SPAWNER DE INIMIGOS
        # =========================================================================
        spawn_liberado = getattr(self.menu_debug, "spawn_natural_ativo", True) if hasattr(self, "menu_debug") else True
        if spawn_liberado:
            novos_inimigos = self.spawner.update(
                dt=dt,
                camera_x=self.camera.x,
                camera_y=self.camera.y,
                total_inimigos_vivos=len(self.inimigos),
                view_w=LARGURA_TELA,
                view_h=ALTURA_TELA,
                arena_w=self.largura_arena,
                arena_h=self.altura_arena
            )
            self.inimigos.extend(novos_inimigos)

        # =========================================================================
        # 4. FÍSICA DOS PROJÉTEIS
        # =========================================================================
        for proj in self.projeteis:
            proj.update(dt)
            # Desativa projéteis que saíram muito longe dos limites da arena
            if (proj.x < -100 or proj.x > self.largura_arena + 100 or
                proj.y < -100 or proj.y > self.altura_arena + 100):
                proj.ativo = False

        # =========================================================================
        # 5. IA DOS INIMIGOS E DANO DE CONTATO NO JOGADOR
        # =========================================================================
        for inimigo in self.inimigos:
            inimigo.update(dt, (centro_jogador_x, centro_jogador_y))
            if hasattr(inimigo, "obter_projeteis_pendentes"):
                novos_tiros = inimigo.obter_projeteis_pendentes()
                if novos_tiros:
                    self.projeteis.extend(novos_tiros)
            if inimigo.tentar_causar_dano_contato(self.jogador):
                self.aplicar_shake(6.0, 0.15)

        # =========================================================================
        # 6. COLISÕES: PROJÉTEIS VS INIMIGOS E DETONAÇÃO DE EXPLOSIVOS
        # =========================================================================
        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None
        mult_explosivo = getattr(mods, "dano_explosivos_mult", 1.0) if mods else 1.0
        auto_dano = getattr(mods, "auto_dano", False) if mods else False

        for proj in self.projeteis:
            if not proj.ativo:
                continue

            # Projéteis de inimigos causam dano ao jogador
            if getattr(proj, "dono", "jogador") == "inimigo":
                if getattr(self.jogador, "vivo", True) and colisao_aabb(
                    proj.x, proj.y, proj.largura, proj.altura,
                    self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura
                ):
                    self.jogador.receber_dano(proj.dano)
                    self.aplicar_shake(6.0, 0.15)
                    proj.ativo = False
                continue

            if getattr(proj, "explosivo", False):
                alvo_direto = None
                detonar = False
                p_cx = proj.x + proj.largura / 2.0
                p_cy = proj.y + proj.altura / 2.0
                r_exp = getattr(proj, "raio_explosao", 80.0)

                for inimigo in self.inimigos:
                    if not inimigo.vivo or getattr(inimigo, "em_fase", False):
                        continue
                    if colisao_aabb(
                        proj.x, proj.y, proj.largura, proj.altura,
                        inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                    ):
                        alvo_direto = inimigo
                        detonar = True
                        break

                if detonar or proj.tempo_vida_restante <= 0.0:
                    proj.ativo = False
                    self.sistema_particulas.emitir_onda_choque(p_cx, p_cy, raio_max=r_exp)
                    self.sistema_particulas.emitir_debris(p_cx, p_cy, cor=(255, 140, 40), qtd=12)
                    self.aplicar_shake(10.0, 0.25)
                    afetados = proj.explodir(
                        self.inimigos,
                        jogador=self.jogador,
                        config_sistema=self.config_sistema,
                        mult_dano_explosivo=mult_explosivo,
                        alvo_direto=alvo_direto
                    )
                    for inim in afetados:
                        dano_base_exp = int(getattr(proj, "dano", 35) * mult_explosivo)
                        dano_exp = dano_base_exp * 2 if (inim is alvo_direto) else dano_base_exp
                        self.dano_total_causado += dano_exp
                        if not inim.vivo:
                            self.abates += 1
                            self.pontos += getattr(inim, "score_valor", 100)
                            if getattr(inim, "is_elite", False):
                                self.aplicar_shake(14.0, 0.35)
                                self.sistema_particulas.emitir_debris(inim.x + 14, inim.y + 14, cor=(255, 215, 0), qtd=16)
                            self.sistema_drops.gerar_drop_morte_inimigo(
                                inim.x + getattr(inim, "largura", 28) / 2.0,
                                inim.y + getattr(inim, "altura", 28) / 2.0,
                                xp_base=getattr(inim, "xp_valor", 5),
                                loot_enriquecido=(getattr(inim, "loot_enriquecido", False) or getattr(mods, "loot_enriquecido", False)),
                                chance_arma=getattr(inim, "chance_drop_arma", None),
                                chance_equipamento=getattr(inim, "chance_drop_equipamento", None),
                                is_elite=getattr(inim, "is_elite", False)
                            )
            else:
                for inimigo in self.inimigos:
                    if not inimigo.vivo:
                        continue

                    if colisao_aabb(
                        proj.x, proj.y, proj.largura, proj.altura,
                        inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                    ):
                        if getattr(inimigo, "em_fase", False):
                            continue

                        if getattr(proj, "perfurante", False):
                            if not hasattr(proj, "alvos_atingidos"):
                                proj.alvos_atingidos = set()
                            if id(inimigo) in proj.alvos_atingidos:
                                continue
                            proj.alvos_atingidos.add(id(inimigo))
                        else:
                            proj.ativo = False

                        self.dano_total_causado += proj.dano
                        self.sistema_particulas.emitir_faiscas(
                            proj.x, proj.y,
                            dir_x=getattr(proj, "dir_x", 0.0),
                            dir_y=getattr(proj, "dir_y", 0.0),
                            cor=(255, 220, 100),
                            qtd=6
                        )

                        inimigo.receber_dano(
                            proj.dano,
                            origem_x=proj.x,
                            origem_y=proj.y,
                            dir_ataque=(getattr(proj, "dir_x", 0.0), getattr(proj, "dir_y", 0.0))
                        )

                        if not inimigo.vivo:
                            self.abates += 1
                            self.pontos += getattr(inimigo, "score_valor", 100)
                            if getattr(inimigo, "is_elite", False):
                                self.aplicar_shake(14.0, 0.35)
                                self.sistema_particulas.emitir_debris(inimigo.x + 14, inimigo.y + 14, cor=(255, 215, 0), qtd=16)
                            self.sistema_drops.gerar_drop_morte_inimigo(
                                inimigo.x + getattr(inimigo, "largura", 28) / 2.0,
                                inimigo.y + getattr(inimigo, "altura", 28) / 2.0,
                                xp_base=getattr(inimigo, "xp_valor", 5),
                                loot_enriquecido=(getattr(inimigo, "loot_enriquecido", False) or getattr(mods, "loot_enriquecido", False)),
                                chance_arma=getattr(inimigo, "chance_drop_arma", None),
                                chance_equipamento=getattr(inimigo, "chance_drop_equipamento", None),
                                is_elite=getattr(inimigo, "is_elite", False)
                            )
                        break

                # Fogo Amigo balístico para projéteis do jogador (após carência inicial de 60ms)
                if auto_dano and proj.ativo and getattr(proj, "dono", "jogador") == "jogador" and (proj.tempo_vida - proj.tempo_vida_restante > 0.06):
                    if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                        self.jogador.receber_dano(proj.dano)
                        self.aplicar_shake(6.0, 0.15)
                        proj.ativo = False
                    elif self.jogador.drone is not None and getattr(self.jogador.drone, "ativo", False):
                        if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, self.jogador.drone.x, self.jogador.drone.y, self.jogador.drone.largura, self.jogador.drone.altura):
                            self.jogador.drone.receber_dano(proj.dano)
                            proj.ativo = False

        # Limpeza de entidades destruídas / inativas
        self.projeteis = [p for p in self.projeteis if p.ativo]
        self.inimigos = [e for e in self.inimigos if e.vivo]

        # =========================================================================
        # 7. SISTEMA DE DROPS E PROGRESSÃO DE XP
        # =========================================================================
        mult_drops = getattr(mods, "drops_valor_mult", 1.0) if mods else 1.0
        self.sistema_drops.update(dt)
        eventos_coleta = self.sistema_drops.coletar_jogador(self.jogador, mult_valor_drop=mult_drops)
        for ev in eventos_coleta:
            drop_x = ev.get("x", self.jogador.x + 16)
            drop_y = ev.get("y", self.jogador.y + 16)
            self.sistema_particulas.emitir_burst_drop(drop_x, drop_y, tipo=ev["tipo"])

            if ev["tipo"] == "xp":
                self.toasts_coleta.append({
                    "texto": f"+{ev['valor']} XP",
                    "cor": AMARELO_XP,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 10,
                    "tempo": 1.1,
                    "tempo_max": 1.1
                })
            elif ev["tipo"] == "cura":
                val_cura = ev.get("valor", 35)
                self.toasts_coleta.append({
                    "texto": f"+{val_cura} HP",
                    "cor": VERDE_CURA,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 10,
                    "tempo": 1.4,
                    "tempo_max": 1.4
                })
            elif ev["tipo"] == "arma":
                nome_arma = getattr(self.jogador.arma_especial, "nome", "Arma Especial")
                mun = getattr(self.jogador.arma_especial, "municao_max", 30)
                self.toasts_coleta.append({
                    "texto": f"{nome_arma} ({mun})",
                    "cor": DOURADO,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 15,
                    "tempo": 1.8,
                    "tempo_max": 1.8
                })
            elif ev["tipo"] == "equipamento":
                nome_drone = getattr(self.jogador.drone, "nome", "Drone")
                self.toasts_coleta.append({
                    "texto": f"{nome_drone} (30s)",
                    "cor": (255, 160, 50),
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 15,
                    "tempo": 1.8,
                    "tempo_max": 1.8
                })

        # Atualiza IA do Scavenger APENAS se a configuração "coleta_inimiga" estiver desbloqueada e ligada
        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None
        coleta_ativa = getattr(mods, "coleta_inimiga", False) or (self.config_sistema.obter_valor("coleta_inimiga") in [True, "Ligado", "true", "1"] if hasattr(self, "config_sistema") and self.config_sistema else False)
        if coleta_ativa:
            self.sistema_scavenger.update(dt, self.inimigos, self.sistema_drops.drops)
        else:
            self.sistema_scavenger.desativar(self.inimigos)

        # Verifica morte do jogador
        if not self.jogador.vivo:
            if not self.game_over:
                self.game_over = True
                self._registrar_fim_partida(vitoria=False)


    def draw(self):
        screen = self.janela.screen
        self._carregar_assets_cenario()

        # =========================================================================
        # CAMADA 1: ESPAÇO DO MUNDO (TRANSFORMADO PELA CÂMERA)
        # =========================================================================
        # Fundo da arena
        screen.fill(CINZA_FUNDO)

        # Renderização do piso ladrilhado visível
        tile_tam = 32
        inicio_tx = max(0, int(self.camera.x // tile_tam))
        fim_tx = min(int(self.largura_arena // tile_tam), int((self.camera.x + LARGURA_TELA) // tile_tam) + 1)
        inicio_ty = max(0, int(self.camera.y // tile_tam))
        fim_ty = min(int(self.altura_arena // tile_tam), int((self.camera.y + ALTURA_TELA) // tile_tam) + 1)

        if self._tile_piso is not None:
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    screen.blit(self._tile_piso, (self.camera.transform_x(wx), self.camera.transform_y(wy)))
        else:
            # Grade fallback caso textura não esteja em RAM
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    dx = self.camera.transform_x(wx)
                    dy = self.camera.transform_y(wy)
                    pygame.draw.rect(screen, (28, 32, 42), (dx, dy, tile_tam, tile_tam), 1)

        # Linhas delimitadoras da arena
        borda_x0 = self.camera.transform_x(0)
        borda_y0 = self.camera.transform_y(0)
        borda_x1 = self.camera.transform_x(self.largura_arena)
        borda_y1 = self.camera.transform_y(self.altura_arena)
        pygame.draw.rect(screen, AZUL_CIANO, (borda_x0, borda_y0, self.largura_arena, self.altura_arena), width=3)

        # Posição virtual do cursor do mouse em coordenadas de mundo
        try:
            mx, my = self.mouse.get_position()
        except Exception:
            mx, my = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)
        mouse_mundo_x = mx + self.camera.x
        mouse_mundo_y = my + self.camera.y

        # Indicador de alcance Melee quando empunhada (Antes do golpe - Cone direcional de 45°)
        arma_ativa = self.jogador.obter_arma_ativa()
        if (isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1) and self.jogador.vivo:
            raio = getattr(arma_ativa, "alcance", 84.0)
            arco = getattr(arma_ativa, "arco_graus", 45.0)
            cx_mundo = self.jogador.x + self.jogador.largura / 2.0
            cy_mundo = self.jogador.y + self.jogador.altura / 2.0
            cx_tela = int(self.camera.transform_x(cx_mundo))
            cy_tela = int(self.camera.transform_y(cy_mundo))

            ang_centro = math.atan2(mouse_mundo_y - cy_mundo, mouse_mundo_x - cx_mundo)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio * 2 + 16)
            surf_alcance = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            s_cx = surf_dim // 2
            s_cy = surf_dim // 2

            pontos_setor = [(s_cx, s_cy)]
            num_seg = 12
            for step in range(num_seg + 1):
                ang = ang_centro - meio_arco + (2.0 * meio_arco * step / num_seg)
                px = s_cx + math.cos(ang) * raio
                py = s_cy + math.sin(ang) * raio
                pontos_setor.append((px, py))

            pygame.draw.polygon(surf_alcance, (0, 220, 255, 25), pontos_setor)
            pygame.draw.polygon(surf_alcance, (0, 220, 255, 80), pontos_setor, width=1)
            screen.blit(surf_alcance, (cx_tela - s_cx, cy_tela - s_cy))

        # Efeitos visuais de golpe Melee (Depois / Durante o golpe - Slash Fan de 45°)
        for ef in self.efeitos_melee:
            raio_base = ef["alcance"]
            arco = ef.get("arco_graus", 45.0)
            ang_centro = ef.get("angulo", 0.0)
            cx_tela = int(self.camera.transform_x(ef["x"]))
            cy_tela = int(self.camera.transform_y(ef["y"]))

            progresso = 1.0 - max(0.0, ef["tempo"] / ef["tempo_total"])
            alpha = int(240 * (1.0 - progresso))
            raio_atual = raio_base * (0.4 + 0.6 * progresso)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio_base * 2 + 16)
            surf_golpe = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            s_cx = surf_dim // 2
            s_cy = surf_dim // 2

            pontos_fan = [(s_cx, s_cy)]
            num_seg = 12
            for step in range(num_seg + 1):
                ang = ang_centro - meio_arco + (2.0 * meio_arco * step / num_seg)
                px = s_cx + math.cos(ang) * raio_atual
                py = s_cy + math.sin(ang) * raio_atual
                pontos_fan.append((px, py))

            pygame.draw.polygon(surf_golpe, (255, 215, 0, alpha // 3), pontos_fan)
            pygame.draw.polygon(surf_golpe, (255, 255, 255, alpha), pontos_fan, width=2)
            screen.blit(surf_golpe, (cx_tela - s_cx, cy_tela - s_cy))

        # Drops de itens e gemas de XP no chão da arena
        self.sistema_drops.desenhar(self.janela, self.camera)

        # Inimigos
        for inimigo in self.inimigos:
            inimigo.desenhar(self.janela, self.camera)

        # Jogador
        self.jogador.desenhar(self.janela, self.camera)

        # Projéteis
        for proj in self.projeteis:
            proj.desenhar(self.janela, self.camera)

        # Partículas de combate (faíscas, ondas de choque, bursts e detritos)
        self.sistema_particulas.desenhar(self.janela, self.camera)

        # Barra de HP in-world flutuando abaixo do jogador
        hud_visivel = (self.gerenciador_config.obter_valor("hud") != "desligado")
        if hud_visivel:
            self._desenhar_hp_in_world()

        # =========================================================================
        # CAMADA 2: ESPAÇO DA TELA (SCREEN-SPACE HUD)
        # =========================================================================
        self._desenhar_hud_tela(hud_visivel=hud_visivel)

        # Overlays modais de Level Up, Menu de Configurações, Debug, Vitória, Game Over e Pausa
        if self.modal_level_up.ativo:
            self.modal_level_up.draw(screen)
        elif self.menu_configs.ativo:
            self.menu_configs.draw(screen)
        elif hasattr(self, "menu_debug") and self.menu_debug.ativo:
            self.menu_debug.draw(screen)
        elif self.vitoria:
            self._desenhar_overlay_vitoria()
        elif self.game_over:
            self._desenhar_overlay_game_over()
        elif self.pausado:
            self._desenhar_overlay_pausa()

    def _desenhar_hp_in_world(self):
        """Desenha a barra de HP diretamente abaixo da batata."""
        if not self.jogador.vivo:
            return

        centro_x = self.jogador.x + self.jogador.largura / 2.0
        base_y = self.jogador.y + self.jogador.altura + 6

        bar_x = self.camera.transform_x(centro_x - 20)
        bar_y = self.camera.transform_y(base_y)

        bar_w = 40
        bar_h = 6

        # Fundo vermelho
        pygame.draw.rect(self.janela.screen, (160, 30, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=2)

        # Preenchimento verde
        proporcao = clamp(self.jogador.hp / float(self.jogador.hp_max), 0.0, 1.0)
        fill_w = int(bar_w * proporcao)
        if fill_w > 0:
            pygame.draw.rect(self.janela.screen, VERDE_CURA, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

        # Borda escura
        pygame.draw.rect(self.janela.screen, (20, 20, 20), (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=2)

    def _desenhar_hud_tela(self, hud_visivel: bool = True):
        """Renderiza o HUD fixo na tela: inventário com ícones/munição, métricas e botão de configurações."""
        screen = self.janela.screen

        if hud_visivel:
            # 1. Slots de inventário (Top-Left: 16, 14) com destaque para o slot ativo
            slot_tam = 42
            slot_ativo = getattr(self.jogador, "slot_ativo", 2)

            fonte_slots = pygame.font.SysFont("Arial", 9, bold=True)
            fonte_municao = pygame.font.SysFont("Arial", 10, bold=True)

            for i in range(4):
                sx = 16 + i * (slot_tam + 6)
                sy = 14
                slot_num = i + 1
                is_ativo = (slot_num == slot_ativo)

                bg_cor = (40, 50, 70) if is_ativo else (22, 28, 38)
                borda_cor = DOURADO if is_ativo else CINZA_BORDA
                borda_largura = 2 if is_ativo else 1

                pygame.draw.rect(screen, bg_cor, (sx, sy, slot_tam, slot_tam), border_radius=4)
                pygame.draw.rect(screen, borda_cor, (sx, sy, slot_tam, slot_tam), width=borda_largura, border_radius=4)

                # Número do slot no canto superior esquerdo
                num_surf = fonte_slots.render(str(slot_num), True, DOURADO if is_ativo else (140, 150, 170))
                screen.blit(num_surf, (sx + 3, sy + 2))

                # Ícone do slot
                icone_img = None
                texto_badge = None
                cor_badge = BRANCO

                if i == 0:
                    icone_img = self._obter_sprite_icone("arma_melee")
                elif i == 1:
                    icone_img = self._obter_sprite_icone("arma_pistola")
                elif i == 2:
                    if self.jogador.arma_especial:
                        nome_arma = getattr(self.jogador.arma_especial, "nome", "")
                        if "Minigun" in nome_arma:
                            icone_img = self._obter_sprite_icone("arma_minigun")
                        elif "Escopeta" in nome_arma or "Shotgun" in nome_arma:
                            icone_img = self._obter_sprite_icone("arma_shotgun")
                        elif "Rifle" in nome_arma:
                            icone_img = self._obter_sprite_icone("arma_rifle")
                        elif "Foguetes" in nome_arma:
                            icone_img = self._obter_sprite_icone("arma_foguetes")
                        elif "Granadas" in nome_arma:
                            icone_img = self._obter_sprite_icone("arma_granadas")
                        elif "Railgun" in nome_arma:
                            icone_img = self._obter_sprite_icone("arma_rifle")

                        mun = getattr(self.jogador.arma_especial, "municao_atual", 0)
                        texto_badge = str(mun)
                        cor_badge = AMARELO_XP if mun > 5 else VERMELHO_HP
                elif i == 3:
                    drones_ativos = getattr(self.jogador, "drones", [])
                    if drones_ativos:
                        primeiro_drone = drones_ativos[0]
                        nome_d = getattr(primeiro_drone, "nome", "")
                        if "Cura" in nome_d:
                            icone_img = self._obter_sprite_icone("drone_cura")
                        elif "Combate" in nome_d:
                            icone_img = self._obter_sprite_icone("drone_combate")
                        else:
                            icone_img = self._obter_sprite_icone("drone_suporte")

                        menor_tempo = min(int(getattr(d, "tempo_restante", 0)) for d in drones_ativos)
                        if len(drones_ativos) > 1:
                            texto_badge = f"x{len(drones_ativos)} ({menor_tempo}s)"
                        else:
                            texto_badge = f"{menor_tempo}s"
                        cor_badge = AZUL_CIANO

                if icone_img is not None:
                    screen.blit(icone_img, (sx + (slot_tam - 26) // 2, sy + (slot_tam - 26) // 2))

                if texto_badge is not None:
                    badge_surf = fonte_municao.render(texto_badge, True, cor_badge)
                    badge_rect = badge_surf.get_rect(right=sx + slot_tam - 2, bottom=sy + slot_tam - 1)
                    sombra_b = fonte_municao.render(texto_badge, True, (0, 0, 0))
                    screen.blit(sombra_b, (badge_rect.x + 1, badge_rect.y + 1))
                    screen.blit(badge_surf, badge_rect)

            # 2. Cronômetro de Sobrevivência e Contador de Abates (Top-Center)
            minutos = int(self.tempo_sobrevivencia // 60)
            segundos = int(self.tempo_sobrevivencia % 60)
            texto_tempo = f"{minutos:02d}:{segundos:02d}"

            fonte_tempo = pygame.font.SysFont("Arial", 22, bold=True)
            tempo_surf = fonte_tempo.render(texto_tempo, True, BRANCO)
            tempo_rect = tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=14)
            screen.blit(tempo_surf, tempo_rect)

            texto_abates = f"Abates: {self.abates}"
            fonte_abates = pygame.font.SysFont("Arial", 14, bold=True)
            abates_surf = fonte_abates.render(texto_abates, True, AMARELO_XP)
            abates_rect = abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=40)
            screen.blit(abates_surf, abates_rect)

            # 3. Barra de Progresso de XP (Top-Center: top=62, 360x10 px)
            if hasattr(self, "hud") and self.hud is not None:
                self.hud.desenhar_barra_xp(screen, self.jogador.sistema_xp)

            # 4. Barra de Mini-Boss / Chefe Elite (Top-Center: top=78, 400x12 px)
            if hasattr(self, "hud") and self.hud is not None:
                boss_ativo = next((e for e in self.inimigos if getattr(e, "is_elite", False) and e.vivo), None)
                if boss_ativo is not None:
                    self.hud.desenhar_barra_boss(screen, boss_ativo, visivel=hud_visivel)

        # 5. Toasts de Coleta Flutuantes
        if self._fonte_toast is None:
            self._fonte_toast = pygame.font.SysFont("Arial", 12, bold=True)

        for t in self.toasts_coleta:
            tx_tela = self.camera.transform_x(t["x"])
            ty_tela = self.camera.transform_y(t["y"])
            alpha = int(clamp((t["tempo"] / max(0.01, t["tempo_max"])) * 255, 0, 255))

            txt_surf = self._fonte_toast.render(t["texto"], True, t["cor"])
            txt_sombra = self._fonte_toast.render(t["texto"], True, (0, 0, 0))
            txt_surf.set_alpha(alpha)
            txt_sombra.set_alpha(alpha)

            rect = txt_surf.get_rect(centerx=int(tx_tela), centery=int(ty_tela))
            screen.blit(txt_sombra, (rect.x + 1, rect.y + 1))
            screen.blit(txt_surf, rect)

        # 6. Botão de Configurações e FPS (Top-Right)
        fps_val = int(self.janela.get_fps())
        fonte_fps = pygame.font.SysFont("Arial", 14)
        fps_surf = fonte_fps.render(f"FPS: {fps_val}", True, AZUL_CIANO)
        fps_rect = fps_surf.get_rect(right=LARGURA_TELA - 60, centery=32)
        screen.blit(fps_surf, fps_rect)

        if self._btn_gear_img is not None:
            screen.blit(self._btn_gear_img, (752, 16))
        else:
            pygame.draw.rect(screen, (45, 55, 75), (752, 16, 32, 32), border_radius=4)
            gear_surf = fonte_fps.render("[C]", True, DOURADO)
            gear_rect = gear_surf.get_rect(centerx=768, centery=32)
            screen.blit(gear_surf, gear_rect)

        # 7. Efeitos Visuais de Configurações em Tempo Real (Post-Processing)
        # 7.1 Iluminação Dinâmica / Fog of War (Config 18)
        val_ilum = self.config_sistema.obter_valor("iluminacao")
        if val_ilum in (True, "Ligado", "ligado", "1"):
            fog = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
            fog.fill((8, 10, 15, 235))
            pj_cx = int(self.camera.transform_x(self.jogador.x + 16))
            pj_cy = int(self.camera.transform_y(self.jogador.y + 16))
            pygame.draw.circle(fog, (0, 0, 0, 0), (pj_cx, pj_cy), 170)
            pygame.draw.circle(fog, (0, 0, 0, 80), (pj_cx, pj_cy), 195)
            screen.blit(fog, (0, 0))

        # 7.2 Cores Invertidas (Config 17)
        val_cores = self.config_sistema.obter_valor("cores_invertidas")
        if val_cores in (True, "Ligado", "ligado", "1"):
            inv_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA))
            inv_surf.fill((255, 255, 255))
            inv_surf.blit(screen, (0, 0), special_flags=pygame.BLEND_SUB)
            screen.blit(inv_surf, (0, 0))

        # 7.3 Resolução / Pixelation (Config 3)
        val_res = str(self.config_sistema.obter_valor("resolucao"))
        if val_res in ("75%", "50%", "25%"):
            fator = 0.75 if val_res == "75%" else (0.50 if val_res == "50%" else 0.25)
            small_w = max(10, int(LARGURA_TELA * fator))
            small_h = max(10, int(ALTURA_TELA * fator))
            small_surf = pygame.transform.scale(screen, (small_w, small_h))
            pygame.transform.scale(small_surf, (LARGURA_TELA, ALTURA_TELA), screen)

    def _calcular_score_final(self, vitoria: bool = False) -> tuple[int, float]:
        """Calcula a pontuação final consolidada e o multiplicador de dificuldade."""
        s_abates = self.pontos
        s_tempo = int(10.0 * self.tempo_sobrevivencia)
        s_dano = int(0.5 * self.dano_total_causado)
        s_vitoria = 10000 if vitoria else 0

        # Multiplicador de dificuldade por configurações ativas não-padrão
        n_configs_nao_padrao = 0
        from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
        for cid, cdef in CONFIGURACOES_GAMEPLAY.items():
            if self.gerenciador_config.is_desbloqueada(cid):
                val_atual = self.gerenciador_config.obter_valor(cid)
                if val_atual != cdef.valor_padrao:
                    n_configs_nao_padrao += 1

        mult_dif = 1.0 + 0.10 * n_configs_nao_padrao
        score_final = int(round((s_abates + s_tempo + s_dano + s_vitoria) * mult_dif))
        return score_final, mult_dif

    def _registrar_fim_partida(self, vitoria: bool = False):
        """Registra e persiste o resultado da partida nas estatísticas globais."""
        if self.partida_registrada:
            return

        self.partida_registrada = True
        score_final, mult_dif = self._calcular_score_final(vitoria=vitoria)
        resultado = self.gerenciador_config.registrar_partida(
            tempo=self.tempo_sobrevivencia,
            abates=self.abates,
            pontos=score_final,
            vitoria=vitoria,
            dano_causado=self.dano_total_causado
        )
        self.estatisticas_partida_resultado = {
            "score_final": score_final,
            "mult_dif": mult_dif,
            "novo_recorde_pontos": resultado.get("novo_recorde_pontos", False),
            "novo_recorde_tempo": resultado.get("novo_recorde_tempo", False)
        }

    def _acionar_vitoria(self):
        """Executa a sequência de vitória de 10 minutos do Protocolo: Batata."""
        try:
            pygame.mixer.music.fadeout(800)
        except Exception:
            pass

        try:
            from PPlay.sound import Sound
            sfx_vitoria_path = obter_caminho_asset("sfx_levelup")
            sfx = Sound(sfx_vitoria_path)
            sfx.play()
        except Exception:
            pass

        # Congela todos os inimigos e desativa projéteis
        for inimigo in self.inimigos:
            inimigo.velocidade = 0.0
            inimigo.vx_knockback = 0.0
            inimigo.vy_knockback = 0.0

        self.projeteis.clear()
        self._registrar_fim_partida(vitoria=True)

    def _desenhar_overlay_vitoria(self):
        """Overlay modal de celebração da vitória aos 10 minutos com grade completa de estatísticas."""
        screen = self.janela.screen
        dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        dark_surf.fill((10, 15, 25, 235))
        screen.blit(dark_surf, (0, 0))

        # Painel central estilizado
        painel_rect = pygame.Rect(90, 40, 620, 520)
        pygame.draw.rect(screen, (25, 32, 45), painel_rect, border_radius=8)
        pygame.draw.rect(screen, DOURADO, painel_rect, width=2, border_radius=8)

        # Faixa superior de destaque
        fonte_tit = pygame.font.SysFont("Arial", 24, bold=True)
        tit_surf = fonte_tit.render("PROTOCOLO EXECUTADO COM SUCESSO", True, DOURADO)
        tit_rect = tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=60)
        screen.blit(tit_surf, tit_rect)

        fonte_sub = pygame.font.SysFont("Arial", 13)
        sub_surf = fonte_sub.render("A Batata superou 10 minutos de compilacao sem erros criticos.", True, (200, 220, 240))
        sub_rect = sub_surf.get_rect(centerx=LARGURA_TELA // 2, top=95)
        screen.blit(sub_surf, sub_rect)

        # Quadro de estatísticas internas
        quadro_rect = pygame.Rect(120, 130, 560, 280)
        pygame.draw.rect(screen, (15, 20, 30), quadro_rect, border_radius=6)
        pygame.draw.rect(screen, (45, 60, 80), quadro_rect, width=1, border_radius=6)

        fonte_stat_label = pygame.font.SysFont("Arial", 14)
        fonte_stat_val = pygame.font.SysFont("Arial", 14, bold=True)
        fonte_stat_destaque = pygame.font.SysFont("Arial", 20, bold=True)

        stats_data = [
            ("Tempo de Sobrevivencia:", "10:00 (600.0s) [MAXIMO]", DOURADO),
            ("Inimigos Neutralizados (Abates):", f"{self.abates}", AMARELO_XP),
            ("Dano Total Infligido:", f"{self.dano_total_causado:,}", (255, 100, 100)),
            ("Configuracoes Desbloqueadas:", f"{len(self.gerenciador_config.desbloqueadas)} / 20", AZUL_CIANO),
            ("Multiplicador de Dificuldade:", f"x{self.estatisticas_partida_resultado.get('mult_dif', 1.0):.2f}", (180, 210, 240)),
        ]

        start_y = 145
        step_y = 34
        for i, (label, val_str, cor_val) in enumerate(stats_data):
            cur_y = start_y + i * step_y
            lbl_surf = fonte_stat_label.render(label, True, (180, 195, 215))
            screen.blit(lbl_surf, (140, cur_y))

            val_surf = fonte_stat_val.render(val_str, True, cor_val)
            val_rect = val_surf.get_rect(right=660, top=cur_y)
            screen.blit(val_surf, val_rect)

        # Linha de separação
        pygame.draw.line(screen, (50, 65, 85), (140, 315), (660, 315), width=1)

        # Pontuação Final
        score_val = self.estatisticas_partida_resultado.get("score_final", self.pontos)
        score_lbl = fonte_stat_destaque.render("PONTUACAO FINAL:", True, DOURADO)
        screen.blit(score_lbl, (140, 330))

        score_num_surf = fonte_stat_destaque.render(f"{score_val:,} PTS", True, DOURADO)
        score_num_rect = score_num_surf.get_rect(right=660, top=330)
        screen.blit(score_num_surf, score_num_rect)

        # Badge de Recorde Histórico se atingido
        if self.estatisticas_partida_resultado.get("novo_recorde_pontos", False):
            badge_rec_surf = fonte_stat_val.render("[NOVO RECORDE HISTORICO!]", True, AMARELO_XP)
            badge_rec_rect = badge_rec_surf.get_rect(centerx=LARGURA_TELA // 2, top=375)
            screen.blit(badge_rec_surf, badge_rec_rect)

        # Rodapé com atalhos de navegação
        fonte_btn = pygame.font.SysFont("Arial", 14, bold=True)
        fonte_btn_sub = pygame.font.SysFont("Arial", 13)

        btn1_surf = fonte_btn.render("[ENTER / ESPACO] Jogar Novamente", True, DOURADO)
        screen.blit(btn1_surf, btn1_surf.get_rect(centerx=LARGURA_TELA // 2, top=430))

        btn2_surf = fonte_btn_sub.render("[ESC / M] Retornar ao Menu Principal", True, (200, 210, 225))
        screen.blit(btn2_surf, btn2_surf.get_rect(centerx=LARGURA_TELA // 2, top=465))

        btn3_surf = fonte_btn_sub.render("[C] Menu de Configuracoes", True, AZUL_CIANO)
        screen.blit(btn3_surf, btn3_surf.get_rect(centerx=LARGURA_TELA // 2, top=498))

    def _desenhar_overlay_pausa(self):
        """Overlay modal de pausa com textos perfeitamente centralizados."""
        screen = self.janela.screen
        dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        dark_surf.fill((10, 15, 22, 180))
        screen.blit(dark_surf, (0, 0))

        fonte_titulo = pygame.font.SysFont("Arial", 34, bold=True)
        fonte_sub = pygame.font.SysFont("Arial", 18, bold=True)

        t_surf = fonte_titulo.render("JOGO PAUSADO", True, DOURADO)
        t_rect = t_surf.get_rect(centerx=LARGURA_TELA // 2, top=200)
        screen.blit(t_surf, t_rect)

        c_surf = fonte_sub.render("[ESC] Continuar Partida", True, BRANCO)
        c_rect = c_surf.get_rect(centerx=LARGURA_TELA // 2, top=280)
        screen.blit(c_surf, c_rect)

        m_surf = fonte_sub.render("[M] Menu Principal", True, CINZA_BORDA)
        m_rect = m_surf.get_rect(centerx=LARGURA_TELA // 2, top=325)
        screen.blit(m_surf, m_rect)

    def _desenhar_overlay_game_over(self):
        """Overlay de fim de jogo com estatísticas perfeitamente centralizadas."""
        screen = self.janela.screen
        dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        dark_surf.fill((20, 5, 5, 210))
        screen.blit(dark_surf, (0, 0))

        fonte_tit = pygame.font.SysFont("Arial", 36, bold=True)
        fonte_sub = pygame.font.SysFont("Arial", 16)
        fonte_stat = pygame.font.SysFont("Arial", 16, bold=True)
        fonte_prompt = pygame.font.SysFont("Arial", 15, bold=True)

        tit_surf = fonte_tit.render("PROTOCOLO FALHOU", True, VERMELHO_HP)
        screen.blit(tit_surf, tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=130))

        sub_surf = fonte_sub.render("A Batata sucumbiu aos bugs e estagiários.", True, (200, 180, 180))
        screen.blit(sub_surf, sub_surf.get_rect(centerx=LARGURA_TELA // 2, top=175))

        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)

        # Quadro escuro
        quadro_rect = pygame.Rect(180, 210, 440, 200)
        pygame.draw.rect(screen, (28, 15, 20), quadro_rect, border_radius=6)
        pygame.draw.rect(screen, (80, 40, 50), quadro_rect, width=1, border_radius=6)

        tempo_surf = fonte_stat.render(f"Tempo de Sobrevivência: {minutos:02d}:{segundos:02d}", True, BRANCO)
        screen.blit(tempo_surf, tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=230))

        abates_surf = fonte_stat.render(f"Total de Abates: {self.abates}", True, AMARELO_XP)
        screen.blit(abates_surf, abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=265))

        dano_surf = fonte_stat.render(f"Dano Total: {self.dano_total_causado:,}", True, (255, 120, 120))
        screen.blit(dano_surf, dano_surf.get_rect(centerx=LARGURA_TELA // 2, top=300))

        score_val = self.estatisticas_partida_resultado.get("score_final", self.pontos)
        pontos_surf = fonte_stat.render(f"Pontuação Final: {score_val:,} PTS", True, DOURADO)
        screen.blit(pontos_surf, pontos_surf.get_rect(centerx=LARGURA_TELA // 2, top=335))

        if self.estatisticas_partida_resultado.get("novo_recorde_pontos", False):
            rec_surf = fonte_stat.render("[NOVO RECORDE DE PONTOS!]", True, AMARELO_XP)
            screen.blit(rec_surf, rec_surf.get_rect(centerx=LARGURA_TELA // 2, top=370))

        prompt_surf = fonte_prompt.render("Pressione [ENTER] para Jogar Novamente ou [ESC] para o Menu", True, DOURADO)
        screen.blit(prompt_surf, prompt_surf.get_rect(centerx=LARGURA_TELA // 2, top=440))

    def _ao_subir_nivel(self, novo_nivel: int):
        """Callback acionado quando o jogador alcança um novo nível."""
        if hasattr(self, "modal_level_up") and self.modal_level_up is not None:
            self.modal_level_up.abrir(novo_nivel)

    def _reiniciar_partida(self):
        SceneManager.change_scene(GameplayScene())

    def _voltar_menu(self):
        from src.cenas.menu_principal import MenuPrincipalScene
        SceneManager.change_scene(MenuPrincipalScene())


