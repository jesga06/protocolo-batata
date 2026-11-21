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
from src.armas.railgun import Railgun
from src.armas import Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas
from src.equipamentos import DroneCura, DroneCombate, DroneSuporte
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_particulas import SistemaParticulas
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.hud import HUD
from src.ui.modal_level_up import ModalLevelUp
from src.ui.modal_overclock import ModalOverclock
from src.ui.menu_configs import MenuConfigs
from src.entidades.geladeira_tsunami import GeladeiraTsunami, ESTADO_MORTE
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    BRANCO, PRETO, CINZA_FUNDO, CINZA_PAINEL, CINZA_BORDA,
    VERMELHO_HP, VERDE_CURA, AMARELO_XP, AZUL_CIANO, DOURADO, LARANJA_ALERTA,
    ROXO_ACENTO, ROXO_CLARO, ROXO_ESCURO,
    BOSS_GELADEIRA_LARGURA, BOSS_GELADEIRA_ALTURA,
    obter_caminho_asset, SAVE_FILE_PATH
)
from src.utils.math_utils import colisao_aabb, clamp, distancia, vetor_direcao


class GameplayScene(BaseScene):
    """
    Cena principal de combate e sobrevivência na arena.
    """
    _tile_piso = None
    _btn_gear_img = None
    _slot_inv_img = None
    _mira_crosshair_img = None

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
        self.camera.obter_mouse_mundo = self._obter_mouse_mundo

        # Sistema de Configurações e Modificadores
        self.gerenciador_config = GerenciadorConfiguracoes()
        self.gerenciador_config.carregar_arquivo(SAVE_FILE_PATH)
        self.modal_level_up = ModalLevelUp(self.gerenciador_config, self.jogador, cena=self)
        self.modal_overclock = ModalOverclock(self.jogador, cena=self)
        self.menu_configs = MenuConfigs(self.gerenciador_config, em_jogo=True, cena=self)

        # Registra callback de level-up no SistemaXP do jogador
        self.jogador.sistema_xp.registrar_callback_level_up(self._ao_subir_nivel)

        # Chefe Final e Cutscene de Transição
        self.chefe_final = None
        self.boss_cutscene_ativa = False
        self.boss_cutscene_fase = "none"
        self.boss_cutscene_timer = 0.0
        self.overlay_cutscene_alpha = 0.0
        self.overlay_cutscene_cor = (255, 255, 255)
        self.tiros_echo_pendentes = []

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

        # Cache de fontes para alta performance (escala nativa 1280x720)
        self._fontes = {
            "slots": pygame.font.SysFont("Arial", 12, bold=True),
            "municao": pygame.font.SysFont("Arial", 13, bold=True),
            "tempo": pygame.font.SysFont("Arial", 28, bold=True),
            "abates": pygame.font.SysFont("Arial", 18, bold=True),
            "buff": pygame.font.SysFont("Arial", 11, bold=True),
            "timer": pygame.font.SysFont("Arial", 11, bold=True),
            "toast": pygame.font.SysFont("Arial", 14, bold=True),
            "fps": pygame.font.SysFont("Arial", 16),
            "tit_vit": pygame.font.SysFont("Arial", 30, bold=True),
            "sub_vit": pygame.font.SysFont("Arial", 16),
            "stat_label": pygame.font.SysFont("Arial", 16),
            "stat_val": pygame.font.SysFont("Arial", 16, bold=True),
            "stat_destaque": pygame.font.SysFont("Arial", 24, bold=True),
            "btn": pygame.font.SysFont("Arial", 16, bold=True),
            "btn_sub": pygame.font.SysFont("Arial", 15),
            "tit_pausa": pygame.font.SysFont("Arial", 40, bold=True),
            "sub_pausa": pygame.font.SysFont("Arial", 20, bold=True),
            "tit_go": pygame.font.SysFont("Arial", 42, bold=True),
            "sub_go": pygame.font.SysFont("Arial", 18),
            "stat_go": pygame.font.SysFont("Arial", 18, bold=True),
            "prompt_go": pygame.font.SysFont("Arial", 16, bold=True),
        }
        self._fonte_toast = self._fontes["toast"]

        # Toasts de itens coletados, Screen Shake e Efeitos
        self.toasts_coleta: list[dict] = []
        self.shake_intensidade: float = 0.0
        self.shake_timer: float = 0.0
        self.arena_freeze_timer: float = 0.0

        # Input buffer e efeitos visuais
        self.buffer_tiro = 0.0
        self.efeitos_melee: list[dict] = []
        self.zonas_fogo: list[dict] = []
        self.trilhas_plasma: list[dict] = []
        self.zonas_estase: list[dict] = []
        self.pocas_gelo: list[dict] = []
        self.aura_cura_timer: float = 0.0
        self._ultimo_slot_ativo = getattr(self.jogador, "slot_ativo", 2)
        self._arma_ativa_anterior = None

        # Buffers de superfícies pré-alocadas e cooldown de alternância de menu
        self._fog_surf = None
        self._inv_surf = None
        self._overlay_surf = None
        self._motion_blur_surf = None
        self._zoom75_surf = None
        self._zoom_crop_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._res_surf_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._melee_surf_cache: dict[int, pygame.Surface] = {}
        self._vsync_strip_surf = None
        self._cooldown_menu_toggle: float = 0.0

        # Aplica modificadores iniciais
        self.aplicar_modificadores()

        # Inicialização da trilha sonora em loop contínuo
        try:
            caminho_musica = obter_caminho_asset("musica_fase")
            if os.path.isfile(caminho_musica):
                if not pygame.mixer.music.get_busy() or getattr(pygame.mixer.music, "_current_track", None) != caminho_musica:
                    pygame.mixer.music.load(caminho_musica)
                    pygame.mixer.music._current_track = caminho_musica
                    vol_efetivo = self._obter_volume_musica_efetivo(0.4)
                    pygame.mixer.music.set_volume(vol_efetivo)
                    pygame.mixer.music.play(-1)
                else:
                    vol_efetivo = self._obter_volume_musica_efetivo(0.4)
                    pygame.mixer.music.set_volume(vol_efetivo)
        except Exception:
            pass

    def _obter_volume_musica_efetivo(self, base: float = 0.4) -> float:
        """Calcula o volume efetivo da música baseado nas configs de volume_master e volume_musica."""
        vol_master = 100.0
        vol_musica = 100.0
        if hasattr(self, "config_sistema") and self.config_sistema is not None:
            try:
                vol_master = float(self.config_sistema.obter_valor("volume_master"))
            except (ValueError, TypeError):
                vol_master = 100.0
            try:
                vol_musica = float(self.config_sistema.obter_valor("volume_musica"))
            except (ValueError, TypeError):
                vol_musica = 100.0
        return float(base * (vol_musica / 100.0) * (vol_master / 100.0))

    @property
    def drops(self):
        """Atalho de compatibilidade para self.sistema_drops.drops."""
        return self.sistema_drops.drops if hasattr(self, "sistema_drops") else []

    @drops.setter
    def drops(self, valor):
        if hasattr(self, "sistema_drops"):
            self.sistema_drops.drops = valor

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
                    cls._icones_slots[chave] = pygame.transform.scale(img, (34, 34))
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

        if cls._slot_inv_img is None:
            try:
                caminho = obter_caminho_asset("slot_inventario")
                if os.path.isfile(caminho):
                    cls._slot_inv_img = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._slot_inv_img = None

        if cls._mira_crosshair_img is None:
            try:
                caminho = obter_caminho_asset("mira_crosshair")
                if os.path.isfile(caminho):
                    cls._mira_crosshair_img = pygame.image.load(caminho).convert_alpha()
            except Exception:
                cls._mira_crosshair_img = None

    def _clamp_entidade_arena(self, ent):
        """Restringe uma entidade (jogador ou inimigo) estritamente aos limites da arena."""
        larg = float(getattr(ent, "largura", 28))
        alt = float(getattr(ent, "altura", 28))
        ent.x = clamp(float(ent.x), 0.0, max(0.0, float(self.largura_arena) - larg))
        ent.y = clamp(float(ent.y), 0.0, max(0.0, float(self.altura_arena) - alt))

    def _obter_viewport_zoom75(self) -> tuple[int, int, float, float]:
        """Calcula dimensões (1067x800) e origem (cam75_x, cam75_y) da câmera expandida para zoom='75%'."""
        fov_w = int(round(LARGURA_TELA / 0.75))  # 1067
        fov_h = int(round(ALTURA_TELA / 0.75))  # 800
        cam_cx = self.camera.x + LARGURA_TELA / 2.0
        cam_cy = self.camera.y + ALTURA_TELA / 2.0
        cam75_x = clamp(cam_cx - fov_w / 2.0, 0.0, max(0.0, float(self.largura_arena - fov_w)))
        cam75_y = clamp(cam_cy - fov_h / 2.0, 0.0, max(0.0, float(self.altura_arena - fov_h)))
        return fov_w, fov_h, cam75_x, cam75_y

    def _obter_mouse_mundo(self, mx: float, my: float) -> tuple[float, float]:
        """Converte coordenadas virtuais de tela (800x600) em coordenadas do mundo considerando o zoom ativo."""
        val_zoom = str(self.config_sistema.obter_valor("zoom")) if hasattr(self, "config_sistema") and self.config_sistema else "100%"
        if val_zoom == "75%":
            fov_w, fov_h, cam75_x, cam75_y = self._obter_viewport_zoom75()
            wx = cam75_x + float(mx) * (fov_w / float(LARGURA_TELA))
            wy = cam75_y + float(my) * (fov_h / float(ALTURA_TELA))
            return wx, wy
        elif val_zoom in ("125%", "150%"):
            z = 1.25 if val_zoom == "125%" else 1.50
            crop_w = int(LARGURA_TELA / z)
            crop_h = int(ALTURA_TELA / z)
            pj_cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
            pj_cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
            crop_x = clamp(pj_cx - crop_w // 2, 0, LARGURA_TELA - crop_w)
            crop_y = clamp(pj_cy - crop_h // 2, 0, ALTURA_TELA - crop_h)
            wx = self.camera.x + crop_x + float(mx) / z
            wy = self.camera.y + crop_y + float(my) / z
            return wx, wy
        return float(mx) + self.camera.x, float(my) + self.camera.y

    def _ao_subir_nivel(self, novo_nivel: int):
        """
        Callback acionado pelo SistemaXP ao subir de nível:
        - Sempre emite onda de choque de fôlego (+10 HP e empurrão em inimigos colados).
        - Nos Marcos de Configuração (Níveis 5 e 11 / múltiplos de 5 / Pity Buffer ativo): abre o Modal de 3 Cartas pausando o jogo.
        - Nos Níveis Normais: NÃO pausa o jogo e derruba 2 Cápsulas de Suprimento na arena para escolha em movimento.
        """
        cx = self.jogador.x + self.jogador.largura / 2.0
        cy = self.jogador.y + self.jogador.altura / 2.0
        self.jogador.curar(10)
        if hasattr(self, "sistema_particulas") and self.sistema_particulas is not None:
            self.sistema_particulas.emitir_onda_choque(cx, cy, raio_max=130.0, cor=DOURADO)

        for inim in getattr(self, "inimigos", []):
            if getattr(inim, "vivo", True) and not getattr(inim, "is_boss", False):
                icx = inim.x + getattr(inim, "largura", 28) / 2.0
                icy = inim.y + getattr(inim, "altura", 28) / 2.0
                if distancia(cx, cy, icx, icy) < 130.0:
                    dx_p, dy_p = vetor_direcao(cx, cy, icx, icy)
                    inim.x += dx_p * 32.0
                    inim.y += dy_p * 32.0
                    self._clamp_entidade_arena(inim)

        eh_marco = (
            (hasattr(self.jogador.sistema_xp, "eh_nivel_marco_config") and self.jogador.sistema_xp.eh_nivel_marco_config(novo_nivel))
            or (int(novo_nivel) % 5 == 0)
            or (hasattr(self, "modal_level_up") and self.modal_level_up is not None and self.modal_level_up.config_pity_buffer is not None)
        )
        if eh_marco and hasattr(self, "modal_level_up") and self.modal_level_up is not None:
            self.modal_level_up.enfileirar_level_up(novo_nivel)
            self.pausado = True
        else:
            from src.ui.modal_level_up import obter_tier_nivel, gerar_pool_consumiveis_por_tier
            pool = gerar_pool_consumiveis_por_tier(obter_tier_nivel(novo_nivel))
            opcoes_2 = random.sample(pool, min(2, len(pool)))
            if hasattr(self, "sistema_drops") and hasattr(self.sistema_drops, "gerar_capsulas_powerup"):
                self.sistema_drops.gerar_capsulas_powerup(cx, cy, opcoes_2)
            self.toasts_coleta.append({
                "texto": f"NÍVEL {novo_nivel}! +10 HP & SUPRIMENTOS",
                "cor": DOURADO,
                "x": cx,
                "y": self.jogador.y - 18,
                "tempo": 1.8,
                "tempo_max": 1.8
            })
            if int(novo_nivel) >= getattr(self.jogador.sistema_xp, "nivel_max", 12):
                self.iniciar_boss_cutscene()

    def aplicar_modificadores(self):
        """Aplica os modificadores matemáticos calculados às entidades ativas."""
        mods = self.gerenciador_config.obter_modificadores()
        # 1. Velocidade do jogador
        self.jogador.recalcular_velocidade(mods.vel_jogador_mult)

        # 2. Dano das armas do jogador
        self.jogador.mult_dano_config = mods.dano_armas_mult
        self.jogador.fps_stutter_dodge = getattr(mods, "fps_stutter_dodge", False)
        self.jogador.motion_blur_ghosting = getattr(mods, "motion_blur_ghosting", False)
        self.jogador.keybinds_overdrive_dash = getattr(mods, "keybinds_overdrive_dash", False)

        for arma in self.jogador.armas:
            if not hasattr(arma, "_dano_original"):
                arma._dano_original = arma.dano
            arma.dano = int(round(arma._dano_original * mods.dano_armas_mult))
        if getattr(self.jogador, "arma_especial", None) is not None:
            if not hasattr(self.jogador.arma_especial, "_dano_original"):
                self.jogador.arma_especial._dano_original = self.jogador.arma_especial.dano
            self.jogador.arma_especial.dano = int(round(self.jogador.arma_especial._dano_original * mods.dano_armas_mult))
        if getattr(self.jogador, "arma_especial_secundaria", None) is not None:
            if not hasattr(self.jogador.arma_especial_secundaria, "_dano_original"):
                self.jogador.arma_especial_secundaria._dano_original = self.jogador.arma_especial_secundaria.dano
            self.jogador.arma_especial_secundaria.dano = int(round(self.jogador.arma_especial_secundaria._dano_original * mods.dano_armas_mult))

        # 3. Propagação de qualidade gráfica e sincronização de áudio
        baixa_qualidade = (str(self.gerenciador_config.obter_valor("graficos_qualidade")).lower() == "baixa") if hasattr(self, "gerenciador_config") else False
        if hasattr(self, "janela") and self.janela:
            self.janela.low_graphics = baixa_qualidade
        if hasattr(self, "sistema_particulas") and self.sistema_particulas:
            self.sistema_particulas.low_graphics = baixa_qualidade

        try:
            pygame.mixer.music.set_volume(self._obter_volume_musica_efetivo(0.4))
            vol_master = float(self.config_sistema.obter_valor("volume_master")) if hasattr(self, "config_sistema") and self.config_sistema else 100.0
            vol_sfx = float(self.config_sistema.obter_valor("volume_sfx")) if hasattr(self, "config_sistema") and self.config_sistema else 100.0
            self.volume_sfx_efetivo = clamp((vol_master / 100.0) * (vol_sfx / 100.0), 0.0, 1.0)
            if pygame.mixer.get_init():
                for ch_idx in range(pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(ch_idx).set_volume(self.volume_sfx_efetivo)
        except Exception:
            pass

    def _aplicar_efeitos_disparo_extras(self, novos_tiros: list, mods):
        """Aplica efeitos adicionais de disparo (Refrigeração, Multithreading e Auto-Fire Burst)."""
        if not novos_tiros:
            return

        # 1. Refrigeração a Nitrogênio: atirar reinicia o timer de resfriamento
        if getattr(self.jogador, "refrigeracao_nitrogenio", False):
            self.jogador.timer_sem_atirar_refrig = 0.0

        # 2. Multithreading (Overclock BIOS): dispara eco via coprocessadores orbitais com 0.08s de delay
        if getattr(self.jogador, "multithreading", False):
            angulos = getattr(self.jogador, "coprocessadores_angulos", [0.0, 3.14159])
            for ang_cop in angulos:
                cx_cop = self.jogador.x + self.jogador.largura / 2.0 + math.cos(ang_cop) * 34.0
                cy_cop = self.jogador.y + self.jogador.altura / 2.0 + math.sin(ang_cop) * 34.0
                tiros_multi = []
                ang_var = random.uniform(-0.10, 0.10)
                cos_v, sin_v = math.cos(ang_var), math.sin(ang_var)
                for p in novos_tiros:
                    vx_n = p.vx * cos_v - p.vy * sin_v
                    vy_n = p.vx * sin_v + p.vy * cos_v
                    tiros_multi.append(p.clonar(x=cx_cop, y=cy_cop, vx=vx_n, vy=vy_n))
                self.tiros_echo_pendentes.append({"timer": 0.08, "projeteis": tiros_multi})

        # 3. Auto-Fire Burst (Configuração de Auto-Disparo): eco adicional independente de 0.08s
        if getattr(mods, "auto_fire_burst", False):
            tiros_burst = []
            ang_var = random.uniform(-0.10, 0.10)
            cos_v, sin_v = math.cos(ang_var), math.sin(ang_var)
            for p in novos_tiros:
                vx_n = p.vx * cos_v - p.vy * sin_v
                vy_n = p.vx * sin_v + p.vy * cos_v
                tiros_burst.append(p.clonar(vx=vx_n, vy=vy_n))
            self.tiros_echo_pendentes.append({"timer": 0.08, "projeteis": tiros_burst})

        # 3.5 Efeitos de disparo de armas únicas (Gatilho Magnético, Munição Superaquecida, Recuo Minigun, Trilha Railgun)
        arma_at = self.jogador.obter_arma_ativa() if self.jogador.vivo else None
        if getattr(self.jogador, "buff_cadencia_timer", 0.0) > 0.0 and arma_at is not None and not getattr(arma_at, "municao_infinita", True):
            if hasattr(arma_at, "municao_atual") and hasattr(arma_at, "municao_max"):
                arma_at.municao_atual = min(arma_at.municao_max, arma_at.municao_atual + 1)

        for p in novos_tiros:
            if getattr(self.jogador, "buff_dano_timer", 0.0) > 0.0:
                p.superaquecido = True
                p.perfuracoes_restantes = max(getattr(p, "perfuracoes_restantes", 0), 1)
            if getattr(p, "recuo_autor", 0.0) > 0.0:
                self.jogador.x -= p.dir_x * p.recuo_autor * 0.15
                self.jogador.y -= p.dir_y * p.recuo_autor * 0.15
                self._clamp_entidade_arena(self.jogador)
            if getattr(p, "trilha_plasma", False):
                ox, oy = getattr(p, "origem_trilha", (p.x_origem, p.y_origem))
                self.trilhas_plasma.append({
                    "x1": ox,
                    "y1": oy,
                    "x2": ox + p.dir_x * 1100.0,
                    "y2": oy + p.dir_y * 1100.0,
                    "tempo": 0.40,
                    "tempo_max": 0.40
                })

    def _aplicar_overvolt_chain(self, alvo_origem, dano_base: int, mods=None):
        """Aplica corrente elétrica em cadeia (Overvolt) a partir de um alvo atingido criticamente."""
        if not getattr(self.jogador, "overvolt", False):
            return

        cx_origem = alvo_origem.x + getattr(alvo_origem, "largura", 28) / 2.0
        cy_origem = alvo_origem.y + getattr(alvo_origem, "altura", 28) / 2.0

        alvos_candidatos = []
        for e in self.inimigos:
            if not getattr(e, "vivo", True) or e is alvo_origem:
                continue
            if getattr(e, "em_fase", False):
                continue
            if getattr(e, "estado", "") in ("morte", ESTADO_MORTE):
                continue
            e_cx = e.x + getattr(e, "largura", 28) / 2.0
            e_cy = e.y + getattr(e, "altura", 28) / 2.0
            dist = distancia(e_cx, e_cy, cx_origem, cy_origem)
            if dist < 220.0:
                alvos_candidatos.append((dist, e, e_cx, e_cy))

        # Ordena por proximidade e seleciona até 4 alvos
        alvos_candidatos.sort(key=lambda item: item[0])
        alvos_chain = alvos_candidatos[:4]

        dano_chain = max(1, dano_base // 2)
        for _, alv, a_cx, a_cy in alvos_chain:
            ret_d = alv.receber_dano(dano_chain)
            dano_efetivo = int(ret_d) if isinstance(ret_d, (int, float)) else dano_chain
            self.dano_total_causado += dano_efetivo
            self.sistema_particulas.emitir_faiscas(a_cx, a_cy, cor=(120, 240, 255), qtd=5)
            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                self.sistema_particulas.emitir_texto_dano(
                    a_cx,
                    alv.y,
                    dano_efetivo,
                    critico=False
                )
            if not getattr(alv, "vivo", True):
                self._registrar_abate_inimigo(alv, mods)

    def _registrar_abate_inimigo(self, inim, mods=None):
        """Contabiliza o abate de um inimigo, score, efeitos de shrapnel, shake e drops."""
        if mods is None:
            mods = self.gerenciador_config.obter_modificadores() if hasattr(self, "gerenciador_config") else None

        self.abates += 1
        self.pontos += getattr(inim, "score_valor", 100)
        inim_cx = inim.x + getattr(inim, "largura", 28) / 2.0
        inim_cy = inim.y + getattr(inim, "altura", 28) / 2.0

        # Overvolt (Abordagem A2): descarga elétrica automática a cada 25 abates
        if getattr(self.jogador, "overvolt", False):
            self.jogador.abates_overvolt_contador = getattr(self.jogador, "abates_overvolt_contador", 0) + 1
            if self.jogador.abates_overvolt_contador >= 25:
                self.jogador.abates_overvolt_contador = 0
                self._aplicar_overvolt_chain(inim, 40, mods)

        abate_rapido = False
        if getattr(inim, "is_elite", False):
            self.aplicar_shake(14.0, 0.35)
            self.sistema_particulas.emitir_debris(inim_cx, inim_cy, cor=(255, 215, 0), qtd=16)
            abate_rapido = bool(getattr(inim, "elegivel_abate_rapido", False) or (getattr(inim, "tempo_vida_restante", 0.0) or 0.0) >= 30.0)
            if abate_rapido:
                self.toasts_coleta.append({
                    "texto": "ABATE RÁPIDO (<30s)! ARMA SUPERAQUECIDA + REPARO!",
                    "cor": DOURADO,
                    "x": inim_cx,
                    "y": inim.y - 24,
                    "tempo": 2.4,
                    "tempo_max": 2.4
                })
            if getattr(self.jogador, "bios_modding", False):
                for arma_rec in (getattr(self.jogador, "arma_especial", None), getattr(self.jogador, "arma_especial_secundaria", None)):
                    if arma_rec is not None and hasattr(arma_rec, "municao_max"):
                        arma_rec.municao_atual = min(arma_rec.municao_max, arma_rec.municao_atual + max(1, int(round(arma_rec.municao_max * 0.15))))

        # Estilhaços Low-Poly (Qualidade Gráfica Baixa)
        if getattr(mods, "graficos_shrapnel", False):
            for ang_sh in (0.0, 1.5708, 3.14159, 4.71239):
                spd_sh = random.uniform(220.0, 300.0)
                vx_sh = math.cos(ang_sh + random.uniform(-0.2, 0.2)) * spd_sh
                vy_sh = math.sin(ang_sh + random.uniform(-0.2, 0.2)) * spd_sh
                self.projeteis.append(Projetil(
                    x=inim_cx - 3.0, y=inim_cy - 3.0, vx=vx_sh, vy=vy_sh, dano=12,
                    tempo_vida=0.45, dono="jogador", largura=6, altura=6, cor=(255, 255, 255),
                    perfurante=True
                ))

        is_boss_lutando = (self.chefe_final is not None and self.chefe_final.vivo)
        self.sistema_drops.gerar_drop_morte_inimigo(
            inim.x + getattr(inim, "largura", 28) / 2.0,
            inim.y + getattr(inim, "altura", 28) / 2.0,
            bonus_chance_drop=getattr(mods, "drop_chance_bonus", 0.0) if mods else 0.0,
            mult_chance_drop=getattr(mods, "drop_chance_mult", 1.0) if mods else 1.0,
            xp_base=getattr(inim, "xp_valor", 5),
            loot_enriquecido=getattr(mods, "loot_enriquecido", False) or getattr(inim, "loot_enriquecido", False),
            chance_arma=getattr(inim, "chance_drop_arma", None),
            chance_equipamento=getattr(inim, "chance_drop_equipamento", None),
            is_elite=getattr(inim, "is_elite", False),
            modo_boss=is_boss_lutando,
            abate_rapido=abate_rapido
        )

    def iniciar_boss_cutscene(self):
        """
        Inicia a sequência cinematográfica de introdução do Chefe Final (Geladeira Tsunami).
        NÃO instancia a Geladeira durante a queda de energia inicial para evitar que ela e o balão
        apareçam antes do fade-in / equalizadores.
        """
        if self.boss_cutscene_ativa or (self.chefe_final is not None and self.chefe_final.vivo):
            return
        self.boss_cutscene_ativa = True
        self.boss_cutscene_fase = "whiteout"
        self.boss_cutscene_timer = 0.0
        self.overlay_cutscene_cor = (255, 255, 255)
        self.overlay_cutscene_alpha = 0.0
        self.projeteis.clear()
        self.tiros_echo_pendentes.clear()
        try:
            pygame.mixer.music.fadeout(1600)
            pygame.mixer.music._current_track = None
        except Exception:
            pass

    def spawn_direto_boss(self):
        """Spawna diretamente a Geladeira Tsunami pronta para combate (atalho de debug)."""
        if self.chefe_final is not None and self.chefe_final.vivo:
            if self.chefe_final not in self.inimigos:
                self.inimigos.append(self.chefe_final)
            return
        self.inimigos = [e for e in self.inimigos if not getattr(e, "is_boss", False)]
        self.chefe_final = GeladeiraTsunami(
            self.largura_arena / 2.0 - BOSS_GELADEIRA_LARGURA / 2.0,
            self.altura_arena / 2.0 - BOSS_GELADEIRA_ALTURA / 2.0 - 50
        )
        self.chefe_final.estado = "fase1"
        self.chefe_final.subestado_fase2 = "stalk"
        self.chefe_final.intro_concluida = True
        self.inimigos.append(self.chefe_final)
        try:
            caminho_boss_music = obter_caminho_asset("musica_boss")
            if os.path.isfile(caminho_boss_music):
                pygame.mixer.music.load(caminho_boss_music)
                pygame.mixer.music._current_track = caminho_boss_music
                vol_efetivo = self._obter_volume_musica_efetivo(0.4)
                pygame.mixer.music.set_volume(vol_efetivo)
                pygame.mixer.music.play(-1, fade_ms=2000)
        except Exception:
            pass

    def update(self, dt: float = None):
        """Atualiza a lógica da cena de gameplay."""
        return self.loop(dt=dt)

    def loop(self, dt: float = None):
        if dt is None:
            dt = self.janela.delta_time()
            # Em testes unitários headless ou loops ultra-rápidos (<10ms), avança 1 frame padrão a 60 FPS
            if dt < 0.010:
                dt = 1.0 / 60.0
            # Clampa dt para evitar saltos quânticos em frames atípicos (máximo 100ms)
            dt = min(dt, 0.1)

        # Atualiza cooldown de reabertura do menu para evitar input bleed (C / ESC)
        if hasattr(self, "_cooldown_menu_toggle") and self._cooldown_menu_toggle > 0.0:
            self._cooldown_menu_toggle = max(0.0, self._cooldown_menu_toggle - dt)

        # 0. Se o Menu de Debug estiver ativo, processa seus inputs e congela o jogo
        if hasattr(self, "menu_debug"):
            self.menu_debug.update(dt, self.teclado, self.mouse)
            if self.menu_debug.ativo:
                self.pausado = True
                self.buffer_tiro = 0.0
                return
            elif not self.modal_level_up.ativo and not self.modal_overclock.ativo and not self.menu_configs.ativo and not self.game_over and not self.vitoria:
                self.pausado = False

        # Sincroniza estado de Modo Deus e Munição Infinita
        if hasattr(self, "menu_debug"):
            self.jogador.modo_deus = getattr(self.menu_debug, "modo_deus", False)
            if getattr(self.menu_debug, "municao_infinita", False):
                if getattr(self.jogador, "arma_especial", None) is not None:
                    self.jogador.arma_especial.municao_atual = self.jogador.arma_especial.municao_max
                if getattr(self.jogador, "arma_especial_secundaria", None) is not None:
                    self.jogador.arma_especial_secundaria.municao_atual = self.jogador.arma_especial_secundaria.municao_max
                if len(getattr(self.jogador, "armas", [])) > 1 and hasattr(self.jogador.armas[1], "municao_max"):
                    self.jogador.armas[1].municao_atual = self.jogador.armas[1].municao_max

        # 1. Se o Modal de Overclock estiver ativo, processa seus inputs e congela o jogo
        if self.modal_overclock.ativo or self.modal_overclock.tempo_transicao_saida > 0.0:
            self.modal_overclock.update(dt, self.teclado, self.mouse)
            self.buffer_tiro = 0.0
            if not self.modal_overclock.ativo and not self.modal_level_up.ativo and not self.menu_configs.ativo and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                self.pausado = False
            return

        # 2. Se o Modal de Level Up estiver ativo, processa seus inputs e congela o jogo
        if self.modal_level_up.ativo or getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) > 0.0:
            self.modal_level_up.update(dt, self.teclado, self.mouse)
            self.buffer_tiro = 0.0
            if not self.modal_level_up.ativo and getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) <= 0.0 and not self.modal_overclock.ativo and not self.menu_configs.ativo and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                self.pausado = False
            return

        # 3. Se o Menu de Configurações estiver ativo, processa seus inputs e congela o jogo
        if self.menu_configs.ativo:
            self.menu_configs.update(dt, self.teclado, self.mouse)
            self.buffer_tiro = 0.0
            if not self.menu_configs.ativo:
                self._cooldown_menu_toggle = 0.18
                if not self.modal_level_up.ativo and not self.modal_overclock.ativo and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                    self.pausado = False
            return

        # 4. Tecla 'C' ou clique no botão de engrenagem (LARGURA_TELA - 48, 16, 32x32 ou 752..784 legado) antes de qualquer inversão de mouse
        pode_abrir_menu = getattr(self, "_cooldown_menu_toggle", 0.0) <= 0.0
        if pode_abrir_menu and self.mouse is not None and hasattr(self.mouse, "button_down") and self.mouse.button_down(1):
            try:
                mx_gear, my_gear = self.mouse.get_position()
                gear_x = LARGURA_TELA - 48
                if ((gear_x <= mx_gear <= gear_x + 32) or (752 <= mx_gear <= 784)) and 16 <= my_gear <= 48:
                    self.menu_configs.abrir()
                    self.pausado = True
                    self.buffer_tiro = 0.0
                    return
            except Exception:
                pass
        if pode_abrir_menu and (
            (hasattr(self.teclado, "key_down") and (self.teclado.key_down("c") or self.teclado.key_down("C"))) or
            (hasattr(self.teclado, "key_pressed") and (self.teclado.key_pressed("c") or self.teclado.key_pressed("C")))
        ):
            self.menu_configs.abrir()
            self.pausado = True
            self.buffer_tiro = 0.0
            return

        # 5. Controle de Pausa / Menu via Teclado (ESC)
        if self.teclado.key_down("ESC"):
            if self.game_over or self.vitoria:
                self._voltar_menu()
                return
            elif pode_abrir_menu:
                if not self.pausado:
                    self.menu_configs.abrir()
                    self.pausado = True
                    self.buffer_tiro = 0.0
                else:
                    self.pausado = False
                    self.buffer_tiro = 0.0
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
            self.buffer_tiro = 0.0
            if self.teclado.key_down("m") or self.teclado.key_down("M"):
                self._voltar_menu()
            return

        # =========================================================================
        # 1. ATUALIZAÇÃO DO JOGADOR, CUTSCENE E INPUTS
        # =========================================================================
        timer_congelado = getattr(self.menu_debug, "timer_congelado", False) if hasattr(self, "menu_debug") else False
        if not timer_congelado and not self.boss_cutscene_ativa:
            self.tempo_sobrevivencia += dt

        # Atualiza temporizador de Screen Shake
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            if self.shake_timer == 0.0:
                self.shake_intensidade = 0.0

        # Atualiza sistema de partículas
        self.sistema_particulas.update(dt)

        # Processamento da Cutscene do Chefe Final (Whiteout -> Blackout -> Música Fade-In -> Subida do Boss)
        if self.boss_cutscene_ativa:
            self.boss_cutscene_timer += dt
            if self.boss_cutscene_fase == "whiteout":
                self.overlay_cutscene_cor = (255, 255, 255)
                self.overlay_cutscene_alpha = min(255, int(255 * (self.boss_cutscene_timer / 2.0)))
                if self.boss_cutscene_timer >= 2.0:
                    self.boss_cutscene_fase = "blackout"
                    self.boss_cutscene_timer = 0.0
                    self.overlay_cutscene_cor = (0, 0, 0)
                    self.overlay_cutscene_alpha = 255
                    # Purga inimigos comuns (desativando scavenger antes) e centraliza jogador
                    self.sistema_scavenger.desativar(self.inimigos)
                    self.inimigos = [self.chefe_final] if (self.chefe_final is not None and self.chefe_final.vivo) else []
                    self.projeteis.clear()
                    self.tiros_echo_pendentes.clear()
                    self.jogador.x = self.largura_arena / 2.0 - self.jogador.largura / 2.0
                    self.jogador.y = self.altura_arena / 2.0 - self.jogador.altura / 2.0
                    self.camera.follow(self.jogador, suavizacao=1.0)
            elif self.boss_cutscene_fase == "blackout":
                self.overlay_cutscene_cor = (0, 0, 0)
                self.overlay_cutscene_alpha = 255
                if self.boss_cutscene_timer >= 1.0:
                    self.boss_cutscene_fase = "musica_in"
                    self.boss_cutscene_timer = 0.0
                    try:
                        caminho_boss_music = obter_caminho_asset("musica_boss")
                        if os.path.isfile(caminho_boss_music):
                            pygame.mixer.music.load(caminho_boss_music)
                            pygame.mixer.music._current_track = caminho_boss_music
                            vol_efetivo = self._obter_volume_musica_efetivo(0.4)
                            pygame.mixer.music.set_volume(vol_efetivo)
                            pygame.mixer.music.play(-1, fade_ms=5000)
                    except Exception:
                        pass
                    # Garante que o Chefe Final está posicionado e enquadrado dentro da câmera (somente APÓS o blackout!)
                    y_dest = self.altura_arena / 2.0 + 70.0
                    y_orig = self.altura_arena / 2.0 + 210.0
                    if self.chefe_final is None or not self.chefe_final.vivo:
                        self.chefe_final = GeladeiraTsunami(
                            self.largura_arena / 2.0 - BOSS_GELADEIRA_LARGURA / 2.0,
                            y_orig,
                            y_destino=y_dest,
                            y_origem=y_orig
                        )
                    else:
                        self.chefe_final.y_intro_destino = y_dest
                        self.chefe_final.y_intro_origem = y_orig
                        self.chefe_final.y = y_orig
                    if self.chefe_final not in self.inimigos:
                        self.inimigos.append(self.chefe_final)
                    self.camera.follow(self.jogador, suavizacao=1.0)
            elif self.boss_cutscene_fase == "musica_in":
                self.camera.follow(self.jogador, suavizacao=1.0)
                fade_prog = clamp(self.boss_cutscene_timer / 1.5, 0.0, 1.0)
                self.overlay_cutscene_alpha = int(255 * (1.0 - fade_prog))
                if self.chefe_final is not None and getattr(self.chefe_final, "intro_concluida", False):
                    self.boss_cutscene_ativa = False
                    self.boss_cutscene_fase = "combate"
                    self.overlay_cutscene_alpha = 0.0

        # Processamento de disparos de eco (Multithreading Overclock)
        if not self.boss_cutscene_ativa:
            novos_ecos = []
            for echo in self.tiros_echo_pendentes:
                echo["timer"] -= dt
                if echo["timer"] <= 0.0:
                    self.projeteis.extend(echo["projeteis"])
                else:
                    novos_ecos.append(echo)
            self.tiros_echo_pendentes = novos_ecos

        # Condição de vitória: disparada exclusivamente pela derrota do Chefe Final (Geladeira Tsunami)
        if self.chefe_final is not None and not self.chefe_final.vivo and not self.vitoria and self.jogador.vivo:
            if not getattr(self.chefe_final, "_abate_contabilizado", False):
                self.chefe_final._abate_contabilizado = True
                self.abates += 1
                self.pontos += getattr(self.chefe_final, "score_valor", 5000)
            self.vitoria = True
            self._acionar_vitoria()
            return

        # Atualiza e limpa toasts de coleta
        for t in self.toasts_coleta:
            t["tempo"] -= dt
            t["y"] -= 22.0 * dt
        self.toasts_coleta = [t for t in self.toasts_coleta if t["tempo"] > 0]

        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None

        # Triggers de Overclock e Configs Globais (Kernel Panic, Barramento, HUD Pulse)
        if getattr(self.jogador, "kernel_panic_trigger", False):
            self.jogador.kernel_panic_trigger = False
            self.arena_freeze_timer = 4.0
            self.aplicar_shake(16.0, 0.5)
            self.projeteis = [p for p in self.projeteis if getattr(p, "dono", "jogador") == "jogador"]
            for inim in self.inimigos:
                if getattr(inim, "vivo", True):
                    inim.cooldown_contato_atual = max(getattr(inim, "cooldown_contato_atual", 0.0), 4.0)
            self.sistema_particulas.emitir_onda_choque(self.jogador.x + self.jogador.largura / 2.0, self.jogador.y + self.jogador.altura / 2.0, raio_max=220.0)
            self.sistema_particulas.emitir_debris(self.jogador.x + self.jogador.largura / 2.0, self.jogador.y + self.jogador.altura / 2.0, cor=(140, 255, 160), qtd=24)

        if self.arena_freeze_timer > 0.0:
            self.arena_freeze_timer = max(0.0, self.arena_freeze_timer - dt)

        if getattr(self.jogador, "upgrade_barramento", False):
            self.jogador.aplicar_pulso_magnetico(self.sistema_drops.drops)

        if getattr(mods, "hud_pulse_magnet", False):
            self.timer_pulso_hud = getattr(self, "timer_pulso_hud", 0.0) + dt
            if self.timer_pulso_hud >= 4.0:
                self.timer_pulso_hud = 0.0
                self.jogador.aplicar_pulso_magnetico(self.sistema_drops.drops)
                self.sistema_particulas.emitir_onda_choque(self.jogador.x + self.jogador.largura / 2.0, self.jogador.y + self.jogador.altura / 2.0, raio_max=160.0)

        centro_jogador_x = self.jogador.x + self.jogador.largura / 2.0
        centro_jogador_y = self.jogador.y + self.jogador.altura / 2.0

        if not self.boss_cutscene_ativa:
            self.jogador.processar_input(
                self.teclado,
                self.mouse,
                dt,
                config_sistema=self.config_sistema,
                limite_arena=(self.largura_arena, self.altura_arena),
                camera=self.camera
            )
            hitbox_mult = (getattr(mods, "hitbox_projeteis_mult", 1.0) if mods else 1.0) * (getattr(mods, "resolucao_chunky_hitbox", 1.0) if mods else 1.0)
            mult_dano_buff = 1.05 if getattr(self.jogador, "buff_dano_timer", 0.0) > 0.0 else 1.0

            tiros_drone = self.jogador.update(
                dt,
                drops=self.sistema_drops.drops,
                inimigos=self.inimigos
            )
            self._clamp_entidade_arena(self.jogador)
            if getattr(self.jogador, "pulso_frio_pronto", False):
                self.jogador.pulso_frio_pronto = False
                cx_j = self.jogador.x + self.jogador.largura / 2.0
                cy_j = self.jogador.y + self.jogador.altura / 2.0
                self.sistema_particulas.emitir_onda_choque(cx_j, cy_j, raio_max=220.0, cor=(100, 220, 255))
                self.sistema_particulas.emitir_faiscas(cx_j, cy_j, cor=(140, 235, 255), qtd=14)
                for inim_frio in self.inimigos:
                    if getattr(inim_frio, "vivo", True):
                        icx_fr = inim_frio.x + getattr(inim_frio, "largura", 28) / 2.0
                        icy_fr = inim_frio.y + getattr(inim_frio, "altura", 28) / 2.0
                        if distancia(cx_j, cy_j, icx_fr, icy_fr) <= 220.0:
                            inim_frio.slow_timer = max(getattr(inim_frio, "slow_timer", 0.0), 3.0)
                            inim_frio.slow_fator = min(getattr(inim_frio, "slow_fator", 1.0), 0.50)
            if getattr(self.jogador, "evento_cura_drone", 0) > 0:
                val_c = self.jogador.evento_cura_drone
                self.jogador.evento_cura_drone = 0
                self.aura_cura_timer = 0.65
                self.toasts_coleta.append({
                    "texto": f"+{val_c} HP",
                    "cor": VERDE_CURA,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 12,
                    "tempo": 1.1,
                    "tempo_max": 1.1
                })
            for d_sup in getattr(self.jogador, "drones", []):
                if hasattr(d_sup, "zonas_estase_pendentes") and d_sup.zonas_estase_pendentes:
                    self.zonas_estase.extend(d_sup.zonas_estase_pendentes)
                    d_sup.zonas_estase_pendentes.clear()
            if tiros_drone:
                for p_dr in tiros_drone:
                    if hitbox_mult != 1.0:
                        p_dr.largura = max(2, int(round(p_dr.largura * hitbox_mult)))
                        p_dr.altura = max(2, int(round(p_dr.altura * hitbox_mult)))
                        p_dr.width = p_dr.largura
                        p_dr.height = p_dr.altura
                self.projeteis.extend(tiros_drone)

            # Cancela carga de armas caso o slot do jogador ou arma ativa tenha mudado
            slot_atual = getattr(self.jogador, "slot_ativo", None)
            arma_atual = self.jogador.obter_arma_ativa() if self.jogador.vivo else None
            slot_mudou = (hasattr(self, "_ultimo_slot_ativo") and self._ultimo_slot_ativo != slot_atual)
            arma_mudou = (hasattr(self, "_arma_ativa_anterior") and self._arma_ativa_anterior is not None and self._arma_ativa_anterior is not arma_atual)
            if slot_mudou or arma_mudou:
                for arma_cancel in (
                    getattr(self.jogador, "arma_primaria", None),
                    getattr(self.jogador, "arma_secundaria", None),
                    getattr(self.jogador, "arma_especial", None),
                    getattr(self.jogador, "arma_especial_secundaria", None),
                    getattr(self, "_arma_ativa_anterior", None)
                ):
                    if arma_cancel is not None and getattr(arma_cancel, "carregando", False):
                        if hasattr(arma_cancel, "cancelar_carga"):
                            arma_cancel.cancelar_carga()
            self._ultimo_slot_ativo = slot_atual
            self._arma_ativa_anterior = arma_atual

            # Atualiza a posição da câmera para seguir o jogador suavemente (dt-independente)
            val_suav = self.config_sistema.obter_valor("suavizacao_camera") if hasattr(self, "config_sistema") and self.config_sistema else "ligado"
            suavizacao_fator = 1.0 if str(val_suav).lower() in ("desligado", "0", "false") else (1.0 - (1.0 - 0.15) ** (dt * 60.0))
            self.camera.follow(self.jogador, suavizacao=suavizacao_fator)

            # =========================================================================
            # 2. DISPARO DE ARMAS (PISTOLA, MELEE E ESPECIAIS COM BUFFER DE INPUT)
            # =========================================================================
            centro_jogador_x = self.jogador.x + self.jogador.largura / 2.0
            centro_jogador_y = self.jogador.y + self.jogador.altura / 2.0

            # Fix 12.3: Pulso de Choque do Overdrive Dash (keybinds_overdrive_dash)
            if getattr(self.jogador, "overdrive_pulse_trigger", False):
                self.jogador.overdrive_pulse_trigger = False
                self.sistema_particulas.emitir_onda_choque(centro_jogador_x, centro_jogador_y, raio_max=110.0, cor=(100, 220, 255))
                for inim in list(self.inimigos):
                    if inim == self.chefe_final or getattr(inim, "is_boss", False):
                        continue
                    if getattr(inim, "vivo", True) and not getattr(inim, "em_fase", False):
                        i_cx = inim.x + getattr(inim, "largura", 28) / 2.0
                        i_cy = inim.y + getattr(inim, "altura", 28) / 2.0
                        if distancia(i_cx, i_cy, centro_jogador_x, centro_jogador_y) < 110.0:
                            dir_p_x, dir_p_y = vetor_direcao(centro_jogador_x, centro_jogador_y, i_cx, i_cy)
                            inim.x += dir_p_x * 32.0
                            inim.y += dir_p_y * 32.0
                            self._clamp_entidade_arena(inim)
                            ret_d = inim.receber_dano(15, origem_x=centro_jogador_x, origem_y=centro_jogador_y, dir_ataque=(dir_p_x, dir_p_y))
                            dano_aplicado = int(ret_d) if isinstance(ret_d, (int, float)) else 15
                            self.dano_total_causado += dano_aplicado
                            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                self.sistema_particulas.emitir_texto_dano(
                                    inim.x + getattr(inim, "largura", 28) / 2.0,
                                    inim.y,
                                    dano_aplicado,
                                    critico=False
                                )
                            if not inim.vivo:
                                self._registrar_abate_inimigo(inim, mods)

            # Posição virtual do cursor convertida para espaço do mundo (com suporte a zoom e presets)
            val_keybinds = str(self.config_sistema.obter_valor("keybinds")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "padrao"
            is_uma_mao = (val_keybinds == "uma_mao")
            try:
                mx_raw, my_raw = self.mouse.get_position()
                mx, my = mx_raw, my_raw
                if val_keybinds == "pesadelo":
                    my = ALTURA_TELA - my
            except Exception:
                mx_raw, my_raw = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)
                mx, my = mx_raw, my_raw

            # Input buffer e Auto-Fire
            val_autofire = str(self.config_sistema.obter_valor("auto_fire")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "ligado"
            autofire_desligado = val_autofire in ("desligado", "0", "false")

            if is_uma_mao:
                # Mira e tiro 100% no teclado: direção do movimento atual, default para cima (0.0, -1.0) se parado
                dir_mov = getattr(self.jogador, "dir_movimento", (0.0, -1.0))
                dir_mira_x, dir_mira_y = float(dir_mov[0]), float(dir_mov[1])
                norm_m = math.hypot(dir_mira_x, dir_mira_y)
                if norm_m > 1e-5:
                    dir_mira_x /= norm_m
                    dir_mira_y /= norm_m
                else:
                    dir_mira_x, dir_mira_y = 0.0, -1.0
                mouse_mundo_x = centro_jogador_x + dir_mira_x * 160.0
                mouse_mundo_y = centro_jogador_y + dir_mira_y * 160.0

                kb_down = bool(
                    self.teclado is not None and hasattr(self.teclado, "key_down") and (
                        self.teclado.key_down("SPACE") or self.teclado.key_down("f") or
                        self.teclado.key_down("F") or self.teclado.key_down("ENTER")
                    )
                )
                kb_pressed = bool(
                    self.teclado is not None and hasattr(self.teclado, "key_pressed") and (
                        self.teclado.key_pressed("SPACE") or self.teclado.key_pressed("f") or
                        self.teclado.key_pressed("F") or self.teclado.key_pressed("ENTER")
                    )
                )
                btn1_down = kb_down
                btn1_pressed = kb_pressed if autofire_desligado else True
            else:
                mouse_mundo_x, mouse_mundo_y = self._obter_mouse_mundo(mx, my)
                btn1_down = bool(self.mouse.button_down(1)) if (self.mouse is not None and hasattr(self.mouse, "button_down")) else False
                if self.mouse is not None and hasattr(self.mouse, "button_pressed"):
                    btn1_pressed = bool(self.mouse.button_pressed(1))
                elif self.mouse is not None and hasattr(self.mouse, "get_pressed_buttons"):
                    pressed_btns = self.mouse.get_pressed_buttons()
                    btn1_pressed = bool(pressed_btns[0]) if pressed_btns else False
                elif pygame.mouse.get_focused() and len(pygame.mouse.get_pressed()) > 0:
                    btn1_pressed = bool(pygame.mouse.get_pressed()[0])
                else:
                    btn1_pressed = False

            if autofire_desligado:
                disparar_agora = btn1_down
                self.buffer_tiro = 0.0
            else:
                if btn1_pressed:
                    self.buffer_tiro = 0.15  # Buffer de 150ms para garantir que cliques rápidos nunca sejam perdidos
                else:
                    self.buffer_tiro = max(0.0, self.buffer_tiro - dt)
                disparar_agora = (self.buffer_tiro > 0.0)

            crit_chance = getattr(mods, "critico_chance", 0.0) if mods else 0.0
            crit_mult = getattr(mods, "critico_mult", 2.0) if mods else 2.0
            if getattr(self.jogador, "overvolt", False):
                crit_chance = min(1.0, crit_chance + 0.30)
                crit_mult = max(crit_mult, 2.0)

            # Direção de mira do jogador
            if not is_uma_mao:
                dir_mira_x, dir_mira_y = vetor_direcao(centro_jogador_x, centro_jogador_y, mouse_mundo_x, mouse_mundo_y)
                if dir_mira_x == 0.0 and dir_mira_y == 0.0:
                    dir_mira_x = 1.0
            # Ponto de saída do projétil deslocado fora do corpo da batata (evita auto-colisão)
            spawn_origem_x = centro_jogador_x + dir_mira_x * 24.0
            spawn_origem_y = centro_jogador_y + dir_mira_y * 24.0

            arma_ativa = self.jogador.obter_arma_ativa() if self.jogador.vivo else None

            # Gerenciamento de Carga da Railgun (1.0s de preparação com faíscas elétricas e SFX)
            if arma_ativa is not None and (isinstance(arma_ativa, Railgun) or "railgun" in getattr(arma_ativa, "nome", "").lower()):
                is_carregando = getattr(arma_ativa, "carregando", False)
                gatilho_railgun = (btn1_pressed if is_carregando else btn1_down) if autofire_desligado else (disparar_agora or btn1_pressed)

                if gatilho_railgun and self.jogador.vivo and (is_carregando or arma_ativa.pode_atirar()):
                    if not is_carregando:
                        arma_ativa.iniciar_carga()

                    mult_cadencia = 1.0
                    if getattr(self.jogador, "refrigeracao_nitrogenio", False):
                        mult_cadencia *= 1.20
                    if getattr(self.jogador, "buff_cadencia_timer", 0.0) > 0.0:
                        mult_cadencia *= 1.08
                    arma_pronta = arma_ativa.update_carga(dt * mult_cadencia)
                    # Emite faíscas elétricas ciano/azul ao redor do jogador enquanto carrega
                    self.sistema_particulas.emitir_faiscas(
                        centro_jogador_x, centro_jogador_y,
                        dir_x=dir_mira_x, dir_y=dir_mira_y,
                        cor=(100, 220, 255), qtd=3
                    )
                    if arma_pronta:
                        novos_tiros = arma_ativa.disparar(
                            spawn_origem_x, spawn_origem_y,
                            mouse_mundo_x, mouse_mundo_y
                        )
                        if novos_tiros:
                            for p in novos_tiros:
                                if hitbox_mult != 1.0:
                                    p.largura = max(2, int(round(p.largura * hitbox_mult)))
                                    p.altura = max(2, int(round(p.altura * hitbox_mult)))
                                    p.width = p.largura
                                    p.height = p.altura
                                if mult_dano_buff != 1.0:
                                    p.dano = max(1, math.ceil(p.dano * mult_dano_buff))
                            self.projeteis.extend(novos_tiros)
                            self.aplicar_shake(12.0, 0.3)
                            self.buffer_tiro = 0.0
                            self._aplicar_efeitos_disparo_extras(novos_tiros, mods)
                else:
                    if is_carregando:
                        arma_ativa.cancelar_carga()
            elif disparar_agora and self.jogador.vivo and arma_ativa is not None:
                if isinstance(arma_ativa, Pistola) or getattr(arma_ativa, "slot", None) == 2:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        novos_tiros = arma_ativa.disparar(
                            spawn_origem_x, spawn_origem_y,
                            mouse_mundo_x, mouse_mundo_y
                        )
                        if novos_tiros:
                            for p in novos_tiros:
                                if hitbox_mult != 1.0:
                                    p.largura = max(2, int(round(p.largura * hitbox_mult)))
                                    p.altura = max(2, int(round(p.altura * hitbox_mult)))
                                    p.width = p.largura
                                    p.height = p.altura
                                if mult_dano_buff != 1.0:
                                    p.dano = max(1, math.ceil(p.dano * mult_dano_buff))
                            self.projeteis.extend(novos_tiros)
                            self.buffer_tiro = 0.0
                            self._aplicar_efeitos_disparo_extras(novos_tiros, mods)
                elif isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        ang_mira = math.atan2(mouse_mundo_y - centro_jogador_y, mouse_mundo_x - centro_jogador_x)
                        if hasattr(arma_ativa, "rebater_projeteis"):
                            rebatidos = arma_ativa.rebater_projeteis(
                                centro_jogador_x, centro_jogador_y,
                                self.projeteis,
                                mira_x=mouse_mundo_x,
                                mira_y=mouse_mundo_y,
                                angulo_mira=ang_mira
                            )
                            if rebatidos:
                                self.aplicar_shake(8.0, 0.20)
                                for pr in rebatidos:
                                    self.sistema_particulas.emitir_faiscas(
                                        pr.x + getattr(pr, "largura", 8) / 2.0,
                                        pr.y + getattr(pr, "altura", 8) / 2.0,
                                        dir_x=math.cos(ang_mira),
                                        dir_y=math.sin(ang_mira),
                                        cor=DOURADO,
                                        qtd=8
                                    )
                                self.toasts_coleta.append({
                                    "texto": "PARRY!",
                                    "cor": DOURADO,
                                    "x": centro_jogador_x,
                                    "y": self.jogador.y - 16,
                                    "tempo": 1.0,
                                    "tempo_max": 1.0
                                })
                        afetados = arma_ativa.executar_ataque(
                            centro_jogador_x, centro_jogador_y,
                            self.inimigos,
                            mira_x=mouse_mundo_x,
                            mira_y=mouse_mundo_y,
                            angulo_mira=ang_mira,
                            aplicar_dano=False
                        )
                        if isinstance(afetados, (list, tuple)):
                            for inim in afetados:
                                dano_base = getattr(arma_ativa, "dano", 10)
                                is_crit = (crit_chance > 0.0 and random.random() < crit_chance)
                                dano_melee = math.ceil(dano_base * mult_dano_buff * (crit_mult if is_crit else 1.0))

                                if getattr(mods, "screen_shake_stagger", False) and inim is not self.chefe_final and not getattr(inim, "is_boss", False):
                                    inim.x += math.cos(ang_mira) * 10.0
                                    inim.y += math.sin(ang_mira) * 10.0
                                    self._clamp_entidade_arena(inim)
                                    inim.slow_timer = max(getattr(inim, "slow_timer", 0.0), 1.2)
                                    inim.slow_fator = 0.50

                                ret_d = inim.receber_dano(
                                    dano_melee,
                                    origem_x=centro_jogador_x,
                                    origem_y=centro_jogador_y,
                                    dir_ataque=(math.cos(ang_mira), math.sin(ang_mira))
                                )
                                dano_efetivo_m = int(ret_d) if isinstance(ret_d, (int, float)) else dano_melee
                                self.dano_total_causado += dano_efetivo_m
                                self.sistema_particulas.emitir_faiscas(
                                    inim.x + getattr(inim, "largura", 28) / 2.0,
                                    inim.y + getattr(inim, "altura", 28) / 2.0,
                                    dir_x=math.cos(ang_mira),
                                    dir_y=math.sin(ang_mira),
                                    cor=(255, 240, 150),
                                    qtd=5
                                )
                                if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                    self.sistema_particulas.emitir_texto_dano(
                                        inim.x + getattr(inim, "largura", 28) / 2.0,
                                        inim.y,
                                        dano_efetivo_m,
                                        critico=is_crit
                                    )

                                if is_crit:
                                    self._aplicar_overvolt_chain(inim, dano_efetivo_m, mods)

                                if not getattr(inim, "vivo", True):
                                    self._registrar_abate_inimigo(inim, mods)
                                elif inim is not self.chefe_final and not getattr(inim, "is_boss", False):
                                    self._clamp_entidade_arena(inim)
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
                                spawn_origem_x, spawn_origem_y,
                                mouse_mundo_x, mouse_mundo_y
                            )
                            if novos_tiros:
                                for p in novos_tiros:
                                    if hitbox_mult != 1.0:
                                        p.largura = max(2, int(round(p.largura * hitbox_mult)))
                                        p.altura = max(2, int(round(p.altura * hitbox_mult)))
                                        p.width = p.largura
                                        p.height = p.altura
                                    if mult_dano_buff != 1.0:
                                        p.dano = max(1, math.ceil(p.dano * mult_dano_buff))
                                self.projeteis.extend(novos_tiros)
                                self.buffer_tiro = 0.0
                                self._aplicar_efeitos_disparo_extras(novos_tiros, mods)

            # Dual-Wield (BIOS Modding): Botão Direito dispara a outra Arma Especial se equipada e diferente da ativa
            if getattr(self.jogador, "bios_modding", False):
                # Se slot 3 ativo, dispara a outra arma especial (secundária ou primária não ativa)
                arma_esp = None
                if getattr(self.jogador, "slot_ativo", None) == 3:
                    if getattr(self.jogador, "arma_especial_secundaria", None) is not None and self.jogador.arma_especial_secundaria is not arma_ativa:
                        arma_esp = self.jogador.arma_especial_secundaria
                    elif getattr(self.jogador, "arma_especial", None) is not None and self.jogador.arma_especial is not arma_ativa:
                        arma_esp = self.jogador.arma_especial
                elif getattr(self.jogador, "arma_especial", None) is not None and self.jogador.arma_especial is not arma_ativa:
                    arma_esp = self.jogador.arma_especial

                if arma_esp is not None and self.jogador.vivo:
                    if is_uma_mao:
                        btn3_down = bool(
                            self.teclado is not None and hasattr(self.teclado, "key_down") and (
                                self.teclado.key_down("SHIFT") or self.teclado.key_down("v") or
                                self.teclado.key_down("V") or self.teclado.key_down("TAB")
                            )
                        )
                        btn3_pressed = bool(
                            self.teclado is not None and hasattr(self.teclado, "key_pressed") and (
                                self.teclado.key_pressed("SHIFT") or self.teclado.key_pressed("v") or
                                self.teclado.key_pressed("V") or self.teclado.key_pressed("TAB")
                            )
                        )
                    else:
                        btn3_down = bool(self.mouse.button_down(3)) if (self.mouse is not None and hasattr(self.mouse, "button_down")) else False
                        if self.mouse is not None and hasattr(self.mouse, "button_pressed"):
                            btn3_pressed = bool(self.mouse.button_pressed(3))
                        elif self.mouse is not None and hasattr(self.mouse, "get_pressed_buttons"):
                            pressed_btns = self.mouse.get_pressed_buttons()
                            btn3_pressed = bool(pressed_btns[2]) if len(pressed_btns) > 2 else False
                        elif len(pygame.mouse.get_pressed()) > 2 and (pygame.mouse.get_focused() or btn3_down):
                            btn3_pressed = bool(pygame.mouse.get_pressed()[2])
                        elif len(pygame.mouse.get_pressed()) > 2:
                            btn3_pressed = bool(pygame.mouse.get_pressed()[2])
                        else:
                            btn3_pressed = False

                    if isinstance(arma_esp, Railgun) or "railgun" in getattr(arma_esp, "nome", "").lower():
                        is_carregando_esp = getattr(arma_esp, "carregando", False)
                        gatilho_esp = (btn3_pressed if is_carregando_esp else btn3_down) if autofire_desligado else btn3_pressed
                        if gatilho_esp and (is_carregando_esp or (hasattr(arma_esp, "pode_atirar") and arma_esp.pode_atirar())):
                            if not is_carregando_esp:
                                arma_esp.iniciar_carga()
                            mult_cadencia = 1.0
                            if getattr(self.jogador, "refrigeracao_nitrogenio", False):
                                mult_cadencia *= 1.20
                            if getattr(self.jogador, "buff_cadencia_timer", 0.0) > 0.0:
                                mult_cadencia *= 1.08
                            arma_pronta = arma_esp.update_carga(dt * mult_cadencia)
                            self.sistema_particulas.emitir_faiscas(
                                centro_jogador_x, centro_jogador_y,
                                dir_x=dir_mira_x, dir_y=dir_mira_y,
                                cor=(100, 220, 255), qtd=3
                            )
                            if arma_pronta:
                                tiros_esp = arma_esp.disparar(spawn_origem_x, spawn_origem_y, mouse_mundo_x, mouse_mundo_y)
                                if tiros_esp:
                                    for p in tiros_esp:
                                        if hitbox_mult != 1.0:
                                            p.largura = max(2, int(round(p.largura * hitbox_mult)))
                                            p.altura = max(2, int(round(p.altura * hitbox_mult)))
                                            p.width = p.largura
                                            p.height = p.altura
                                        if mult_dano_buff != 1.0:
                                            p.dano = max(1, math.ceil(p.dano * mult_dano_buff))
                                    self.projeteis.extend(tiros_esp)
                                    self.aplicar_shake(12.0, 0.3)
                                    self._aplicar_efeitos_disparo_extras(tiros_esp, mods)
                        else:
                            if is_carregando_esp:
                                arma_esp.cancelar_carga()
                    else:
                        rmb_disparar = btn3_down if autofire_desligado else btn3_pressed
                        if rmb_disparar and hasattr(arma_esp, "pode_atirar") and arma_esp.pode_atirar():
                            tiros_esp = arma_esp.disparar(spawn_origem_x, spawn_origem_y, mouse_mundo_x, mouse_mundo_y)
                            if tiros_esp:
                                for p in tiros_esp:
                                    if hitbox_mult != 1.0:
                                        p.largura = max(2, int(round(p.largura * hitbox_mult)))
                                        p.altura = max(2, int(round(p.altura * hitbox_mult)))
                                        p.width = p.largura
                                        p.height = p.altura
                                    if mult_dano_buff != 1.0:
                                        p.dano = max(1, math.ceil(p.dano * mult_dano_buff))
                                self.projeteis.extend(tiros_esp)
                                self._aplicar_efeitos_disparo_extras(tiros_esp, mods)

        # Atualiza o tempo de vida dos efeitos visuais de Melee
        for ef in self.efeitos_melee:
            ef["tempo"] -= dt
        self.efeitos_melee = [ef for ef in self.efeitos_melee if ef["tempo"] > 0]

        # =========================================================================
        # 3. SPAWNER DE INIMIGOS
        # =========================================================================
        spawn_liberado = getattr(self.menu_debug, "spawn_natural_ativo", True) if hasattr(self, "menu_debug") else True
        if spawn_liberado and not self.boss_cutscene_ativa and self.arena_freeze_timer <= 0.0:
            fogo_cruzado_ranged = (str(self.config_sistema.obter_valor("inimigos_ranged")).lower() in ("ligado", "true", "1")) if hasattr(self, "config_sistema") and self.config_sistema else False
            permitir_ranged = True
            hp_inim_mult = getattr(mods, "hp_inimigos_mult", 1.0) if mods else 1.0
            vel_inim_mult = getattr(mods, "vel_inimigos_mult", 1.0) if mods else 1.0
            possui_elite = any(getattr(e, "is_elite", False) and getattr(e, "vivo", True) for e in self.inimigos) or (self.chefe_final is not None and self.chefe_final.vivo)

            if self.chefe_final is not None and self.chefe_final.vivo:
                if getattr(self.chefe_final, "estado", "") not in ("morte", ESTADO_MORTE):
                    # Durante o Chefe Final: horda de apoio ativa (Padrão, Rápido e Projetor Laser) até 22 mobs
                    from src.entidades.inimigo_padrao import InimigoPadrao
                    from src.entidades.inimigo_rapido import InimigoRapido
                    from src.entidades.inimigo_ranged import InimigoRanged
                    mobs_comuns = [e for e in self.inimigos if e.vivo and e != self.chefe_final and not getattr(e, "is_caixa_som", False)]
                    if len(mobs_comuns) < 22 and random.random() < 0.85 * dt * 4.0:
                        ex, ey = self.spawner.gerar_posicao_spawn(
                            self.camera.x, self.camera.y,
                            view_w=LARGURA_TELA, view_h=ALTURA_TELA,
                            arena_w=self.largura_arena, arena_h=self.altura_arena
                        )
                        r_mob = random.random()
                        if r_mob < 0.25:
                            mob_boss = InimigoRapido(x=ex, y=ey)
                        elif r_mob < 0.38:
                            mob_boss = InimigoRanged(x=ex, y=ey)
                            if fogo_cruzado_ranged:
                                mob_boss.rajada_tripla = True
                        else:
                            mob_boss = InimigoPadrao(x=ex, y=ey)
                        mob_boss.hp_max = max(1, int(round(mob_boss.hp_max * hp_inim_mult)))
                        mob_boss.hp = mob_boss.hp_max
                        mob_boss.velocidade = float(mob_boss.velocidade) * vel_inim_mult
                        self.inimigos.append(mob_boss)
            else:
                novos_inimigos = self.spawner.update(
                    dt=dt,
                    camera_x=self.camera.x,
                    camera_y=self.camera.y,
                    total_inimigos_vivos=len([e for e in self.inimigos if e.vivo]),
                    view_w=LARGURA_TELA,
                    view_h=ALTURA_TELA,
                    arena_w=self.largura_arena,
                    arena_h=self.altura_arena,
                    hp_mult=hp_inim_mult,
                    vel_mult=vel_inim_mult,
                    permitir_ranged=permitir_ranged,
                    possui_elite_vivo=possui_elite
                )
                if fogo_cruzado_ranged:
                    for ni in novos_inimigos:
                        if hasattr(ni, "rajada_tripla"):
                            ni.rajada_tripla = True
                self.inimigos.extend(novos_inimigos)

                # Gatilho "Jogar aos Lobos": após o ciclo dos Mini-Bosses, a Geladeira Tsunami entra mesmo se o jogador estiver em nível baixo
                if self.chefe_final is None and not self.boss_cutscene_ativa and not possui_elite and getattr(self.spawner, "tempo_elite", 0.0) >= 265.0:
                    self.iniciar_boss_cutscene()

        # =========================================================================
        # 4. FÍSICA DOS PROJÉTEIS
        # =========================================================================
        if not self.boss_cutscene_ativa:
            # Sincronização Vertical (Desligado): Linha de tearing que duplica projéteis
            if getattr(mods, "vsync_tear_refraction", False):
                self.vsync_tear_y = (getattr(self, "vsync_tear_y", 0.0) + 160.0 * dt) % ALTURA_TELA
                proj_clones = []
                for proj in self.projeteis:
                    if getattr(proj, "dono", "jogador") == "jogador" and not getattr(proj, "split_done", False):
                        tela_y = proj.y - self.camera.y
                        if abs(tela_y - self.vsync_tear_y) < 18.0:
                            proj.split_done = True
                            ang_r = 0.15
                            cos_r, sin_r = math.cos(ang_r), math.sin(ang_r)
                            vx_d = proj.vx * cos_r - proj.vy * sin_r
                            vy_d = proj.vx * sin_r + proj.vy * cos_r
                            clone = proj.clonar(vx=vx_d, vy=vy_d, cor=(255, 180, 255))
                            clone.split_done = True
                            proj_clones.append(clone)
                if proj_clones:
                    self.projeteis.extend(proj_clones)

            for proj in self.projeteis:
                if getattr(proj, "dono", "jogador") == "inimigo" and self.arena_freeze_timer > 0.0:
                    continue
                proj._x_ant = proj.x
                proj._y_ant = proj.y
                proj.update(dt)
                if getattr(proj, "superaquecido", False) and proj.ativo:
                    self.sistema_particulas.emitir_faiscas(
                        proj.x + proj.largura / 2.0,
                        proj.y + proj.altura / 2.0,
                        dir_x=-proj.dir_x,
                        dir_y=-proj.dir_y,
                        cor=(255, 120, 30),
                        qtd=1
                    )
                # Desativa projéteis que saíram muito longe dos limites da arena
                if (proj.x < -100 or proj.x > self.largura_arena + 100 or
                    proj.y < -100 or proj.y > self.altura_arena + 100):
                    proj.ativo = False

            # Atualiza Zonas de Fogo (Foguetes), Trilhas de Plasma (Railgun), Zonas de Estase (Drone Suporte) e Poças de Gelo (Geladeira)
            if self.aura_cura_timer > 0.0:
                self.aura_cura_timer = max(0.0, self.aura_cura_timer - dt)

            for zf in self.zonas_fogo:
                zf["tempo"] -= dt
                zf["tick"] = zf.get("tick", 0.0) + dt
                if zf["tick"] >= 0.35:
                    zf["tick"] = 0.0
                    for inim_f in self.inimigos:
                        if getattr(inim_f, "vivo", True) and not getattr(inim_f, "em_fase", False):
                            icx = inim_f.x + getattr(inim_f, "largura", 28) / 2.0
                            icy = inim_f.y + getattr(inim_f, "altura", 28) / 2.0
                            if distancia(icx, icy, zf["x"], zf["y"]) <= zf["raio"]:
                                inim_f.receber_dano(10)
                                if not inim_f.vivo:
                                    self._registrar_abate_inimigo(inim_f, mods)
            self.zonas_fogo = [z for z in self.zonas_fogo if z["tempo"] > 0.0]

            for tp in self.trilhas_plasma:
                tp["tempo"] -= dt
            self.trilhas_plasma = [t for t in self.trilhas_plasma if t["tempo"] > 0.0]

            for ze in self.zonas_estase:
                ze["tempo"] -= dt
                for inim_e in self.inimigos:
                    if getattr(inim_e, "vivo", True):
                        icx = inim_e.x + getattr(inim_e, "largura", 28) / 2.0
                        icy = inim_e.y + getattr(inim_e, "altura", 28) / 2.0
                        if distancia(icx, icy, ze["x"], ze["y"]) <= ze["raio"]:
                            inim_e.slow_timer = max(getattr(inim_e, "slow_timer", 0.0), 0.35)
                            inim_e.slow_fator = 0.50
                            inim_e.vulneravel_estase_timer = 0.35
            self.zonas_estase = [z for z in self.zonas_estase if z["tempo"] > 0.0]

            for pg in self.pocas_gelo:
                pg["tempo"] -= dt
                if distancia(centro_jogador_x, centro_jogador_y, pg["x"], pg["y"]) <= pg["raio"]:
                    self.jogador.x -= getattr(self.jogador, "ultima_dir_dx", 0.0) * 45.0 * dt
                    self.jogador.y -= getattr(self.jogador, "ultima_dir_dy", 0.0) * 45.0 * dt
                    self._clamp_entidade_arena(self.jogador)
            self.pocas_gelo = [p for p in self.pocas_gelo if p["tempo"] > 0.0]

        # =========================================================================
        # 5. IA DOS INIMIGOS E DANO DE CONTATO NO JOGADOR
        # =========================================================================
        val_ilum = str(self.config_sistema.obter_valor("iluminacao")).lower() in ("ligado", "true", "1") if hasattr(self, "config_sistema") and self.config_sistema else False
        mult_dano_inim_base = getattr(mods, "dano_inimigos_mult", 1.0) if mods else 1.0

        pular_ia_inimigos = getattr(self.jogador, "stutter_freeze_timer", 0.0) > 0.0 or self.arena_freeze_timer > 0.0

        for inimigo in self.inimigos:
            if inimigo == self.chefe_final:
                continue
            if not pular_ia_inimigos and not self.boss_cutscene_ativa:
                # Passo Fantasma (buff_vel_timer > 0): desacelera inimigos muito próximos em 40%
                if getattr(self.jogador, "buff_vel_timer", 0.0) > 0.0:
                    icx_p = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                    icy_p = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                    if distancia(icx_p, icy_p, centro_jogador_x, centro_jogador_y) <= 95.0:
                        inimigo.slow_timer = max(getattr(inimigo, "slow_timer", 0.0), 0.25)
                        inimigo.slow_fator = min(getattr(inimigo, "slow_fator", 1.0), 0.60)

                inimigo.update(dt, (centro_jogador_x, centro_jogador_y))
                if getattr(inimigo, "explodiu_sobrecarga", False) or getattr(inimigo, "superaqueceu", False):
                    if not getattr(inimigo, "toast_superaquecimento_exibido", False):
                        inimigo.toast_superaquecimento_exibido = True
                        icx_e = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                        icy_e = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                        self.sistema_particulas.emitir_onda_choque(icx_e, icy_e, raio_max=150.0, cor=LARANJA_ALERTA)
                        self.sistema_particulas.emitir_debris(icx_e, icy_e, cor=LARANJA_ALERTA, qtd=18)
                        self.aplicar_shake(14.0, 0.35)
                        if distancia(icx_e, icy_e, centro_jogador_x, centro_jogador_y) <= 150.0:
                            self.jogador.receber_dano(25, causa_morte="Explosão de Mini-Boss (Superaquecimento)")
                        inimigo.vivo = False
                        self.toasts_coleta.append({
                            "texto": "O MINI-BOSS SUPERAQUECEU. VOCÊ NÃO RECEBERÁ RECOMPENSAS POR ELE.",
                            "cor": LARANJA_ALERTA,
                            "x": self.jogador.x + 16,
                            "y": self.jogador.y - 25,
                            "tempo": 3.5,
                            "tempo_max": 3.5
                        })
                        continue
                if getattr(inimigo, "pulso_eletrico_pendente", False):
                    inimigo.pulso_eletrico_pendente = False
                    icx_f = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                    icy_f = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                    self.sistema_particulas.emitir_onda_choque(icx_f, icy_f, raio_max=125.0, cor=LARANJA_ALERTA)
                    if distancia(icx_f, icy_f, centro_jogador_x, centro_jogador_y) <= 125.0:
                        self.jogador.receber_dano(18, causa_morte="Pulso Elétrico (Fonte Genérica 500W)")
                if getattr(inimigo, "projeteis_elite_pendentes", None):
                    self.projeteis.extend(inimigo.projeteis_elite_pendentes)
                    inimigo.projeteis_elite_pendentes.clear()
                if getattr(inimigo, "projeteis_pendentes", None) and getattr(inimigo, "is_caixa_som", False):
                    self.projeteis.extend(inimigo.projeteis_pendentes)
                    inimigo.projeteis_pendentes.clear()
                if hasattr(inimigo, "obter_projeteis_pendentes"):
                    novos_tiros = inimigo.obter_projeteis_pendentes()
                    if novos_tiros:
                        self.projeteis.extend(novos_tiros)

            if self.boss_cutscene_ativa:
                continue

            # Atropelamento (Movimento pelo Mouse)
            if getattr(mods, "movimento_ram_collision", False) and not getattr(inimigo, "is_elite", False):
                if getattr(inimigo, "cooldown_ram_atual", 0.0) <= 0.0:
                    if colisao_aabb(inimigo.x, inimigo.y, inimigo.largura, inimigo.altura,
                                    self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                        i_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                        i_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                        dir_ram_x, dir_ram_y = vetor_direcao(centro_jogador_x, centro_jogador_y, i_cx, i_cy)
                        inimigo.x += dir_ram_x * 24.0
                        inimigo.y += dir_ram_y * 24.0
                        self._clamp_entidade_arena(inimigo)
                        ret_d = inimigo.receber_dano(15, origem_x=centro_jogador_x, origem_y=centro_jogador_y, dir_ataque=(dir_ram_x, dir_ram_y))
                        dano_ram = int(ret_d) if isinstance(ret_d, (int, float)) else 15
                        inimigo.cooldown_ram_atual = 0.35
                        self.dano_total_causado += dano_ram
                        if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                            self.sistema_particulas.emitir_texto_dano(
                                inimigo.x + getattr(inimigo, "largura", 28) / 2.0,
                                inimigo.y,
                                dano_ram,
                                critico=False
                            )
                        if not inimigo.vivo:
                            self._registrar_abate_inimigo(inimigo, mods)
                            continue

            # Checa dano de contato com reduções da configuração (Iluminação fora de visão)
            if inimigo.vivo and colisao_aabb(inimigo.x, inimigo.y, inimigo.largura, inimigo.altura,
                            self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                if getattr(inimigo, "cooldown_contato_atual", 0.0) <= 0.0:
                    dano_contato_base = getattr(inimigo, "dano_contato", 10)
                    mult_dano_inim = mult_dano_inim_base
                    if val_ilum:
                        dist_vis = distancia(inimigo.x + inimigo.largura / 2.0, inimigo.y + inimigo.altura / 2.0, centro_jogador_x, centro_jogador_y)
                        if dist_vis > 195.0:
                            mult_dano_inim *= getattr(mods, "dano_fora_visao_mult", 0.50)
                    dano_efetivo_contato = max(1, int(round(dano_contato_base * mult_dano_inim)))
                    nome_inim = getattr(inimigo, "nome_elite", "") or getattr(inimigo, "nome_exibicao", "") or type(inimigo).__name__
                    self.jogador.receber_dano(dano_efetivo_contato, causa_morte=f"Contato com {nome_inim}")
                    inimigo.cooldown_contato_atual = getattr(inimigo, "cooldown_contato_max", 0.4)
                    self.aplicar_shake(6.0, 0.15)
                    # Casco Eletrostático (buff_resistencia_timer > 0): empurra e dá choque em quem encostar
                    if getattr(self.jogador, "buff_resistencia_timer", 0.0) > 0.0 and not getattr(inimigo, "is_boss", False):
                        icx_c = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                        icy_c = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                        dx_c, dy_c = vetor_direcao(centro_jogador_x, centro_jogador_y, icx_c, icy_c)
                        inimigo.x += dx_c * 32.0
                        inimigo.y += dy_c * 32.0
                        self._clamp_entidade_arena(inimigo)
                        inimigo.receber_dano(12)
                        self.sistema_particulas.emitir_faiscas(icx_c, icy_c, dir_x=dx_c, dir_y=dy_c, cor=(80, 255, 160), qtd=6)
                        if not inimigo.vivo:
                            self._registrar_abate_inimigo(inimigo, mods)

        # Atualização do Chefe Final (Geladeira Tsunami)
        _boss_pode_atualizar = (
            self.chefe_final is not None
            and self.chefe_final.vivo
            and (not self.boss_cutscene_ativa or (self.boss_cutscene_fase == "musica_in" and self.chefe_final.estado == "intro"))
        )
        if _boss_pode_atualizar and (not pular_ia_inimigos or self.chefe_final.estado == "intro"):
            self.chefe_final.update(dt, (centro_jogador_x, centro_jogador_y), limite_arena=(self.largura_arena, self.altura_arena))
            novos_tiros_boss = self.chefe_final.obter_projeteis_pendentes()
            if novos_tiros_boss:
                self.projeteis.extend(novos_tiros_boss)
            if getattr(self.chefe_final, "caixas_som_pendentes", None):
                caixas_ativas = [e for e in self.inimigos if getattr(e, "vivo", True) and getattr(e, "is_caixa_som", False)]
                for cx_som in self.chefe_final.caixas_som_pendentes:
                    if len(caixas_ativas) < 4:
                        self.inimigos.append(cx_som)
                        caixas_ativas.append(cx_som)
                self.chefe_final.caixas_som_pendentes.clear()
            if getattr(self.chefe_final, "pocas_gelo_pendentes", None):
                self.pocas_gelo.extend(self.chefe_final.pocas_gelo_pendentes)
                self.chefe_final.pocas_gelo_pendentes.clear()
            if getattr(self.chefe_final, "pulso_empurrao_pendente", False):
                self.chefe_final.pulso_empurrao_pendente = False
                bcx = self.chefe_final.x + self.chefe_final.largura / 2.0
                bcy = self.chefe_final.y + self.chefe_final.altura / 2.0
                if distancia(bcx, bcy, centro_jogador_x, centro_jogador_y) <= 210.0:
                    dx_b, dy_b = vetor_direcao(bcx, bcy, centro_jogador_x, centro_jogador_y)
                    if hasattr(self.jogador, "aplicar_knockback"):
                        self.jogador.aplicar_knockback(dx_b, dy_b, forca=360.0)
                    else:
                        self.jogador.x += dx_b * 46.0
                        self.jogador.y += dy_b * 46.0
                        self._clamp_entidade_arena(self.jogador)
            if getattr(self.chefe_final, "vortice_succao_ativo", False) and not self.boss_cutscene_ativa:
                bcx = self.chefe_final.x + self.chefe_final.largura / 2.0
                bcy = self.chefe_final.y + self.chefe_final.altura / 2.0
                dx_v, dy_v = vetor_direcao(centro_jogador_x, centro_jogador_y, bcx, bcy)
                self.jogador.x += dx_v * 65.0 * dt
                self.jogador.y += dy_v * 65.0 * dt
                self._clamp_entidade_arena(self.jogador)
            shake_boss = self.chefe_final.obter_shake_pendente()
            if shake_boss > 0.0:
                self.aplicar_shake(shake_boss, 0.35)

        # Condição de vitória: avaliada imediatamente após chefe_final.update(dt) (antes de game_over)
        if self.chefe_final is not None and not self.chefe_final.vivo and not self.vitoria and self.jogador.vivo:
            if not getattr(self.chefe_final, "_abate_contabilizado", False):
                self.chefe_final._abate_contabilizado = True
                self.abates += 1
                self.pontos += getattr(self.chefe_final, "score_valor", 5000)
            self.vitoria = True
            self._acionar_vitoria()
            return

        # Checa dano de contato com o Chefe Final (sempre que o chefe estiver vivo e em combate)
        if (self.chefe_final is not None and self.chefe_final.vivo
                and not self.boss_cutscene_ativa and not self.pausado
                and getattr(self.chefe_final, "estado", "") not in ("morte", ESTADO_MORTE)):
            if colisao_aabb(self.chefe_final.x, self.chefe_final.y, self.chefe_final.largura, self.chefe_final.altura,
                            self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                if getattr(self.chefe_final, "cooldown_contato_atual", 0.0) <= 0.0:
                    dano_contato_base = getattr(self.chefe_final, "dano_contato", 25)
                    mult_dano_inim = mult_dano_inim_base
                    if val_ilum:
                        dist_vis = distancia(self.chefe_final.x + self.chefe_final.largura / 2.0, self.chefe_final.y + self.chefe_final.altura / 2.0, centro_jogador_x, centro_jogador_y)
                        if dist_vis > 195.0:
                            mult_dano_inim *= getattr(mods, "dano_fora_visao_mult", 0.50)
                    dano_efetivo_contato = max(1, int(round(dano_contato_base * mult_dano_inim)))
                    nome_inim = getattr(inimigo, "nome_elite", "") or getattr(inimigo, "nome_exibicao", "") or type(inimigo).__name__
                    self.jogador.receber_dano(dano_efetivo_contato, causa_morte=f"Contato com {nome_inim}")
                    self.chefe_final.cooldown_contato_atual = getattr(self.chefe_final, "cooldown_contato_max", 0.4)
                    self.aplicar_shake(10.0, 0.25)

        # =========================================================================
        # 6. COLISÕES: PROJÉTEIS VS INIMIGOS E DETONAÇÃO DE EXPLOSIVOS
        # =========================================================================
        mult_explosivo = getattr(mods, "dano_explosivos_mult", 1.0) if mods else 1.0
        auto_dano = getattr(mods, "auto_dano", False) if mods else False

        for proj in list(self.projeteis):
            if self.boss_cutscene_ativa:
                break
            if not proj.ativo and not getattr(proj, "requer_detonacao_ao_expirar", False):
                continue

            vel = float(getattr(proj, "velocidade", 0.0))
            largura_proj = max(1.0, float(getattr(proj, "largura", 8)))
            dist_frame = vel * dt

            x_fim = proj.x
            y_fim = proj.y
            x_ini = getattr(proj, "_x_ant", x_fim - getattr(proj, "dir_x", 0.0) * dist_frame)
            y_ini = getattr(proj, "_y_ant", y_fim - getattr(proj, "dir_y", 0.0) * dist_frame)

            if dist_frame > largura_proj:
                num_passos = max(1, int(math.ceil(dist_frame / largura_proj)))
                passos = [
                    (x_ini + (x_fim - x_ini) * (s / num_passos),
                     y_ini + (y_fim - y_ini) * (s / num_passos))
                    for s in range(1, num_passos + 1)
                ]
            else:
                passos = [(x_fim, y_fim)]

            for sub_x, sub_y in passos:
                if not proj.ativo and not getattr(proj, "requer_detonacao_ao_expirar", False):
                    break
                proj.x = sub_x
                proj.y = sub_y

                # Projéteis de inimigos podem ser bloqueados por núcleos de Multithreading (1 a cada 4s) ou causam dano ao jogador
                if getattr(proj, "dono", "jogador") == "inimigo":
                    if getattr(self.jogador, "vivo", True) and getattr(self.jogador, "multithreading", False) and getattr(self.jogador, "coprocessador_escudo_timer", 0.0) <= 0.0:
                        px_c = proj.x + proj.largura / 2.0
                        py_c = proj.y + proj.altura / 2.0
                        bloqueado_cop = False
                        for ang_cop in getattr(self.jogador, "coprocessadores_angulos", [0.0, 3.14159]):
                            cop_x = centro_jogador_x + math.cos(ang_cop) * 34.0
                            cop_y = centro_jogador_y + math.sin(ang_cop) * 34.0
                            if distancia(px_c, py_c, cop_x, cop_y) <= 18.0:
                                self.jogador.coprocessador_escudo_timer = 4.0
                                self.sistema_particulas.emitir_faiscas(cop_x, cop_y, cor=(0, 240, 255), qtd=8)
                                proj.ativo = False
                                bloqueado_cop = True
                                break
                        if bloqueado_cop:
                            break
                    if getattr(self.jogador, "vivo", True) and colisao_aabb(
                        proj.x, proj.y, proj.largura, proj.altura,
                        self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura
                    ):
                        mult_dano_inim = mult_dano_inim_base
                        if val_ilum:
                            ox = getattr(proj, "x_origem", proj.x + proj.largura / 2.0)
                            oy = getattr(proj, "y_origem", proj.y + proj.altura / 2.0)
                            dist_vis = distancia(ox, oy, centro_jogador_x, centro_jogador_y)
                            if dist_vis > 195.0:
                                mult_dano_inim *= getattr(mods, "dano_fora_visao_mult", 0.50)
                        dano_proj = max(1, int(round(proj.dano * mult_dano_inim)))
                        self.jogador.receber_dano(dano_proj, causa_morte="Projétil Inimigo / Ondas da Geladeira")
                        self.aplicar_shake(6.0, 0.15)
                        proj.ativo = False
                        break
                    continue

                if getattr(proj, "explosivo", False):
                    alvo_direto = None
                    detonar = False
                    p_cx = proj.x + proj.largura / 2.0
                    p_cy = proj.y + proj.altura / 2.0
                    r_exp = getattr(proj, "raio_explosao", 80.0)

                    for inimigo in self.inimigos:
                        if not inimigo.vivo or getattr(inimigo, "em_fase", False) or getattr(inimigo, "estado", "") in ("morte", ESTADO_MORTE):
                            continue
                        if colisao_aabb(
                            proj.x, proj.y, proj.largura, proj.altura,
                            inimigo.x, inimigo.y, inimigo.largura, inimigo.altura
                        ):
                            alvo_direto = inimigo
                            detonar = True
                            break

                    if not detonar and auto_dano and getattr(proj, "dono", "jogador") == "jogador":
                        dist_origem = distancia(proj.x, proj.y, getattr(proj, "x_origem", proj.x), getattr(proj, "y_origem", proj.y))
                        if (dist_origem >= 42.0 or (proj.tempo_vida - proj.tempo_vida_restante > 0.20)) and getattr(self.jogador, "vivo", True):
                            if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                                detonar = True
                        if not detonar:
                            drones_exp = list(self.jogador.drones) if (hasattr(self.jogador, "drones") and self.jogador.drones) else ([self.jogador.drone] if getattr(self.jogador, "drone", None) is not None else [])
                            for dr in drones_exp:
                                if getattr(dr, "ativo", True) and colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, dr.x, dr.y, dr.largura, dr.altura):
                                    detonar = True
                                    break

                    if detonar or proj.tempo_vida_restante <= 0.0 or getattr(proj, "requer_detonacao_ao_expirar", False):
                        proj.ativo = False
                        proj.requer_detonacao_ao_expirar = False
                        self.sistema_particulas.emitir_onda_choque(p_cx, p_cy, raio_max=r_exp)
                        self.sistema_particulas.emitir_debris(p_cx, p_cy, cor=(255, 140, 40), qtd=12)
                        self.aplicar_shake(10.0, 0.25)

                        # Lança-Foguetes: Zona de chão em chamas por 2.5s
                        if getattr(proj, "chao_em_chamas", False):
                            self.zonas_fogo.append({
                                "x": p_cx,
                                "y": p_cy,
                                "raio": 72.0,
                                "tempo": 2.5,
                                "tempo_max": 2.5,
                                "tick": 0.0
                            })

                        # Lança-Granadas: 3 sub-explosões de fragmentação
                        if getattr(proj, "fragmentar", False):
                            for i_frag in range(3):
                                ang_f = i_frag * (2.0 * math.pi / 3.0) + 0.4
                                fx = p_cx + math.cos(ang_f) * 42.0
                                fy = p_cy + math.sin(ang_f) * 42.0
                                self.sistema_particulas.emitir_onda_choque(fx, fy, raio_max=38.0, cor=LARANJA_ALERTA)
                                for inim_fr in self.inimigos:
                                    if getattr(inim_fr, "vivo", True) and not getattr(inim_fr, "em_fase", False):
                                        if distancia(fx, fy, inim_fr.x + getattr(inim_fr, "largura", 28) / 2.0, inim_fr.y + getattr(inim_fr, "altura", 28) / 2.0) <= 45.0:
                                            inim_fr.receber_dano(15)
                                            if not inim_fr.vivo:
                                                self._registrar_abate_inimigo(inim_fr, mods)

                        # Onda de Choque (Tremor de Tela Ligado): tropeço/slow em inimigos próximos (sem empurrar Boss)
                        if getattr(mods, "screen_shake_stagger", False):
                            for inim_st in self.inimigos:
                                if not inim_st.vivo or inim_st is self.chefe_final or getattr(inim_st, "is_boss", False):
                                    continue
                                st_cx = inim_st.x + getattr(inim_st, "largura", 28) / 2.0
                                st_cy = inim_st.y + getattr(inim_st, "altura", 28) / 2.0
                                if distancia(st_cx, st_cy, p_cx, p_cy) < 140.0:
                                    dir_st_x, dir_st_y = vetor_direcao(p_cx, p_cy, st_cx, st_cy)
                                    inim_st.x += dir_st_x * 22.0
                                    inim_st.y += dir_st_y * 22.0
                                    self._clamp_entidade_arena(inim_st)
                                    inim_st.slow_timer = max(getattr(inim_st, "slow_timer", 0.0), 1.5)
                                    inim_st.slow_fator = 0.50
                                    inim_st.cooldown_contato_atual = max(getattr(inim_st, "cooldown_contato_atual", 0.0), 0.6)

                        hp_antes_map = {id(e): getattr(e, "hp", 0) for e in self.inimigos if getattr(e, "vivo", True)}
                        afetados = proj.explodir(
                            self.inimigos,
                            jogador=self.jogador,
                            config_sistema=self.config_sistema,
                            mult_dano_explosivo=mult_explosivo,
                            alvo_direto=alvo_direto
                        )

                        # Rocket-Jump (Fogo Amigo Ligado) com animação suave de knockback
                        if getattr(mods, "fogo_amigo_rocket_jump", False) and distancia(p_cx, p_cy, centro_jogador_x, centro_jogador_y) < r_exp:
                            dir_rj_x, dir_rj_y = vetor_direcao(p_cx, p_cy, centro_jogador_x, centro_jogador_y)
                            if hasattr(self.jogador, "aplicar_knockback"):
                                self.jogador.aplicar_knockback(dir_rj_x, dir_rj_y, forca=420.0)
                                self.sistema_particulas.emitir_faiscas(centro_jogador_x, centro_jogador_y, dir_x=dir_rj_x, dir_y=dir_rj_y, cor=(255, 190, 90), qtd=8)
                            else:
                                self.jogador.x += dir_rj_x * 48.0
                                self.jogador.y += dir_rj_y * 48.0
                                self._clamp_entidade_arena(self.jogador)

                        for inim in afetados:
                            dano_base_exp = int(getattr(proj, "dano", 35) * mult_explosivo)
                            dano_prev = dano_base_exp * 2 if (inim is alvo_direto) else dano_base_exp
                            hp_ant = hp_antes_map.get(id(inim))
                            dano_exp = max(0, int(hp_ant - getattr(inim, "hp", 0))) if hp_ant is not None and hp_ant > getattr(inim, "hp", 0) else dano_prev
                            is_crit_exp = (inim is alvo_direto)
                            self.dano_total_causado += dano_exp
                            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                self.sistema_particulas.emitir_texto_dano(
                                    inim.x + getattr(inim, "largura", 28) / 2.0,
                                    inim.y,
                                    dano_exp,
                                    critico=is_crit_exp
                                )
                            if is_crit_exp:
                                self._aplicar_overvolt_chain(inim, dano_exp, mods)
                            if not inim.vivo:
                                self._registrar_abate_inimigo(inim, mods)
                        break
                else:
                    for inimigo in self.inimigos:
                        if not inimigo.vivo or getattr(inimigo, "estado", "") in ("morte", ESTADO_MORTE):
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
                            elif getattr(proj, "perfuracoes_restantes", 0) > 0:
                                if not hasattr(proj, "alvos_atingidos"):
                                    proj.alvos_atingidos = set()
                                if id(inimigo) in proj.alvos_atingidos:
                                    continue
                                proj.alvos_atingidos.add(id(inimigo))
                                proj.perfuracoes_restantes -= 1
                            else:
                                proj.ativo = False

                            chance_crit_proj = max(crit_chance, float(getattr(proj, "chance_critico_arma", 0.0)))
                            is_crit = bool(getattr(proj, "critico_nativo", False)) or (chance_crit_proj > 0.0 and random.random() < chance_crit_proj)
                            mult_estase = 1.20 if getattr(inimigo, "vulneravel_estase_timer", 0.0) > 0.0 else 1.0
                            dano_final = int(round(proj.dano * mult_estase * (crit_mult if is_crit else 1.0)))

                            dx_k, dy_k = getattr(proj, "dir_x", 0.0), getattr(proj, "dir_y", 0.0)

                            # Knockback individual por pellet (Escopeta / Drone de Combate)
                            kb_proj = float(getattr(proj, "knockback_forca", 0.0))
                            if kb_proj > 0.0 and inimigo is not self.chefe_final and not getattr(inimigo, "is_boss", False):
                                inimigo.x += dx_k * (kb_proj * 0.45)
                                inimigo.y += dy_k * (kb_proj * 0.45)
                                self._clamp_entidade_arena(inimigo)

                            # Números de Dano (Texto com Peso): Empurrão leve no inimigo (exceto Boss)
                            if getattr(mods, "damage_numbers_knockback", False) and inimigo is not self.chefe_final and not getattr(inimigo, "is_boss", False):
                                if dx_k != 0.0 or dy_k != 0.0:
                                    inimigo.x += dx_k * 14.0
                                    inimigo.y += dy_k * 14.0
                                    self._clamp_entidade_arena(inimigo)

                            # Tremor de Tela (screen_shake_stagger): estendido para tiros balísticos (exceto Boss)
                            if getattr(mods, "screen_shake_stagger", False) and inimigo is not self.chefe_final and not getattr(inimigo, "is_boss", False):
                                if dx_k != 0.0 or dy_k != 0.0:
                                    inimigo.x += dx_k * 10.0
                                    inimigo.y += dy_k * 10.0
                                    self._clamp_entidade_arena(inimigo)
                                inimigo.slow_timer = max(getattr(inimigo, "slow_timer", 0.0), 1.2)
                                inimigo.slow_fator = 0.50

                            ret_d = inimigo.receber_dano(
                                dano_final,
                                origem_x=proj.x,
                                origem_y=proj.y,
                                dir_ataque=(dx_k, dy_k)
                            )
                            dano_efetivo_b = int(ret_d) if isinstance(ret_d, (int, float)) else dano_final

                            self.dano_total_causado += dano_efetivo_b
                            self.sistema_particulas.emitir_faiscas(
                                proj.x, proj.y,
                                dir_x=dx_k,
                                dir_y=dy_k,
                                cor=(255, 220, 100),
                                qtd=6
                            )
                            if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                self.sistema_particulas.emitir_texto_dano(
                                    inimigo.x + getattr(inimigo, "largura", 28) / 2.0,
                                    inimigo.y,
                                    dano_efetivo_b,
                                    critico=is_crit
                                )

                            # Overvolt (Tensão Crítica): Faíscas elétricas em cadeia em acertos críticos
                            if is_crit:
                                self._aplicar_overvolt_chain(inimigo, dano_efetivo_b, mods)

                            if not inimigo.vivo:
                                self._registrar_abate_inimigo(inimigo, mods)

                            if not getattr(proj, "perfurante", False):
                                break

                    if not proj.ativo:
                        break

                # Fogo Amigo balístico para projéteis do jogador (após carência >= 42px para o jogador e >= 48px para drones)
                if auto_dano and proj.ativo and getattr(proj, "dono", "jogador") == "jogador":
                    dist_origem = distancia(proj.x, proj.y, getattr(proj, "x_origem", proj.x), getattr(proj, "y_origem", proj.y))
                    if dist_origem >= 42.0 or (proj.tempo_vida - proj.tempo_vida_restante > 0.20):
                        if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                            if getattr(proj, "perfurante", False):
                                if not hasattr(proj, "alvos_atingidos"):
                                    proj.alvos_atingidos = set()
                                if "jogador" not in proj.alvos_atingidos:
                                    proj.alvos_atingidos.add("jogador")
                                    self.jogador.receber_dano(proj.dano, causa_morte="Fogo Amigo (Seu próprio projétil)")
                                    self.aplicar_shake(6.0, 0.15)
                            else:
                                self.jogador.receber_dano(proj.dano, causa_morte="Fogo Amigo (Seu próprio projétil)")
                                self.aplicar_shake(6.0, 0.15)
                                proj.ativo = False
                                break

                    # Destruição de drones companheiros por fogo amigo (evitando auto-colisão do próprio DroneCombate no spawn)
                    if getattr(proj, "sprite_key", "") != "projetil_drone" or dist_origem >= 28.0:
                        drones_list = []
                        if hasattr(self.jogador, "drones") and self.jogador.drones:
                            drones_list = list(self.jogador.drones)
                        elif getattr(self.jogador, "drone", None) is not None:
                            drones_list = [self.jogador.drone]

                        for dr in drones_list:
                            if getattr(dr, "ativo", True):
                                if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura, dr.x, dr.y, dr.largura, dr.altura):
                                    dr.receber_dano(proj.dano)
                                    if not getattr(proj, "perfurante", False):
                                        proj.ativo = False
                                        break
                    if not proj.ativo:
                        break

            if proj.ativo:
                proj.x = x_fim
                proj.y = y_fim

        # Limpeza de entidades destruídas / inativas
        self.projeteis = [p for p in self.projeteis if p.ativo]
        self.inimigos = [e for e in self.inimigos if e.vivo]

        # =========================================================================
        # 7. SISTEMA DE DROPS E PROGRESSÃO DE XP
        # =========================================================================
        is_boss_lutando = (self.chefe_final is not None and self.chefe_final.vivo)
        mult_drops = getattr(mods, "drops_valor_mult", 1.0) if mods else 1.0
        mult_xp = getattr(mods, "xp_ganho_mult", 1.0) if mods else 1.0
        self.sistema_drops.update(dt, pausar_despawn=is_boss_lutando)
        eventos_coleta = self.sistema_drops.coletar_jogador(self.jogador, mult_valor_drop=mult_drops, mult_xp=mult_xp)
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
                arma_coletada = ev.get("arma") or self.jogador.arma_especial
                nome_arma = getattr(arma_coletada, "nome", "Arma Especial")
                mun = getattr(arma_coletada, "municao_max", 30)
                self.toasts_coleta.append({
                    "texto": f"{nome_arma} ({mun})",
                    "cor": DOURADO,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 15,
                    "tempo": 1.8,
                    "tempo_max": 1.8
                })
            elif ev["tipo"] == "equipamento":
                nome_drone = "Drone"
                if hasattr(self.jogador, "drones") and self.jogador.drones:
                    nome_drone = getattr(self.jogador.drones[-1], "nome", "Drone")
                elif hasattr(self.jogador, "drone") and self.jogador.drone:
                    nome_drone = getattr(self.jogador.drone, "nome", "Drone")
                self.toasts_coleta.append({
                    "texto": f"{nome_drone} (30s)",
                    "cor": (255, 160, 50),
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 15,
                    "tempo": 1.8,
                    "tempo_max": 1.8
                })
            elif ev["tipo"] == "overclock":
                self.toasts_coleta.append({
                    "texto": "NÚCLEO DE OVERCLOCK OBTIDO!",
                    "cor": (215, 140, 255),
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 20,
                    "tempo": 2.5,
                    "tempo_max": 2.5
                })
                self.modal_overclock.abrir()
                self.pausado = True
            elif ev["tipo"] == "capsula_powerup":
                drop_obj = ev.get("drop")
                sub = getattr(drop_obj, "subtipo", "buff_dano_temp") if drop_obj else "buff_dano_temp"
                rotulo = getattr(drop_obj, "rotulo", "Suprimento") if drop_obj else "Suprimento"
                if sub == "buff_dano_temp":
                    self.jogador.buff_dano_timer = 15.0
                elif sub == "buff_vel_temp":
                    self.jogador.buff_vel_timer = 15.0
                elif sub == "buff_cadencia_temp":
                    self.jogador.buff_cadencia_timer = 15.0
                elif sub == "buff_resistencia_temp":
                    self.jogador.buff_resistencia_timer = 15.0
                elif sub in ("cura_pequena", "cura"):
                    self.jogador.curar(25)
                elif sub == "cura_grande":
                    self.jogador.curar(50)
                elif sub in ("xp_pequeno", "xp"):
                    self.jogador.ganhar_xp(15, mult_xp=mult_xp)
                elif sub == "xp_grande":
                    self.jogador.ganhar_xp(30, mult_xp=mult_xp)
                elif sub == "escudo":
                    self.jogador.escudo_ativo = True
                elif sub == "pulso_magnetico":
                    self.jogador.aplicar_pulso_magnetico(self.sistema_drops.drops)
                elif sub == "caixa_arma":
                    nova_a = random.choice([Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun])()
                    self.jogador.equipar_arma_especial(nova_a)
                elif sub == "caixa_equip":
                    novo_d = random.choice([DroneCura, DroneCombate, DroneSuporte])(tempo_vida=30.0)
                    self.jogador.adicionar_drone(novo_d)
                self.toasts_coleta.append({
                    "texto": f"{rotulo} ATIVO!",
                    "cor": AZUL_CIANO,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 16,
                    "tempo": 1.6,
                    "tempo_max": 1.6
                })

        # Atualiza IA do Scavenger APENAS se a configuração "coleta_inimiga" estiver desbloqueada e ligada
        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None
        val_coleta = str(self.config_sistema.obter_valor("coleta_inimiga")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        coleta_ativa = getattr(mods, "coleta_inimiga", False) or (val_coleta in ("ligado", "true", "1"))
        if coleta_ativa:
            self.sistema_scavenger.update(dt, self.inimigos, self.sistema_drops.drops, mover_manualmente=False)
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

        # Propagação da flag graficos_qualidade == "baixa"
        baixa_qualidade = (str(self.config_sistema.obter_valor("graficos_qualidade")).lower() == "baixa") if hasattr(self, "config_sistema") and self.config_sistema else False
        if hasattr(self, "janela") and self.janela:
            self.janela.low_graphics = baixa_qualidade
        if hasattr(self, "sistema_particulas") and self.sistema_particulas:
            self.sistema_particulas.low_graphics = baixa_qualidade

        # =========================================================================
        # CAMADA 1: ESPAÇO DO MUNDO (TRANSFORMADO PELA CÂMERA, COM SUPORTE A ZOOM 75% FOV REAL)
        # =========================================================================
        val_zoom = str(self.config_sistema.obter_valor("zoom")) if hasattr(self, "config_sistema") and self.config_sistema else "100%"
        cam_orig_x = self.camera.x
        cam_orig_y = self.camera.y
        cam_orig_w = getattr(self.camera, "largura", LARGURA_TELA)
        cam_orig_h = getattr(self.camera, "altura", ALTURA_TELA)
        jan_orig_w = getattr(self.janela, "largura", LARGURA_TELA)
        jan_orig_h = getattr(self.janela, "altura", ALTURA_TELA)

        if val_zoom == "75%":
            view_w, view_h, cam_base_x, cam_base_y = self._obter_viewport_zoom75()
            if self._zoom75_surf is None or self._zoom75_surf.get_size() != (view_w, view_h):
                self._zoom75_surf = pygame.Surface((view_w, view_h))
            world_surf = self._zoom75_surf
            self.camera.x = cam_base_x
            self.camera.y = cam_base_y
            self.camera.largura = view_w
            self.camera.altura = view_h
            self.janela.screen = world_surf
            self.janela.largura = view_w
            self.janela.altura = view_h
        else:
            view_w, view_h = LARGURA_TELA, ALTURA_TELA
            world_surf = screen

        # Screen Shake: aplica jitter temporário à câmera durante renderização do mundo
        if self.shake_timer > 0.0 and self.shake_intensidade > 0.0:
            self.camera.x += random.uniform(-self.shake_intensidade, self.shake_intensidade)
            self.camera.y += random.uniform(-self.shake_intensidade, self.shake_intensidade)

        # Fundo da arena
        world_surf.fill(CINZA_FUNDO)

        # Renderização do piso ladrilhado visível (ou grade fallback / baixa qualidade)
        tile_tam = 32
        inicio_tx = max(0, int(self.camera.x // tile_tam))
        fim_tx = min(int(self.largura_arena // tile_tam), int((self.camera.x + view_w) // tile_tam) + 1)
        inicio_ty = max(0, int(self.camera.y // tile_tam))
        fim_ty = min(int(self.altura_arena // tile_tam), int((self.camera.y + view_h) // tile_tam) + 1)

        if self._tile_piso is not None and not baixa_qualidade:
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    world_surf.blit(self._tile_piso, (self.camera.transform_x(wx), self.camera.transform_y(wy)))
        else:
            # Grade fallback caso textura não esteja em RAM ou graficos_qualidade == "baixa"
            for tx in range(inicio_tx, fim_tx):
                for ty in range(inicio_ty, fim_ty):
                    wx = tx * tile_tam
                    wy = ty * tile_tam
                    dx = self.camera.transform_x(wx)
                    dy = self.camera.transform_y(wy)
                    pygame.draw.rect(world_surf, (28, 32, 42), (dx, dy, tile_tam, tile_tam), 1)

        # Linhas delimitadoras da arena
        borda_x0 = self.camera.transform_x(0)
        borda_y0 = self.camera.transform_y(0)
        pygame.draw.rect(world_surf, AZUL_CIANO, (borda_x0, borda_y0, self.largura_arena, self.altura_arena), width=3)

        # Posição virtual do cursor do mouse em coordenadas de mundo (respeitando keybinds e zoom)
        val_keybinds_draw = str(self.config_sistema.obter_valor("keybinds")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "padrao"
        cx_mundo = self.jogador.x + self.jogador.largura / 2.0
        cy_mundo = self.jogador.y + self.jogador.altura / 2.0
        if val_keybinds_draw == "uma_mao":
            dir_mov_d = getattr(self.jogador, "dir_movimento", (0.0, -1.0))
            dmx, dmy = float(dir_mov_d[0]), float(dir_mov_d[1])
            if dmx == 0.0 and dmy == 0.0:
                dmx, dmy = 0.0, -1.0
            mouse_mundo_x = cx_mundo + dmx * 160.0
            mouse_mundo_y = cy_mundo + dmy * 160.0
        else:
            try:
                mx, my = self.mouse.get_position()
                if val_keybinds_draw == "pesadelo":
                    my = ALTURA_TELA - my
            except Exception:
                mx, my = (LARGURA_TELA / 2.0, ALTURA_TELA / 2.0)
            # Restaura temporariamente camera.x/y base para _obter_mouse_mundo
            _cur_cx, _cur_cy = self.camera.x, self.camera.y
            self.camera.x, self.camera.y = cam_orig_x, cam_orig_y
            mouse_mundo_x, mouse_mundo_y = self._obter_mouse_mundo(mx, my)
            self.camera.x, self.camera.y = _cur_cx, _cur_cy

        # Indicador de alcance Melee quando empunhada (Antes do golpe - Cone direcional)
        arma_ativa = self.jogador.obter_arma_ativa()
        if (isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1) and self.jogador.vivo:
            raio = getattr(arma_ativa, "alcance", 84.0)
            arco = getattr(arma_ativa, "arco_graus", 45.0)
            cx_tela = int(self.camera.transform_x(cx_mundo))
            cy_tela = int(self.camera.transform_y(cy_mundo))

            ang_centro = math.atan2(mouse_mundo_y - cy_mundo, mouse_mundo_x - cx_mundo)
            meio_arco = math.radians(arco / 2.0)

            surf_dim = int(raio * 2 + 16)
            if surf_dim not in self._melee_surf_cache:
                self._melee_surf_cache[surf_dim] = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            surf_alcance = self._melee_surf_cache[surf_dim]
            surf_alcance.fill((0, 0, 0, 0))
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
            world_surf.blit(surf_alcance, (cx_tela - s_cx, cy_tela - s_cy))

        # Efeitos visuais de golpe Melee (Depois / Durante o golpe - Slash Fan)
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
            if surf_dim not in self._melee_surf_cache:
                self._melee_surf_cache[surf_dim] = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
            surf_golpe = self._melee_surf_cache[surf_dim]
            surf_golpe.fill((0, 0, 0, 0))
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
            world_surf.blit(surf_golpe, (cx_tela - s_cx, cy_tela - s_cy))

        # Zonas de Efeito no Piso (Poças de Gelo, Zonas de Estase, Zonas de Fogo, Trilhas de Plasma, Aura de Cura e Lasers)
        for pg in self.pocas_gelo:
            px_t = int(self.camera.transform_x(pg["x"]))
            py_t = int(self.camera.transform_y(pg["y"]))
            r_pg = int(pg["raio"])
            pygame.draw.circle(world_surf, (45, 110, 165), (px_t, py_t), r_pg)
            pygame.draw.circle(world_surf, (130, 220, 255), (px_t, py_t), r_pg, width=2)

        for ze in self.zonas_estase:
            zx_t = int(self.camera.transform_x(ze["x"]))
            zy_t = int(self.camera.transform_y(ze["y"]))
            r_ze = int(ze["raio"])
            pygame.draw.circle(world_surf, (20, 75, 120), (zx_t, zy_t), r_ze, width=2)
            pygame.draw.circle(world_surf, (56, 189, 248), (zx_t, zy_t), max(4, int(r_ze * 0.65)), width=1)

        for zf in self.zonas_fogo:
            fx_t = int(self.camera.transform_x(zf["x"]))
            fy_t = int(self.camera.transform_y(zf["y"]))
            r_zf = int(zf["raio"])
            pygame.draw.circle(world_surf, (95, 32, 12), (fx_t, fy_t), r_zf)
            pygame.draw.circle(world_surf, (255, 115, 25), (fx_t, fy_t), r_zf, width=2)

        for tp in self.trilhas_plasma:
            tx1 = int(self.camera.transform_x(tp["x1"]))
            ty1 = int(self.camera.transform_y(tp["y1"]))
            tx2 = int(self.camera.transform_x(tp["x2"]))
            ty2 = int(self.camera.transform_y(tp["y2"]))
            w_p = max(1, int(4 * (tp["tempo"] / max(0.01, tp["tempo_max"]))))
            pygame.draw.line(world_surf, (56, 189, 248), (tx1, ty1), (tx2, ty2), width=w_p + 2)
            pygame.draw.line(world_surf, (255, 255, 255), (tx1, ty1), (tx2, ty2), width=w_p)

        # Laser guia ciano fino da Railgun enquanto carrega
        if arma_ativa is not None and getattr(arma_ativa, "carregando", False) and self.jogador.vivo:
            cx_rg = int(self.camera.transform_x(cx_mundo))
            cy_rg = int(self.camera.transform_y(cy_mundo))
            ang_rg = math.atan2(mouse_mundo_y - cy_mundo, mouse_mundo_x - cx_mundo)
            lx_rg = int(cx_rg + math.cos(ang_rg) * 900.0)
            ly_rg = int(cy_rg + math.sin(ang_rg) * 900.0)
            pygame.draw.line(world_surf, (0, 220, 255), (cx_rg, cy_rg), (lx_rg, ly_rg), width=1)

        # Aura circular sob a Batata ao receber pulso de cura (Opção C)
        if self.aura_cura_timer > 0.0 and self.jogador.vivo:
            cx_ac = int(self.camera.transform_x(cx_mundo))
            cy_ac = int(self.camera.transform_y(self.jogador.y + self.jogador.altura - 3))
            r_ac = int(16 + (0.65 - self.aura_cura_timer) * 18.0)
            pygame.draw.ellipse(world_surf, (74, 222, 128), (cx_ac - r_ac, cy_ac - r_ac // 2, r_ac * 2, max(6, r_ac)), width=2)

        # Feixe verde do Drone de Cura e Mira Laser pontilhada do Drone de Combate (Opção C)
        for dr_v in getattr(self.jogador, "drones", []):
            if not getattr(dr_v, "ativo", False):
                continue
            dcx_t = int(self.camera.transform_x(dr_v.x + dr_v.largura / 2.0))
            dcy_t = int(self.camera.transform_y(dr_v.y + dr_v.altura / 2.0))
            if getattr(dr_v, "feixe_cura_timer", 0.0) > 0.0:
                jcx_t = int(self.camera.transform_x(cx_mundo))
                jcy_t = int(self.camera.transform_y(cy_mundo))
                pygame.draw.line(world_surf, (74, 222, 128), (dcx_t, dcy_t), (jcx_t, jcy_t), width=3)
                pygame.draw.line(world_surf, (220, 255, 230), (dcx_t, dcy_t), (jcx_t, jcy_t), width=1)
            alv_d = getattr(dr_v, "alvo_atual", None)
            if alv_d is not None and getattr(alv_d, "vivo", False):
                acx_t = int(self.camera.transform_x(alv_d.x + getattr(alv_d, "largura", 28) / 2.0))
                acy_t = int(self.camera.transform_y(alv_d.y + getattr(alv_d, "altura", 28) / 2.0))
                for s_pt in range(0, 7, 2):
                    f1 = s_pt / 7.0
                    f2 = (s_pt + 1) / 7.0
                    p1 = (int(dcx_t + (acx_t - dcx_t) * f1), int(dcy_t + (acy_t - dcy_t) * f1))
                    p2 = (int(dcx_t + (acx_t - dcx_t) * f2), int(dcy_t + (acy_t - dcy_t) * f2))
                    pygame.draw.line(world_surf, (244, 63, 94), p1, p2, width=1)

        # Drops de itens e gemas de XP no chão da arena (pausando pisca durante Boss)
        is_boss_lutando_draw = (self.chefe_final is not None and self.chefe_final.vivo)
        self.sistema_drops.desenhar(self.janela, self.camera, pausar_despawn=is_boss_lutando_draw)

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

        # Restaura a câmera e a janela antes dos efeitos de pós-processamento de tela e HUD
        if val_zoom == "75%":
            self.janela.screen = screen
            self.janela.largura = jan_orig_w
            self.janela.altura = jan_orig_h
            self.camera.largura = cam_orig_w
            self.camera.altura = cam_orig_h
            pygame.transform.scale(world_surf, (LARGURA_TELA, ALTURA_TELA), screen)

        self.camera.x = cam_orig_x
        self.camera.y = cam_orig_y

        # Motion Blur (Config 6: motion_blur == "ligado")
        val_blur = str(self.config_sistema.obter_valor("motion_blur")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        if val_blur in ("ligado", "true", "1"):
            if self._motion_blur_surf is None:
                self._motion_blur_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA))
                self._motion_blur_surf.set_alpha(95)
                self._motion_blur_surf.blit(screen, (0, 0))
            else:
                screen.blit(self._motion_blur_surf, (0, 0))
                self._motion_blur_surf.blit(screen, (0, 0))
        elif self._motion_blur_surf is not None:
            self._motion_blur_surf = None

        # Viewport Zoom (Config 9: zoom in 125%, 150%; 75% já escalado com FOV expandido 1067x800)
        if val_zoom in ("125%", "150%"):
            z = 1.25 if val_zoom == "125%" else 1.50
            crop_w = int(LARGURA_TELA / z)
            crop_h = int(ALTURA_TELA / z)
            pj_cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
            pj_cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
            crop_x = clamp(pj_cx - crop_w // 2, 0, LARGURA_TELA - crop_w)
            crop_y = clamp(pj_cy - crop_h // 2, 0, ALTURA_TELA - crop_h)
            crop_key = (crop_w, crop_h)
            if crop_key not in self._zoom_crop_cache:
                self._zoom_crop_cache[crop_key] = pygame.Surface(crop_key)
            crop_surf = self._zoom_crop_cache[crop_key]
            crop_surf.blit(screen, (0, 0), area=pygame.Rect(crop_x, crop_y, crop_w, crop_h))
            pygame.transform.scale(crop_surf, (LARGURA_TELA, ALTURA_TELA), screen)

        # Resolução / Pixelation do Mundo (Config 3: 75%, 50%, 25%)
        val_res = str(self.config_sistema.obter_valor("resolucao")) if hasattr(self, "config_sistema") and self.config_sistema else "100%"
        if val_res in ("75%", "50%", "25%"):
            fator = 0.75 if val_res == "75%" else (0.50 if val_res == "50%" else 0.25)
            small_w = max(10, int(LARGURA_TELA * fator))
            small_h = max(10, int(ALTURA_TELA * fator))
            res_key = (small_w, small_h)
            if res_key not in self._res_surf_cache:
                self._res_surf_cache[res_key] = pygame.Surface(res_key)
            small_surf = self._res_surf_cache[res_key]
            pygame.transform.scale(screen, res_key, small_surf)
            pygame.transform.scale(small_surf, (LARGURA_TELA, ALTURA_TELA), screen)

        # Sincronização Vertical (Config 4: vsync == "desligado" -> vsync_tear_refraction)
        mods = self.config_sistema.obter_modificadores() if hasattr(self, "config_sistema") and self.config_sistema else None
        if getattr(mods, "vsync_tear_refraction", False):
            tear_y = int(getattr(self, "vsync_tear_y", 0.0))
            band_y = max(0, tear_y - 10)
            band_h = min(20, ALTURA_TELA - band_y)
            if band_h > 0:
                if self._vsync_strip_surf is None:
                    self._vsync_strip_surf = pygame.Surface((LARGURA_TELA, 20))
                self._vsync_strip_surf.blit(screen, (0, 0), area=pygame.Rect(0, band_y, LARGURA_TELA, band_h))
                screen.blit(self._vsync_strip_surf, (8, band_y), area=pygame.Rect(0, 0, LARGURA_TELA - 8, band_h))
            pygame.draw.line(screen, (255, 180, 255), (0, tear_y), (LARGURA_TELA, tear_y), width=2)
            pygame.draw.line(screen, AZUL_CIANO, (0, min(ALTURA_TELA - 1, tear_y + 2)), (LARGURA_TELA, min(ALTURA_TELA - 1, tear_y + 2)), width=1)

        # Iluminação Dinâmica / Fog of War (Config 18) - renderizado antes do HUD
        val_ilum = self.config_sistema.obter_valor("iluminacao") if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        if val_ilum in (True, "Ligado", "ligado", "1"):
            if self._fog_surf is None:
                self._fog_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
            fog = self._fog_surf
            fog.fill((8, 10, 15, 235))
            if val_zoom == "75%":
                fov_w, fov_h, cam75_x, cam75_y = self._obter_viewport_zoom75()
                pj_cx = int((self.jogador.x + self.jogador.largura / 2.0 - cam75_x) * (LARGURA_TELA / float(fov_w)))
                pj_cy = int((self.jogador.y + self.jogador.altura / 2.0 - cam75_y) * (ALTURA_TELA / float(fov_h)))
            elif val_zoom in ("125%", "150%"):
                z = 1.25 if val_zoom == "125%" else 1.50
                crop_w = int(LARGURA_TELA / z)
                crop_h = int(ALTURA_TELA / z)
                raw_cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
                raw_cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
                crop_x = clamp(raw_cx - crop_w // 2, 0, LARGURA_TELA - crop_w)
                crop_y = clamp(raw_cy - crop_h // 2, 0, ALTURA_TELA - crop_h)
                pj_cx = int((raw_cx - crop_x) * z)
                pj_cy = int((raw_cy - crop_y) * z)
            else:
                pj_cx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
                pj_cy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
            pygame.draw.circle(fog, (0, 0, 0, 80), (pj_cx, pj_cy), 195)
            pygame.draw.circle(fog, (0, 0, 0, 0), (pj_cx, pj_cy), 170)
            screen.blit(fog, (0, 0))

        # =========================================================================
        # CAMADA 2: ESPAÇO DA TELA (SCREEN-SPACE HUD)
        # =========================================================================
        self._desenhar_hud_tela(hud_visivel=hud_visivel)

        # Cores Invertidas (Config 17) - renderizado antes dos modais, independente de hud_visivel e buffs
        val_cores = self.config_sistema.obter_valor("cores_invertidas") if hasattr(self, "config_sistema") and self.config_sistema else "desligado"
        if val_cores in (True, "Ligado", "ligado", "1"):
            if self._inv_surf is None:
                self._inv_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA))
            inv_surf = self._inv_surf
            inv_surf.fill((255, 255, 255))
            inv_surf.blit(screen, (0, 0), special_flags=pygame.BLEND_SUB)
            screen.blit(inv_surf, (0, 0))

        # Overlays modais de Level Up, Overclock, Menu de Configurações, Debug, Vitória, Game Over e Pausa
        if self.modal_overclock.ativo or self.modal_overclock.tempo_transicao_saida > 0.0:
            self.modal_overclock.draw(screen)
        elif self.modal_level_up.ativo or getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) > 0.0:
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

        # Overlay da Cutscene do Chefe Final (Queda de Energia c/ Holofote -> Equalizadores)
        if self.boss_cutscene_ativa:
            if self.overlay_cutscene_alpha > 0:
                if self._overlay_surf is None or self._overlay_surf.get_size() != (LARGURA_TELA, ALTURA_TELA):
                    self._overlay_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
                r, g, b = self.overlay_cutscene_cor
                self._overlay_surf.fill((r, g, b, int(self.overlay_cutscene_alpha)))
                if self.boss_cutscene_fase == "whiteout":
                    pj_sx = int(self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0))
                    pj_sy = int(self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0))
                    pygame.draw.circle(self._overlay_surf, (0, 0, 0, 40), (pj_sx, pj_sy), 72)
                screen.blit(self._overlay_surf, (0, 0))

            if self.boss_cutscene_fase == "musica_in":
                num_barras = 32
                larg_b = max(6, (LARGURA_TELA // num_barras) - 4)
                for idx_b in range(num_barras):
                    bx = idx_b * (LARGURA_TELA // num_barras) + 2
                    alt_b = int(12 + abs(math.sin(self.boss_cutscene_timer * 7.5 + idx_b * 0.55)) * 28)
                    cor_eq = DOURADO if idx_b % 3 == 0 else (ROXO_ACENTO if idx_b % 2 == 0 else AZUL_CIANO)
                    pygame.draw.rect(screen, cor_eq, (bx, 0, larg_b, alt_b), border_radius=2)
                    pygame.draw.rect(screen, cor_eq, (bx, ALTURA_TELA - alt_b, larg_b, alt_b), border_radius=2)

    def _desenhar_hp_in_world(self):
        """Desenha a barra de HP em Pixel Art Limpo (Opção A) abaixo da batata, com extensão azul da Barreira de Sobrevida."""
        if not self.jogador.vivo:
            return

        centro_x = self.jogador.x + float(self.jogador.largura) / 2.0
        base_y = self.jogador.y + float(self.jogador.altura) + 5.0

        bar_w = 34
        bar_h = 6
        bar_x = int(self.camera.transform_x(centro_x) - bar_w // 2)
        bar_y = int(self.camera.transform_y(base_y))

        # Moldura pixelada escura (#0f172a)
        pygame.draw.rect(self.janela.screen, (15, 23, 42), (bar_x, bar_y, bar_w, bar_h))

        # Preenchimento verde nítido
        proporcao = clamp(self.jogador.hp / float(max(1, self.jogador.hp_max)), 0.0, 1.0)
        fill_w = int((bar_w - 2) * proporcao)
        if fill_w > 0:
            pygame.draw.rect(self.janela.screen, VERDE_CURA, (bar_x + 1, bar_y + 1, fill_w, bar_h - 2))

        # Barreira de Sobrevida (Drone de Cura quando vida cheia) em azul ciano
        escudo_val = int(getattr(self.jogador, "escudo_sobrevida", 0))
        if escudo_val > 0:
            esc_w = max(2, int((bar_w - 2) * clamp(escudo_val / 25.0, 0.0, 1.0)))
            pygame.draw.rect(self.janela.screen, (56, 189, 248), (bar_x + 1, bar_y - 2, esc_w, 2))

    def _desenhar_hud_tela(self, hud_visivel: bool = True):
        """Renderiza o HUD fixo na tela: inventário com ícones/munição, métricas e botão de configurações."""
        screen = self.janela.screen

        if hud_visivel:
            # 1. Slots de inventário (Top-Left: 16, 14) com destaque para o slot ativo (escala 1280x720)
            slot_tam = 54
            slot_ativo = getattr(self.jogador, "slot_ativo", 2)

            fonte_slots = self._fontes["slots"]
            fonte_municao = self._fontes["municao"]

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
                    arma_slot2 = self.jogador.armas[1] if (hasattr(self.jogador, "armas") and len(self.jogador.armas) > 1) else None
                    if arma_slot2 is not None:
                        icone_chave = getattr(arma_slot2, "icone_asset", None)
                        if icone_chave:
                            icone_img = self._obter_sprite_icone(icone_chave)
                        if icone_img is None:
                            nome_arma2 = getattr(arma_slot2, "nome", "")
                            if "Minigun" in nome_arma2:
                                icone_img = self._obter_sprite_icone("arma_minigun")
                            elif "Escopeta" in nome_arma2 or "Shotgun" in nome_arma2:
                                icone_img = self._obter_sprite_icone("arma_shotgun")
                            elif "Rifle" in nome_arma2 or "Railgun" in nome_arma2:
                                icone_img = self._obter_sprite_icone("arma_rifle")
                            elif "Foguetes" in nome_arma2:
                                icone_img = self._obter_sprite_icone("arma_foguetes")
                            elif "Granadas" in nome_arma2:
                                icone_img = self._obter_sprite_icone("arma_granadas")
                            else:
                                icone_img = self._obter_sprite_icone("arma_pistola")
                        if not getattr(arma_slot2, "municao_infinita", False) and hasattr(arma_slot2, "municao_atual"):
                            mun2 = getattr(arma_slot2, "municao_atual", 0)
                            texto_badge = str(mun2)
                            cor_badge = AMARELO_XP if mun2 > 5 else VERMELHO_HP
                    else:
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
                    screen.blit(icone_img, (sx + (slot_tam - 34) // 2, sy + (slot_tam - 34) // 2))

                if texto_badge is not None:
                    badge_surf = fonte_municao.render(texto_badge, True, cor_badge)
                    badge_rect = badge_surf.get_rect(right=sx + slot_tam - 2, bottom=sy + slot_tam - 1)
                    sombra_b = fonte_municao.render(texto_badge, True, (0, 0, 0))
                    screen.blit(sombra_b, (badge_rect.x + 1, badge_rect.y + 1))
                    screen.blit(badge_surf, badge_rect)

            # Slot 3B secundário (desbloqueado com BIOS Modding)
            if getattr(self.jogador, "bios_modding", False):
                sx3b = 16 + 2 * (slot_tam + 6)
                sy3b = 14 + slot_tam + 4
                bg_cor = (35, 20, 50)
                borda_cor = ROXO_ACENTO
                pygame.draw.rect(screen, bg_cor, (sx3b, sy3b, slot_tam, slot_tam), border_radius=4)
                pygame.draw.rect(screen, borda_cor, (sx3b, sy3b, slot_tam, slot_tam), width=1, border_radius=4)

                num_surf = fonte_slots.render("3B", True, ROXO_CLARO)
                screen.blit(num_surf, (sx3b + 3, sy3b + 2))

                if getattr(self.jogador, "arma_especial_secundaria", None) is not None:
                    nome_arma = getattr(self.jogador.arma_especial_secundaria, "nome", "")
                    icone_img = None
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

                    if icone_img:
                        screen.blit(icone_img, (sx3b + (slot_tam - 34) // 2, sy3b + (slot_tam - 34) // 2))

                    mun = getattr(self.jogador.arma_especial_secundaria, "municao_atual", 0)
                    texto_badge = str(mun)
                    cor_badge = AMARELO_XP if mun > 5 else VERMELHO_HP
                    badge_surf = fonte_municao.render(texto_badge, True, cor_badge)
                    badge_rect = badge_surf.get_rect(right=sx3b + slot_tam - 2, bottom=sy3b + slot_tam - 1)
                    sombra_b = fonte_municao.render(texto_badge, True, (0, 0, 0))
                    screen.blit(sombra_b, (badge_rect.x + 1, badge_rect.y + 1))
                    screen.blit(badge_surf, badge_rect)

            # 2. Cronômetro de Sobrevivência e Contador de Abates (Top-Center)
            minutos = int(self.tempo_sobrevivencia // 60)
            segundos = int(self.tempo_sobrevivencia % 60)
            texto_tempo = f"{minutos:02d}:{segundos:02d}"

            fonte_tempo = self._fontes["tempo"]
            tempo_surf = fonte_tempo.render(texto_tempo, True, BRANCO)
            tempo_rect = tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=14)
            screen.blit(tempo_surf, tempo_rect)

            texto_abates = f"Abates: {self.abates}"
            fonte_abates = self._fontes["abates"]
            abates_surf = fonte_abates.render(texto_abates, True, AMARELO_XP)
            abates_rect = abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=44)
            screen.blit(abates_surf, abates_rect)

            # 3. Barra de Progresso de XP (Top-Center: top=62, 360x10 px)
            if hasattr(self, "hud") and self.hud is not None:
                self.hud.desenhar_barra_xp(screen, self.jogador.sistema_xp)

            # 4. Barra de Mini-Boss / Chefe Final (Top-Center: top=78, 400x12 px)
            if hasattr(self, "hud") and self.hud is not None:
                boss_ativo = self.chefe_final if (self.chefe_final is not None and self.chefe_final.vivo) else next((e for e in self.inimigos if getattr(e, "is_elite", False) and e.vivo), None)
                if boss_ativo is not None:
                    self.hud.desenhar_barra_boss(screen, boss_ativo, visivel=hud_visivel)

            # 5. Indicadores visuais de Buffs Ativos na Tela
            self._desenhar_buffs_ativos(screen)

            # 6. FPS (Top-Right) sob hud_visivel
            fps_val = int(self.janela.get_fps())
            fonte_fps = self._fontes["fps"]
            fps_surf = fonte_fps.render(f"FPS: {fps_val}", True, AZUL_CIANO)
            fps_rect = fps_surf.get_rect(right=LARGURA_TELA - 60, centery=32)
            screen.blit(fps_surf, fps_rect)

        # 5. Toasts de Coleta Flutuantes
        self._desenhar_toasts(screen)

        # 6. Botão de Configurações e engrenagem [C] - sempre visível mesmo com hud="desligado"
        gear_x = LARGURA_TELA - 48
        if self._btn_gear_img is not None:
            screen.blit(self._btn_gear_img, (gear_x, 16))
        else:
            pygame.draw.rect(screen, (45, 55, 75), (gear_x, 16, 32, 32), border_radius=4)
            fonte_fps = self._fontes["fps"]
            gear_surf = fonte_fps.render("[C]", True, DOURADO)
            gear_rect = gear_surf.get_rect(centerx=gear_x + 16, centery=32)
            screen.blit(gear_surf, gear_rect)

        # 7. Mira (Crosshair) na coordenada virtual clampada (ou direção de teclado em uma_mao)
        em_combate_ativo = (
            not self.pausado and not self.game_over and not self.vitoria and not self.boss_cutscene_ativa
            and not self.menu_configs.ativo and not self.modal_level_up.ativo and not self.modal_overclock.ativo
            and not (hasattr(self, "menu_debug") and self.menu_debug.ativo)
        )
        if em_combate_ativo and self.jogador.vivo:
            val_kb = str(self.config_sistema.obter_valor("keybinds")).lower() if hasattr(self, "config_sistema") and self.config_sistema else "padrao"
            if val_kb == "uma_mao":
                dir_m = getattr(self.jogador, "dir_movimento", (0.0, -1.0))
                dmx, dmy = float(dir_m[0]), float(dir_m[1])
                if dmx == 0.0 and dmy == 0.0:
                    dmx, dmy = 0.0, -1.0
                cx_t = self.camera.transform_x(self.jogador.x + self.jogador.largura / 2.0)
                cy_t = self.camera.transform_y(self.jogador.y + self.jogador.altura / 2.0)
                mira_tx = int(clamp(cx_t + dmx * 72.0, 0.0, float(LARGURA_TELA)))
                mira_ty = int(clamp(cy_t + dmy * 72.0, 0.0, float(ALTURA_TELA)))
            else:
                try:
                    mx_c, my_c = self.mouse.get_position()
                    if val_kb == "pesadelo":
                        my_c = ALTURA_TELA - my_c
                except Exception:
                    mx_c, my_c = LARGURA_TELA // 2, ALTURA_TELA // 2
                mira_tx = int(clamp(float(mx_c), 0.0, float(LARGURA_TELA)))
                mira_ty = int(clamp(float(my_c), 0.0, float(ALTURA_TELA)))

            if self._mira_crosshair_img is not None:
                cw, ch = self._mira_crosshair_img.get_size()
                screen.blit(self._mira_crosshair_img, (mira_tx - cw // 2, mira_ty - ch // 2))
            else:
                pygame.draw.circle(screen, AZUL_CIANO, (mira_tx, mira_ty), 6, width=1)
                pygame.draw.circle(screen, DOURADO, (mira_tx, mira_ty), 2)

    def _desenhar_toasts(self, screen):
        """Renderiza toasts de coleta flutuantes com clamp horizontal em [12, LARGURA_TELA - 12]."""
        fonte_toast = self._fontes["toast"]
        for t in self.toasts_coleta:
            tx_tela = self.camera.transform_x(t["x"])
            ty_tela = self.camera.transform_y(t["y"])
            alpha = int(clamp((t["tempo"] / max(0.01, t["tempo_max"])) * 255, 0, 255))

            txt_surf = fonte_toast.render(t["texto"], True, t["cor"])
            txt_sombra = fonte_toast.render(t["texto"], True, (0, 0, 0))
            txt_surf.set_alpha(alpha)
            txt_sombra.set_alpha(alpha)

            rect = txt_surf.get_rect(centerx=int(tx_tela), centery=int(ty_tela))
            if rect.left < 12:
                rect.left = 12
            if rect.right > LARGURA_TELA - 12:
                rect.right = LARGURA_TELA - 12
            if rect.left < 12:
                rect.left = 12

            screen.blit(txt_sombra, (rect.x + 1, rect.y + 1))
            screen.blit(txt_surf, rect)

    def _desenhar_buffs_ativos(self, screen):
        """Renderiza badges e indicadores com timers de todos os buffs ativos abaixo do inventário."""
        if not hasattr(self.jogador, "obter_buffs_ativos"):
            return

        buffs = self.jogador.obter_buffs_ativos()
        if not buffs:
            return

        fonte_buff = self._fontes["buff"]
        fonte_timer = self._fontes["timer"]

        start_x = 16
        start_y = 132 if getattr(self.jogador, "bios_modding", False) else 76
        badge_w = 152
        badge_h = 22

        for b in buffs:
            bg_rect = (start_x, start_y, badge_w, badge_h)
            cor_bg = b.get("cor_bg", (30, 30, 40))
            cor_borda = b.get("cor", (255, 255, 255))
            pygame.draw.rect(screen, cor_bg, bg_rect, border_radius=3)
            pygame.draw.rect(screen, cor_borda, bg_rect, width=1, border_radius=3)

            # Barra de progresso do timer
            timer_val = b.get("timer", 0.0)
            duracao_max = b.get("duracao", 15.0)
            if duracao_max > 0.0 and timer_val < 900.0:
                prog = clamp(timer_val / duracao_max, 0.0, 1.0)
                bar_w = int((badge_w - 4) * prog)
                if bar_w > 0:
                    pygame.draw.rect(screen, cor_borda, (start_x + 2, start_y + badge_h - 2, bar_w, 1))

            # Texto do nome do buff
            nome_surf = fonte_buff.render(b["nome"], True, cor_borda)
            screen.blit(nome_surf, (start_x + 4, start_y + 2))

            # Texto do timer
            if timer_val < 900.0:
                timer_str = f"{timer_val:.1f}s"
                timer_surf = fonte_timer.render(timer_str, True, BRANCO)
                t_rect = timer_surf.get_rect(right=start_x + badge_w - 4, centery=start_y + badge_h // 2 - 1)
                screen.blit(timer_surf, t_rect)

            start_y += badge_h + 3

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
        """Executa a sequência de vitória pela derrota da Geladeira Tsunami."""
        try:
            pygame.mixer.music.fadeout(800)
            pygame.mixer.music._current_track = None
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
        """Overlay modal de vitória centralizado em 1280x720 com grade de estatísticas."""
        screen = self.janela.screen
        if self._overlay_surf is None or self._overlay_surf.get_size() != (LARGURA_TELA, ALTURA_TELA):
            self._overlay_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._overlay_surf.fill((10, 15, 25, 235))
        screen.blit(self._overlay_surf, (0, 0))

        ox = (LARGURA_TELA - 800) // 2
        oy = (ALTURA_TELA - 600) // 2

        # Painel central estilizado
        painel_rect = pygame.Rect(ox + 90, oy + 40, 620, 520)
        pygame.draw.rect(screen, (25, 32, 45), painel_rect, border_radius=8)
        pygame.draw.rect(screen, DOURADO, painel_rect, width=2, border_radius=8)

        # Faixa superior de destaque
        fonte_tit = self._fontes["tit_vit"]
        tit_surf = fonte_tit.render("GELADEIRA TSUNAMI DESLIGADA", True, DOURADO)
        tit_rect = tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 60)
        screen.blit(tit_surf, tit_rect)

        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)
        tempo_str = f"{minutos:02d}:{segundos:02d} ({self.tempo_sobrevivencia:.1f}s)"

        fonte_sub = self._fontes["sub_vit"]
        sub_surf = fonte_sub.render(f"Cleiton sobreviveu ao escritório por {minutos:02d}:{segundos:02d}.", True, (200, 220, 240))
        sub_rect = sub_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 95)
        screen.blit(sub_surf, sub_rect)

        # Quadro de estatísticas internas
        quadro_rect = pygame.Rect(ox + 120, oy + 130, 560, 280)
        pygame.draw.rect(screen, (15, 20, 30), quadro_rect, border_radius=6)
        pygame.draw.rect(screen, (45, 60, 80), quadro_rect, width=1, border_radius=6)

        fonte_stat_label = self._fontes["stat_label"]
        fonte_stat_val = self._fontes["stat_val"]
        fonte_stat_destaque = self._fontes["stat_destaque"]

        stats_data = [
            ("Tempo de Partida:", tempo_str, DOURADO),
            ("Máquinas Destruídas:", f"{self.abates}", AMARELO_XP),
            ("Dano Total Causado:", f"{self.dano_total_causado:,}", (255, 100, 100)),
            ("Configurações Desbloqueadas:", f"{len(self.gerenciador_config.desbloqueadas)} / 20", AZUL_CIANO),
            ("Multiplicador de Configurações:", f"x{self.estatisticas_partida_resultado.get('mult_dif', 1.0):.2f}", (180, 210, 240)),
        ]

        start_y = oy + 145
        step_y = 34
        for i, (label, val_str, cor_val) in enumerate(stats_data):
            cur_y = start_y + i * step_y
            lbl_surf = fonte_stat_label.render(label, True, (180, 195, 215))
            screen.blit(lbl_surf, (ox + 140, cur_y))

            val_surf = fonte_stat_val.render(val_str, True, cor_val)
            val_rect = val_surf.get_rect(right=ox + 660, top=cur_y)
            screen.blit(val_surf, val_rect)

        # Linha de separação
        pygame.draw.line(screen, (50, 65, 85), (ox + 140, oy + 315), (ox + 660, oy + 315), width=1)

        # Pontuação Final
        score_val = self.estatisticas_partida_resultado.get("score_final", self.pontos)
        score_lbl = fonte_stat_destaque.render("PONTUAÇÃO FINAL:", True, DOURADO)
        screen.blit(score_lbl, (ox + 140, oy + 330))

        score_num_surf = fonte_stat_destaque.render(f"{score_val:,} PTS", True, DOURADO)
        score_num_rect = score_num_surf.get_rect(right=ox + 660, top=oy + 330)
        screen.blit(score_num_surf, score_num_rect)

        # Badge de Recorde Histórico se atingido
        if self.estatisticas_partida_resultado.get("novo_recorde_pontos", False):
            badge_rec_surf = fonte_stat_val.render("[NOVO RECORDE!]", True, AMARELO_XP)
            badge_rec_rect = badge_rec_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 375)
            screen.blit(badge_rec_surf, badge_rec_rect)

        # Rodapé com atalhos de navegação
        fonte_btn = self._fontes["btn"]
        fonte_btn_sub = self._fontes["btn_sub"]

        btn1_surf = fonte_btn.render("[ENTER / ESPAÇO] Jogar Novamente", True, DOURADO)
        screen.blit(btn1_surf, btn1_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 430))

        btn2_surf = fonte_btn_sub.render("[ESC / M] Menu Principal", True, (200, 210, 225))
        screen.blit(btn2_surf, btn2_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 465))

        btn3_surf = fonte_btn_sub.render("[C] Menu de Configurações", True, AZUL_CIANO)
        screen.blit(btn3_surf, btn3_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 498))

    def _desenhar_overlay_pausa(self):
        """Overlay modal de pausa com textos perfeitamente centralizados."""
        screen = self.janela.screen
        if self._overlay_surf is None or self._overlay_surf.get_size() != (LARGURA_TELA, ALTURA_TELA):
            self._overlay_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._overlay_surf.fill((10, 15, 22, 180))
        screen.blit(self._overlay_surf, (0, 0))

        oy = (ALTURA_TELA - 600) // 2
        fonte_titulo = self._fontes["tit_pausa"]
        fonte_sub = self._fontes["sub_pausa"]

        t_surf = fonte_titulo.render("JOGO PAUSADO", True, DOURADO)
        t_rect = t_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 200)
        screen.blit(t_surf, t_rect)

        c_surf = fonte_sub.render("[ESC] Continuar Partida", True, BRANCO)
        c_rect = c_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 280)
        screen.blit(c_surf, c_rect)

        m_surf = fonte_sub.render("[M] Menu Principal", True, CINZA_BORDA)
        m_rect = m_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 325)
        screen.blit(m_surf, m_rect)

    def _desenhar_overlay_game_over(self):
        """Overlay de fim de jogo com estatísticas perfeitamente centralizadas em 1280x720."""
        screen = self.janela.screen
        if self._overlay_surf is None or self._overlay_surf.get_size() != (LARGURA_TELA, ALTURA_TELA):
            self._overlay_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._overlay_surf.fill((20, 5, 5, 210))
        screen.blit(self._overlay_surf, (0, 0))

        ox = (LARGURA_TELA - 800) // 2
        oy = (ALTURA_TELA - 600) // 2

        fonte_tit = self._fontes["tit_go"]
        fonte_sub = self._fontes["sub_go"]
        fonte_stat = self._fontes["stat_go"]
        fonte_prompt = self._fontes["prompt_go"]

        tit_surf = fonte_tit.render("FIM DE LINHA", True, VERMELHO_HP)
        screen.blit(tit_surf, tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 115))

        sub_surf = fonte_sub.render("As máquinas do escritório drenaram a bateria de Cleiton.", True, (200, 180, 180))
        screen.blit(sub_surf, sub_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 162))

        causa_str = getattr(self.jogador, "ultima_causa_morte", "") or "Dano fatal no escritório"
        causa_surf = fonte_stat.render(f"Causa da Morte: {causa_str}", True, LARANJA_ALERTA)
        screen.blit(causa_surf, causa_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 190))

        minutos = int(self.tempo_sobrevivencia // 60)
        segundos = int(self.tempo_sobrevivencia % 60)

        # Quadro escuro
        quadro_rect = pygame.Rect(ox + 150, oy + 225, 500, 210)
        pygame.draw.rect(screen, (28, 15, 20), quadro_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 40, 50), quadro_rect, width=1, border_radius=8)

        tempo_surf = fonte_stat.render(f"Tempo de Partida: {minutos:02d}:{segundos:02d}", True, BRANCO)
        screen.blit(tempo_surf, tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 242))

        abates_surf = fonte_stat.render(f"Total de Abates: {self.abates}", True, AMARELO_XP)
        screen.blit(abates_surf, abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 278))

        dano_surf = fonte_stat.render(f"Dano Total: {self.dano_total_causado:,}", True, (255, 120, 120))
        screen.blit(dano_surf, dano_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 314))

        score_val = self.estatisticas_partida_resultado.get("score_final", self.pontos)
        pontos_surf = fonte_stat.render(f"Pontuação Final: {score_val:,} PTS", True, DOURADO)
        screen.blit(pontos_surf, pontos_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 350))

        if self.estatisticas_partida_resultado.get("novo_recorde_pontos", False):
            rec_surf = fonte_stat.render("[NOVO RECORDE DE PONTOS!]", True, AMARELO_XP)
            screen.blit(rec_surf, rec_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 386))

        prompt_surf = fonte_prompt.render("Pressione [ENTER] para Jogar Novamente ou [ESC] para o Menu", True, DOURADO)
        screen.blit(prompt_surf, prompt_surf.get_rect(centerx=LARGURA_TELA // 2, top=oy + 458))


    def _reiniciar_partida(self):
        SceneManager.change_scene(GameplayScene())

    def _voltar_menu(self):
        from src.cenas.menu_principal import MenuPrincipalScene
        SceneManager.change_scene(MenuPrincipalScene())


