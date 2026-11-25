"""
Testes de Regressão — Stage 1 UX & Combat Backport — Protocolo: Batata
Valida constantes de física/câmera, persistência de parries/dash, stacking de i-frames,
melee 120° + parry 0.18s/90px splash + hitstop + RMB BIOS Modding, pistola 2.2x + pips,
toggle F de auto-fire, persistência de chão (cápsulas/queimaduras), VSync tear ±6°
e escala de resolução somente-mundo.
"""

import math
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame

from src.armas.melee import Melee
from src.armas.pistola import Pistola
from src.armas.rifle_assalto import RifleAssalto
from src.cenas.gameplay import GameplayScene
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.jogador import Jogador
from src.entidades.projetil import Projetil
from src.sistemas.config_efeitos import ModificadoresGameplay
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_particulas import SistemaParticulas
from src.utils import constantes
from src.utils.constantes import (
    CAMERA_DAMPING_K,
    DASH_COOLDOWN,
    DASH_DURACAO,
    DASH_IFRAMES_BASE,
    DASH_MULT_VEL,
    DASH_PARRY_META,
    DT_CLAMP_MAX,
    MELEE_ARCO_GRAUS,
)
from src.utils.janela import Janela


class _DummyKeyboard:
    def __init__(self, pressed=None, down=None):
        self._pressed = {k.lower() for k in (pressed or [])}
        self._down = {k.lower() for k in (down or [])}

    def key_pressed(self, tecla: str) -> bool:
        return tecla.lower() in self._pressed

    def key_down(self, tecla: str) -> bool:
        return tecla.lower() in self._down


class _DummyMouse:
    def __init__(self, pos=(640, 360), left=False, right=False, left_down=False, right_down=False):
        self._pos = pos
        self._left = left
        self._right = right
        self._left_down = left_down
        self._right_down = right_down

    def get_position(self):
        return self._pos

    def is_button_pressed(self, btn: int) -> bool:
        if btn == 1:
            return self._left
        if btn == 3:
            return self._right
        return False

    def is_button_down(self, btn: int) -> bool:
        if btn == 1:
            return self._left_down
        if btn == 3:
            return self._right_down
        return False

    def get_pressed_buttons(self):
        return (self._left, False, self._right)


class TestStage1ConstantsAndWindow(unittest.TestCase):
    """Valida DT_CLAMP_MAX, CAMERA_DAMPING_K e clamping real em Janela.update()."""

    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.janela = Janela.get_instance()

    def test_constants_dt_clamp_and_camera_damping(self):
        self.assertAlmostEqual(DT_CLAMP_MAX, 0.05)
        self.assertAlmostEqual(CAMERA_DAMPING_K, 0.115)
        self.assertAlmostEqual(MELEE_ARCO_GRAUS, 120.0)
        self.assertAlmostEqual(DASH_DURACAO, 0.22)
        self.assertAlmostEqual(DASH_MULT_VEL, 2.6)
        self.assertAlmostEqual(DASH_IFRAMES_BASE, 0.26)
        self.assertAlmostEqual(DASH_COOLDOWN, 1.8)
        self.assertEqual(DASH_PARRY_META, 15)

    def test_janela_update_clamps_dt_to_dt_clamp_max(self):
        j = Janela(largura_virtual=1280, altura_virtual=720, titulo="Clamp Test")
        j._clock = MagicMock()
        j._clock.tick.return_value = 250  # 250ms spike -> 0.25s, must clamp to 0.05s
        j.update(fps_alvo=0)
        self.assertAlmostEqual(j.delta_time(), DT_CLAMP_MAX, places=6)


class TestParryPersistenceAndDashUnlock(unittest.TestCase):
    """Valida persistência de parries_total e dash_desbloqueado em save.json."""

    def test_15_parry_persistence_and_legacy_save_compat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "save.json")
            old_save_path = constantes.SAVE_FILE_PATH
            constantes.SAVE_FILE_PATH = save_path
            try:
                gc = GerenciadorConfiguracoes()
                self.assertEqual(gc.estatisticas["parries_total"], 0)
                self.assertFalse(gc.estatisticas["dash_desbloqueado"])

                # Save v2 sem parries_total/dash_desbloqueado carrega estatísticas limpas
                save_v2 = {
                    "schema_version": 2,
                    "desbloqueadas": ["fps_cap"],
                    "ativas": {"fps_cap": "ilimitado"},
                    "sistema_configs": {"volume_master": 80},
                    "estatisticas": {"high_score": 1234},
                }
                self.assertTrue(gc.from_dict(save_v2))
                self.assertEqual(gc.estatisticas["high_score"], 1234)
                self.assertEqual(gc.estatisticas["parries_total"], 0)
                self.assertFalse(gc.estatisticas["dash_desbloqueado"])

                # 1..14 do not unlock dash; 15 unlocks dash; 16..51 do not re-trigger unlock
                for i in range(1, 51):
                    total, unlocked = gc.registrar_parry(meta=DASH_PARRY_META)
                    self.assertEqual(total, i)
                    self.assertEqual(unlocked, i == DASH_PARRY_META)

                total51, unlocked51 = gc.registrar_parry(meta=DASH_PARRY_META)
                self.assertEqual(total51, 51)
                self.assertFalse(unlocked51)

                # Reload from disk and verify persistence (saves on unlock at 50, zero I/O on normal parry 51)
                gc_reloaded = GerenciadorConfiguracoes()
                self.assertTrue(gc_reloaded.carregar_arquivo(save_path))
                self.assertEqual(gc_reloaded.estatisticas["parries_total"], 50)
                self.assertTrue(gc_reloaded.estatisticas["dash_desbloqueado"])
            finally:
                constantes.SAVE_FILE_PATH = old_save_path

    def test_level_10_does_not_open_modal_and_debug_kit_unlocks_dash(self):
        from src.cenas.gameplay import GameplayScene
        cena = GameplayScene()
        cena.modal_level_up.config_pity_buffer = None
        cena._ao_subir_nivel(10)
        self.assertFalse(cena.modal_level_up.ativo)
        self.assertFalse(cena.pausado)

        cena.jogador.dash_desbloqueado = False
        cena.menu_debug._aplicar_kit_debug()
        self.assertTrue(cena.jogador.dash_desbloqueado)


class TestDashIframesAndOverdriveCoexistence(unittest.TestCase):
    """Valida Dash direcional, stacking de i-frames e coexistência com keybinds_overdrive_dash."""

    def test_dash_locked_and_base_iframes(self):
        j = Jogador(x=400.0, y=400.0)
        j.dash_desbloqueado = False
        self.assertFalse(j.iniciar_dash(1.0, 0.0))

        j.dash_desbloqueado = True
        self.assertTrue(j.iniciar_dash(1.0, 0.0))
        self.assertAlmostEqual(j.dash_ativo_timer, DASH_DURACAO, places=4)
        self.assertAlmostEqual(j.dash_cooldown_restante, DASH_COOLDOWN, places=4)
        self.assertAlmostEqual(j.invulnerabilidade_timer, 0.26, places=4)
        self.assertFalse(j.dash_stutter_trigger)

    def test_dash_iframes_stacking_motion_blur_and_fps_stutter(self):
        j = Jogador(x=400.0, y=400.0)
        j.dash_desbloqueado = True
        mods = ModificadoresGameplay(motion_blur_ghosting=True, fps_stutter_dodge=True)
        self.assertTrue(j.iniciar_dash(1.0, 0.0, mods=mods))
        # 0.26 base + 0.08 motion_blur + 0.06 fps_stutter = 0.40s
        self.assertAlmostEqual(j.invulnerabilidade_timer, 0.40, places=4)
        self.assertTrue(j.dash_stutter_trigger)

    def test_dash_coexists_with_passive_keybinds_overdrive_dash(self):
        j = Jogador(x=500.0, y=500.0)
        j.dash_desbloqueado = True
        j.keybinds_overdrive_dash = True
        j.overdrive_dash_cooldown = 0.0
        j._ult_dir_x = 1.0
        j._ult_dir_y = 0.0

        # Active directional dash still fires independently
        self.assertTrue(j.iniciar_dash(0.0, 1.0))
        self.assertGreater(j.dash_ativo_timer, 0.0)
        self.assertTrue(j.keybinds_overdrive_dash)

        # After active dash finishes, reversing movement still triggers passive overdrive pulse
        j.dash_ativo_timer = 0.0
        j.dash_cooldown_restante = 0.0
        teclado = _DummyKeyboard(["a"])  # reverses from _ult_dir_x = +1.0
        mouse = _DummyMouse((500, 500))
        j.processar_input(teclado, mouse, dt=0.05, limite_arena=(2240, 1560))
        self.assertTrue(j.overdrive_pulse_trigger)


class TestMeleeParryAndPistolOverload(unittest.TestCase):
    """Valida Melee 120°, janela de parry 0.18s / ~128.6px, splash 90px/75%, hitstop, RMB BIOS Modding e Pistola 2.2x."""

    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.janela = Janela.get_instance()

    def test_melee_120_arc_and_parry_window_reflection(self):
        melee = Melee()
        self.assertEqual(melee.arco_graus, 120.0)
        self.assertAlmostEqual(melee.parry_duracao, 0.12)
        self.assertAlmostEqual(melee.parry_alcance, 64.0 * 1.0, places=2)

        # Executing attack opens parry window even with empty enemy list
        melee.executar_ataque(200.0, 200.0, [], angulo_mira=0.0, abrir_janela_parry=True)
        self.assertAlmostEqual(melee.parry_janela_restante, 0.12)

        # Projectile at +35° (inside 90° arc = +-45°) and distance ~50px (inside 64px)
        ang_35 = math.radians(35.0)
        p_hit = Projetil(
            x=200.0 + 50.0 * math.cos(ang_35) - 4.0,
            y=200.0 + 50.0 * math.sin(ang_35) - 4.0,
            dir_x=-1.0,
            dir_y=0.0,
            velocidade=240.0,
            dano=12,
            tempo_vida=1.0,
            dono="inimigo",
        )
        # Projectile at +80° (outside 90° arc)
        ang_80 = math.radians(80.0)
        p_miss = Projetil(
            x=200.0 + 50.0 * math.cos(ang_80) - 4.0,
            y=200.0 + 50.0 * math.sin(ang_80) - 4.0,
            dir_x=-1.0,
            dir_y=0.0,
            velocidade=240.0,
            dano=12,
            tempo_vida=1.0,
            dono="inimigo",
        )

        refletidos = melee.tentar_parry_projeteis(200.0, 200.0, [p_hit, p_miss], angulo_mira=0.0)
        self.assertEqual(refletidos, [p_hit])
        self.assertEqual(p_hit.dono, "jogador")
        self.assertAlmostEqual(p_hit.velocidade, 360.0)  # 1.5x
        self.assertEqual(p_hit.dano, 36)  # 3.0x
        self.assertTrue(p_hit.refletido_parry)
        self.assertAlmostEqual(p_hit.raio_explosao, 90.0)
        self.assertAlmostEqual(p_hit.splash_mult, 0.75)
        self.assertGreaterEqual(p_hit.tempo_vida_restante, 2.0)
        self.assertEqual(p_miss.dono, "inimigo")

        # Window expires after 0.18s
        melee.atualizar(0.20)
        self.assertEqual(melee.parry_janela_restante, 0.0)
        self.assertEqual(melee.tentar_parry_projeteis(200.0, 200.0, [p_miss], angulo_mira=ang_80), [])

    def test_gameplay_parry_hitstop_80ms_and_90px_75pct_splash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_save = constantes.SAVE_FILE_PATH
            constantes.SAVE_FILE_PATH = os.path.join(tmpdir, "save.json")
            try:
                cena = GameplayScene()
                cx = cena.jogador.x + cena.jogador.largura / 2.0
                cy = cena.jogador.y + cena.jogador.altura / 2.0
                melee = cena._obter_arma_melee()
                melee.iniciar_golpe_parry(0.0)

                proj_inim = Projetil(
                    x=cx + 50.0, y=cy - 4.0, dir_x=-1.0, dir_y=0.0,
                    velocidade=200.0, dano=20, tempo_vida=1.5, dono="inimigo"
                )
                cena.projeteis = [proj_inim]
                rebatidos = cena._processar_parry_ativo(melee, cx, cy, angulo_mira=0.0)
                self.assertEqual(len(rebatidos), 1)
                self.assertAlmostEqual(cena.hitstop_timer, 0.10, places=4)
                # "PARRY!" deve aparecer apenas via TextoDano em sistema_particulas (sem toast duplicado)
                parry_toasts = [t for t in cena.toasts_coleta if t.get("texto") == "PARRY!"]
                self.assertEqual(parry_toasts, [])
                parry_callouts = [t for t in cena.sistema_particulas.textos_dano if t.texto == "PARRY!"]
                self.assertEqual(len(parry_callouts), 1)

                # Now simulate reflected projectile hitting direct enemy + nearby enemy within 90px
                e_direct = InimigoPadrao(x=cx + 200.0, y=cy - 14.0)
                e_direct.hp = 200
                e_direct.hp_max = 200
                e_splash = InimigoPadrao(x=cx + 250.0, y=cy - 14.0)  # 50px away <= 90px
                e_splash.hp = 200
                e_splash.hp_max = 200
                e_far = InimigoPadrao(x=cx + 350.0, y=cy - 14.0)  # 150px away > 90px
                e_far.hp = 200
                e_far.hp_max = 200
                cena.inimigos = [e_direct, e_splash, e_far]

                proj_inim.x = e_direct.x + 2.0
                proj_inim.y = e_direct.y + 2.0
                cena.hitstop_timer = 0.0
                cena.teclado = _DummyKeyboard()
                cena.mouse = _DummyMouse(pos=(640, 360))
                cena.update(0.001)

                # Direct hit took 60 dmg (20 * 3.0); splash took 75% of 60 = 45 dmg; far took 0
                self.assertEqual(e_direct.hp, 140)
                self.assertEqual(e_splash.hp, 155)
                self.assertEqual(e_far.hp, 200)
                self.assertGreaterEqual(len(cena.sistema_particulas.marcas_queimadura), 1)
            finally:
                constantes.SAVE_FILE_PATH = old_save

    def test_rmb_yields_to_bios_modding(self):
        cena = GameplayScene()
        cena.jogador.bios_modding = True
        cena.jogador.equipar_arma_especial(RifleAssalto())
        cena.jogador.selecionar_slot(2)
        melee = cena._obter_arma_melee()
        melee.parry_janela_restante = 0.0

        cena.teclado = _DummyKeyboard()
        # LMB dispara tanto a Pistola (Slot 2) quanto o Rifle (Slot 3) simultaneamente (Dual-Wield B1)
        cena.mouse = _DummyMouse(pos=(700, 360), left=True, left_down=True)
        cena.update(0.016)
        self.assertGreaterEqual(len(cena.projeteis), 2)

        # RMB permanece exclusivo para Parry Rápido mesmo com BIOS Modding ativo
        melee.parry_janela_restante = 0.0
        cena.mouse = _DummyMouse(pos=(700, 360), right=True, right_down=True)
        cena.update(0.016)
        self.assertGreater(melee.parry_janela_restante, 0.0)

    def test_pistol_4th_shot_2_2x_and_charge_pips(self):
        pistola = Pistola(dano=10, cooldown=0.0)
        self.assertEqual(pistola.pips_carga, 0)
        self.assertFalse(pistola.esta_carregada)

        for esperado in (1, 2, 3):
            tiros = pistola.disparar(0.0, 0.0, 100.0, 0.0)
            self.assertEqual(len(tiros), 1)
            self.assertEqual(tiros[0].dano, 10)
            self.assertFalse(tiros[0].sobrecarregado)
            self.assertEqual(pistola.pips_carga, esperado)
            self.assertEqual(pistola.esta_carregada, esperado == 3)

        tiros4 = pistola.disparar(0.0, 0.0, 100.0, 0.0)
        self.assertEqual(len(tiros4), 1)
        self.assertEqual(tiros4[0].dano, 22)  # int(round(10 * 2.2))
        self.assertTrue(tiros4[0].perfurante)
        self.assertTrue(tiros4[0].sobrecarregado)
        self.assertEqual(pistola.pips_carga, 0)
        self.assertFalse(pistola.esta_carregada)


class TestAutoFireFloorPersistenceAndVisualMeta(unittest.TestCase):
    """Valida toggle F de auto-fire, persistência de chão, VSync tear ±6° e resolução somente-mundo."""

    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.janela = Janela.get_instance()

    def test_f_autofire_toggle_vs_cursed_autofire_desligado(self):
        cena = GameplayScene()
        self.assertFalse(cena.auto_fire_toggle_ativo)

        # Normal mode (auto_fire neutral/ligado): pressing F toggles ON
        cena.teclado = _DummyKeyboard(down=["f"])
        cena.mouse = _DummyMouse(pos=(800, 360))
        cena.update(0.016)
        self.assertTrue(cena.auto_fire_toggle_ativo)

        # Cursed auto_fire="desligado": forces toggle OFF and ignores F
        cena.config_sistema.desbloquear_config("auto_fire")
        cena.config_sistema.definir_valor("auto_fire", "desligado")
        cena.teclado = _DummyKeyboard(down=["f"])
        cena.update(0.016)
        self.assertFalse(cena.auto_fire_toggle_ativo)

    def test_floor_persistence_casings_1_5s_and_scorch_5_0s(self):
        sp = SistemaParticulas()
        surf = pygame.Surface((1280, 720))

        sp.adicionar_capsula(200.0, 200.0, 1.0, 0.0)
        sp.adicionar_marca_queimadura(300.0, 300.0, raio=40.0)
        sp.adicionar_arco_parry(400.0, 400.0, 0.0, raio=128.0, arco_graus=120.0)
        sp.adicionar_onda_dash(500.0, 500.0)

        self.assertEqual(len(sp.capsulas), 1)
        self.assertEqual(len(sp.marcas_queimadura), 1)
        self.assertEqual(len(sp.arcos_parry), 1)
        self.assertTrue(any(td.texto == "PARRY!" for td in sp.textos_dano))

        # Renders cleanly under headless surface
        sp.desenhar_chao(surf, cam_x=0.0, cam_y=0.0, scale=1.0)
        sp.desenhar(surf)

        # After 1.55s: shell casing expired, scorch mark still alive
        sp.atualizar(1.55)
        self.assertEqual(len(sp.capsulas), 0)
        self.assertEqual(len(sp.marcas_queimadura), 1)

        # After additional 3.55s (total 5.1s): scorch mark expired
        sp.atualizar(3.55)
        self.assertEqual(len(sp.marcas_queimadura), 0)

    def test_vsync_tear_one_time_6_deg_split(self):
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("vsync")
        cena.config_sistema.definir_valor("vsync", "desligado")
        cena.teclado = _DummyKeyboard()
        cena.mouse = _DummyMouse(pos=(640, 360))
        # Align camera directly onto player so camera.y stays steady across the frame
        cena.camera.x = max(0.0, cena.jogador.x - 640.0)
        cena.camera.y = max(0.0, cena.jogador.y - 360.0)
        cena.vsync_tear_y = 200.0

        proj = Projetil(
            x=cena.camera.x + 400.0,
            y=cena.camera.y + 202.0,
            dir_x=1.0,
            dir_y=0.0,
            velocidade=400.0,
            dano=10,
            dono="jogador",
        )
        cena.projeteis = [proj]

        # First frame crossing the tear line splits into 2 diverging projectiles at ±6°
        cena.update(0.016)
        self.assertEqual(len(cena.projeteis), 2)
        p1, p2 = cena.projeteis[0], cena.projeteis[1]
        self.assertTrue(p1.ja_dividido_tear)
        self.assertTrue(p2.ja_dividido_tear)
        ang1 = math.degrees(math.atan2(p1.dir_y, p1.dir_x))
        ang2 = math.degrees(math.atan2(p2.dir_y, p2.dir_x))
        self.assertAlmostEqual(abs(ang1 - ang2), 12.0, places=1)

        # Re-aligning with tear line must NOT split again (one-time guard)
        p1.y = cena.camera.y + cena.vsync_tear_y
        p2.y = cena.camera.y + cena.vsync_tear_y
        cena.update(0.016)
        self.assertEqual(len(cena.projeteis), 2)

    def test_vsync_tear_speed_reduced_by_50_percent_to_80px_per_second(self):
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("vsync")
        cena.config_sistema.definir_valor("vsync", "desligado")
        cena.teclado = _DummyKeyboard()
        cena.mouse = _DummyMouse(pos=(640, 360))
        cena.vsync_tear_y = 100.0
        cena.update(0.5)
        # 100.0 + 80.0 * 0.5 = 140.0
        self.assertAlmostEqual(cena.vsync_tear_y, 140.0, places=1)

    def test_world_only_resolution_scaling_draws_without_shrinking_window(self):
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("resolucao")
        for opt, expected_scale in (("75%", 0.75), ("50%", 0.50), ("25%", 0.25), ("100%", 1.0)):
            cena.config_sistema.definir_valor("resolucao", opt)
            self.janela.definir_resolucao(opt)
            self.assertAlmostEqual(self.janela.escala_resolucao_mundo, expected_scale)
            self.assertEqual((self.janela.largura_janela_atual, self.janela.altura_janela_atual), (1280, 720))
            cena.draw()


class TestPhase2ParryDuelNinjaTankAndBoss(unittest.TestCase):
    """Valida whiff lockout/Exposed, Tank Controls HP proporcional, InimigoNinja, Impressora Térmica e Boss."""

    def test_parry_whiff_lockout_exposed_ninja_duel_and_tank_controls(self):
        from src.entidades.inimigo_ninja import InimigoNinja
        from src.entidades.inimigo_impressora import InimigoImpressoraTermica
        from src.entidades.inimigos.geladeira_tsunami import GeladeiraTsunami
        from src.sistemas.sistema_spawn import SistemaSpawn

        # 1. Parry whiff adds +0.8s lockout, 0.20s hitstop, and Exposed (+25% dmg)
        cena = GameplayScene()
        melee = cena._obter_arma_melee()
        melee.tempo_recarga_restante = 0.6
        melee.iniciar_golpe_parry(0.0, punir_whiff=True)
        melee.atualizar(0.20)
        self.assertAlmostEqual(melee.tempo_recarga_restante, 1.4, places=3)
        self.assertAlmostEqual(cena.hitstop_timer, 0.20, places=3)
        self.assertGreater(cena.jogador.exposed_timer, 1.0)

        # 2. Tank Controls proportional HP scaling (125/250 <-> 75/150)
        cena.jogador.atualizar_modo_tanque(True)
        self.assertEqual(cena.jogador.hp_max, 250)
        cena.jogador.hp = 125
        cena.jogador.atualizar_modo_tanque(False)
        self.assertEqual(cena.jogador.hp_max, 150)
        self.assertEqual(cena.jogador.hp, 75)

        # 3. InimigoNinja max-2 & 20s spawn cooldown
        sp = SistemaSpawn(max_ativos=50)
        sp.tempo_decorrido = 80.0
        novos = sp.update(dt=0.1, camera_x=0.0, camera_y=0.0, total_inimigos_vivos=0, ninjas_vivos=2)
        self.assertFalse(any(getattr(e, "is_ninja", False) for e in novos))
        novos_ok = sp.update(dt=0.1, camera_x=0.0, camera_y=0.0, total_inimigos_vivos=0, ninjas_vivos=1)
        self.assertTrue(any(getattr(e, "is_ninja", False) for e in novos_ok))
        novos_cd = sp.update(dt=0.1, camera_x=0.0, camera_y=0.0, total_inimigos_vivos=0, ninjas_vivos=1)
        self.assertFalse(any(getattr(e, "is_ninja", False) for e in novos_cd))

        # 4. InimigoImpressoraTermica fires Overload Core
        imp = InimigoImpressoraTermica(x=200.0, y=200.0)
        imp.timer_tiro = 2.5
        imp.update(0.1, (400.0, 224.0))
        cores = imp.obter_projeteis_pendentes()
        self.assertEqual(len(cores), 1)
        self.assertTrue(cores[0].sobrecarga_termica)

        # 5. GeladeiraTsunami speed 268.0 and aimed Phase 1 shots (18 ring + 5 aimed fan)
        boss = GeladeiraTsunami(x=300.0, y=300.0)
        self.assertAlmostEqual(boss.velocidade, 268.0)
        boss._disparar_pulso_subwoofer((600.0, 378.0))
        tiros_boss = boss.obter_projeteis_pendentes()
        self.assertGreaterEqual(len(tiros_boss), 23)

        # 6. Rocket starts slower (140 px/s) and accelerates smoothly
        from src.armas.lanca_foguetes import LancaFoguetes
        lf = LancaFoguetes()
        foguete = lf.disparar(100.0, 100.0, 300.0, 100.0)[0]
        self.assertAlmostEqual(foguete.velocidade, 140.0)
        foguete.update(0.5)
        self.assertAlmostEqual(foguete.velocidade, 480.0)

        # 7. ModalOverclock never shows duplicates or already-owned BIOS upgrades
        cena.jogador.overclocks_adquiridos = {"multithreading", "refrigeracao", "overvolt", "bios_modding"}
        cena.modal_overclock.abrir()
        ids_ofertados = [c["id"] for c in cena.modal_overclock.cards_sorteados]
        self.assertEqual(len(ids_ofertados), 2)
        self.assertEqual(len(set(ids_ofertados)), 2)
        self.assertTrue(all(cid not in cena.jogador.overclocks_adquiridos for cid in ids_ofertados))


if __name__ == "__main__":
    unittest.main()
