import math
import os
import random
import pygame
from src.cenas.base_scene import BaseScene
from src.cenas.gameplay_combate import GameplayCombateMixin
from src.cenas.gameplay_render import GameplayRenderMixin
from src.entidades.jogador import Jogador
from src.entidades.inimigo_base import InimigoBase
from src.entidades.projetil import Projetil
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.armas.railgun import Railgun
from src.armas import (
    Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas,
    BastaoChoque, SMGCompacta, RifleArco, LancaChamas,
)
from src.equipamentos import DroneCura, DroneCombate, DroneSuporte
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_particulas import SistemaParticulas
from src.sistemas.sistema_audio import GerenciadorAudio, AnalisadorFFTBoss
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.conquistas_dados import CHIPS_FIRMWARE
from src.sistemas.sistema_conquistas import COTAS_SLOTS_FIRMWARE
from src.sistemas.efeitos_combate import GerenciadorEfeitosCombate, ContextoCombate
from src.ui.hud import HUD
from src.ui.banner_dicas import BannerDica
from src.ui.modal_level_up import ModalLevelUp
from src.utils.traducao import t as tr
from src.ui.modal_overclock import ModalOverclock
from src.ui.menu_configs import MenuConfigs
from src.entidades.inimigos.geladeira_tsunami import GeladeiraTsunami, ESTADO_MORTE
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    CAMERA_DAMPING_K, DT_CLAMP_MAX, DASH_COOLDOWN, DASH_PARRY_META, MELEE_ARCO_GRAUS,
    SPAWN_MAX_ATIVOS, MINIBOSS_CICLOS_RUN,
    SEPARACAO_INIMIGOS_FATOR_RAIO, SEPARACAO_INIMIGOS_RIGIDEZ, SEPARACAO_INIMIGOS_VEL_MAX,
    MINION_BLOCK_FATOR_RAIO, MINION_BLOCK_FORCA_JOGADOR, MINION_BLOCK_VEL_MAX, MINION_BLOCK_EMPURRAO_INIMIGO,
    BRANCO, PRETO, CINZA_FUNDO, CINZA_PAINEL, CINZA_BORDA,
    VERMELHO_HP, VERMELHO_DANO, VERDE_CURA, AMARELO_XP, AZUL_CIANO, DOURADO, LARANJA_ALERTA,
    ROXO_ACENTO, ROXO_CLARO, ROXO_ESCURO,
    BOSS_GELADEIRA_LARGURA, BOSS_GELADEIRA_ALTURA,
    obter_caminho_asset, SAVE_FILE_PATH
)
from src.utils.math_utils import colisao_aabb, clamp, distancia, vetor_direcao


class GameplayScene(GameplayCombateMixin, GameplayRenderMixin, BaseScene):
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
        self.sistema_conquistas = getattr(self.gerenciador_config, "sistema_conquistas", None)
        dash_conq = (
            self.sistema_conquistas.possui_recompensa("habilidade", "dash")
            if self.sistema_conquistas is not None
            else False
        )
        self.jogador.dash_desbloqueado = bool(
            self.gerenciador_config.estatisticas.get("dash_desbloqueado", False) or dash_conq
        )
        loadout = getattr(self.gerenciador_config, "loadout", {}) or {}
        if hasattr(self.jogador, "aplicar_loadout"):
            self.jogador.aplicar_loadout(
                slot1_id=str(loadout.get("slot1", "chave_manutencao")),
                slot2_id=str(loadout.get("slot2", "pistola")),
            )
        self.modal_level_up = ModalLevelUp(self.gerenciador_config, self.jogador, cena=self)
        self.modal_overclock = ModalOverclock(self.jogador, cena=self)
        self.menu_configs = MenuConfigs(self.gerenciador_config, em_jogo=True, cena=self)
        try:
            from src.ui.menu_conquistas import MenuConquistas
            self.menu_conquistas = MenuConquistas(
                self.gerenciador_config,
                self.sistema_conquistas,
                em_jogo=True,
                cena=self,
            )
        except ImportError:
            self.menu_conquistas = None

        # Registra callback de level-up no SistemaXP do jogador
        self.jogador.sistema_xp.registrar_callback_level_up(self._ao_subir_nivel)

        # Chefe Final e Cutscene de Transição
        self.chefe_final = None
        try:
            from src.entidades.inimigos.geladeira_tsunami import GeladeiraTsunami
            GeladeiraTsunami.preaquecer_cache_fontes()
        except Exception:
            pass
        self.boss_grace_period_ativo = False
        self.boss_grace_timer = 0.0
        self.boss_cutscene_ativa = False
        self.boss_cutscene_fase = "none"
        self.boss_cutscene_timer = 0.0
        self.overlay_cutscene_alpha = 0.0
        self.overlay_cutscene_cor = (255, 255, 255)
        self.tiros_echo_pendentes = []

        # Sistemas de combate, spawn, drops, partículas e progressão
        self.config_sistema = self.gerenciador_config
        self.spawner = SistemaSpawn(max_ativos=SPAWN_MAX_ATIVOS)
        self.sistema_drops = SistemaDrops()
        self.sistema_scavenger = SistemaScavenger()
        self.sistema_particulas = SistemaParticulas()
        self.sistema_audio = GerenciadorAudio()
        self.analisador_fft_boss = AnalisadorFFTBoss()
        self.efeitos_combate = GerenciadorEfeitosCombate()
        self.hologramas: list = []
        self.pulso_assault_intro_timer: float = 0.0
        self._dano_na_fase3_boss: bool = False
        self.hud = HUD()

        from src.ui.menu_debug import MenuDebug
        self.menu_debug = MenuDebug(cena_gameplay=self)

        self.projeteis: list[Projetil] = []
        self.inimigos: list[InimigoBase] = []

        # Métricas de partida e condição de vitória
        self.tempo_sobrevivencia = 0.0
        self.tempo_15fps_acumulado = 0.0
        self.abates = 0
        self.pontos = 0
        self.dano_total_causado = 0
        self.pausado = False
        self.banner_dicas = BannerDica(gerenciador_config=self.gerenciador_config)
        self.game_over = False
        self.vitoria = False
        self.partida_registrada = False
        self.estatisticas_partida_resultado = {}

        # Cache de fontes para alta performance (escala nativa 1280x720 + monospace Cyber-Office + DPI nativo)
        self._fontes_spec = {
            "slots": ("DejaVu Sans Mono", 10, True),
            "municao": ("DejaVu Sans Mono", 11, True),
            "tempo": ("DejaVu Sans Mono", 14, True),
            "abates": ("DejaVu Sans Mono", 12, True),
            "buff": ("Arial", 11, True),
            "timer": ("Arial", 11, True),
            "toast": ("Arial", 14, True),
            "grace_banner": ("Arial", 18, True),
            "fps": ("DejaVu Sans Mono", 12, True),
            "tit_vit": ("Arial", 30, True),
            "sub_vit": ("Arial", 16, False),
            "stat_label": ("Arial", 16, False),
            "stat_val": ("Arial", 16, True),
            "stat_destaque": ("Arial", 24, True),
            "btn": ("Arial", 16, True),
            "btn_sub": ("Arial", 15, False),
            "tit_pausa": ("Arial", 40, True),
            "sub_pausa": ("Arial", 20, True),
            "tit_go": ("Arial", 42, True),
            "sub_go": ("Arial", 18, False),
            "stat_go": ("Arial", 18, True),
            "prompt_go": ("Arial", 16, True),
        }
        self._fontes = {
            k: pygame.font.SysFont(nome, tam, bold=bold)
            for k, (nome, tam, bold) in self._fontes_spec.items()
        }
        self._fontes_nativas_cache: dict[tuple[str, int], pygame.font.Font] = {}
        self._fonte_toast = self._fontes["toast"]
        self._hud_stats_pill_surf = None
        self._world_canvas_surf = None
        self._world_scaled_surf = None

        # Toasts de itens coletados, Banners de Desbloqueio, Screen Shake, Hitstop e Efeitos
        self.toasts_coleta: list[dict] = []
        self.banners_desbloqueio: list[dict] = []
        self.shake_intensidade: float = 0.0
        self.shake_timer: float = 0.0
        self.arena_freeze_timer: float = 0.0
        self.hitstop_timer: float = 0.0
        self.auto_fire_toggle_ativo: bool = False
        self._ultimo_vsync_ativo: bool | None = None
        self._ultimo_dt_draw: float = 1.0 / 60.0
        try:
            self._aguardando_soltar_lmb: bool = bool(
                self.mouse is not None and hasattr(self.mouse, "button_pressed") and self.mouse.button_pressed(1)
            )
        except Exception:
            self._aguardando_soltar_lmb = False

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

        # Inicialização da trilha sonora dinâmica (corte abrupto para anticipation)
        from src.sistemas.sistema_musica import obter_sistema_musica
        self.sistema_musica = obter_sistema_musica()

        # Aplica modificadores iniciais
        self.aplicar_modificadores()

        try:
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
            self.sistema_musica.inicializar()
            self.sistema_musica.atualizar_volume(vol_master, vol_musica)
            self.sistema_musica.iniciar_partida()
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
        """Converte coordenadas virtuais de tela (1280x720) em coordenadas do mundo considerando o zoom ativo."""
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
        cfg_sis = getattr(self, "config_sistema", None) or getattr(self, "gerenciador_config", None)
        hud_off = bool(
            cfg_sis is not None
            and str(cfg_sis.obter_valor("hud")).strip().lower() in ("desligado", "false", "0", "off")
        )
        ilum_on = bool(
            cfg_sis is not None
            and str(cfg_sis.obter_valor("iluminacao")).strip().lower() in ("ligado", "true", "1", "on")
        )
        self._emitir_evento_conquista(
            "nivel_alcancado",
            int(novo_nivel),
            {"nivel": int(novo_nivel), "hud_desligado": hud_off, "iluminacao_ligada": ilum_on},
        )
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

        if hasattr(self, "gerenciador_config") and self.gerenciador_config:
            if hasattr(self.gerenciador_config, "obter_configs_bloqueadas_level_up"):
                tem_bloqueadas = bool(self.gerenciador_config.obter_configs_bloqueadas_level_up())
            else:
                tem_bloqueadas = bool(self.gerenciador_config.obter_bloqueadas())
        else:
            tem_bloqueadas = False
        eh_marco = tem_bloqueadas and (
            (hasattr(self.jogador.sistema_xp, "eh_nivel_marco_config") and self.jogador.sistema_xp.eh_nivel_marco_config(novo_nivel))
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
                "texto": tr("ui_geral", "toast_nivel_normal", nivel=novo_nivel),
                "cor": DOURADO,
                "x": cx,
                "y": self.jogador.y - 18,
                "tempo": 1.8,
                "tempo_max": 1.8
            })
            if int(novo_nivel) >= getattr(self.jogador.sistema_xp, "nivel_max", 12) and getattr(self, "tempo_sobrevivencia", 0.0) >= 185.0:
                self.iniciar_boss_grace_period()

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
        self.jogador.dano_recebido_mult = float(getattr(mods, "dano_recebido_mult", 1.0))
        if hasattr(self.jogador, "atualizar_modo_tanque"):
            self.jogador.atualizar_modo_tanque(getattr(mods, "controles_tanque", False))

        # Calibragem & Efeito de Parry
        parry_prec = getattr(mods, "parry_precisao", "padrao")
        parry_ef = getattr(mods, "parry_efeito", "padrao")
        self.jogador.exposed_mult = 1.45 if parry_ef == "pulso_emp" else 1.25
        self.jogador.dash_protocolo = str(getattr(mods, "dash_protocolo", "padrao"))
        self.jogador.dash_rastro = str(getattr(mods, "dash_rastro", "padrao"))
        if self.jogador.dash_protocolo == "propulsor_instavel":
            self.jogador.dash_cargas_max = 2
            self.jogador.dash_sem_iframes = True
            self.jogador.dash_recarga_mult = 1.35
        else:
            self.jogador.dash_cargas_max = 1
            self.jogador.dash_sem_iframes = False
            self.jogador.dash_recarga_mult = 1.0
        self.jogador.dash_cargas_atuais = min(
            getattr(self.jogador, "dash_cargas_atuais", 1),
            self.jogador.dash_cargas_max,
        )

        arma_melee = self._obter_arma_melee()
        if arma_melee is not None:
            arma_melee.whiff_callback = self._ao_errar_parry
            arma_melee.parry_modo_postura_riposte = (parry_prec == "postura_riposte")
            arma_melee.parry_modo_firewall = (parry_ef == "firewall_estatico")
            arma_melee.parry_modo_ventoinha = (parry_ef == "ventoinha_360")
            arma_melee.parry_efeito = parry_ef
            arco_base = float(getattr(arma_melee, "_arco_graus_base", MELEE_ARCO_GRAUS))
            alc_base = float(getattr(arma_melee, "_alcance_base", getattr(arma_melee, "alcance", 84.0)))
            cd_base = float(getattr(arma_melee, "_cooldown_base", 0.6))
            arma_melee.alcance = alc_base
            if parry_prec == "cirurgico":
                arma_melee.arco_graus = 65.0
                arma_melee.parry_duracao = 0.09
                arma_melee.parry_alcance_mult = 0.85 * (0.75 if parry_ef == "ventoinha_360" else 1.0)
                arma_melee.parry_dano_mult = 1.75
                arma_melee.parry_splash_raio = 140.0
                arma_melee.cooldown = cd_base
            elif parry_prec == "amplificado":
                arma_melee.arco_graus = 135.0
                arma_melee.parry_duracao = 0.17
                arma_melee.parry_alcance_mult = 1.25 * (0.75 if parry_ef == "ventoinha_360" else 1.0)
                arma_melee.parry_dano_mult = 0.70
                arma_melee.parry_splash_raio = 90.0
                arma_melee.cooldown = round(cd_base + 0.25, 4)
            elif parry_prec == "postura_riposte":
                arma_melee.arco_graus = arco_base
                arma_melee.parry_duracao = 0.45
                arma_melee.parry_alcance_mult = 0.75 if parry_ef == "ventoinha_360" else 1.0
                arma_melee.parry_dano_mult = 1.25
                arma_melee.parry_splash_raio = 110.0
                arma_melee.cooldown = cd_base
            else:
                arma_melee.arco_graus = arco_base
                arma_melee.parry_duracao = 0.12
                arma_melee.parry_alcance_mult = 0.75 if parry_ef == "ventoinha_360" else 1.0
                arma_melee.parry_dano_mult = 1.0
                arma_melee.parry_splash_raio = 90.0
                arma_melee.cooldown = cd_base
            if parry_ef == "ventoinha_360":
                arma_melee.ultimo_parry_cd_total = 6.5
            elif parry_ef == "firewall_estatico":
                arma_melee.ultimo_parry_cd_total = 5.5
            elif arma_melee.tempo_recarga_restante <= 0.0:
                arma_melee.ultimo_parry_cd_total = float(arma_melee.cooldown)

        n_configs_ativas = (
            self.gerenciador_config.contar_configs_nao_neutras()
            if hasattr(self, "gerenciador_config") and hasattr(self.gerenciador_config, "contar_configs_nao_neutras")
            else 0
        )
        if getattr(self, "sistema_conquistas", None) is not None and hasattr(self.sistema_conquistas, "obter_firmwares_ativos"):
            equipados_todos = list(getattr(self.sistema_conquistas, "modificadores_equipados", []))
            firmwares = self.sistema_conquistas.obter_firmwares_ativos(n_configs_ativas)
            if hasattr(self, "_firmwares_ativos_partida"):
                prev_ativos = set(self._firmwares_ativos_partida)
                novos_ativos = set(firmwares)
                for slot_idx in (2, 1, 0):
                    if slot_idx < len(equipados_todos):
                        cid = equipados_todos[slot_idx]
                        if cid in prev_ativos and cid not in novos_ativos:
                            chip_def = CHIPS_FIRMWARE.get(cid)
                            nome_c = chip_def.nome if chip_def else cid
                            cota = COTAS_SLOTS_FIRMWARE[slot_idx]
                            self.enfileirar_banner_desbloqueio(
                                tr("ui_geral", "banner_firmware_desativado_tit"),
                                tr("ui_geral", "banner_firmware_desativado_sub", nome=nome_c, slot=slot_idx + 1, cota=cota),
                                cor=LARANJA_ALERTA,
                            )
                for slot_idx in (0, 1, 2):
                    if slot_idx < len(equipados_todos):
                        cid = equipados_todos[slot_idx]
                        if cid in novos_ativos and cid not in prev_ativos:
                            chip_def = CHIPS_FIRMWARE.get(cid)
                            nome_c = chip_def.nome if chip_def else cid
                            cota = COTAS_SLOTS_FIRMWARE[slot_idx]
                            self.enfileirar_banner_desbloqueio(
                                tr("ui_geral", "banner_firmware_reativado_tit"),
                                tr("ui_geral", "banner_firmware_reativado_sub", nome=nome_c, n_configs=n_configs_ativas, cota=cota),
                                cor=VERDE_CURA,
                            )
            self._firmwares_ativos_partida = set(firmwares)
        else:
            firmwares = (
                list(getattr(self.sistema_conquistas, "modificadores_equipados", []))
                if getattr(self, "sistema_conquistas", None) is not None
                else []
            )
        if hasattr(self, "efeitos_combate") and self.efeitos_combate is not None:
            self.efeitos_combate.reconstruir(mods, firmwares)

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

        # 3. Propagação de qualidade gráfica, vsync, escala de resolução e sincronização de áudio
        baixa_qualidade = (str(self.gerenciador_config.obter_valor("graficos_qualidade")).lower() == "baixa") if hasattr(self, "gerenciador_config") else False
        if hasattr(self, "janela") and self.janela:
            self.janela.low_graphics = baixa_qualidade
            if hasattr(self, "gerenciador_config") and self.gerenciador_config:
                val_vsync = str(self.gerenciador_config.obter_valor("vsync")).strip().lower()
                vsync_desejado = val_vsync not in ("desligado", "false", "0", "off")
                if getattr(self, "_ultimo_vsync_ativo", None) != vsync_desejado:
                    self._ultimo_vsync_ativo = vsync_desejado
                    if getattr(self.janela, "vsync_ativo", None) != vsync_desejado and hasattr(self.janela, "definir_vsync"):
                        self.janela.definir_vsync(vsync_desejado)
                val_res = str(self.gerenciador_config.obter_valor("resolucao"))
                if hasattr(self.janela, "definir_resolucao"):
                    self.janela.definir_resolucao(val_res)
        if hasattr(self, "sistema_particulas") and self.sistema_particulas:
            self.sistema_particulas.low_graphics = baixa_qualidade

        try:
            vol_master = float(self.config_sistema.obter_valor("volume_master")) if hasattr(self, "config_sistema") and self.config_sistema else 100.0
            vol_musica = float(self.config_sistema.obter_valor("volume_musica")) if hasattr(self, "config_sistema") and self.config_sistema else 100.0
            vol_sfx = float(self.config_sistema.obter_valor("volume_sfx")) if hasattr(self, "config_sistema") and self.config_sistema else 100.0
            if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                self.sistema_audio.definir_volumes_alvo(vol_master, vol_musica, vol_sfx)
            if hasattr(self, "sistema_musica") and self.sistema_musica is not None:
                self.sistema_musica.atualizar_volume(vol_master, vol_musica)
            pygame.mixer.music.set_volume(self._obter_volume_musica_efetivo(0.4))
            self.volume_sfx_efetivo = clamp((vol_master / 100.0) * (vol_sfx / 100.0), 0.0, 1.0)
            from PPlay.sound import SoundManager
            SoundManager.set_sfx_volume(int(round(self.volume_sfx_efetivo * 100.0)))
            if pygame.mixer.get_init():
                from src.sistemas.sistema_musica import SistemaMusica
                inicio_canais_sfx = SistemaMusica._CANAIS_RESERVADOS
                for ch_idx in range(inicio_canais_sfx, pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(ch_idx).set_volume(self.volume_sfx_efetivo)
        except (pygame.error, ValueError, TypeError, ImportError):
            pass

    def _obter_arma_melee(self):
        for arma in getattr(self.jogador, "armas", []):
            if isinstance(arma, Melee) or getattr(arma, "slot", None) == 1:
                return arma
        return None


    def iniciar_boss_grace_period(self):
        """
        Inicia o grace period de 10 segundos antes da cutscene do Chefe Final,
        permitindo ao jogador limpar as hordas ao redor e coletar o loot no chão.
        """
        if self.boss_grace_period_ativo or self.boss_cutscene_ativa or (self.chefe_final is not None and self.chefe_final.vivo):
            return
        self.boss_grace_period_ativo = True
        self.boss_grace_timer = 10.0

    def obter_texto_boss_grace_period(self) -> str:
        """Retorna o texto formatado da contagem regressiva do grace period."""
        segundos = max(1, int(math.ceil(self.boss_grace_timer)))
        return tr("ui_geral", "boss_grace_period", segundos=segundos)

    def iniciar_boss_cutscene(self):
        """
        Inicia a sequência cinematográfica de introdução do Chefe Final (Geladeira Tsunami).
        NÃO instancia a Geladeira durante a queda de energia inicial para evitar que ela e o balão
        apareçam antes do fade-in / equalizadores.
        """
        if self.boss_cutscene_ativa or (self.chefe_final is not None and self.chefe_final.vivo):
            return
        self.boss_grace_period_ativo = False
        self.boss_grace_timer = 0.0
        self.boss_cutscene_ativa = True
        self.boss_cutscene_fase = "whiteout"
        self.boss_cutscene_timer = 0.0
        self.overlay_cutscene_cor = (255, 255, 255)
        self.overlay_cutscene_alpha = 0.0
        try:
            if hasattr(self, "sistema_musica") and self.sistema_musica is not None:
                self.sistema_musica.fadeout_para_boss(1600)
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
            if hasattr(self, "sistema_musica") and self.sistema_musica is not None:
                self.sistema_musica.parar_dinamica(entrar_estado_boss=True)
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
            dt_real = None
            if hasattr(self.janela, "delta_time_real"):
                cand = self.janela.delta_time_real()
                if isinstance(cand, (int, float)) and not isinstance(cand, bool):
                    dt_real = float(cand)
            dt = dt_real if dt_real is not None else self.janela.delta_time()
            # Em testes unitários headless (primeiro frame sem tick), avança 1 frame padrão (1/60s)
            if dt <= 0.0:
                dt = 1.0 / 60.0
            # Preserva tempo real sob fps_cap intencional (ex: 15 FPS = 0.0667s/frame), mantendo teto seguro <= 0.10s
            max_dt_loop = DT_CLAMP_MAX
            if hasattr(self, "config_sistema") and self.config_sistema is not None:
                val_fps = str(self.config_sistema.obter_valor("fps_cap")).strip().lower()
                if val_fps in ("15", "30", "45"):
                    max_dt_loop = max(DT_CLAMP_MAX, min(0.10, 1.25 / float(int(val_fps))))
            dt = min(dt, max_dt_loop)
        self._ultimo_dt_draw = max(1e-4, float(dt))

        # Atualiza rampa suave de volume do gerenciador de áudio
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            self.sistema_audio.atualizar(dt)

        # Atualiza a máquina de estados da música dinâmica (inclusive pausado / modais / game over / hitstop)
        if hasattr(self, "sistema_musica") and self.sistema_musica is not None:
            menu_conq_ativo = bool(
                getattr(self, "menu_conquistas", None) is not None
                and getattr(self.menu_conquistas, "ativo", False)
            )
            musica_abafada = bool(
                self.pausado
                or self.game_over
                or self.menu_configs.ativo
                or menu_conq_ativo
                or self.modal_level_up.ativo
                or getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) > 0.0
                or self.modal_overclock.ativo
                or getattr(self.modal_overclock, "tempo_transicao_saida", 0.0) > 0.0
                or (hasattr(self, "menu_debug") and self.menu_debug.ativo)
            )
            possui_elite_agora = any(
                getattr(e, "is_elite", False) and getattr(e, "vivo", True)
                for e in getattr(self, "inimigos", [])
            )
            pausar_transicao = bool(
                musica_abafada
                or self.vitoria
                or getattr(self, "boss_cutscene_ativa", False)
                or getattr(self, "boss_grace_period_ativo", False)
            )
            self.sistema_musica.atualizar(
                tempo_sobrevivencia=self.tempo_sobrevivencia,
                abafado=musica_abafada,
                dt=dt,
                trava_assault=possui_elite_agora,
                pausar_transicao=pausar_transicao,
            )

        # Atualiza cooldown de reabertura do menu para evitar input bleed (C / ESC)
        if hasattr(self, "_cooldown_menu_toggle") and self._cooldown_menu_toggle > 0.0:
            self._cooldown_menu_toggle = max(0.0, self._cooldown_menu_toggle - dt)

        # Visibilidade do cursor do sistema: visível em pausa/modais/menus, oculto apenas em combate ativo com mira customizada
        if pygame.display.get_init():
            menu_conq_ativo_cur = bool(
                getattr(self, "menu_conquistas", None) is not None
                and getattr(self.menu_conquistas, "ativo", False)
            )
            mostrar_cursor_sistema = bool(
                self.pausado
                or self.game_over
                or self.vitoria
                or self.menu_configs.ativo
                or menu_conq_ativo_cur
                or self.modal_level_up.ativo
                or self.modal_overclock.ativo
                or (hasattr(self, "menu_debug") and self.menu_debug.ativo)
                or (getattr(self, "boss_cutscene_ativa", False) and getattr(self, "boss_cutscene_fase", "") != "whiteout")
                or not getattr(self.jogador, "vivo", True)
            )
            if not getattr(self, "_cursor_hw_ativo", False):
                pygame.mouse.set_visible(mostrar_cursor_sistema)
            elif mostrar_cursor_sistema:
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                except Exception:
                    pass
                self._cursor_hw_ativo = False
                pygame.mouse.set_visible(True)

        # 0. Se o Menu de Debug estiver ativo, processa seus inputs e congela o jogo
        if hasattr(self, "menu_debug"):
            debug_estava_ativo = self.menu_debug.ativo
            self.menu_debug.update(dt, self.teclado, self.mouse)
            if self.menu_debug.ativo:
                self.pausado = True
                self.buffer_tiro = 0.0
                return
            elif debug_estava_ativo and not self.modal_level_up.ativo and not self.modal_overclock.ativo and not self.menu_configs.ativo and not (getattr(self, "menu_conquistas", None) is not None and getattr(self.menu_conquistas, "ativo", False)) and not self.game_over and not self.vitoria:
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
            if not self.modal_overclock.ativo and not self.modal_level_up.ativo and not self.menu_configs.ativo and not (getattr(self, "menu_conquistas", None) is not None and getattr(self.menu_conquistas, "ativo", False)) and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                self.pausado = False
            return

        # 2. Se o Modal de Level Up estiver ativo, processa seus inputs e congela o jogo
        if self.modal_level_up.ativo or getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) > 0.0:
            self.modal_level_up.update(dt, self.teclado, self.mouse)
            self.buffer_tiro = 0.0
            if not self.modal_level_up.ativo and getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) <= 0.0 and not self.modal_overclock.ativo and not self.menu_configs.ativo and not (getattr(self, "menu_conquistas", None) is not None and getattr(self.menu_conquistas, "ativo", False)) and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                self.pausado = False
            return

        # 3. Se o Menu de Configurações estiver ativo, processa seus inputs e congela o jogo
        if self.menu_configs.ativo:
            self.menu_configs.update(dt, self.teclado, self.mouse)
            self.buffer_tiro = 0.0
            if not self.menu_configs.ativo:
                self._cooldown_menu_toggle = 0.18
                if not self.modal_level_up.ativo and not self.modal_overclock.ativo and not (getattr(self, "menu_conquistas", None) is not None and getattr(self.menu_conquistas, "ativo", False)) and not (hasattr(self, "menu_debug") and self.menu_debug.ativo):
                    self.pausado = False
            return

        # 3b. Se o Menu de Conquistas (somente leitura na pausa) estiver ativo, processa seus inputs
        if getattr(self, "menu_conquistas", None) is not None and getattr(self.menu_conquistas, "ativo", False):
            self.menu_conquistas.update(dt, self.teclado, self.mouse)
            self.buffer_tiro = 0.0
            if not self.menu_conquistas.ativo:
                self._cooldown_menu_toggle = 0.18
                self.pausado = True
            return

        # 4. Tecla 'C' ou clique no botão de engrenagem (LARGURA_TELA - 48, 16, 32x32) antes de qualquer inversão de mouse
        pode_abrir_menu = getattr(self, "_cooldown_menu_toggle", 0.0) <= 0.0
        if pode_abrir_menu and self.mouse is not None and hasattr(self.mouse, "button_down") and self.mouse.button_down(1):
            try:
                mx_gear, my_gear = self.mouse.get_position()
                gear_x = LARGURA_TELA - 48
                if (gear_x <= mx_gear <= gear_x + 32) and 16 <= my_gear <= 48:
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
                self.pausado = not self.pausado
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
            if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
                self.banner_dicas.atualizar(dt)
            if self.teclado.key_down("m") or self.teclado.key_down("M"):
                self._voltar_menu()
                return
            if self.mouse is not None and hasattr(self.mouse, "button_down") and self.mouse.button_down(1):
                try:
                    mx_p, my_p = self.mouse.get_position()
                    btn_cont_rect, btn_menu_rect = self._obter_rects_overlay_pausa()
                    if btn_cont_rect.collidepoint(mx_p, my_p):
                        self.pausado = False
                        return
                    if (
                        hasattr(self, "_obter_rect_btn_conquistas_pausa")
                        and getattr(self, "menu_conquistas", None) is not None
                        and self._obter_rect_btn_conquistas_pausa().collidepoint(mx_p, my_p)
                    ):
                        self.menu_conquistas.abrir()
                        return
                    if btn_menu_rect.collidepoint(mx_p, my_p):
                        self._voltar_menu()
                        return
                except Exception:
                    pass
            return

        # =========================================================================
        # 1. ATUALIZAÇÃO DO JOGADOR, CUTSCENE E INPUTS
        # =========================================================================
        # Grace period de 10s antes da Cutscene do Chefe Final
        if self.boss_grace_period_ativo and not self.boss_cutscene_ativa:
            self.boss_grace_timer = max(0.0, self.boss_grace_timer - dt)
            if self.boss_grace_timer <= 0.0:
                self.boss_grace_period_ativo = False
                self.iniciar_boss_cutscene()

        # Processamento da Cutscene do Chefe Final (Whiteout c/ Slow-Mo -> Blackout -> Música Fade-In -> Subida do Boss)
        if self.boss_cutscene_ativa:
            self.boss_cutscene_timer += dt
            if self.boss_cutscene_fase == "whiteout":
                prog_whiteout = clamp(self.boss_cutscene_timer / 2.0, 0.0, 1.0)
                self.overlay_cutscene_cor = (255, 255, 255)
                self.overlay_cutscene_alpha = min(255, int(255 * prog_whiteout))
                if self.boss_cutscene_timer >= 2.0:
                    self.boss_cutscene_fase = "blackout"
                    self.boss_cutscene_timer = 0.0
                    self.overlay_cutscene_cor = (0, 0, 0)
                    self.overlay_cutscene_alpha = 255
                    # Purga completa do mapa (inimigos, drops, projéteis, partículas e efeitos não-buff) e centraliza jogador
                    self.sistema_scavenger.desativar(self.inimigos)
                    self.inimigos = [self.chefe_final] if (self.chefe_final is not None and self.chefe_final.vivo) else []
                    self.sistema_drops.drops.clear()
                    self.projeteis.clear()
                    self.tiros_echo_pendentes.clear()
                    self.sistema_particulas.limpar()
                    self.efeitos_melee.clear()
                    self.zonas_fogo.clear()
                    self.trilhas_plasma.clear()
                    self.zonas_estase.clear()
                    self.pocas_gelo.clear()
                    self.toasts_coleta.clear()
                    if hasattr(self, "banners_desbloqueio"):
                        self.banners_desbloqueio.clear()
                    self.shake_timer = 0.0
                    self.shake_intensidade = 0.0
                    self.arena_freeze_timer = 0.0
                    self.hitstop_timer = 0.0
                    self.aura_cura_timer = 0.0
                    self.buffer_tiro = 0.0
                    self.spawner.timer_spawn = 0.0
                    self.vsync_tear_y = 0.0
                    self._motion_blur_surf = None
                    if hasattr(self.jogador, "rastro_posicoes") and self.jogador.rastro_posicoes is not None:
                        self.jogador.rastro_posicoes.clear()
                    if hasattr(self.jogador, "_rastro_timer"):
                        self.jogador._rastro_timer = 0.0
                    self.jogador.x = self.largura_arena / 2.0 - self.jogador.largura / 2.0
                    self.jogador.y = self.altura_arena / 2.0 - self.jogador.altura / 2.0
                    self.camera.follow(self.jogador, suavizacao=1.0)
                else:
                    # Durante o fade-out branco, o jogo continua rodando mas desacelera progressivamente até zerar
                    dt = dt * max(0.0, 1.0 - prog_whiteout)
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

        cutscene_congelada = self.boss_cutscene_ativa and self.boss_cutscene_fase != "whiteout"

        timer_congelado = getattr(self.menu_debug, "timer_congelado", False) if hasattr(self, "menu_debug") else False
        if not timer_congelado and not cutscene_congelada:
            self.tempo_sobrevivencia += dt
            if getattr(self, "sistema_conquistas", None) is not None and getattr(self.jogador, "vivo", True):
                val_fps_15 = str(self.config_sistema.obter_valor("fps_cap")).strip() if hasattr(self, "config_sistema") and self.config_sistema else ""
                if val_fps_15 == "15":
                    self.tempo_15fps_acumulado = getattr(self, "tempo_15fps_acumulado", 0.0) + dt
                else:
                    self.tempo_15fps_acumulado = 0.0
                notifs_15 = self.sistema_conquistas.atualizar_progresso_15fps(self.tempo_15fps_acumulado)
                if notifs_15:
                    self._enfileirar_notificacoes_conquistas(notifs_15)
                    if hasattr(self, "gerenciador_config") and self.gerenciador_config is not None:
                        self.gerenciador_config.sincronizar_recompensas_conquistas()
                        self.gerenciador_config.salvar_arquivo()

        # Atualiza temporizador de Screen Shake
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            if self.shake_timer == 0.0:
                self.shake_intensidade = 0.0

        # Atualiza sistema de partículas
        self.sistema_particulas.update(dt)

        # Atualiza e limpa toasts de coleta (mantém toasts e partículas fluindo durante hitstop)
        for t in self.toasts_coleta:
            t["tempo"] -= dt
            t["y"] -= 22.0 * dt
        self.toasts_coleta = [t for t in self.toasts_coleta if t["tempo"] > 0]

        # Atualiza fila de banners estilo Steam de conquistas/desbloqueios
        if getattr(self, "banners_desbloqueio", None):
            for b in self.banners_desbloqueio:
                b["tempo"] -= dt
            self.banners_desbloqueio = [b for b in self.banners_desbloqueio if b["tempo"] > 0.0]

        # Hitstop (0.08s no parry): pausa física da simulação mantendo partículas, shake e áudio ativos
        if getattr(self, "hitstop_timer", 0.0) > 0.0:
            self.hitstop_timer = max(0.0, self.hitstop_timer - dt)
            return

        # Processamento de disparos de eco (Multithreading Overclock)
        if not cutscene_congelada:
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

        crit_chance, crit_mult = 0.0, 2.0
        if not cutscene_congelada:
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

            efeitos_inst = self._obter_efeitos_combate() if hasattr(self, "_obter_efeitos_combate") else getattr(self, "efeitos_combate", None)
            if efeitos_inst is not None:
                self.jogador.mult_cadencia_efeitos = efeitos_inst.obter_mult_cadencia()
                self.jogador.mult_vel_efeitos = efeitos_inst.obter_mult_velocidade()
                self.jogador.mult_dano_recebido_efeitos = efeitos_inst.obter_mult_dano_recebido()
            else:
                self.jogador.mult_cadencia_efeitos = 1.0
                self.jogador.mult_vel_efeitos = 1.0
                self.jogador.mult_dano_recebido_efeitos = 1.0

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
                    "texto": tr("ui_geral", "toast_cura", val=val_c),
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
                    p_dr.origem_drone = True
                    if hitbox_mult != 1.0:
                        p_dr.largura = max(2, int(round(p_dr.largura * hitbox_mult)))
                        p_dr.altura = max(2, int(round(p_dr.altura * hitbox_mult)))
                        p_dr.width = p_dr.largura
                        p_dr.height = p_dr.altura
                self.projeteis.extend(tiros_drone)

            slot_atual = getattr(self.jogador, "slot_ativo", None)
            arma_atual = self.jogador.obter_arma_ativa() if self.jogador.vivo else None
            self._ultimo_slot_ativo = slot_atual
            self._arma_ativa_anterior = arma_atual

            # Atualiza a posição da câmera para seguir o jogador suavemente (dt-independente com CAMERA_DAMPING_K)
            val_suav = self.config_sistema.obter_valor("suavizacao_camera") if hasattr(self, "config_sistema") and self.config_sistema else "ligado"
            suavizacao_fator = 1.0 if str(val_suav).lower() in ("desligado", "0", "false") else (1.0 - (1.0 - CAMERA_DAMPING_K) ** (dt * 60.0))
            self.camera.follow(self.jogador, suavizacao=suavizacao_fator)

            # =========================================================================
            # 2. DISPARO DE ARMAS (PISTOLA, MELEE E ESPECIAIS COM BUFFER DE INPUT)
            # =========================================================================
            centro_jogador_x, centro_jogador_y, crit_chance, crit_mult = self._atualizar_disparos_jogador(
                dt,
                mods,
                hitbox_mult,
                mult_dano_buff,
            )

        # Atualiza o tempo de vida dos efeitos visuais de Melee e pulso de ASSAULT_INTRO
        if getattr(self, "pulso_assault_intro_timer", 0.0) > 0.0:
            self.pulso_assault_intro_timer = max(0.0, self.pulso_assault_intro_timer - dt)
        for ef in self.efeitos_melee:
            ef["tempo"] -= dt
        self.efeitos_melee = [ef for ef in self.efeitos_melee if ef["tempo"] > 0]

        # Atualiza Hologramas e hooks B+ por tick
        if hasattr(self, "hologramas") and self.hologramas:
            for holo in self.hologramas:
                if hasattr(holo, "update"):
                    ev_holo = holo.update(dt, inimigos=self.inimigos)
                    if isinstance(ev_holo, dict) and ev_holo.get("explodir"):
                        hx = float(ev_holo.get("x", 0.0))
                        hy = float(ev_holo.get("y", 0.0))
                        h_raio = float(ev_holo.get("raio", 115.0))
                        h_dano = int(ev_holo.get("dano", 45))
                        if hasattr(self, "sistema_particulas") and self.sistema_particulas is not None:
                            self.sistema_particulas.emitir_onda_choque(hx, hy, raio_max=h_raio, cor=(120, 230, 255))
                        for inim in self.inimigos:
                            if getattr(inim, "vivo", True):
                                icx = inim.x + getattr(inim, "largura", 28) * 0.5
                                icy = inim.y + getattr(inim, "altura", 28) * 0.5
                                if distancia(hx, hy, icx, icy) <= h_raio:
                                    inim.receber_dano(h_dano)
                                    if not inim.vivo and hasattr(self, "_registrar_abate_inimigo"):
                                        self._registrar_abate_inimigo(inim, mods)
            self.hologramas = [h for h in self.hologramas if getattr(h, "vivo", True)]

        if hasattr(self, "efeitos_combate") and self.efeitos_combate is not None:
            ctx_tick = ContextoCombate(
                cena=self,
                jogador=self.jogador,
                inimigos=self.inimigos,
                projeteis=self.projeteis,
                drops=self.sistema_drops.drops,
                particulas=getattr(self, "sistema_particulas", None),
                mods=mods,
                sistema_conquistas=getattr(self, "sistema_conquistas", None),
                hologramas=getattr(self, "hologramas", None),
                tempo_sobrevivencia=self.tempo_sobrevivencia,
            )
            self.efeitos_combate.disparar_ao_tick(ctx_tick, dt)

        # =========================================================================
        # 3. SPAWNER DE INIMIGOS
        # =========================================================================
        spawn_liberado = getattr(self.menu_debug, "spawn_natural_ativo", True) if hasattr(self, "menu_debug") else True
        if spawn_liberado and not cutscene_congelada and not self.boss_grace_period_ativo and self.arena_freeze_timer <= 0.0:
            fogo_cruzado_ranged = (str(self.config_sistema.obter_valor("inimigos_ranged")).lower() in ("ligado", "true", "1")) if hasattr(self, "config_sistema") and self.config_sistema else False
            permitir_ranged = True
            hp_inim_mult = getattr(mods, "hp_inimigos_mult", 1.0) if mods else 1.0
            vel_inim_mult = getattr(mods, "vel_inimigos_mult", 1.0) if mods else 1.0
            possui_elite = any(getattr(e, "is_elite", False) and getattr(e, "vivo", True) for e in self.inimigos) or (self.chefe_final is not None and self.chefe_final.vivo)

            if self.chefe_final is not None and self.chefe_final.vivo:
                if getattr(self.chefe_final, "estado", "") not in ("morte", ESTADO_MORTE):
                    # Durante o Chefe Final: ondas híbridas de especialistas coreografadas por fase (cap 24)
                    from src.entidades.inimigo_padrao import InimigoPadrao
                    from src.entidades.inimigo_rapido import InimigoRapido
                    from src.entidades.inimigo_ranged import InimigoRanged
                    from src.entidades.inimigo_phasing import InimigoPhasing
                    from src.entidades.inimigo_impressora import InimigoImpressoraTermica
                    from src.entidades.inimigo_ninja import InimigoNinja
                    from src.entidades.inimigo_blindado import InimigoBlindado
                    mobs_comuns = [e for e in self.inimigos if e.vivo and e != self.chefe_final and not getattr(e, "is_caixa_som", False)]
                    ninjas_vivos = sum(1 for e in mobs_comuns if getattr(e, "is_ninja", False))
                    impressoras_vivas = sum(1 for e in mobs_comuns if type(e).__name__ == "InimigoImpressoraTermica")
                    if len(mobs_comuns) < 24 and random.random() < min(0.95, 1.6 * dt * 3.0):
                        ex, ey = self.spawner.gerar_posicao_spawn(
                            self.camera.x, self.camera.y,
                            view_w=LARGURA_TELA, view_h=ALTURA_TELA,
                            arena_w=self.largura_arena, arena_h=self.altura_arena
                        )
                        estado_boss = str(getattr(self.chefe_final, "estado", "fase1"))
                        r_mob = random.random()
                        if estado_boss == "fase1":
                            if ninjas_vivos < 1 and r_mob < 0.14:
                                mob_boss = InimigoNinja(x=ex, y=ey)
                            elif r_mob < 0.40:
                                mob_boss = InimigoRapido(x=ex, y=ey)
                            elif r_mob < 0.60:
                                mob_boss = InimigoRanged(x=ex, y=ey, modo_homing=fogo_cruzado_ranged)
                                if fogo_cruzado_ranged:
                                    mob_boss.rajada_tripla = True
                            else:
                                mob_boss = InimigoPadrao(x=ex, y=ey)
                        elif estado_boss == "fase2":
                            if impressoras_vivas < 1 and r_mob < 0.16:
                                mob_boss = InimigoImpressoraTermica(x=ex, y=ey)
                            elif r_mob < 0.36:
                                mob_boss = InimigoPhasing(x=ex, y=ey)
                            elif r_mob < 0.62:
                                mob_boss = InimigoRapido(x=ex, y=ey)
                            else:
                                mob_boss = InimigoRanged(x=ex, y=ey, modo_homing=fogo_cruzado_ranged)
                                if fogo_cruzado_ranged:
                                    mob_boss.rajada_tripla = True
                        else:
                            if impressoras_vivas < 1 and r_mob < 0.14:
                                mob_boss = InimigoImpressoraTermica(x=ex, y=ey)
                            elif ninjas_vivos < 1 and r_mob < 0.28:
                                mob_boss = InimigoNinja(x=ex, y=ey)
                            elif r_mob < 0.48:
                                mob_boss = InimigoBlindado(x=ex, y=ey)
                            else:
                                mob_boss = InimigoRapido(x=ex, y=ey)
                        escala_hp_tempo = self.spawner.calcular_escala_hp_tempo(self.tempo_sobrevivencia)
                        mob_boss.hp_max = max(1, int(round(mob_boss.hp_max * hp_inim_mult * escala_hp_tempo)))
                        mob_boss.hp = mob_boss.hp_max
                        mob_boss.velocidade = float(mob_boss.velocidade) * vel_inim_mult
                        if hasattr(mob_boss, "orientar_para"):
                            mob_boss.orientar_para(centro_jogador_x, centro_jogador_y)
                        self.inimigos.append(mob_boss)
            else:
                gatilho_intro = (
                    self.sistema_musica.consumir_evento_assault_intro()
                    if hasattr(self, "sistema_musica") and self.sistema_musica is not None
                    else False
                )
                if gatilho_intro:
                    self.pulso_assault_intro_timer = 1.6
                fase_onda = (
                    getattr(self.sistema_musica, "fase_onda_atual", "ANTICIPATION")
                    if hasattr(self, "sistema_musica") and self.sistema_musica is not None
                    else None
                )
                contagens_taticas = {"ranged": 0, "impressora": 0, "tank": 0, "ninja": 0}
                total_vivos = 0
                for e in self.inimigos:
                    if not getattr(e, "vivo", True):
                        continue
                    total_vivos += 1
                    nome_cls = type(e).__name__
                    if nome_cls == "InimigoRanged":
                        contagens_taticas["ranged"] += 1
                    elif nome_cls == "InimigoImpressoraTermica":
                        contagens_taticas["impressora"] += 1
                    elif nome_cls == "InimigoTank":
                        contagens_taticas["tank"] += 1
                    elif getattr(e, "is_ninja", False):
                        contagens_taticas["ninja"] += 1

                forcar_rajada = bool(getattr(mods, "inimigos_ranged_bullet_hell", False) or fogo_cruzado_ranged)
                novos_inimigos = self.spawner.update(
                    dt=dt,
                    camera_x=self.camera.x,
                    camera_y=self.camera.y,
                    total_inimigos_vivos=total_vivos,
                    view_w=LARGURA_TELA,
                    view_h=ALTURA_TELA,
                    arena_w=self.largura_arena,
                    arena_h=self.altura_arena,
                    hp_mult=hp_inim_mult,
                    vel_mult=vel_inim_mult,
                    permitir_ranged=permitir_ranged,
                    possui_elite_vivo=possui_elite,
                    ninjas_vivos=contagens_taticas["ninja"],
                    fase_onda=fase_onda,
                    gatilho_assault_intro=gatilho_intro,
                    contagens_taticas=contagens_taticas,
                    forcar_rajada_tripla=forcar_rajada,
                )
                if fogo_cruzado_ranged:
                    for ni in novos_inimigos:
                        if hasattr(ni, "rajada_tripla"):
                            ni.rajada_tripla = True
                        if hasattr(ni, "modo_homing"):
                            ni.modo_homing = True
                for ni in novos_inimigos:
                    if hasattr(ni, "orientar_para"):
                        ni.orientar_para(centro_jogador_x, centro_jogador_y)
                self.inimigos.extend(novos_inimigos)

                # Gatilho Nível 12 após ~3:05 (185s) OU 2º Ciclo Musical (MINIBOSS_CICLOS_RUN) / fallback tempo_elite >= 195s
                nivel_max = getattr(getattr(self.jogador, "sistema_xp", None), "nivel_max", 12)
                ciclos_concluidos = (
                    getattr(self.sistema_musica, "ciclos_assault_concluidos", 0)
                    if hasattr(self, "sistema_musica") and self.sistema_musica is not None
                    else 0
                )
                if self.chefe_final is None and not self.boss_cutscene_ativa and not self.boss_grace_period_ativo:
                    if getattr(self.jogador, "nivel", 1) >= nivel_max and getattr(self, "tempo_sobrevivencia", 0.0) >= 185.0:
                        self.iniciar_boss_grace_period()
                    elif not possui_elite and (ciclos_concluidos >= MINIBOSS_CICLOS_RUN or getattr(self.spawner, "tempo_elite", 0.0) >= 195.0):
                        self.iniciar_boss_grace_period()

        # =========================================================================
        # 4. FÍSICA DOS PROJÉTEIS
        # =========================================================================
        self._atualizar_fisica_projeteis(
            dt,
            mods,
            cutscene_congelada,
            centro_jogador_x,
            centro_jogador_y,
        )

        # =========================================================================
        # 5. IA DOS INIMIGOS E DANO DE CONTATO NO JOGADOR
        # =========================================================================
        val_ilum = str(self.config_sistema.obter_valor("iluminacao")).lower() in ("ligado", "true", "1") if hasattr(self, "config_sistema") and self.config_sistema else False
        mult_dano_inim_base = getattr(mods, "dano_inimigos_mult", 1.0) if mods else 1.0

        pular_ia_inimigos = getattr(self.jogador, "stutter_freeze_timer", 0.0) > 0.0 or self.arena_freeze_timer > 0.0

        for inimigo in self.inimigos:
            if inimigo == self.chefe_final:
                continue
            if not pular_ia_inimigos and not cutscene_congelada:
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
                            self.jogador.receber_dano(25, causa_morte=tr("ui_geral", "causa_explosao_miniboss"))
                        inimigo.vivo = False
                        self.toasts_coleta.append({
                            "texto": tr("ui_geral", "toast_miniboss_superaqueceu"),
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
                        self.jogador.receber_dano(18, causa_morte=tr("ui_geral", "causa_pulso_eletrico"))
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
                if hasattr(self, "_processar_eventos_blindagem"):
                    self._processar_eventos_blindagem(inimigo)

            if cutscene_congelada:
                continue

            # Atropelamento (Movimento pelo Mouse ou Controles de Tanque Bulldozer)
            tanque_bulldozer = getattr(self.jogador, "controles_tanque", False) and getattr(self.jogador, "tanque_avancando", False)
            ram_imune_contato = False
            if (getattr(mods, "movimento_ram_collision", False) or tanque_bulldozer) and not getattr(inimigo, "is_elite", False):
                if getattr(inimigo, "cooldown_ram_atual", 0.0) <= 0.0:
                    if colisao_aabb(inimigo.x, inimigo.y, inimigo.largura, inimigo.altura,
                                    self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                        i_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                        i_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                        dir_ram_x, dir_ram_y = vetor_direcao(centro_jogador_x, centro_jogador_y, i_cx, i_cy)
                        dist_push = 40.0 if tanque_bulldozer else 24.0
                        dano_ram_base = 25 if tanque_bulldozer else 15
                        inimigo.x += dir_ram_x * dist_push
                        inimigo.y += dir_ram_y * dist_push
                        self._clamp_entidade_arena(inimigo)
                        ret_d = inimigo.receber_dano(dano_ram_base, origem_x=centro_jogador_x, origem_y=centro_jogador_y, dir_ataque=(dir_ram_x, dir_ram_y))
                        dano_ram = int(ret_d) if isinstance(ret_d, (int, float)) else dano_ram_base
                        inimigo.cooldown_ram_atual = 0.35
                        ram_imune_contato = tanque_bulldozer
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
            if not ram_imune_contato and inimigo.vivo and colisao_aabb(inimigo.x, inimigo.y, inimigo.largura, inimigo.altura,
                            self.jogador.x, self.jogador.y, self.jogador.largura, self.jogador.altura):
                if getattr(self.jogador, "em_dash_iframes", False):
                    if hasattr(self, "_tentar_registrar_just_dodge"):
                        self._tentar_registrar_just_dodge(origem="contato", mods=mods)
                    continue
                if getattr(inimigo, "cooldown_contato_atual", 0.0) <= 0.0:
                    dano_contato_base = getattr(inimigo, "dano_contato", 10)
                    mult_dano_inim = mult_dano_inim_base
                    if val_ilum:
                        dist_vis = distancia(inimigo.x + inimigo.largura / 2.0, inimigo.y + inimigo.altura / 2.0, centro_jogador_x, centro_jogador_y)
                        if dist_vis > 195.0:
                            mult_dano_inim *= getattr(mods, "dano_fora_visao_mult", 0.50)
                    dano_efetivo_contato = max(1, int(round(dano_contato_base * mult_dano_inim)))
                    nome_inim = getattr(inimigo, "nome_elite", "") or getattr(inimigo, "nome_exibicao", "") or type(inimigo).__name__
                    self.jogador.receber_dano(dano_efetivo_contato, causa_morte=tr("ui_geral", "causa_contato_inimigo", nome=nome_inim))
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

        self._resolver_fisica_suave_horda(dt, mods, cutscene_congelada, pular_ia_inimigos)

        # Atualização do Chefe Final (Geladeira Tsunami)
        _boss_pode_atualizar = (
            self.chefe_final is not None
            and self.chefe_final.vivo
            and (not self.boss_cutscene_ativa or (self.boss_cutscene_fase == "musica_in" and self.chefe_final.estado == "intro"))
        )
        if _boss_pode_atualizar and (not pular_ia_inimigos or self.chefe_final.estado == "intro"):
            bass_energy = 0.0
            if hasattr(self, "analisador_fft_boss") and self.analisador_fft_boss is not None:
                pos_ms = -1
                try:
                    if pygame.mixer.get_init():
                        pos_ms = pygame.mixer.music.get_pos()
                except Exception:
                    pos_ms = -1
                if pos_ms is None or pos_ms < 0:
                    pos_ms = self.tempo_sobrevivencia * 1000.0
                bass_energy = self.analisador_fft_boss.obter_energia_grave(float(pos_ms), dt=dt)
            self.chefe_final.update(dt, (centro_jogador_x, centro_jogador_y), limite_arena=(self.largura_arena, self.altura_arena), bass_energy=bass_energy)
            novos_tiros_boss = self.chefe_final.obter_projeteis_pendentes()
            if novos_tiros_boss:
                self.projeteis.extend(novos_tiros_boss)
            if getattr(self.chefe_final, "goons_pendentes", None):
                self.inimigos.extend(self.chefe_final.goons_pendentes)
                self.chefe_final.goons_pendentes.clear()
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
                if getattr(self.jogador, "em_dash_iframes", False):
                    if hasattr(self, "_tentar_registrar_just_dodge"):
                        self._tentar_registrar_just_dodge(origem="contato_boss", mods=mods)
                elif getattr(self.chefe_final, "cooldown_contato_atual", 0.0) <= 0.0:
                    dano_contato_base = getattr(self.chefe_final, "dano_contato", 25)
                    mult_dano_inim = mult_dano_inim_base
                    if val_ilum:
                        dist_vis = distancia(self.chefe_final.x + self.chefe_final.largura / 2.0, self.chefe_final.y + self.chefe_final.altura / 2.0, centro_jogador_x, centro_jogador_y)
                        if dist_vis > 195.0:
                            mult_dano_inim *= getattr(mods, "dano_fora_visao_mult", 0.50)
                    dano_efetivo_contato = max(1, int(round(dano_contato_base * mult_dano_inim)))
                    nome_inim = getattr(self.chefe_final, "nome_elite", "") or getattr(self.chefe_final, "nome_exibicao", "") or type(self.chefe_final).__name__
                    self.jogador.receber_dano(dano_efetivo_contato, causa_morte=tr("ui_geral", "causa_contato_inimigo", nome=nome_inim))
                    self.chefe_final.cooldown_contato_atual = getattr(self.chefe_final, "cooldown_contato_max", 0.4)
                    self.aplicar_shake(10.0, 0.25)

        # =========================================================================
        # 6. COLISÕES: PROJÉTEIS VS INIMIGOS E DETONAÇÃO DE EXPLOSIVOS
        # =========================================================================
        self._atualizar_projeteis_e_colisoes(
            dt,
            mods,
            cutscene_congelada,
            centro_jogador_x,
            centro_jogador_y,
            crit_chance,
            crit_mult,
            val_ilum,
            mult_dano_inim_base,
        )

        # =========================================================================
        # 7. SISTEMA DE DROPS E PROGRESSÃO DE XP
        # =========================================================================
        is_boss_lutando = (self.chefe_final is not None and self.chefe_final.vivo)
        mult_drops = getattr(mods, "drops_valor_mult", 1.0) if mods else 1.0
        mult_xp = getattr(mods, "xp_ganho_mult", 1.0) if mods else 1.0
        self.sistema_drops.update(dt, pausar_despawn=is_boss_lutando)
        eventos_coleta = self.sistema_drops.coletar_jogador(
            self.jogador,
            mult_valor_drop=mult_drops,
            mult_xp=mult_xp,
            sistema_conquistas=getattr(self, "sistema_conquistas", None),
        )
        for ev in eventos_coleta:
            drop_x = ev.get("x", self.jogador.x + 16)
            drop_y = ev.get("y", self.jogador.y + 16)
            self.sistema_particulas.emitir_burst_drop(drop_x, drop_y, tipo=ev["tipo"])
            if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                mapa_sfx_drop = {
                    "xp": "sfx_pickup_xp",
                    "cura": "sfx_pickup_cura",
                    "arma": "sfx_pickup_arma",
                    "equipamento": "sfx_pickup_equipamento",
                    "overclock": "sfx_levelup",
                    "powerup": "sfx_pickup_equipamento",
                    "micro_sucata": "sfx_pickup_xp",
                }
                sfx_drop = mapa_sfx_drop.get(ev["tipo"])
                if sfx_drop:
                    self.sistema_audio.tocar_sfx(sfx_drop, pitch_aleatorio=True)

            if ev["tipo"] == "xp":
                xp_exibido = int(ev.get("xp_ganho") or max(1, int(round(ev["valor"] * mult_xp))))
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_xp", val=xp_exibido),
                    "cor": AMARELO_XP,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 10,
                    "tempo": 1.1,
                    "tempo_max": 1.1
                })
            elif ev["tipo"] == "cura":
                val_cura = ev.get("valor", 35)
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_cura", val=val_cura),
                    "cor": VERDE_CURA,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 10,
                    "tempo": 1.4,
                    "tempo_max": 1.4
                })
            elif ev["tipo"] == "arma":
                arma_coletada = ev.get("arma") or self.jogador.arma_especial
                nome_arma = getattr(arma_coletada, "nome", tr("ui_geral", "fallback_arma_especial"))
                mun = getattr(arma_coletada, "municao_max", 30)
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_arma_coletada", nome=nome_arma, val=mun),
                    "cor": DOURADO,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 15,
                    "tempo": 1.8,
                    "tempo_max": 1.8
                })
            elif ev["tipo"] == "equipamento":
                nome_drone = tr("ui_geral", "fallback_drone")
                if hasattr(self.jogador, "drones") and self.jogador.drones:
                    nome_drone = getattr(self.jogador.drones[-1], "nome", nome_drone)
                elif hasattr(self.jogador, "drone") and self.jogador.drone:
                    nome_drone = getattr(self.jogador.drone, "nome", nome_drone)
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_drone_coletado", nome=nome_drone),
                    "cor": (255, 160, 50),
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 15,
                    "tempo": 1.8,
                    "tempo_max": 1.8
                })
            elif ev["tipo"] == "overclock":
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_overclock_obtido"),
                    "cor": (215, 140, 255),
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 20,
                    "tempo": 2.5,
                    "tempo_max": 2.5
                })
                self.modal_overclock.abrir()
                if self.modal_overclock.ativo:
                    self.pausado = True
                else:
                    self.jogador.curar(25)
                    self.pontos += 500
            elif ev["tipo"] == "micro_sucata":
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_micro_sucata"),
                    "cor": AZUL_CIANO,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 12,
                    "tempo": 1.0,
                    "tempo_max": 1.0,
                })
            elif ev["tipo"] == "capsula_powerup":
                drop_obj = ev.get("drop")
                sub = getattr(drop_obj, "subtipo", "buff_dano_temp") if drop_obj else "buff_dano_temp"
                rotulo = getattr(drop_obj, "rotulo", tr("combate_entidades", "drop_suprimento")) if drop_obj else tr("combate_entidades", "drop_suprimento")
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
                    pool_armas = self.sistema_drops.obter_pool_armas_especiais(
                        sistema_conquistas=getattr(self, "sistema_conquistas", None)
                    )
                    nova_a = random.choice(pool_armas)()
                    self.jogador.equipar_arma_especial(nova_a)
                elif sub == "caixa_equip":
                    novo_d = random.choice([DroneCura, DroneCombate, DroneSuporte])(tempo_vida=30.0)
                    self.jogador.adicionar_drone(novo_d)
                self.toasts_coleta.append({
                    "texto": tr("ui_geral", "toast_capsula_ativa", nome=rotulo),
                    "cor": AZUL_CIANO,
                    "x": self.jogador.x + 16,
                    "y": self.jogador.y - 16,
                    "tempo": 1.6,
                    "tempo_max": 1.6
                })

        # Atualiza IA do Scavenger APENAS se a configuração "coleta_inimiga" estiver desbloqueada e ligada
        if (
            self.chefe_final is not None
            and getattr(self.chefe_final, "vivo", False)
            and not getattr(self, "_dano_na_fase3_boss", False)
        ):
            em_f3 = (
                getattr(self.chefe_final, "fase_atual", 1) >= 3
                or "fase3" in str(getattr(self.chefe_final, "estado", "")).lower()
                or getattr(self.chefe_final, "hp", 1) <= getattr(self.chefe_final, "hp_max", 1) * 0.35
            )
            if em_f3:
                hp_atual_j = getattr(self.jogador, "hp", 0)
                if hasattr(self, "_hp_anterior_f3_boss") and hp_atual_j < self._hp_anterior_f3_boss:
                    self._dano_na_fase3_boss = True
                self._hp_anterior_f3_boss = hp_atual_j
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
        if getattr(self, "sistema_conquistas", None) is not None:
            if vitoria:
                from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
                configs_nao_neutras = sum(
                    1
                    for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
                    if self.gerenciador_config.is_desbloqueada(cid)
                    and self.gerenciador_config.obter_valor(cid) != cdef.valor_padrao
                )
                cores_inv = str(self.gerenciador_config.obter_valor("cores_invertidas")).strip().lower() in (
                    "ligado", "true", "1"
                )
                vsync_off = str(self.gerenciador_config.obter_valor("vsync")).strip().lower() in (
                    "desligado", "false", "0", "off"
                )
                sem_dano_f3 = not getattr(self, "_dano_na_fase3_boss", False)
                notifs_boss = self.sistema_conquistas.registrar_evento(
                    "vitoria_boss",
                    1,
                    {
                        "sem_configs": (configs_nao_neutras == 0),
                        "configs_nao_neutras": configs_nao_neutras,
                        "cores_invertidas": cores_inv,
                        "vsync_desligado": vsync_off,
                        "sem_dano_f3": sem_dano_f3,
                    },
                )
                self._enfileirar_notificacoes_conquistas(notifs_boss)
            self.gerenciador_config.sincronizar_recompensas_conquistas()
            self.gerenciador_config.salvar_arquivo()

    def enfileirar_banner_desbloqueio(self, titulo: str, subtitulo: str = "", cor=None, duracao: float = 4.2) -> None:
        """Enfileira um banner estilo Steam no canto inferior direito e toca chime de desbloqueio."""
        if not hasattr(self, "banners_desbloqueio") or self.banners_desbloqueio is None:
            self.banners_desbloqueio = []
        cor_final = cor if (isinstance(cor, tuple) and len(cor) >= 3) else DOURADO
        self.banners_desbloqueio.append({
            "titulo": str(titulo),
            "subtitulo": str(subtitulo),
            "cor": cor_final,
            "tempo": float(duracao),
            "tempo_max": float(duracao),
        })
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            if hasattr(self.sistema_audio, "tocar_sfx"):
                self.sistema_audio.tocar_sfx("sfx_levelup")
            elif hasattr(self.sistema_audio, "tocar_parry_clang"):
                self.sistema_audio.tocar_parry_clang()

    def _emitir_evento_conquista(
        self,
        evento: str,
        quantidade: int | float = 1,
        contexto: dict | None = None,
    ) -> list[dict]:
        """Despacha um evento para SistemaConquistas, enfileira banners e salva apenas em desbloqueio novo."""
        sis_cnq = getattr(self, "sistema_conquistas", None)
        if sis_cnq is None and hasattr(self, "_obter_sistema_conquistas"):
            sis_cnq = self._obter_sistema_conquistas()
        if sis_cnq is None or not hasattr(sis_cnq, "registrar_evento"):
            return []
        notifs = list(sis_cnq.registrar_evento(evento, quantidade, contexto) or [])
        if notifs:
            self._enfileirar_notificacoes_conquistas(notifs)
            ger = getattr(self, "gerenciador_config", None) or getattr(self, "config_sistema", None)
            if ger is not None:
                if hasattr(ger, "sincronizar_recompensas_conquistas"):
                    ger.sincronizar_recompensas_conquistas()
                if hasattr(ger, "salvar_arquivo"):
                    try:
                        ger.salvar_arquivo(SAVE_FILE_PATH)
                    except OSError:
                        pass
        return notifs

    def _enfileirar_notificacoes_conquistas(self, notifs: list[dict] | None) -> None:
        """Converte notificações de `SistemaConquistas.registrar_evento` em banners estilo Steam."""
        if not notifs:
            return
        from src.ui.hud import formatar_recompensas_conquista
        for notif in notifs:
            titulo = str(notif.get("titulo", tr("ui_geral", "hud_banner_titulo_fallback")))
            recomps = notif.get("recompensas", [])
            subtitulo = formatar_recompensas_conquista(recomps) if recomps else tr("ui_geral", "banner_conquista_sub_fallback")
            self.enfileirar_banner_desbloqueio(titulo, subtitulo, cor=DOURADO)

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


    def _reiniciar_partida(self):
        SceneManager.change_scene(GameplayScene())

    def _voltar_menu(self):
        from src.cenas.menu_principal import MenuPrincipalScene
        SceneManager.change_scene(MenuPrincipalScene())

    def _resolver_fisica_suave_horda(
        self, dt: float, mods, cutscene_congelada: bool, pular_ia_inimigos: bool
    ) -> None:
        """
        Aplica separação suave (dampened) entre inimigos via spatial hash O(N)
        e minion block suave no jogador (contornado durante Dash ou atropelamento).
        """
        if cutscene_congelada or pular_ia_inimigos or dt <= 0.0:
            return

        tangiveis = [
            e for e in self.inimigos
            if getattr(e, "vivo", True)
            and not getattr(e, "is_boss", False)
            and not getattr(e, "is_caixa_som", False)
            and not getattr(e, "em_fase", False)
            and getattr(e, "estado", "") not in ("morte", ESTADO_MORTE)
        ]
        n = len(tangiveis)
        if n == 0:
            return

        if n >= 2:
            cell = 48.0
            centros_w_h = []
            buckets: dict[tuple[int, int], list[int]] = {}
            for idx, inim in enumerate(tangiveis):
                w = float(getattr(inim, "largura", 28))
                h = float(getattr(inim, "altura", 28))
                cx = float(inim.x) + w * 0.5
                cy = float(inim.y) + h * 0.5
                centros_w_h.append((cx, cy, max(w, h) * 0.5))
                chave = (int(cx // cell), int(cy // cell))
                buckets.setdefault(chave, []).append(idx)

            disp_x = [0.0] * n
            disp_y = [0.0] * n
            fator_r = float(SEPARACAO_INIMIGOS_FATOR_RAIO)
            rigidez = float(SEPARACAO_INIMIGOS_RIGIDEZ)
            vel_max = float(SEPARACAO_INIMIGOS_VEL_MAX)

            for idx, (cx1, cy1, r1) in enumerate(centros_w_h):
                gx = int(cx1 // cell)
                gy = int(cy1 // cell)
                peso1 = 0.35 if getattr(tangiveis[idx], "is_elite", False) else 1.0
                for ox in (-1, 0, 1):
                    for oy in (-1, 0, 1):
                        vizinhos = buckets.get((gx + ox, gy + oy))
                        if not vizinhos:
                            continue
                        for jdx in vizinhos:
                            if jdx <= idx:
                                continue
                            cx2, cy2, r2 = centros_w_h[jdx]
                            raio_sep = (r1 + r2) * fator_r
                            dx = cx2 - cx1
                            dy = cy2 - cy1
                            dist_sq = dx * dx + dy * dy
                            if dist_sq >= raio_sep * raio_sep:
                                continue
                            if dist_sq < 1e-6:
                                ang = (idx + jdx) * 2.39996
                                nx, ny = math.cos(ang), math.sin(ang)
                                frac = 1.0
                            else:
                                dist = math.sqrt(dist_sq)
                                nx, ny = dx / dist, dy / dist
                                frac = 1.0 - (dist / raio_sep)
                            imp = min(vel_max, rigidez * frac)
                            peso2 = 0.35 if getattr(tangiveis[jdx], "is_elite", False) else 1.0
                            disp_x[idx] -= nx * imp * peso1
                            disp_y[idx] -= ny * imp * peso1
                            disp_x[jdx] += nx * imp * peso2
                            disp_y[jdx] += ny * imp * peso2

            max_step = vel_max * dt
            for idx, inim in enumerate(tangiveis):
                vx, vy = disp_x[idx], disp_y[idx]
                if vx == 0.0 and vy == 0.0:
                    continue
                step_x = vx * dt
                step_y = vy * dt
                mag = math.hypot(step_x, step_y)
                if mag > max_step and mag > 1e-6:
                    escala = max_step / mag
                    step_x *= escala
                    step_y *= escala
                inim.x += step_x
                inim.y += step_y
                self._clamp_entidade_arena(inim)

        if not getattr(self.jogador, "vivo", True):
            return
        em_dash = (
            float(getattr(self.jogador, "dash_ativo_timer", 0.0)) > 0.0
            or bool(getattr(self.jogador, "em_dash_iframes", False))
        )
        tanque_bulldozer = (
            getattr(self.jogador, "controles_tanque", False)
            and getattr(self.jogador, "tanque_avancando", False)
        )
        em_ram = bool(getattr(mods, "movimento_ram_collision", False)) or tanque_bulldozer
        if em_dash or em_ram:
            return

        jw = float(getattr(self.jogador, "largura", 32))
        jh = float(getattr(self.jogador, "altura", 32))
        jx = float(self.jogador.x) + jw * 0.5
        jy = float(self.jogador.y) + jh * 0.5
        rj = max(jw, jh) * 0.5

        push_jx = 0.0
        push_jy = 0.0
        fator_bloq = float(MINION_BLOCK_FATOR_RAIO)
        forca_j = float(MINION_BLOCK_FORCA_JOGADOR)
        empurrao_inim = float(MINION_BLOCK_EMPURRAO_INIMIGO)

        for inim in tangiveis:
            iw = float(getattr(inim, "largura", 28))
            ih = float(getattr(inim, "altura", 28))
            icx = float(inim.x) + iw * 0.5
            icy = float(inim.y) + ih * 0.5
            re = max(iw, ih) * 0.5
            raio_bloq = (rj + re) * fator_bloq
            dx = jx - icx
            dy = jy - icy
            dist_sq = dx * dx + dy * dy
            if dist_sq >= raio_bloq * raio_bloq:
                continue
            if dist_sq < 1e-6:
                dir_m = getattr(inim, "_dir_mov", (1.0, 0.0))
                nx, ny = float(dir_m[0]), float(dir_m[1])
                if nx == 0.0 and ny == 0.0:
                    nx, ny = 1.0, 0.0
                frac = 1.0
            else:
                dist = math.sqrt(dist_sq)
                nx, ny = dx / dist, dy / dist
                frac = 1.0 - (dist / raio_bloq)

            push_jx += nx * forca_j * frac
            push_jy += ny * forca_j * frac
            peso_inim = 0.30 if getattr(inim, "is_elite", False) else 1.0
            inim.x -= nx * empurrao_inim * frac * peso_inim * dt
            inim.y -= ny * empurrao_inim * frac * peso_inim * dt
            self._clamp_entidade_arena(inim)

        if push_jx != 0.0 or push_jy != 0.0:
            step_jx = push_jx * dt
            step_jy = push_jy * dt
            max_j_step = float(MINION_BLOCK_VEL_MAX) * dt
            mag_j = math.hypot(step_jx, step_jy)
            if mag_j > max_j_step and mag_j > 1e-6:
                escala = max_j_step / mag_j
                step_jx *= escala
                step_jy *= escala
            self.jogador.x += step_jx
            self.jogador.y += step_jy
            self._clamp_entidade_arena(self.jogador)


