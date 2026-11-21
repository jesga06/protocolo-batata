"""
Testes Unitários — Condição de Vitória (10 Minutos), Pontuação Final e Estatísticas de Partida
Valida o disparo de vitória aos 600.0s, congelamento de horda e spawner,
cálculo exato de pontuação final e renderização do overlay de vitória sem emojis.
"""

import os
import tempfile
import unittest
from unittest.mock import patch
import pygame
from src.cenas.gameplay import GameplayScene
from src.entidades.inimigo_padrao import InimigoPadrao
from src.utils.constantes import TEMPO_VITORIA
from PPlay.window import Window


class TestVitoriaStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save_path = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save_path)
        self._p2 = patch("src.ui.modal_level_up.SAVE_FILE_PATH", self.temp_save_path)
        self._p3 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save_path)
        self._p1.start()
        self._p2.start()
        self._p3.start()
        self.janela = Window(800, 600)
        self.cena = GameplayScene()

    def tearDown(self):
        self._p3.stop()
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    def test_tempo_vitoria_constante(self):
        """Verifica se a constante TEMPO_VITORIA equivale a 600.0s (10 minutos)."""
        self.assertEqual(TEMPO_VITORIA, 600.0)

    def test_tempo_sobrevivencia_600s_nao_dispara_vitoria_automatica(self):
        """Valida que atingir 600.0s (10 min) NÃO dispara vitória automaticamente (vitória requer derrotar o boss)."""
        self.cena.tempo_sobrevivencia = 600.0
        self.cena.jogador.hp = 100
        self.assertFalse(self.cena.vitoria)

        # Adiciona inimigo com velocidade normal
        inimigo = InimigoPadrao(100, 100)
        self.cena.inimigos.append(inimigo)
        vel_inicial = inimigo.velocidade
        self.assertGreater(vel_inicial, 0.0)

        # Avança loop
        self.cena.loop()

        # Jogo continua ativo: NÃO venceu automaticamente aos 600s
        self.assertFalse(self.cena.vitoria)
        self.assertFalse(self.cena.partida_registrada)
        self.assertGreater(inimigo.velocidade, 0.0)

    def test_disparo_vitoria_explicita_congela_jogo(self):
        """Testa o disparo da sequência de vitória (ex: ao abater Geladeira Tsunami)."""
        self.cena.tempo_sobrevivencia = 600.0
        self.cena.jogador.hp = 100
        inimigo = InimigoPadrao(100, 100)
        self.cena.inimigos.append(inimigo)

        # Aciona vitória
        self.cena.vitoria = True
        self.cena._acionar_vitoria()

        self.assertTrue(self.cena.vitoria)
        self.assertTrue(self.cena.partida_registrada)
        self.assertEqual(inimigo.velocidade, 0.0)
        self.assertEqual(len(self.cena.projeteis), 0)



    def test_calculo_formula_pontuacao_final_derrota_e_vitoria(self):
        """Valida a fórmula matemática de cálculo da pontuação final."""
        # Caso 1: Derrota aos 300s, 50 abates (5000 pts), 2000 dano, 0 configs ativas
        self.cena.tempo_sobrevivencia = 300.0
        self.cena.pontos = 5000
        self.cena.dano_total_causado = 2000
        score_derrota, mult1 = self.cena._calcular_score_final(vitoria=False)

        # S_abates=5000, S_tempo=300*10=3000, S_dano=2000*0.5=1000, S_vit=0 => Total = 9000 * 1.0 = 9000
        self.assertEqual(score_derrota, 9000)
        self.assertEqual(mult1, 1.0)

        # Caso 2: Vitória aos 600s, 100 abates (10000 pts), 4000 dano, 2 configs punitivas ativas (+20%)
        self.cena.tempo_sobrevivencia = 600.0
        self.cena.pontos = 10000
        self.cena.dano_total_causado = 4000
        self.cena.gerenciador_config.desbloquear_config("fps_cap")
        self.cena.gerenciador_config.definir_valor("fps_cap", "30")  # Não-padrão (+10%)
        self.cena.gerenciador_config.desbloquear_config("screen_shake")
        self.cena.gerenciador_config.definir_valor("screen_shake", "ligado")  # Não-padrão (+10%)

        score_vitoria, mult2 = self.cena._calcular_score_final(vitoria=True)
        # S_abates=10000, S_tempo=6000, S_dano=2000, S_vit=10000 => Total = 28000 * 1.20 = 33600
        self.assertEqual(score_vitoria, 33600)
        self.assertAlmostEqual(mult2, 1.20)

    def test_renderizacao_overlay_vitoria_sem_excecao(self):
        """Valida que _desenhar_overlay_vitoria desenha todos os elementos sem exceções."""
        self.cena.tempo_sobrevivencia = 600.0
        self.cena.abates = 150
        self.cena.dano_total_causado = 12500
        self.cena.vitoria = True
        self.cena._acionar_vitoria()

        screen = self.janela.screen
        self.cena._desenhar_overlay_vitoria()
        self.assertIsNotNone(screen)

    def test_renderizacao_overlay_game_over_sem_excecao(self):
        """Valida que _desenhar_overlay_game_over desenha todos os elementos sem exceções."""
        self.cena.tempo_sobrevivencia = 240.0
        self.cena.abates = 45
        self.cena.dano_total_causado = 3400
        self.cena.game_over = True
        self.cena._registrar_fim_partida(vitoria=False)

        screen = self.janela.screen
        self.cena._desenhar_overlay_game_over()
        self.assertIsNotNone(screen)


if __name__ == "__main__":
    unittest.main()
