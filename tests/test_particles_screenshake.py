"""
Testes Unitários — Sistema de Partículas e Feedback Visual / Screen Shake
Valida emissão de faíscas, bursts de drop, ondas de choque, detritos,
teto máximo de partículas (MAX_PARTICULAS = 300) e controle de screen shake.
"""

import os
import unittest
import pygame
from src.sistemas.sistema_particulas import SistemaParticulas, Particula, OndaChoque
from src.sistemas.config_sistema import GerenciadorConfiguracoes


class TestParticlesScreenshake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def setUp(self):
        self.sistema = SistemaParticulas()

    def test_emissao_faiscas_impacto(self):
        """Testa emissão de faíscas balísticas com direção e quantidade."""
        self.sistema.emitir_faiscas(x=100.0, y=100.0, dir_x=1.0, dir_y=0.0, qtd=8)
        self.assertEqual(len(self.sistema.particulas), 8)

        # Avança o tempo e confirma que as partículas se movem
        p_inicial_x = self.sistema.particulas[0].x
        self.sistema.update(0.05)
        self.assertNotEqual(self.sistema.particulas[0].x, p_inicial_x)

    def test_emissao_bursts_drop(self):
        """Testa emissão de partículas de coleta para diferentes tipos de drops."""
        self.sistema.emitir_burst_drop(50.0, 50.0, tipo="xp")
        self.assertGreater(len(self.sistema.particulas), 0)
        cor_xp = self.sistema.particulas[0].cor
        self.assertEqual(cor_xp, (255, 215, 0))

        self.sistema.limpar()
        self.sistema.emitir_burst_drop(50.0, 50.0, tipo="cura")
        self.assertEqual(self.sistema.particulas[0].cor, (50, 230, 90))

        self.sistema.limpar()
        self.sistema.emitir_burst_drop(50.0, 50.0, tipo="arma")
        self.assertEqual(self.sistema.particulas[0].cor, (255, 140, 0))

        self.sistema.limpar()
        self.sistema.emitir_burst_drop(50.0, 50.0, tipo="equipamento")
        self.assertEqual(self.sistema.particulas[0].cor, (175, 75, 255))

    def test_emissao_onda_choque_e_debris(self):
        """Testa geração de onda de choque e fragmentos em explosões."""
        self.sistema.emitir_onda_choque(200.0, 200.0, raio_max=90.0)
        self.assertEqual(len(self.sistema.ondas_choque), 1)

        oc = self.sistema.ondas_choque[0]
        self.assertTrue(oc.viva)
        self.assertLess(oc.progresso, 0.1)

        # Avança tempo para expandir
        self.sistema.update(0.10)
        self.assertGreater(oc.obter_raio_atual(), 10.0)

        # Detritos
        self.sistema.emitir_debris(200.0, 200.0, qtd=10)
        self.assertEqual(len(self.sistema.particulas), 10)

    def test_expiracao_de_particulas_e_ondas(self):
        """Garante que partículas e ondas de choque mortas são removidas na atualização."""
        self.sistema.emitir_faiscas(0, 0, qtd=5)
        self.sistema.emitir_onda_choque(0, 0)
        self.assertEqual(len(self.sistema.particulas), 5)
        self.assertEqual(len(self.sistema.ondas_choque), 1)

        # Simula 1.0s de tempo (tempo suficiente para expirar tudo)
        self.sistema.update(1.0)
        self.assertEqual(len(self.sistema.particulas), 0)
        self.assertEqual(len(self.sistema.ondas_choque), 0)

    def test_teto_maximo_particulas(self):
        """Garante que o teto de 300 partículas é rigidamente respeitado."""
        for _ in range(100):
            self.sistema.emitir_faiscas(0, 0, qtd=10)

        self.assertLessEqual(len(self.sistema.particulas), SistemaParticulas.MAX_PARTICULAS)
        self.assertEqual(len(self.sistema.particulas), 300)

    def test_controle_screen_shake_config(self):
        """Valida que o tremor de tela obedece à configuração 5 'screen_shake'."""
        from src.cenas.gameplay import GameplayScene
        from PPlay.window import Window

        janela = Window(800, 600)
        cena = GameplayScene()

        # Por padrão, screen_shake está 'desligado'
        self.assertEqual(cena.gerenciador_config.obter_valor("screen_shake"), "desligado")
        cena.aplicar_shake(intensidade=10.0, duracao=0.25)
        self.assertEqual(cena.shake_timer, 0.0)
        self.assertEqual(cena.shake_intensidade, 0.0)

        # Desbloqueia e ativa screen_shake
        cena.gerenciador_config.desbloquear_config("screen_shake")
        cena.gerenciador_config.definir_valor("screen_shake", "ligado")
        self.assertEqual(cena.gerenciador_config.obter_valor("screen_shake"), "ligado")

        cena.aplicar_shake(intensidade=10.0, duracao=0.25)
        self.assertEqual(cena.shake_intensidade, 10.0)
        self.assertEqual(cena.shake_timer, 0.25)

        # Simula passagem de tempo no loop
        dt = 0.30
        if cena.shake_timer > 0.0:
            cena.shake_timer = max(0.0, cena.shake_timer - dt)
            if cena.shake_timer == 0.0:
                cena.shake_intensidade = 0.0

        self.assertEqual(cena.shake_timer, 0.0)
        self.assertEqual(cena.shake_intensidade, 0.0)


if __name__ == "__main__":
    unittest.main()
