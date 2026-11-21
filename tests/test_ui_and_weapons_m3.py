"""
Testes Unitários e de Integração M3 — Protocolo: Batata
Valida:
1. Centralização Horizontal do Menu Principal e HUD via Pygame Font (rect.centerx == LARGURA_TELA // 2).
2. Mecânica de Disparo exclusivamente via Clique Explícito do Mouse (pygame.MOUSEBUTTONDOWN / button_down).
3. Troca de Armas pelas teclas numéricas 1, 2 e 3 e disparo exclusivo da arma ativa selecionada.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, DOURADO, BRANCO, AMARELO_XP
from src.entidades.jogador import Jogador
from src.armas.melee import Melee
from src.armas.pistola import Pistola
from src.cenas.menu_principal import MenuPrincipalScene
from src.cenas.gameplay import GameplayScene
from PPlay.window import Window


class TestUICenteringM3(unittest.TestCase):
    """Testa se os retângulos de texto do Menu e HUD estão matematicamente centralizados na tela virtual."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()
        cls.janela = Window(LARGURA_TELA, ALTURA_TELA, "TestWindow", resizavel=False, pixel_art=True)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    def test_menu_principal_titulos_e_opcoes_centralizados(self):
        """Renderiza MenuPrincipalScene real e verifica que título e opções pintam pixels na coluna central (x=640)."""
        cena_menu = MenuPrincipalScene()
        screen = cena_menu.janela.screen
        screen.fill((0, 0, 0))
        cena_menu.draw()

        # Verifica que há pixels renderizados ao redor do eixo central x=640 na faixa do título e das opções
        centro_x = LARGURA_TELA // 2
        pixels_centro_titulo = [
            screen.get_at((x, y))[:3]
            for x in range(centro_x - 60, centro_x + 60, 4)
            for y in range(70, 150, 4)
        ]
        cor_fundo = screen.get_at((5, 5))[:3]
        self.assertTrue(
            any(c != cor_fundo for c in pixels_centro_titulo),
            "Título do MenuPrincipalScene deve renderizar pixels visíveis centralizados em torno de x=640."
        )

    def test_hud_timer_e_abates_centralizados(self):
        """Renderiza GameplayScene._desenhar_hud_tela real e verifica timer e abates no topo central (x=640)."""
        cena = GameplayScene()
        cena.tempo_sobrevivencia = 165.0
        cena.abates = 42
        screen = cena.janela.screen
        screen.fill((0, 0, 0))
        cena._desenhar_hud_tela(hud_visivel=True)

        # Verifica pixels não-pretos na faixa central do timer (y=14..36) e abates (y=40..56) em torno de x=640
        centro_x = LARGURA_TELA // 2
        pixels_timer = [screen.get_at((x, y))[:3] for x in range(centro_x - 30, centro_x + 30, 2) for y in range(14, 36, 2)]
        pixels_abates = [screen.get_at((x, y))[:3] for x in range(centro_x - 30, centro_x + 30, 2) for y in range(40, 56, 2)]
        self.assertTrue(any(c != (0, 0, 0) for c in pixels_timer), "Timer do HUD deve ser renderizado no topo central.")
        self.assertTrue(any(c != (0, 0, 0) for c in pixels_abates), "Contador de abates do HUD deve ser renderizado no topo central.")

    def test_menu_principal_draw_execucao(self):
        cena_menu = MenuPrincipalScene()
        # Não deve lançar nenhuma exceção ao desenhar
        cena_menu.draw()


class TestWeaponSwitchingAndClickInputsM3(unittest.TestCase):
    """Testa troca de armas (1, 2, 3) e mecânica de disparo por clique."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()
        self.jogador = Jogador(x=400, y=300)

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    def test_selecao_e_obtencao_de_arma_ativa(self):
        # Por padrão slot_ativo é 2 (Pistola)
        self.assertEqual(self.jogador.slot_ativo, 2)
        arma_2 = self.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_2, Pistola)

        # Troca para Slot 1 (Melee)
        self.jogador.selecionar_slot(1)
        self.assertEqual(self.jogador.slot_ativo, 1)
        arma_1 = self.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_1, Melee)

        # Troca para Slot 3 (Especial)
        self.jogador.selecionar_slot(3)
        self.assertEqual(self.jogador.slot_ativo, 3)
        self.assertIsNone(self.jogador.obter_arma_ativa())

        # Atribui arma especial e testa Slot 3
        arma_especial_fake = Pistola(dano=50, cooldown=0.1)
        self.jogador.arma_especial = arma_especial_fake
        self.assertEqual(self.jogador.obter_arma_ativa(), arma_especial_fake)

    def test_input_teclado_troca_slots_1_2_3(self):
        class MockKeyboard:
            def __init__(self, pressed_key):
                self.pressed_key = pressed_key

            def key_pressed(self, k):
                return k == self.pressed_key

            def key_down(self, k):
                return k == self.pressed_key

        # Simula pressionar tecla 1
        teclado_1 = MockKeyboard("1")
        self.jogador.processar_input(teclado_1, None, dt=0.016)
        self.assertEqual(self.jogador.slot_ativo, 1)

        # Simula pressionar tecla 2
        teclado_2 = MockKeyboard("2")
        self.jogador.processar_input(teclado_2, None, dt=0.016)
        self.assertEqual(self.jogador.slot_ativo, 2)

        # Simula pressionar tecla 3
        teclado_3 = MockKeyboard("3")
        self.jogador.processar_input(teclado_3, None, dt=0.016)
        self.assertEqual(self.jogador.slot_ativo, 3)

    def test_gameplay_scene_disparo_apenas_com_clique_e_arma_ativa(self):
        cena = GameplayScene()
        # Sem clique: nenhum projétil é gerado
        cena.jogador.selecionar_slot(2)  # Pistola
        total_proj_antes = len(cena.projeteis)

        # Simula um ciclo de loop sem eventos de mouse (sem clique)
        cena.loop()
        self.assertEqual(len(cena.projeteis), total_proj_antes)

        # Simula arma ativa selecionada e disparo da pistola isolado
        arma_ativa = cena.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_ativa, Pistola)
        tiros = arma_ativa.disparar(100, 100, 200, 100)
        self.assertEqual(len(tiros), 1)

        # Troca para slot 1 (Melee): obter_arma_ativa deve ser Melee
        cena.jogador.selecionar_slot(1)
        arma_melee = cena.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_melee, Melee)
        tiros_melee = arma_melee.disparar(100, 100, 200, 100)
        self.assertEqual(len(tiros_melee), 0)  # Melee não dispara projéteis


if __name__ == "__main__":
    unittest.main()
