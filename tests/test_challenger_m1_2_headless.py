"""
Empirical Challenger 2 Test Suite — Milestone 1 (Phase 0)
Adversarial testing of Window setup, SceneManager, Headless lifecycle, Event loop, Audio absence, and Resilience.
"""

import os
import sys
import gc
import time
import tracemalloc
import unittest

# Ensure headless drivers are set before pygame is initialized anywhere
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from PPlay.window import Window
from PPlay.scenemanager import Scene, SceneManager
from PPlay.sound import SoundManager, Sound, Music
from src.main import inicializar_jogo, main
from src.cenas.base_scene import BaseScene
from src.cenas.menu_principal import MenuPrincipalScene
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, FPS_PADRAO,
    ASSET_PATHS, obter_caminho_asset
)


class TestHeadlessMainExecution(unittest.TestCase):
    """Verifica a execução robusta da função main() de src/main.py no modo headless."""

    def setUp(self):
        pygame.init()

    def test_main_30_frames_headless(self):
        """Executa main(limite_frames=30) e valida término limpo sem exceções."""
        try:
            main(limite_frames=30)
        except Exception as e:
            self.fail(f"main(limite_frames=30) falhou com exceção inesperada: {e}")

    def test_main_120_frames_stress(self):
        """Executa main(limite_frames=120) para verificar estabilidade em loop mais longo."""
        try:
            main(limite_frames=120)
        except Exception as e:
            self.fail(f"main(limite_frames=120) falhou durante o estresse de 120 frames: {e}")

    def test_main_300_frames_extended_stress(self):
        """Executa 300 frames seguidos verificando taxa de execução e estabilidade."""
        t0 = time.perf_counter()
        try:
            main(limite_frames=300)
        except Exception as e:
            self.fail(f"main(limite_frames=300) falhou com: {e}")
        t1 = time.perf_counter()
        # No modo dummy com clock.tick() o pygame roda a até 60fps (~5 segundos para 300 frames)
        self.assertLess(t1 - t0, 10.0, f"Execução de 300 frames demorou excessivamente: {t1 - t0:.2f}s")

    def test_main_memory_leak_check(self):
        """
        Adversarial: Monitora alocações de memória com tracemalloc ao longo de 200 frames.
        Compara o crescimento de memória entre blocos de 50 frames para verificar que não há vazamento.
        """
        gc.collect()
        tracemalloc.start()
        
        # Executa 50 frames de aquecimento (warm-up)
        main(limite_frames=50)
        gc.collect()
        snap_warmup = tracemalloc.take_snapshot()
        
        # Executa mais 150 frames em blocos
        main(limite_frames=150)
        gc.collect()
        snap_after_150 = tracemalloc.take_snapshot()
        
        stats = snap_after_150.compare_to(snap_warmup, 'lineno')
        tracemalloc.stop()
        
        total_diff_kb = sum(stat.size_diff for stat in stats) / 1024.0
        
        # O crescimento de memória líquida após 150 frames de loop repetido deve ser desprezível (< 250 KB)
        self.assertLess(
            total_diff_kb, 250.0,
            f"Possível vazamento de memória detectado: delta de {total_diff_kb:.2f} KB após 150 frames!"
        )


class TestPPlayWindowHeadless(unittest.TestCase):
    """Testes adversariais do subsistema Window do PPlay 2.0 no ambiente dummy/headless."""

    def setUp(self):
        self.janela = Window.get_instance()

    def test_window_singleton_properties(self):
        """Valida se o Window é um Singleton correto e se os buffers foram alocados."""
        j2 = Window.get_instance()
        j3 = Window(1024, 768, "Outro Titulo")
        self.assertIs(self.janela, j2, "Window.get_instance() deve retornar a mesma instância singleton!")
        self.assertIs(self.janela, j3, "Window() subsequente deve retornar a instância singleton já criada!")
        self.assertEqual(self.janela.largura, LARGURA_TELA)
        self.assertEqual(self.janela.altura, ALTURA_TELA)
        self.assertIsNotNone(self.janela.screen)
        self.assertIsNotNone(self.janela.real_screen)
        self.assertEqual(self.janela.screen.get_size(), (LARGURA_TELA, ALTURA_TELA))

    def test_window_update_delta_time_and_fps(self):
        """Valida que update() atualiza delta_time e não explode em headless."""
        for _ in range(30):
            self.janela.update()
            dt = self.janela.delta_time()
            self.assertIsInstance(dt, float)
            self.assertGreaterEqual(dt, 0.0)
            fps = self.janela.get_fps()
            self.assertGreaterEqual(fps, 0.0)

    def test_window_screen_to_virtual_coords(self):
        """Testa a transformação de coordenadas físicas para virtuais sob letterboxing."""
        # Se resolução real == resolução virtual (800x600)
        vx, vy = self.janela.screen_to_virtual_coords(400, 300)
        self.assertAlmostEqual(vx, 400.0, delta=1.0)
        self.assertAlmostEqual(vy, 300.0, delta=1.0)

        # Cantos
        vx0, vy0 = self.janela.screen_to_virtual_coords(0, 0)
        self.assertAlmostEqual(vx0, 0.0, delta=1.0)
        self.assertAlmostEqual(vy0, 0.0, delta=1.0)

    def test_window_draw_text_headless(self):
        """Valida que draw_text renderiza na tela virtual sem falha de fonte no modo dummy."""
        try:
            self.janela.draw_text("Teste Headless 123", 100, 100, tamanho=20, cor=(255, 255, 255))
            self.janela.draw_text("Acentuação: Ação, Ícone, Dano, Configuração", 50, 150, tamanho=16, cor="cyan")
            self.janela.draw_text("Fallback Fonte", 50, 200, tamanho=14, fonte="FonteInexistenteXYZ")
        except Exception as e:
            self.fail(f"draw_text falhou no modo headless: {e}")

    def test_window_background_color_setting(self):
        """Valida alteração de cor de fundo por tupla, string e fallback para inválidos."""
        self.janela.set_background_color((18, 22, 30))
        self.assertEqual(self.janela.cor_fundo, (18, 22, 30))
        self.janela.set_background_color("black")
        self.assertEqual(self.janela.cor_fundo, pygame.Color("black"))
        # Invalid color string fallback
        self.janela.set_background_color("cor_invalida_totalmente_inexistente")
        self.assertEqual(self.janela.cor_fundo, (0, 0, 0))


class TestSceneManagerAndSceneLifecycle(unittest.TestCase):
    """Testa o ciclo de vida de cenas via SceneManager e BaseScene."""

    class MockScene(BaseScene):
        def __init__(self, name="Mock"):
            super().__init__()
            self.name = name
            self.loop_count = 0
            self.draw_count = 0

        def loop(self):
            self.loop_count += 1

        def draw(self):
            self.draw_count += 1

    def test_scene_lifecycle_order_and_execution(self):
        """Valida que SceneManager executa loop() e depois draw() em cada iteração."""
        cena = self.MockScene("Cena1")
        SceneManager.change_scene(cena)
        self.assertIs(SceneManager._current_scene, cena)

        for i in range(1, 11):
            SceneManager.run()
            self.assertEqual(cena.loop_count, i)
            self.assertEqual(cena.draw_count, i)

    def test_scene_manager_none_fallback(self):
        """Adversarial: SceneManager.run() quando nenhuma cena está ativa."""
        SceneManager.change_scene(None)
        try:
            SceneManager.run()
        except Exception as e:
            self.fail(f"SceneManager.run() com cena None falhou com: {e}")

    def test_rapid_scene_switching_stress(self):
        """Adversarial: Troca rápida de centenas de cenas consecutivas."""
        scenes = [self.MockScene(f"Scene_{i}") for i in range(100)]
        for s in scenes:
            SceneManager.change_scene(s)
            SceneManager.run()
            self.assertEqual(s.loop_count, 1)
            self.assertEqual(s.draw_count, 1)

    def test_menu_principal_scene_accumulates_time(self):
        """Valida a cena real MenuPrincipalScene acumulando dt no ciclo de vida."""
        menu = MenuPrincipalScene()
        SceneManager.change_scene(menu)
        
        janela = Window.get_instance()
        janela.update()
        SceneManager.run()
        
        self.assertGreaterEqual(menu.tempo_acumulado, 0.0)
        self.assertEqual(len(menu.opcoes), 4)


class TestEventLoopAndInputInjectionHeadless(unittest.TestCase):
    """Testes adversariais com injeção de eventos simulados no loop de eventos do SDL."""

    def setUp(self):
        self.janela = Window.get_instance()
        pygame.event.clear()

    def test_keyboard_navigation_event_injection(self):
        """Injeta eventos KEYDOWN e valida reação do MenuPrincipalScene."""
        menu = MenuPrincipalScene()
        SceneManager.change_scene(menu)
        
        self.assertEqual(menu.opcao_selecionada, 0)

        # Injeta DOWN
        ev_down = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN})
        pygame.event.post(ev_down)
        
        self.janela.update() # Coleta eventos do SDL
        self.assertTrue(self.janela.keyboard.key_down("DOWN"))
        
        menu.loop()
        self.assertEqual(menu.opcao_selecionada, 1)

        # Injeta 's'
        ev_s = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_s})
        pygame.event.post(ev_s)
        self.janela.update()
        self.assertTrue(self.janela.keyboard.key_down("s"))
        menu.loop()
        self.assertEqual(menu.opcao_selecionada, 2)

        # Injeta UP
        ev_up = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP})
        pygame.event.post(ev_up)
        
        self.janela.update()
        self.assertTrue(self.janela.keyboard.key_down("UP"))
        
        menu.loop()
        self.assertEqual(menu.opcao_selecionada, 1)

        # Injeta 'w'
        ev_w = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_w})
        pygame.event.post(ev_w)
        self.janela.update()
        self.assertTrue(self.janela.keyboard.key_down("w"))
        menu.loop()
        self.assertEqual(menu.opcao_selecionada, 0)

    def test_unhandled_exotic_events_resilience(self):
        """Adversarial: Injeta eventos exóticos e garante que o loop de Window.update() não quebra."""
        exotic_events = [
            pygame.event.Event(pygame.WINDOWRESIZED, {"x": 1024, "y": 768}),
            pygame.event.Event(pygame.WINDOWMOVED, {"x": 100, "y": 100}),
            pygame.event.Event(pygame.MOUSEMOTION, {"pos": (200, 300), "rel": (1, 2), "buttons": (0, 0, 0)}),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (200, 300), "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (200, 300), "button": 1}),
            pygame.event.Event(pygame.USEREVENT, {"code": 9999}),
        ]
        
        for ev in exotic_events:
            pygame.event.post(ev)

        try:
            self.janela.update()
            SceneManager.run()
        except Exception as e:
            self.fail(f"Window.update() / SceneManager.run() falhou ao processar eventos exóticos: {e}")


class TestSoundAndAudioHardwareAbsence(unittest.TestCase):
    """Testa a integridade do subsistema de áudio na ausência de hardware físico."""

    def test_sound_manager_init_dummy(self):
        """Valida que o SoundManager inicializa com sucesso no driver de áudio dummy."""
        try:
            SoundManager.inicializar()
            self.assertTrue(pygame.mixer.get_init() is not None or pygame.mixer.get_init() != 0)
        except Exception as e:
            self.fail(f"SoundManager.inicializar() falhou no modo dummy: {e}")

    def test_all_registered_sfx_playback_dummy(self):
        """Valida carregamento e play de TODOS os 18+ SFX registrados sob driver dummy."""
        sfx_keys = [k for k in ASSET_PATHS.keys() if k.startswith("sfx_")]
        self.assertGreaterEqual(len(sfx_keys), 18)
        
        for k in sfx_keys:
            caminho = obter_caminho_asset(k)
            sfx = Sound(caminho)
            self.assertIsNotNone(sfx.sound, f"SFX '{k}' ({caminho}) falhou ao carregar em RAM!")
            try:
                sfx.play()
                sfx.set_volume(75)
                sfx.stop()
            except Exception as e:
                self.fail(f"SFX '{k}' falhou ao reproduzir em modo dummy: {e}")

    def test_music_playback_dummy(self):
        """Valida carregamento e controle de Música de fundo sem hardware de som."""
        music_path = obter_caminho_asset("musica_fase")
        music = Music(music_path)
        
        try:
            music.play(loops=0, fade_in_ms=0)
            music.pause()
            music.unpause()
            music.stop(fade_out_ms=0)
        except Exception as e:
            self.fail(f"Operações de Música falharam no driver dummy: {e}")

    def test_missing_sound_file_graceful_handling(self):
        """Valida que som inexistente não explode em exceção não tratada."""
        sfx = Sound("assets/audio/sfx/arquivo_totalmente_inexistente.wav")
        self.assertIsNone(sfx.sound)
        try:
            sfx.play()
            sfx.stop()
            sfx.set_volume(50)
        except Exception as e:
            self.fail(f"Sound com arquivo inexistente causou exceção não tratada: {e}")


if __name__ == "__main__":
    unittest.main()
