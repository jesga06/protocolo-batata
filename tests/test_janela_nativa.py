"""
Testes Unitários para o Gerenciador de Janela e Escalonamento Nativo (src/utils/janela.py).
"""

import unittest
import pygame
from src.utils.janela import Janela


class TestJanelaNativa(unittest.TestCase):
    """Valida o funcionamento do controlador de Janela nativa em Pygame."""

    @classmethod
    def setUpClass(cls):
        if not pygame.get_init():
            pygame.init()

    def test_singleton_e_resolucao_virtual(self):
        """Verifica se a Janela mantém resolução virtual 1280x720 e comportamento Singleton."""
        j1 = Janela.get_instance()
        j2 = Janela()
        self.assertIs(j1, j2)
        self.assertEqual(j1.largura, 1280)
        self.assertEqual(j1.altura, 720)
        self.assertEqual(j1.screen.get_size(), (1280, 720))

    def test_screen_to_virtual_coords_clamping(self):
        """Verifica se a conversão de coordenadas mapeia e clampa o mouse aos limites do canvas."""
        janela = Janela.get_instance()
        rw, rh = janela.real_screen.get_size()

        # Coordenadas no centro da tela real devem mapear para o centro do canvas virtual (640, 360)
        vx, vy = janela.screen_to_virtual_coords(rw / 2.0, rh / 2.0)
        self.assertAlmostEqual(vx, 640.0, delta=2.0)
        self.assertAlmostEqual(vy, 360.0, delta=2.0)

        # Coordenadas fora da janela (nas bordas pretas) devem ser clampadas em [0, 1280] e [0, 720]
        vx_neg, vy_neg = janela.screen_to_virtual_coords(-500.0, -500.0)
        self.assertGreaterEqual(vx_neg, 0.0)
        self.assertGreaterEqual(vy_neg, 0.0)

        vx_max, vy_max = janela.screen_to_virtual_coords(rw + 500.0, rh + 500.0)
        self.assertLessEqual(vx_max, 1280.0)
        self.assertLessEqual(vy_max, 720.0)

    def test_draw_text_cached_fonts(self):
        """Verifica se o método draw_text utiliza cache interno sem recriar fontes."""
        janela = Janela.get_instance()
        janela.draw_text("TESTE FPS", 10, 10, tamanho=14, cor=(255, 255, 255))
        self.assertTrue(any("Arial" in str(k) and 14 in k for k in janela._fontes_cache.keys()))

    def test_alternar_fullscreen(self):
        """Verifica a alternância de estado do modo tela cheia."""
        janela = Janela.get_instance()
        estado_antigo = janela.is_fullscreen
        janela.alternar_fullscreen()
        self.assertNotEqual(janela.is_fullscreen, estado_antigo)
        janela.alternar_fullscreen()
        self.assertEqual(janela.is_fullscreen, estado_antigo)

    def test_definir_resolucao_menores_que_720p(self):
        """Valida que a janela aceita e aplica resoluções de 1280x720 para baixo."""
        janela = Janela.get_instance()
        janela.definir_resolucao("75%")
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (960, 540))

        janela.definir_resolucao("50%")
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (640, 360))

        janela.definir_resolucao("25%")
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (320, 180))

        janela.definir_resolucao("100%")
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (1280, 720))

    def test_fps_ilimitado_zero_passado_ao_clock(self):
        """fps_alvo=0 (ilimitado) deve chamar clock.tick(0) sem fallback para valor positivo."""
        from unittest.mock import MagicMock
        from src.main import _parse_fps_alvo

        self.assertEqual(_parse_fps_alvo("ilimitado"), 0)
        self.assertEqual(_parse_fps_alvo("45"), 45)

        janela = Janela(largura_virtual=1280, altura_virtual=720, titulo="Teste FPS")
        janela.fps_alvo = 30
        janela._clock = MagicMock()
        janela._clock.tick.return_value = 4
        janela.update(fps_alvo=0)
        janela._clock.tick.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
