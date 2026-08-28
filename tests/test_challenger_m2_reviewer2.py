import os, sys, math, unittest
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)
import pygame
from PPlay.window import Window
from PPlay.camera import Camera
from PPlay.scenemanager import SceneManager
from src.cenas.gameplay import GameplayScene
from src.cenas.menu_principal import MenuPrincipalScene
from src.sistemas.sistema_spawn import SistemaSpawn
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.projetil import Projetil
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, LARGURA_ARENA, ALTURA_ARENA, SPAWN_DISTANCIA_OFFSET

class MockTecladoAdv:
    def __init__(self, pressed=None, down=None):
        self.pressed = set(k.lower() for k in (pressed or []))
        self.down = set(k.lower() for k in (down or []))
    def key_pressed(self, k): return k.lower() in self.pressed
    def key_down(self, k): return k.lower() in self.down

class MockMouseAdv:
    def __init__(self, pos=(400, 300), pressed_btn=None, down_btn=None):
        self.pos = pos
        self.pressed_btn = set(pressed_btn or [])
        self.down_btn = set(down_btn or [])
    def get_position(self): return self.pos
    def button_pressed(self, btn): return btn in self.pressed_btn
    def button_down(self, btn): return btn in self.down_btn

class TestSistemaSpawnAdversarialRev2(unittest.TestCase):
    def setUp(self):
        self.spawner = SistemaSpawn(max_ativos=60)
    def test_intervalo_spawn_boundary_values(self):
        self.assertAlmostEqual(self.spawner.intervalo_spawn(0.0), 1.80)
        self.assertAlmostEqual(self.spawner.intervalo_spawn(50.0), 1.20)
        self.assertAlmostEqual(self.spawner.intervalo_spawn(116.66666666666667), 0.40)
        self.assertAlmostEqual(self.spawner.intervalo_spawn(200.0), 0.40)
        self.assertAlmostEqual(self.spawner.intervalo_spawn(100000.0), 0.40)
    def test_tamanho_lote_scaling_and_ceiling(self):
        self.assertEqual(self.spawner.tamanho_lote(0.0), 1)
        self.assertEqual(self.spawner.tamanho_lote(24.999), 1)
        self.assertEqual(self.spawner.tamanho_lote(25.0), 2)
        self.assertEqual(self.spawner.tamanho_lote(49.999), 2)
        self.assertEqual(self.spawner.tamanho_lote(50.0), 3)
        self.assertEqual(self.spawner.tamanho_lote(175.0), 8)
        self.assertEqual(self.spawner.tamanho_lote(1000.0), 8)
    def test_gerar_posicao_spawn_5000_iterations(self):
        margem = float(SPAWN_DISTANCIA_OFFSET)
        for cam_x, cam_y in [(0, 0), (400, 300), (800, 600)]:
            for _ in range(1000):
                sx, sy = self.spawner.gerar_posicao_spawn(camera_x=cam_x, camera_y=cam_y)
                in_viewport = (cam_x <= sx <= cam_x + 800) and (cam_y <= sy <= cam_y + 600)
                self.assertFalse(in_viewport)
                self.assertGreaterEqual(sx, -margem)
                self.assertLessEqual(sx, 1600 + margem)
                self.assertGreaterEqual(sy, -margem)
                self.assertLessEqual(sy, 1200 + margem)
    def test_soft_cap_strict_enforcement(self):
        spawner = SistemaSpawn(max_ativos=10)
        spawner.tempo_decorrido = 200.0
        spawner.timer_spawn = 5.0
        novos = spawner.update(dt=0.1, camera_x=0, camera_y=0, total_inimigos_vivos=8)
        self.assertEqual(len(novos), 2)
        spawner.timer_spawn = 5.0
        novos = spawner.update(dt=0.1, camera_x=0, camera_y=0, total_inimigos_vivos=10)
        self.assertEqual(len(novos), 0)

class TestGameplaySceneAdversarialRev2(unittest.TestCase):
    def setUp(self):
        self.janela = Window(800, 600, 'Protocolo: Batata', resizavel=True, pixel_art=True)
        self.cena = GameplayScene()
        SceneManager.change_scene(self.cena)
    def test_camera_tracking_and_boundary_clamping(self):
        cam = self.cena.camera
        self.cena.jogador.x = 800.0; self.cena.jogador.y = 600.0
        for _ in range(50): cam.follow(self.cena.jogador, suavizacao=0.5)
        self.assertAlmostEqual(cam.x, 416.0, delta=1.0)
        self.assertAlmostEqual(cam.y, 316.0, delta=1.0)
    def test_pause_mode_toggle_and_state_freeze(self):
        self.cena.teclado = MockTecladoAdv(down=['esc'])
        self.cena.loop()
        self.assertTrue(self.cena.pausado)
        tempo_antes = self.cena.tempo_sobrevivencia
        self.cena.teclado = MockTecladoAdv(pressed=['d'])
        self.cena.loop()
        self.assertEqual(self.cena.tempo_sobrevivencia, tempo_antes)
    def test_gear_button_click_triggers_pause(self):
        self.cena.mouse = MockMouseAdv(pos=(760, 20), down_btn=[1])
        self.cena.teclado = MockTecladoAdv()
        self.cena.loop()
        self.assertTrue(self.cena.pausado)
    def test_game_over_lifecycle(self):
        self.cena.jogador.receber_dano(200)
        self.assertFalse(self.cena.jogador.vivo)
        self.cena.teclado = MockTecladoAdv()
        self.cena.loop()
        self.assertTrue(self.cena.game_over)
        self.cena.draw()
    def test_out_of_bounds_bullet_cleanup(self):
        b = Projetil(x=1800.0, y=1400.0, dir_x=1.0, dir_y=0.0, velocidade=100.0, dano=10)
        self.cena.projeteis.append(b)
        self.cena.teclado = MockTecladoAdv()
        self.cena.auto_fire_ativo = False
        self.cena.loop()
        self.assertNotIn(b, self.cena.projeteis)

class TestMenuPrincipalSceneAdversarialRev2(unittest.TestCase):
    def setUp(self):
        self.janela = Window(800, 600, 'Protocolo: Batata', resizavel=True, pixel_art=True)
        self.menu = MenuPrincipalScene()
        SceneManager.change_scene(self.menu)
    def test_menu_navigation_wrap_around(self):
        self.menu.teclado = MockTecladoAdv(down=['up'])
        self.menu.loop()
        self.assertEqual(self.menu.opcao_selecionada, 3)
    def test_menu_iniciar_jogo_transitions_to_gameplay(self):
        self.menu.opcao_selecionada = 0
        self.menu.teclado = MockTecladoAdv(down=['enter'])
        self.menu.loop()
        self.assertIsInstance(SceneManager._current_scene, GameplayScene)

if __name__ == '__main__': unittest.main()
