"""
Testes Unitários da Entidade Jogador — Protocolo: Batata
Valida estatísticas base, movimentação WASD/Setas, normalização diagonal,
clamping de arena, facing do cursor, dano, cura e estado de morte.
"""

import os
import sys
import math
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.entidades.jogador import Jogador
from src.utils.constantes import (
    JOGADOR_HP_MAX_PADRAO, JOGADOR_VELOCIDADE_PADRAO,
    JOGADOR_LARGURA, JOGADOR_ALTURA, LARGURA_ARENA, ALTURA_ARENA
)


class MockKeyboard:
    """Simulador de teclado para testes unitários determinísticos."""
    def __init__(self, pressed_keys=None, just_pressed_keys=None):
        self.pressed_keys = set(k.lower() for k in (pressed_keys or []))
        self.just_pressed_keys = set(k.lower() for k in (just_pressed_keys or []))

    def key_pressed(self, key):
        return key.lower() in self.pressed_keys

    def key_down(self, key):
        """Simula 'tecla pressionada neste frame apenas' (equivalente a key_down do PPlay)."""
        return key.lower() in self.just_pressed_keys


class MockMouse:
    """Simulador de mouse para testes unitários."""
    def __init__(self, pos=(400, 300)):
        self.pos = pos

    def get_position(self):
        return self.pos


class TestJogadorBasicos(unittest.TestCase):
    """Verifica atributos e valores iniciais do Jogador."""

    def test_jogador_inicializacao_padrao(self):
        j = Jogador(x=100.0, y=200.0)
        self.assertEqual(j.x, 100.0)
        self.assertEqual(j.y, 200.0)
        self.assertEqual(j.largura, JOGADOR_LARGURA)
        self.assertEqual(j.altura, JOGADOR_ALTURA)
        self.assertEqual(j.hp, 150)
        self.assertEqual(j.hp_max, 150)
        self.assertEqual(j.velocidade_base, 200.0)
        self.assertEqual(j.velocidade_atual, 200.0)
        self.assertTrue(j.vivo)
        self.assertTrue(j.facing_right)
        self.assertEqual(len(j.armas), 2)
        self.assertEqual(j.armas[0].nome, "Chave de Manutenção")
        self.assertEqual(j.armas[1].nome, "Padrão de Fábrica")


class TestJogadorMovimentacao(unittest.TestCase):
    """Testa movimentação linear, diagonal e clamping na arena."""

    def test_movimento_cardinal_direita(self):
        j = Jogador(x=100.0, y=100.0)
        teclado = MockKeyboard(["d"])
        mouse = MockMouse((400, 300))
        dt = 0.5  # 0.5s -> 100px a 200px/s
        j.processar_input(teclado, mouse, dt, limite_arena=(1600, 1200))
        self.assertAlmostEqual(j.x, 200.0)
        self.assertAlmostEqual(j.y, 100.0)

    def test_movimento_cardinal_esquerda_e_setas(self):
        j = Jogador(x=100.0, y=100.0)
        teclado = MockKeyboard(["left"])
        mouse = MockMouse((50, 100))
        dt = 0.25
        j.processar_input(teclado, mouse, dt, limite_arena=(1600, 1200))
        self.assertAlmostEqual(j.x, 50.0)
        self.assertAlmostEqual(j.y, 100.0)
        self.assertFalse(j.facing_right)

    def test_normalizacao_movimento_diagonal(self):
        """Verifica se o deslocamento diagonal tem magnitude igual a velocidade * dt."""
        j = Jogador(x=500.0, y=500.0)
        teclado = MockKeyboard(["w", "d"])  # cima e direita
        mouse = MockMouse((600, 400))
        dt = 1.0
        j.processar_input(teclado, mouse, dt, limite_arena=(1600, 1200))

        dx = j.x - 500.0
        dy = j.y - 500.0
        distancia_percorrida = math.sqrt(dx * dx + dy * dy)

        # Distância deve ser exatamente 200.0 px (velocidade * 1.0s)
        self.assertAlmostEqual(distancia_percorrida, 200.0, places=3)
        self.assertAlmostEqual(dx, 200.0 * 0.70710678118, places=3)
        self.assertAlmostEqual(dy, -200.0 * 0.70710678118, places=3)

    def test_arena_boundary_clamping(self):
        """Verifica restrição contra limites da arena."""
        j = Jogador(x=10.0, y=10.0)
        teclado_left_up = MockKeyboard(["a", "w"])
        mouse = MockMouse((0, 0))

        # Tenta mover além da borda superior esquerda
        j.processar_input(teclado_left_up, mouse, dt=2.0, limite_arena=(1600, 1200))
        self.assertEqual(j.x, 0.0)
        self.assertEqual(j.y, 0.0)

        # Tenta mover além da borda inferior direita
        j.x = 1590.0
        j.y = 1190.0
        teclado_right_down = MockKeyboard(["d", "s"])
        j.processar_input(teclado_right_down, mouse, dt=2.0, limite_arena=(1600, 1200))
        self.assertEqual(j.x, 1600.0 - JOGADOR_LARGURA)
        self.assertEqual(j.y, 1200.0 - JOGADOR_ALTURA)


class TestJogadorDanoECura(unittest.TestCase):
    """Testa sistema de dano, flash timer, cura e morte."""

    def test_recebimento_dano_e_cura(self):
        j = Jogador(x=100, y=100)
        self.assertEqual(j.hp, 150)

        j.receber_dano(40)
        self.assertEqual(j.hp, 110)
        self.assertGreater(j.flash_dano_timer, 0.0)

        j.curar(20)
        self.assertEqual(j.hp, 130)

        # Cura não deve ultrapassar hp_max
        j.curar(100)
        self.assertEqual(j.hp, 150)

    def test_morte_do_jogador(self):
        j = Jogador(x=100, y=100)
        j.receber_dano(150)
        self.assertEqual(j.hp, 0)
        self.assertFalse(j.vivo)

        # Dano adicional após morte não altera estado
        j.receber_dano(50)
        self.assertEqual(j.hp, 0)
        self.assertFalse(j.vivo)

        # Jogador morto não se move
        teclado = MockKeyboard(["d"])
        j.processar_input(teclado, None, dt=1.0, limite_arena=(1600, 1200))
        self.assertEqual(j.x, 100)


class TestJogadorSlotInputRegression(unittest.TestCase):
    """
    Regression: pressionar e segurar a tecla 3 não deve alternar slots repetidamente.
    Bug: key_pressed (held) era usado junto com key_down, causando toggle frame-a-frame
    de 3A/3B quando bios_modding estava ativo.
    Fix: apenas key_down (um frame) é aceito para seleção de slot.
    """

    def _fazer_jogador_com_bios_modding(self):
        """Retorna um Jogador com bios_modding ativo e arma especial dupla configurada."""
        from src.armas.pistola import Pistola
        j = Jogador(x=100.0, y=100.0)
        j.bios_modding = True
        j.arma_especial = Pistola()
        j.arma_especial_secundaria = Pistola()
        j.slot_ativo = 3
        return j

    def test_segurar_3_com_bios_modding_nao_alterna_slots(self):
        """
        Segurar a tecla 3 (key_down=False, key_pressed=True) não deve acionar
        selecionar_slot, portanto não deve alternar entre 3A e 3B.
        """
        j = self._fazer_jogador_com_bios_modding()
        arma_original = j.arma_especial
        secundaria_original = j.arma_especial_secundaria

        # Simula tecla SEGURADA: key_pressed=True mas key_down=False (não é novo frame de press)
        teclado_held = MockKeyboard(pressed_keys=["3"], just_pressed_keys=[])
        mouse = MockMouse()

        for _ in range(30):  # 30 frames com a tecla segurada
            j.processar_input(teclado_held, mouse, dt=0.016, limite_arena=(1600, 1200))

        # Slot e armas devem ser os mesmos — sem alternância
        self.assertEqual(j.slot_ativo, 3)
        self.assertIs(j.arma_especial, arma_original)
        self.assertIs(j.arma_especial_secundaria, secundaria_original)
        self.assertFalse(j.slot_especial_secundario_ativo)

    def test_novo_press_de_3_com_bios_modding_alterna_uma_vez(self):
        """
        Um novo press de tecla (key_down=True por exatamente 1 frame) deve
        alternar entre 3A e 3B exatamente uma vez.
        """
        j = self._fazer_jogador_com_bios_modding()
        arma_a = j.arma_especial
        arma_b = j.arma_especial_secundaria

        mouse = MockMouse()

        # Frame 1: tecla pressionada neste frame (key_down=True)
        teclado_press = MockKeyboard(pressed_keys=["3"], just_pressed_keys=["3"])
        j.processar_input(teclado_press, mouse, dt=0.016, limite_arena=(1600, 1200))

        # Deve ter alternado: arma_especial agora é a antiga secundária
        self.assertIs(j.arma_especial, arma_b)
        self.assertIs(j.arma_especial_secundaria, arma_a)
        self.assertTrue(j.slot_especial_secundario_ativo)

        # Frames 2–30: tecla ainda segurada mas key_down=False — NÃO deve alternar mais
        teclado_held = MockKeyboard(pressed_keys=["3"], just_pressed_keys=[])
        for _ in range(29):
            j.processar_input(teclado_held, mouse, dt=0.016, limite_arena=(1600, 1200))

        # Armas devem permanecer como estavam após o 1º frame
        self.assertIs(j.arma_especial, arma_b)
        self.assertIs(j.arma_especial_secundaria, arma_a)

    def test_selecionar_slot_1_e_2_com_key_down(self):
        """Slots 1 e 2 também respondem apenas a key_down, não a key_pressed contínuo."""
        j = Jogador(x=100.0, y=100.0)
        mouse = MockMouse()

        # Slot 2 é o padrão; vai para slot 1 via key_down
        teclado_press1 = MockKeyboard(just_pressed_keys=["1"])
        j.processar_input(teclado_press1, mouse, dt=0.016, limite_arena=(1600, 1200))
        self.assertEqual(j.slot_ativo, 1)

        # Segurar tecla 2 (key_pressed only) não deve mudar slot
        j.slot_ativo = 1
        teclado_held2 = MockKeyboard(pressed_keys=["2"], just_pressed_keys=[])
        j.processar_input(teclado_held2, mouse, dt=0.016, limite_arena=(1600, 1200))
        self.assertEqual(j.slot_ativo, 1)  # permanece em 1


if __name__ == "__main__":
    unittest.main()
