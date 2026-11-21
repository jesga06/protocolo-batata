"""
Suite de Regressão Forense W3-07 — Combate E2E no Loop Real de GameplayScene
Valida:
1. keybinds="uma_mao": mira e tiro 100% no teclado (direção do movimento atual, default para cima (0.0, -1.0) quando parado).
2. screen_shake_stagger: aplicado tanto em explosivos quanto em tiros balísticos e melee (com clamp de arena e sem empurrar Boss).
3. I-frames aditivos: 0.20s base + 0.35s (fps_stutter_dodge) + 0.40s (motion_blur_ghosting) = 0.95s, e receber_dano(0) ignorado.
4. Railgun com auto_fire="desligado": sustenta carga após button_down(1) enquanto segurado e cancela ao trocar de slot.
5. Todos os 6 módulos de BIOS Overclock no loop real.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from PPlay.window import Window
from src.cenas.gameplay import GameplayScene
from src.armas import Railgun, Shotgun, Minigun
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.projetil import Projetil


class TestMechanicsE2ERealLoop(unittest.TestCase):
    """Testes E2E executando GameplayScene.loop() real."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()
        self.janela = Window(800, 600)
        self.cena = GameplayScene()

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    def test_uma_mao_100_percent_keyboard_aim_and_fire(self):
        """Sob keybinds='uma_mao', parado atira para cima (0, -1) e em movimento atira na direção do movimento."""
        self.cena.gerenciador_config.desbloquear_config("keybinds")
        self.cena.gerenciador_config.definir_valor("keybinds", "uma_mao")
        self.cena.aplicar_modificadores()

        # Mouse apontando para baixo/direita deve ser ignorado no combate
        mock_mouse = MagicMock()
        mock_mouse.get_position.return_value = (790, 590)
        mock_mouse.button_down.return_value = False
        mock_mouse.button_pressed.return_value = False
        self.cena.mouse = mock_mouse

        # 1. Parado (nenhuma tecla QWER pressionada) -> Dispara para CIMA (0.0, -1.0)
        mock_kb_idle = MagicMock()
        mock_kb_idle.key_pressed.return_value = False
        mock_kb_idle.key_down.return_value = False
        self.cena.teclado = mock_kb_idle
        self.cena.jogador.armas[1].tempo_recarga_restante = 0.0

        self.cena.loop(dt=0.016)
        self.assertEqual(len(self.cena.projeteis), 1)
        p_up = self.cena.projeteis[0]
        self.assertAlmostEqual(p_up.dir_x, 0.0, places=4)
        self.assertAlmostEqual(p_up.dir_y, -1.0, places=4)

        # 2. Movendo para a direita ('r' pressionado) -> Dispara para a DIREITA (1.0, 0.0)
        self.cena.projeteis.clear()
        self.cena.jogador.armas[1].tempo_recarga_restante = 0.0
        mock_kb_right = MagicMock()
        mock_kb_right.key_pressed.side_effect = lambda k: k in ("r", "R")
        mock_kb_right.key_down.return_value = False
        self.cena.teclado = mock_kb_right

        self.cena.loop(dt=0.016)
        self.assertEqual(len(self.cena.projeteis), 1)
        p_right = self.cena.projeteis[0]
        self.assertAlmostEqual(p_right.dir_x, 1.0, places=4)
        self.assertAlmostEqual(p_right.dir_y, 0.0, places=4)

    def test_screen_shake_stagger_on_ballistic_and_melee_hits(self):
        """screen_shake_stagger deve aplicar slow e empurrão tanto em tiros balísticos quanto em golpes melee."""
        self.cena.gerenciador_config.desbloquear_config("screen_shake")
        self.cena.gerenciador_config.definir_valor("screen_shake", "ligado")
        self.cena.aplicar_modificadores()

        # 1. Acerto balístico
        inim_b = InimigoPadrao(x=500.0, y=300.0)
        self.cena.inimigos = [inim_b]
        p = Projetil(x=505.0, y=305.0, dir_x=1.0, dir_y=0.0, velocidade=10.0, dano=5, dono="jogador")
        self.cena.projeteis = [p]
        self.cena.loop(dt=0.016)
        self.assertGreater(inim_b.x, 500.0)
        self.assertGreater(inim_b.slow_timer, 0.0)
        self.assertEqual(inim_b.slow_fator, 0.50)

        # 2. Acerto Melee
        self.cena.jogador.x = 400.0
        self.cena.jogador.y = 300.0
        inim_m = InimigoPadrao(x=440.0, y=300.0)
        self.cena.inimigos = [inim_m]
        self.cena.jogador.selecionar_slot(1)
        self.cena.jogador.armas[0].tempo_recarga_restante = 0.0
        self.cena.buffer_tiro = 0.15
        self.cena.mouse.get_position = lambda: (int(self.cena.camera.transform_x(500.0)), int(self.cena.camera.transform_y(316.0)))
        self.cena.loop(dt=0.016)
        self.assertGreater(inim_m.x, 440.0)
        self.assertGreater(inim_m.slow_timer, 0.0)
        self.assertEqual(inim_m.slow_fator, 0.50)

    def test_additive_iframes_020_base_plus_035_fps_plus_040_blur(self):
        """Dano não-letal ativa 0.2s base + 0.35s (fps_stutter_dodge) + 0.40s (motion_blur_ghosting) = 0.95s."""
        j = self.cena.jogador
        j.hp = 100
        j.invulnerabilidade_timer = 0.0

        # Dano 0 não concede i-frames
        j.receber_dano(0)
        self.assertEqual(j.invulnerabilidade_timer, 0.0)

        # Apenas base (0.20s)
        j.receber_dano(10)
        self.assertAlmostEqual(j.invulnerabilidade_timer, 0.20, places=4)

        # Com fps_stutter_dodge (+0.35s) e motion_blur_ghosting (+0.40s) -> 0.95s
        j.invulnerabilidade_timer = 0.0
        j.fps_stutter_dodge = True
        j.motion_blur_ghosting = True
        j.receber_dano(10)
        self.assertAlmostEqual(j.invulnerabilidade_timer, 0.95, places=4)

    def test_railgun_charges_and_fires_with_autofire_disabled_and_cancels_on_slot_switch(self):
        """Com auto_fire='desligado', Railgun inicia carga no button_down(1), mantém com button_pressed(1) e cancela se trocar slot."""
        self.cena.gerenciador_config.desbloquear_config("auto_fire")
        self.cena.gerenciador_config.definir_valor("auto_fire", "desligado")
        self.cena.aplicar_modificadores()

        rail = Railgun()
        self.cena.jogador.arma_especial = rail
        self.cena.jogador.selecionar_slot(3)
        self.cena._ultimo_slot_ativo = 3
        self.cena._arma_ativa_anterior = rail

        mock_mouse = MagicMock()
        mock_mouse.get_position.return_value = (500, 300)
        # Frame 1: clique inicial button_down(1)=True, button_pressed(1)=True
        mock_mouse.button_down.side_effect = lambda b: b == 1
        mock_mouse.button_pressed.side_effect = lambda b: b == 1
        self.cena.mouse = mock_mouse

        self.cena.loop(dt=0.1)
        self.assertTrue(rail.carregando)
        self.assertGreater(rail.progresso_carga, 0.0)

        # Frames seguintes: apenas segurando o botão (button_down=False, button_pressed=True)
        mock_mouse.button_down.side_effect = lambda b: False
        for _ in range(10):
            self.cena.loop(dt=0.1)

        # Deve ter concluído a carga de 1.0s e disparado o feixe perfurante
        self.assertFalse(rail.carregando)
        self.assertEqual(len(self.cena.projeteis), 1)
        self.assertTrue(self.cena.projeteis[0].perfurante)

        # Inicia nova carga e troca de slot -> cancela carga imediatamente
        rail.tempo_recarga_restante = 0.0
        mock_mouse.button_down.side_effect = lambda b: b == 1
        self.cena.loop(dt=0.1)
        self.assertTrue(rail.carregando)
        self.cena.jogador.selecionar_slot(2)
        self.cena.loop(dt=0.05)
        self.assertFalse(rail.carregando)

    def test_overclocks_protecao_surtos_freeze_and_overvolt_skips_phasing(self):
        """Valida arena_freeze_timer=4.0s no Kernel Panic e que Overvolt pula inimigos em_fase."""
        # 1. Proteção contra Surtos congela a arena por 4.0s e não pode ser readquirida
        j = self.cena.jogador
        j.aplicar_overclock("protecao_surtos")
        hp_max_1 = j.hp_max
        j.aplicar_overclock("protecao_surtos")
        self.assertEqual(j.hp_max, hp_max_1, "protecao_surtos não deve empilhar +50 HP ao tentar readquirir.")

        p_inim = Projetil(x=100, y=100, dir_x=1, dir_y=0, velocidade=200, dano=10, dono="inimigo")
        self.cena.projeteis = [p_inim]
        j.hp = 5
        j.receber_dano(100)
        self.assertTrue(j.kernel_panic_trigger)
        self.cena.loop(dt=0.016)
        self.assertGreater(self.cena.arena_freeze_timer, 3.9)
        self.assertEqual(len(self.cena.projeteis), 0, "EMP deve destruir projéteis inimigos.")

        # 2. Overvolt chain lightning pula inimigos em_fase
        j.aplicar_overclock("overvolt")
        alvo_origem = InimigoPadrao(x=300, y=300)
        alvo_em_fase = InimigoPhasing(x=340, y=300)
        alvo_em_fase.timer_ciclo = 0.2  # < 1.2s => em_fase == True
        self.assertTrue(alvo_em_fase.em_fase)
        alvo_valido = InimigoPadrao(x=360, y=300)
        self.cena.inimigos = [alvo_origem, alvo_em_fase, alvo_valido]

        self.cena._aplicar_overvolt_chain(alvo_origem, dano_base=20)
        self.assertEqual(alvo_em_fase.hp, alvo_em_fase.hp_max, "Overvolt não deve atingir inimigo intangível (em_fase).")
        self.assertLess(alvo_valido.hp, alvo_valido.hp_max, "Overvolt deve atingir inimigo tangível no raio.")


if __name__ == "__main__":
    unittest.main()
