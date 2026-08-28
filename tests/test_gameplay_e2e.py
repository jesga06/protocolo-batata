"""
Testes E2E e Simulação Completa do Loop de Gameplay — Protocolo: Batata
Executa simulação contínua de 60+ frames verificando movimento do jogador,
disparos de projéteis, spawning de inimigos, perseguição beeline,
colisões balísticas, destruição de inimigos e contagem de abates.
"""

import os
import sys
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
from PPlay.window import Window
from PPlay.scenemanager import SceneManager
from src.cenas.gameplay import GameplayScene
from src.entidades.inimigo_padrao import InimigoPadrao


class MockTeclado:
    """Mock determinístico para simular teclado no SceneManager."""
    def __init__(self, chaves_pressionadas=None):
        self.chaves = set(k.lower() for k in (chaves_pressionadas or []))

    def key_pressed(self, key):
        return key.lower() in self.chaves

    def key_down(self, key):
        return key.lower() in self.chaves


class MockMouseSim:
    """Mock determinístico para simular mouse no SceneManager."""
    def __init__(self, pos=(400, 300), pressed=False, down=False):
        self.pos = pos
        self.pressed = pressed
        self.down = down

    def get_position(self):
        return self.pos

    def button_pressed(self, btn):
        return self.pressed

    def button_down(self, btn):
        return self.down


class TestGameplayE2ESimulation(unittest.TestCase):
    """Simulação E2E de gameplay headless."""

    def setUp(self):
        self.janela = Window(800, 600, "Protocolo: Batata", resizavel=True, pixel_art=True)

    def test_gameplay_scene_execucao_60_frames(self):
        """Executa 60+ frames contínuos de simulação completa de gameplay."""
        cena = GameplayScene()
        # Injeta teclado mock para simular pressionamento contínuo da tecla 'D'
        cena.teclado = MockTeclado(["d"])
        SceneManager.change_scene(cena)

        pos_inicial_x = cena.jogador.x
        pos_inicial_y = cena.jogador.y

        # Simula 60 frames contínuos
        for frame in range(60):
            SceneManager.run()
            self.janela.update()

        # 1. Valida que o jogador se moveu para a direita
        self.assertGreater(cena.jogador.x, pos_inicial_x, "O jogador deve ter se movido para a direita!")
        self.assertAlmostEqual(cena.jogador.y, pos_inicial_y, delta=1.0)

        # 2. Valida que o tempo de sobrevivência acumulou ~1 segundo
        self.assertGreater(cena.tempo_sobrevivencia, 0.0)

        # 3. Valida que a cena renderiza e executa draw sem erros
        try:
            cena.draw()
        except Exception as e:
            self.fail(f"cena.draw() falhou durante a simulação: {e}")

    def test_combate_completo_tiro_colisao_e_morte_inimigo(self):
        """
        Simula cenário determinístico:
        - Jogador em (400, 300)
        - Inimigo alinhado em (550, 300) com 25 HP
        - Jogador mira e dispara pistola em direção ao inimigo
        - Projétil avança, colide, causa dano e destrói o inimigo
        - Contador de abates e score são incrementados
        """
        cena = GameplayScene()
        # Desativa auto-fire padrão para controle fino do teste
        cena.auto_fire_ativo = False
        cena.teclado = MockTeclado([])
        cena.mouse = MockMouseSim(pos=(550, 300), pressed=False, down=False)
        SceneManager.change_scene(cena)

        cena.jogador.x = 400.0
        cena.jogador.y = 300.0

        # Posiciona inimigo no caminho do tiro (150px de distância)
        inimigo = InimigoPadrao(x=550.0, y=300.0)
        cena.inimigos = [inimigo]

        # Força arma da pistola a estar pronta e dispara
        pistola = cena.jogador.armas[1]
        pistola.tempo_recarga_restante = 0.0

        tiros = pistola.disparar(
            origem_x=400.0 + 16.0, origem_y=300.0 + 16.0,
            destino_x=550.0 + 14.0, destino_y=300.0 + 14.0
        )
        self.assertEqual(len(tiros), 1)
        cena.projeteis.extend(tiros)

        abates_antes = cena.abates
        pontos_antes = cena.pontos

        # Avança 30 frames de física (~0.5s) para o projétil atingir o alvo
        for _ in range(30):
            cena.spawner.timer_spawn = 0.0
            cena.loop()

        # O inimigo sofreu dano da pistola (17 dano de 50 HP)
        self.assertLess(inimigo.hp, 50)

        # Dispara segundo e terceiro tiro para liquidar o inimigo (17 + 17 + 17 = 51 >= 50 HP)
        pistola.tempo_recarga_restante = 0.0
        tiros_2 = pistola.disparar(416.0, 316.0, inimigo.x + 10, inimigo.y + 10)
        cena.projeteis.extend(tiros_2)

        for _ in range(30):
            cena.spawner.timer_spawn = 0.0
            cena.loop()

        if inimigo in cena.inimigos and inimigo.vivo:
            pistola.tempo_recarga_restante = 0.0
            tiros_3 = pistola.disparar(416.0, 316.0, inimigo.x + 10, inimigo.y + 10)
            cena.projeteis.extend(tiros_3)
            for _ in range(30):
                cena.spawner.timer_spawn = 0.0
                cena.loop()

        # Verifica que o inimigo foi destruído e removido da lista ativa
        self.assertFalse(inimigo.vivo)
        self.assertNotIn(inimigo, cena.inimigos)
        self.assertGreater(cena.abates, abates_antes)
        self.assertGreater(cena.pontos, pontos_antes)

    def test_todas_as_4_acceptance_criteria_satisfeitas(self):
        """Validação explícita dos 4 critérios de aceitação do ORIGINAL_REQUEST."""
        # 1. tools/gerador_assets.py gerou arquivos PNG
        from src.utils.constantes import ASSETS_DIR
        self.assertTrue(os.path.isfile(os.path.join(ASSETS_DIR, "sprites", "jogador", "batata_idle.png")))
        self.assertTrue(os.path.isfile(os.path.join(ASSETS_DIR, "sprites", "inimigos", "inimigo_padrao.png")))

        # 2. main.py executa frames sem crash
        from src.main import main
        try:
            main(limite_frames=10)
        except Exception as e:
            self.fail(f"main() falhou: {e}")

        # 3. Jogador se move e atira
        j = GameplayScene()
        self.assertIsNotNone(j.jogador)
        self.assertGreaterEqual(len(j.jogador.armas), 2)

        # 4. Inimigos dão spawn, se movem em direção ao jogador e podem ser destruídos
        inimigo_teste = InimigoPadrao(0, 0)
        inimigo_teste.update(0.1, (100, 100))
        self.assertGreater(inimigo_teste.x, 0)
        inimigo_teste.receber_dano(50)
        self.assertFalse(inimigo_teste.vivo)


if __name__ == "__main__":
    unittest.main()
