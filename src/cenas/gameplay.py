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
from src.armas import Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas
from src.equipamentos import DroneCura, DroneCombate, DroneSuporte
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_particulas import SistemaParticulas
from src.sistemas.sistema_audio import GerenciadorAudio, AnalisadorFFTBoss
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.hud import HUD
from src.ui.banner_dicas import BannerDica
from src.ui.modal_level_up import ModalLevelUp
from src.ui.modal_overclock import ModalOverclock
from src.ui.menu_configs import MenuConfigs
from src.entidades.geladeira_tsunami import GeladeiraTsunami, ESTADO_MORTE
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA,
    CAMERA_DAMPING_K, DT_CLAMP_MAX, DASH_COOLDOWN, DASH_PARRY_META, MELEE_ARCO_GRAUS,
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
        self.jogador.dash_desbloqueado = bool(self.gerenciador_config.estatisticas.get("dash_desbloqueado", False))
        self.modal_level_up = ModalLevelUp(self.gerenciador_config, self.jogador, cena=self)
        self.modal_overclock = ModalOverclock(self.jogador, cena=self)
        self.menu_configs = MenuConfigs(self.gerenciador_config, em_jogo=True, cena=self)

        # Registra callback de level-up no SistemaXP do jogador
        self.jogador.sistema_xp.registrar_callback_level_up(self._ao_subir_nivel)

        # Chefe Final e Cutscene de Transição
        self.chefe_final = None
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
        self.spawner = SistemaSpawn(max_ativos=400)
        self.sistema_drops = SistemaDrops()
        self.sistema_scavenger = SistemaScavenger()
        self.sistema_particulas = SistemaParticulas()
        self.sistema_audio = GerenciadorAudio()
        self.analisador_fft_boss = AnalisadorFFTBoss()
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
        self.banner_dicas = BannerDica()
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

        # Toasts de itens coletados, Screen Shake, Hitstop e Efeitos
        self.toasts_coleta: list[dict] = []
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

        tem_bloqueadas = bool(self.gerenciador_config.obter_bloqueadas()) if hasattr(self, "gerenciador_config") and self.gerenciador_config else False
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
                "texto": f"NÍVEL {novo_nivel}! +10 HP & SUPRIMENTOS",
                "cor": DOURADO,
                "x": cx,
                "y": self.jogador.y - 18,
                "tempo": 1.8,
                "tempo_max": 1.8
            })
            if int(novo_nivel) >= getattr(self.jogador.sistema_xp, "nivel_max", 12) and getattr(self, "tempo_sobrevivencia", 0.0) >= 270.0:
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
        arma_melee = self._obter_arma_melee()
        if arma_melee is not None:
            arma_melee.whiff_callback = self._ao_errar_parry
            if parry_prec == "cirurgico":
                arma_melee.arco_graus = 65.0
                arma_melee.parry_duracao = 0.09
                arma_melee.parry_alcance_mult = 0.85
                arma_melee.parry_dano_mult = 1.75
                arma_melee.parry_splash_raio = 140.0
                arma_melee.cooldown = 0.6
            elif parry_prec == "amplificado":
                arma_melee.arco_graus = 135.0
                arma_melee.parry_duracao = 0.17
                arma_melee.parry_alcance_mult = 1.25
                arma_melee.parry_dano_mult = 0.70
                arma_melee.parry_splash_raio = 90.0
                arma_melee.cooldown = 0.85
            else:
                arma_melee.arco_graus = float(MELEE_ARCO_GRAUS)
                arma_melee.parry_duracao = 0.12
                arma_melee.parry_alcance_mult = 1.0
                arma_melee.parry_dano_mult = 1.0
                arma_melee.parry_splash_raio = 90.0
                arma_melee.cooldown = 0.6

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
            if pygame.mixer.get_init():
                from src.sistemas.sistema_musica import SistemaMusica
                inicio_canais_sfx = SistemaMusica._CANAIS_RESERVADOS
                for ch_idx in range(inicio_canais_sfx, pygame.mixer.get_num_channels()):
                    pygame.mixer.Channel(ch_idx).set_volume(self.volume_sfx_efetivo)
        except Exception:
            pass


    @staticmethod
    def _obter_sfx_arma(arma) -> str | None:
        if arma is None:
            return None
        if isinstance(arma, Pistola):
            return "sfx_tiro_pistola"
        if isinstance(arma, Minigun):
            return "sfx_tiro_minigun"
        if isinstance(arma, Shotgun):
            return "sfx_tiro_shotgun"
        if isinstance(arma, RifleAssalto):
            return "sfx_tiro_rifle"
        if isinstance(arma, LancaFoguetes):
            return "sfx_tiro_foguete"
        if isinstance(arma, LancaGranadas):
            return "sfx_tiro_granada"
        if isinstance(arma, Railgun):
            return "sfx_tiro_railgun"
        return None

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
        return (
            "Você ouve o Ritmo Cruel sacudindo o baile inteiro.\n"
            f"Você tem {segundos} segundos até experienciar The Perfect Sound™"
        )

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
            dt = self.janela.delta_time()
            # Em testes unitários headless (primeiro frame sem tick), avança 1 frame padrão (1/60s)
            if dt <= 0.0:
                dt = 1.0 / 60.0
            # Clampa dt para evitar saltos quânticos em frames atípicos (DT_CLAMP_MAX = 0.05s)
            dt = min(dt, DT_CLAMP_MAX)
        self._ultimo_dt_draw = max(1e-4, float(dt))

        # Atualiza rampa suave de volume do gerenciador de áudio
        if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
            self.sistema_audio.atualizar(dt)

        # Atualiza a máquina de estados da música dinâmica (inclusive pausado / modais / game over)
        if hasattr(self, "sistema_musica") and self.sistema_musica is not None:
            musica_abafada = bool(
                self.pausado
                or self.game_over
                or self.menu_configs.ativo
                or self.modal_level_up.ativo
                or getattr(self.modal_level_up, "tempo_transicao_saida", 0.0) > 0.0
                or self.modal_overclock.ativo
                or getattr(self.modal_overclock, "tempo_transicao_saida", 0.0) > 0.0
                or (hasattr(self, "menu_debug") and self.menu_debug.ativo)
            )
            self.sistema_musica.atualizar(
                tempo_sobrevivencia=self.tempo_sobrevivencia,
                abafado=musica_abafada,
                dt=dt,
            )

        # Atualiza cooldown de reabertura do menu para evitar input bleed (C / ESC)
        if hasattr(self, "_cooldown_menu_toggle") and self._cooldown_menu_toggle > 0.0:
            self._cooldown_menu_toggle = max(0.0, self._cooldown_menu_toggle - dt)

        # 0. Se o Menu de Debug estiver ativo, processa seus inputs e congela o jogo
        if hasattr(self, "menu_debug"):
            debug_estava_ativo = self.menu_debug.ativo
            self.menu_debug.update(dt, self.teclado, self.mouse)
            if self.menu_debug.ativo:
                self.pausado = True
                self.buffer_tiro = 0.0
                return
            elif debug_estava_ativo and not self.modal_level_up.ativo and not self.modal_overclock.ativo and not self.menu_configs.ativo and not self.game_over and not self.vitoria:
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

            # Atualiza a posição da câmera para seguir o jogador suavemente (dt-independente com CAMERA_DAMPING_K)
            val_suav = self.config_sistema.obter_valor("suavizacao_camera") if hasattr(self, "config_sistema") and self.config_sistema else "ligado"
            suavizacao_fator = 1.0 if str(val_suav).lower() in ("desligado", "0", "false") else (1.0 - (1.0 - CAMERA_DAMPING_K) ** (dt * 60.0))
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

                if getattr(self, "_aguardando_soltar_lmb", False):
                    if not btn1_pressed or btn1_down:
                        self._aguardando_soltar_lmb = False
                    else:
                        btn1_pressed = False
                        btn1_down = False

            # Toggle de Auto-Fire na tecla 'F' quando auto_fire == "ligado" (estritamente anulado quando desligado)
            if not is_uma_mao and not autofire_desligado and self.teclado is not None and hasattr(self.teclado, "key_down"):
                if self.teclado.key_down("f") or self.teclado.key_down("F"):
                    self.auto_fire_toggle_ativo = not getattr(self, "auto_fire_toggle_ativo", False)
                    self.toasts_coleta.append({
                        "texto": "AUTO-FIRE: ON" if self.auto_fire_toggle_ativo else "AUTO-FIRE: OFF",
                        "cor": AZUL_CIANO if self.auto_fire_toggle_ativo else CINZA_TEXTO if "CINZA_TEXTO" in globals() else (180, 190, 205),
                        "x": centro_jogador_x,
                        "y": self.jogador.y - 14,
                        "tempo": 1.1,
                        "tempo_max": 1.1
                    })

            if autofire_desligado:
                self.auto_fire_toggle_ativo = False
                disparar_agora = btn1_down
                self.buffer_tiro = 0.0
            else:
                if btn1_pressed:
                    self.buffer_tiro = 0.15  # Buffer de 150ms para garantir que cliques rápidos nunca sejam perdidos
                else:
                    self.buffer_tiro = max(0.0, self.buffer_tiro - dt)
                disparar_agora = (self.buffer_tiro > 0.0) or (not is_uma_mao and getattr(self, "auto_fire_toggle_ativo", False))

            # Dash Direcional Permanente: SPACE/LSHIFT no modo padrão; LSHIFT em uma_mao (preserva SPACE para disparo)
            if self.jogador.vivo and self.teclado is not None and hasattr(self.teclado, "key_down"):
                if is_uma_mao:
                    dash_press = bool(self.teclado.key_down("LSHIFT"))
                else:
                    dash_press = bool(self.teclado.key_down("SPACE") or self.teclado.key_down("LSHIFT"))
                if dash_press:
                    dx_d, dy_d = getattr(self.jogador, "dir_movimento_atual", (0.0, 0.0))
                    if self.jogador.iniciar_dash(dx_d, dy_d, mods=mods):
                        if hasattr(self.sistema_particulas, "adicionar_onda_dash"):
                            self.sistema_particulas.adicionar_onda_dash(centro_jogador_x, centro_jogador_y)
                        if getattr(self.jogador, "dash_stutter_trigger", False):
                            self.jogador.dash_stutter_trigger = False
                            self.arena_freeze_timer = max(self.arena_freeze_timer, 0.15)

            # Atualiza janela ativa de Parry da Chave de Manutenção (Melee)
            arma_melee_slot1 = self._obter_arma_melee()
            if arma_melee_slot1 is not None:
                if hasattr(arma_melee_slot1, "atualizar"):
                    arma_melee_slot1.atualizar(dt)
                if getattr(arma_melee_slot1, "parry_ativo", False) and self.jogador.vivo:
                    self._processar_parry_ativo(arma_melee_slot1, centro_jogador_x, centro_jogador_y)

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

            # Railgun instantânea (port 1:1 da v2: disparo hitscan perfurante de 1800 px sem carga)
            if arma_ativa is not None and (isinstance(arma_ativa, Railgun) or "railgun" in getattr(arma_ativa, "nome", "").lower()):
                if disparar_agora and self.jogador.vivo and arma_ativa.pode_atirar():
                    if self._executar_disparo_railgun(
                        arma_ativa,
                        centro_jogador_x, centro_jogador_y,
                        mouse_mundo_x, mouse_mundo_y,
                        mods=mods,
                        hitbox_mult=hitbox_mult,
                        mult_dano_buff=mult_dano_buff
                    ):
                        self.buffer_tiro = 0.0
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
                                if getattr(self.jogador, "controles_tanque", False):
                                    p.perfuracoes_restantes = int(getattr(p, "perfuracoes_restantes", 0)) + 1
                            if getattr(self.jogador, "controles_tanque", False) and getattr(self.jogador, "tanque_parado", False):
                                arma_ativa.tempo_recarga_restante *= 0.80
                            self.projeteis.extend(novos_tiros)
                            self.buffer_tiro = 0.0
                            self._aplicar_efeitos_disparo_extras(novos_tiros, mods)
                elif isinstance(arma_ativa, Melee) or getattr(arma_ativa, "slot", None) == 1:
                    if hasattr(arma_ativa, "pode_atirar") and arma_ativa.pode_atirar():
                        self._executar_golpe_melee(
                            arma_ativa,
                            centro_jogador_x, centro_jogador_y,
                            mouse_mundo_x, mouse_mundo_y,
                            crit_chance, crit_mult, mult_dano_buff, mods
                        )
                        self.buffer_tiro = 0.0
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

            # Dual-Wield (BIOS Modding - B1): LMB (disparar_agora) dispara também a outra Arma Especial equipada,
            # preservando o Botão Direito (RMB) exclusivamente para o Parry Rápido.
            if getattr(self.jogador, "bios_modding", False) and disparar_agora and self.jogador.vivo:
                arma_esp = None
                if getattr(self.jogador, "slot_ativo", None) == 3:
                    if getattr(self.jogador, "arma_especial_secundaria", None) is not None and self.jogador.arma_especial_secundaria is not arma_ativa:
                        arma_esp = self.jogador.arma_especial_secundaria
                    elif getattr(self.jogador, "arma_especial", None) is not None and self.jogador.arma_especial is not arma_ativa:
                        arma_esp = self.jogador.arma_especial
                elif getattr(self.jogador, "arma_especial", None) is not None and self.jogador.arma_especial is not arma_ativa:
                    arma_esp = self.jogador.arma_especial

                if arma_esp is not None:
                    if isinstance(arma_esp, Railgun) or "railgun" in getattr(arma_esp, "nome", "").lower():
                        if hasattr(arma_esp, "pode_atirar") and arma_esp.pode_atirar():
                            self._executar_disparo_railgun(
                                arma_esp,
                                centro_jogador_x, centro_jogador_y,
                                mouse_mundo_x, mouse_mundo_y,
                                mods=mods,
                                hitbox_mult=hitbox_mult,
                                mult_dano_buff=mult_dano_buff
                            )
                    else:
                        if hasattr(arma_esp, "pode_atirar") and arma_esp.pode_atirar():
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

            # Quick-Melee / Parry Rápido (sem trocar de arma): tecla 'E' ou Botão Direito (RMB) sempre disponíveis
            if self.jogador.vivo and arma_melee_slot1 is not None and hasattr(arma_melee_slot1, "pode_atirar") and arma_melee_slot1.pode_atirar():
                tecla_e_down = bool(
                    self.teclado is not None and hasattr(self.teclado, "key_down") and (
                        self.teclado.key_down("e") or self.teclado.key_down("E")
                    )
                )
                rmb_down = False
                if not is_uma_mao and self.mouse is not None:
                    if hasattr(self.mouse, "button_down"):
                        rmb_down = bool(self.mouse.button_down(3))
                    elif hasattr(self.mouse, "is_button_down"):
                        rmb_down = bool(self.mouse.is_button_down(3))
                rmb_quick_melee = rmb_down
                if tecla_e_down or rmb_quick_melee:
                    self._executar_golpe_melee(
                        arma_melee_slot1,
                        centro_jogador_x, centro_jogador_y,
                        mouse_mundo_x, mouse_mundo_y,
                        crit_chance, crit_mult, mult_dano_buff, mods
                    )

        # Atualiza o tempo de vida dos efeitos visuais de Melee
        for ef in self.efeitos_melee:
            ef["tempo"] -= dt
        self.efeitos_melee = [ef for ef in self.efeitos_melee if ef["tempo"] > 0]

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
                        elif r_mob < 0.315:
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
                    possui_elite_vivo=possui_elite,
                    ninjas_vivos=len([e for e in self.inimigos if getattr(e, "vivo", True) and getattr(e, "is_ninja", False)])
                )
                if fogo_cruzado_ranged:
                    for ni in novos_inimigos:
                        if hasattr(ni, "rajada_tripla"):
                            ni.rajada_tripla = True
                self.inimigos.extend(novos_inimigos)

                # Gatilho Nível 12 após 4:30 (270s) OU "Jogar aos Lobos" (tempo_elite >= 300s)
                nivel_max = getattr(getattr(self.jogador, "sistema_xp", None), "nivel_max", 12)
                if self.chefe_final is None and not self.boss_cutscene_ativa and not self.boss_grace_period_ativo:
                    if getattr(self.jogador, "nivel", 1) >= nivel_max and getattr(self, "tempo_sobrevivencia", 0.0) >= 270.0:
                        self.iniciar_boss_grace_period()
                    elif not possui_elite and getattr(self.spawner, "tempo_elite", 0.0) >= 300.0:
                        self.iniciar_boss_grace_period()

        # =========================================================================
        # 4. FÍSICA DOS PROJÉTEIS
        # =========================================================================
        if not cutscene_congelada:
            # Sincronização Vertical (Desligado): Linha de Rasgo que divide projéteis em ±6° uma única vez
            if getattr(mods, "vsync_tear_refraction", False):
                self.vsync_tear_y = (getattr(self, "vsync_tear_y", 0.0) + 80.0 * dt) % ALTURA_TELA
                proj_clones = []
                ang_split = math.radians(6.0)
                cos_pos, sin_pos = math.cos(ang_split), math.sin(ang_split)
                cos_neg, sin_neg = math.cos(-ang_split), math.sin(-ang_split)
                for proj in self.projeteis:
                    if (
                        getattr(proj, "dono", "jogador") == "jogador"
                        and not getattr(proj, "ja_dividido_tear", False)
                        and not getattr(proj, "split_done", False)
                    ):
                        tela_y = proj.y - self.camera.y
                        if abs(tela_y - self.vsync_tear_y) < 18.0:
                            proj.ja_dividido_tear = True
                            proj.split_done = True
                            orig_vx, orig_vy = proj.vx, proj.vy
                            # Projétil original desvia -6°
                            orig_dx, orig_dy = proj.dir_x, proj.dir_y
                            proj.dir_x = orig_dx * cos_neg - orig_dy * sin_neg
                            proj.dir_y = orig_dx * sin_neg + orig_dy * cos_neg
                            # Clone diverge +6°
                            vx_d = orig_vx * cos_pos - orig_vy * sin_pos
                            vy_d = orig_vx * sin_pos + orig_vy * cos_pos
                            clone = proj.clonar(vx=vx_d, vy=vy_d, cor=(56, 189, 248))
                            clone.ja_dividido_tear = True
                            clone.split_done = True
                            proj_clones.append(clone)
                            self.sistema_particulas.emitir_faiscas(
                                proj.x + getattr(proj, "largura", 6) / 2.0,
                                proj.y + getattr(proj, "altura", 6) / 2.0,
                                dir_x=proj.dir_x,
                                dir_y=proj.dir_y,
                                cor=(56, 189, 248),
                                qtd=5
                            )
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
            if cutscene_congelada:
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
                        duel_stg = int(getattr(proj, "duel_stage", 0))
                        if duel_stg >= 2:
                            dano_proj = max(1, int(round(dano_proj * (2.2 if duel_stg == 2 else 3.0))))
                            self.jogador.exposed_timer = max(getattr(self.jogador, "exposed_timer", 0.0), 2.0)
                            self.aplicar_shake(14.0, 0.30)
                            self.toasts_coleta.append({
                                "texto": "FALHA NO DUELO DE PARRY!",
                                "cor": VERMELHO_DANO,
                                "x": centro_jogador_x, "y": self.jogador.y - 26, "tempo": 1.8, "tempo_max": 1.8
                            })
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
                        if hasattr(self.sistema_particulas, "adicionar_marca_queimadura"):
                            self.sistema_particulas.adicionar_marca_queimadura(p_cx, p_cy, raio=min(55.0, float(r_exp) * 0.65))
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

                            if getattr(inimigo, "is_ninja", False) and not getattr(proj, "refletido_parry", False) and hasattr(inimigo, "aparar_projetil_jogador") and inimigo.pode_aparar_projetil():
                                rebatido_n = inimigo.aparar_projetil_jogador(proj, (centro_jogador_x, centro_jogador_y))
                                if rebatido_n is not None:
                                    if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                                        self.sistema_audio.tocar_parry_clang(pitch_mult=1.25)
                                    nx_c = inimigo.x + inimigo.largura / 2.0
                                    ny_c = inimigo.y + inimigo.altura / 2.0
                                    self.sistema_particulas.emitir_onda_choque(nx_c, ny_c, raio_max=48.0, cor=(232, 121, 249))
                                    self.sistema_particulas.emitir_faiscas(nx_c, ny_c, cor=(192, 132, 252), qtd=12)
                                    self.toasts_coleta.append({
                                        "texto": "NINJA PARRY!",
                                        "cor": (232, 121, 249),
                                        "x": nx_c, "y": inimigo.y - 18, "tempo": 0.9, "tempo_max": 0.9
                                    })
                                    break

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

                            fonte_dano = (
                                "parry_ninja_proprio"
                                if (getattr(proj, "refletido_parry", False) and getattr(proj, "duel_owner", None) is inimigo)
                                else ("parry_outro" if getattr(proj, "refletido_parry", False) else "projetil_jogador")
                            )
                            ret_d = inimigo.receber_dano(
                                dano_final,
                                origem_x=proj.x,
                                origem_y=proj.y,
                                dir_ataque=(dx_k, dy_k),
                                fonte=fonte_dano
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

                            # Projétil refletido por Parry: detona em AoE 90px (75% splash) + onda de choque + marca de queimadura
                            if getattr(proj, "refletido_parry", False):
                                p_cx_parry = proj.x + proj.largura / 2.0
                                p_cy_parry = proj.y + proj.altura / 2.0
                                r_parry_exp = float(getattr(proj, "raio_explosao", 90.0))
                                splash_mult = float(getattr(proj, "splash_mult", 0.75))
                                dano_splash = max(1, int(round(dano_final * splash_mult)))
                                self.sistema_particulas.emitir_onda_choque(p_cx_parry, p_cy_parry, raio_max=r_parry_exp, cor=DOURADO)
                                if hasattr(self.sistema_particulas, "adicionar_marca_queimadura"):
                                    self.sistema_particulas.adicionar_marca_queimadura(p_cx_parry, p_cy_parry, raio=45.0)
                                self.aplicar_shake(8.0, 0.18)
                                for inim_sp in self.inimigos:
                                    if inim_sp is inimigo or not getattr(inim_sp, "vivo", True):
                                        continue
                                    if getattr(inim_sp, "em_fase", False) or getattr(inim_sp, "estado", "") in ("morte", ESTADO_MORTE):
                                        continue
                                    sp_cx = inim_sp.x + getattr(inim_sp, "largura", 28) / 2.0
                                    sp_cy = inim_sp.y + getattr(inim_sp, "altura", 28) / 2.0
                                    if distancia(p_cx_parry, p_cy_parry, sp_cx, sp_cy) <= r_parry_exp:
                                        ret_sp = inim_sp.receber_dano(
                                            dano_splash,
                                            origem_x=p_cx_parry,
                                            origem_y=p_cy_parry,
                                            dir_ataque=vetor_direcao(p_cx_parry, p_cy_parry, sp_cx, sp_cy)
                                        )
                                        dano_sp_ef = int(ret_sp) if isinstance(ret_sp, (int, float)) else dano_splash
                                        self.dano_total_causado += dano_sp_ef
                                        if hasattr(self, "config_sistema") and str(self.config_sistema.obter_valor("damage_numbers")).lower() in ("ligado", "true", "1"):
                                            self.sistema_particulas.emitir_texto_dano(sp_cx, inim_sp.y, dano_sp_ef, critico=False)
                                        if not inim_sp.vivo:
                                            self._registrar_abate_inimigo(inim_sp, mods)

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
            if hasattr(self, "sistema_audio") and self.sistema_audio is not None:
                mapa_sfx_drop = {
                    "xp": "sfx_pickup_xp",
                    "cura": "sfx_pickup_cura",
                    "arma": "sfx_pickup_arma",
                    "equipamento": "sfx_pickup_equipamento",
                }
                sfx_drop = mapa_sfx_drop.get(ev["tipo"])
                if sfx_drop:
                    self.sistema_audio.tocar_sfx(sfx_drop, pitch_aleatorio=True)

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
                if self.modal_overclock.ativo:
                    self.pausado = True
                else:
                    self.jogador.curar(25)
                    self.pontos += 500
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


    def _reiniciar_partida(self):
        SceneManager.change_scene(GameplayScene())

    def _voltar_menu(self):
        from src.cenas.menu_principal import MenuPrincipalScene
        SceneManager.change_scene(MenuPrincipalScene())


