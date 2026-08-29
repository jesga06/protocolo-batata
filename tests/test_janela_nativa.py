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
        """Verifica se a Janela mantém resolução virtual 800x600 e comportamento Singleton."""
        j1 = Janela.get_instance()
        j2 = Janela()
        self.assertIs(j1, j2)
        self.assertEqual(j1.largura, 800)
        self.assertEqual(j1.altura, 600)
        self.assertEqual(j1.screen.get_size(), (800, 600))

    def test_screen_to_virtual_coords_clamping(self):
        """Verifica se a conversão de coordenadas mapeia e clampa o mouse aos limites do canvas."""
        janela = Janela.get_instance()

        # Coordenadas no centro da tela (400, 300)
        vx, vy = janela.screen_to_virtual_coords(400.0, 300.0)
        self.assertAlmostEqual(vx, 400.0, delta=2.0)
        self.assertAlmostEqual(vy, 300.0, delta=2.0)

        # Coordenadas fora da janela (nas bordas pretas) devem ser clampadas em [0, 800] e [0, 600]
        vx_neg, vy_neg = janela.screen_to_virtual_coords(-50.0, -100.0)
        self.assertGreaterEqual(vx_neg, 0.0)
        self.assertGreaterEqual(vy_neg, 0.0)

        vx_max, vy_max = janela.screen_to_virtual_coords(2000.0, 1500.0)
        self.assertLessEqual(vx_max, 800.0)
        self.assertLessEqual(vy_max, 600.0)

    def test_draw_text_cached_fonts(self):
        """Verifica se o método draw_text utiliza cache interno sem recriar fontes."""
        janela = Janela.get_instance()
        janela.draw_text("TESTE FPS", 10, 10, tamanho=14, cor=(255, 255, 255))
        self.assertIn(("Arial", 14), janela._fontes_cache)

    def test_alternar_fullscreen(self):
        """Verifica a alternância de estado do modo tela cheia."""
        janela = Janela.get_instance()
        estado_antigo = janela.is_fullscreen
        janela.alternar_fullscreen()
        self.assertNotEqual(janela.is_fullscreen, estado_antigo)
        janela.alternar_fullscreen()
        self.assertEqual(janela.is_fullscreen, estado_antigo)


if __name__ == "__main__":
    unittest.main()
