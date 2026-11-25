"""
Testes de Validação das Correções de Requisitos (RF2/5, RF2/6, RF2/7, RF3/5, RF4/5, RF4/7 e HUD FPS).
"""

import unittest
import math
import pygame
from src.entidades.projetil import Projetil
from src.armas.lanca_foguetes import LancaFoguetes
from src.armas.lanca_granadas import LancaGranadas
from src.armas.railgun import Railgun
from src.entidades.jogador import Jogador
from src.entidades.inimigo_ranged import InimigoRanged
from src.equipamentos.drone_cura import DroneCura
from src.sistemas.sistema_spawn import SistemaSpawn
from src.cenas.gameplay import GameplayScene


class TestRFFixesValidation(unittest.TestCase):
    """Validações pontuais para cada um dos itens de requisitos refinados."""

    @classmethod
    def setUpClass(cls):
        if not pygame.get_init():
            pygame.init()

    def test_rf2_5_rocket_sprite_rotation_angles(self):
        """RF2/5: Projétil do Lança-Foguetes calcula a rotação correta baseada no vetor de tiro."""
        arma = LancaFoguetes()
        # Disparo para a direita
        tiros_dir = arma.disparar(100.0, 100.0, 200.0, 100.0)
        self.assertEqual(len(tiros_dir), 1)
        p_dir = tiros_dir[0]
        ang_dir = -math.degrees(math.atan2(p_dir.dir_y, p_dir.dir_x))
        self.assertAlmostEqual(ang_dir, 0.0, places=2)

        # Disparo para cima (0, -1) -> 90 graus
        arma.tempo_recarga_restante = 0.0
        tiros_cima = arma.disparar(100.0, 100.0, 100.0, 0.0)
        self.assertEqual(len(tiros_cima), 1)
        p_cima = tiros_cima[0]
        ang_cima = -math.degrees(math.atan2(p_cima.dir_y, p_cima.dir_x))
        self.assertAlmostEqual(ang_cima, 90.0, places=2)

    def test_rf2_6_grenade_trajectory_and_detonation(self):
        """RF2/6: Granada desacelera até parar e detona em 1.0s."""
        arma = LancaGranadas()
        tiros = arma.disparar(0.0, 0.0, 100.0, 0.0)
        self.assertEqual(len(tiros), 1)
        granada = tiros[0]
        self.assertEqual(granada.tempo_vida, 1.0)
        self.assertGreater(granada.desaceleracao, 0.0)

        # Avança 0.5s -> Velocidade cai pela metade
        vel_inicial = granada.velocidade
        granada.update(0.5)
        self.assertAlmostEqual(granada.velocidade, vel_inicial * 0.5, delta=1.0)
        self.assertTrue(granada.ativo)

        # Avança mais 0.5s (total 1.0s) -> Para completamente e expira marcando detonação
        granada.update(0.5)
        self.assertEqual(granada.velocidade, 0.0)
        self.assertFalse(granada.ativo)
        self.assertTrue(granada.requer_detonacao_ao_expirar)

    def test_rf2_7_railgun_instant_hitscan_v2_port(self):
        """RF2/7 (Port v2): Railgun dispara instantaneamente sem carga com stats da v2 (165 dano, 10 cargas, 0.95s cd)."""
        railgun = Railgun()
        self.assertEqual(railgun.dano, 165)
        self.assertEqual(railgun.municao_max, 10)
        self.assertAlmostEqual(railgun.cooldown, 0.95, places=2)
        self.assertEqual(railgun.icone_asset, "arma_railgun")

        feixe = railgun.disparar_feixe(100.0, 100.0, 500.0, 100.0)
        self.assertIsNotNone(feixe)
        self.assertEqual(feixe["dano"], 165)
        self.assertAlmostEqual(feixe["x2"], 1900.0, places=1)
        self.assertEqual(railgun.municao_atual, 9)

    def test_rf3_5_railgun_destroys_drone_under_friendly_fire(self):
        """RF3/5: Projétil perfurante da Railgun destrói drones orbitando o jogador com Fogo Amigo."""
        cena = GameplayScene()
        cena.gerenciador_config.desbloquear_config("fogo_amigo")
        cena.gerenciador_config.definir_valor("fogo_amigo", "ligado")
        cena.aplicar_modificadores()

        # Equipa drone de cura (1 HP sob fogo amigo)
        drone = DroneCura()
        drone.hp = 1
        drone.velocidade_orbita = 0.0
        cena.jogador.drones = [drone]
        cena.jogador.update(0.016, None)

        # Dispara feixe da Railgun alinhado à órbita do drone
        tiro_railgun = Projetil(
            x=drone.x - 2, y=drone.y - 2,
            dir_x=1.0, dir_y=0.0,
            velocidade=100.0,
            dano=50,
            dono="jogador",
            perfurante=True
        )
        tiro_railgun.largura = 30.0
        tiro_railgun.altura = 30.0
        cena.projeteis = [tiro_railgun]

        # Executa ciclo de colisão
        cena.loop()

        self.assertEqual(drone.hp, 0)
        self.assertFalse(drone.ativo)

    def test_extra_safe_shooting_while_moving_forward(self):
        """Extra Crítico: Disparar enquanto a batata se move para a frente NÃO causa auto-dano imediato."""
        cena = GameplayScene()
        cena.gerenciador_config.desbloquear_config("fogo_amigo")
        cena.gerenciador_config.definir_valor("fogo_amigo", "ligado")
        cena.aplicar_modificadores()

        hp_inicial = cena.jogador.hp

        # Jogador movendo-se a 200px/s para a direita
        cena.jogador.x = 400.0
        cena.jogador.y = 300.0

        # Dispara para a direita
        tiros = cena.jogador.armas[1].disparar(
            origem_x=cena.jogador.x + 24.0,
            origem_y=cena.jogador.y + 16.0,
            destino_x=cena.jogador.x + 100.0,
            destino_y=cena.jogador.y + 16.0
        )
        cena.projeteis.extend(tiros)

        # Move jogador para a direita no mesmo frame
        cena.jogador.x += 10.0
        cena.loop()

        # O jogador NÃO tomou auto-dano no primeiro frame
        self.assertEqual(cena.jogador.hp, hp_inicial)

    def test_rf4_5_inimigo_ranged_lead_targeting_on_moving_target(self):
        """RF4/5: Inimigo Ranged compensa a velocidade do alvo ao atirar em jogador em movimento."""
        inimigo = InimigoRanged(x=0.0, y=0.0)
        # Alvo em (100, 21) alinhado ao centro Y do inimigo, movendo-se com vy = 150 px/s
        proj = inimigo.disparar(pos_alvo=(100.0, 21.0), vel_alvo=(0.0, 150.0))
        # O tiro deve ter componente Y positivo (mirando à frente da trajetória)
        self.assertGreater(proj.dir_y, 0.0)

    def test_rf4_7_boss_schedule_at_2_30_intervals(self):
        """RF4/7: Chefes surgem aos 60s (1:00), 120s (2:00), 180s (3:00) e 240s (4:00)."""
        spawner = SistemaSpawn()
        elites = []

        for t in range(1, 600):
            novos = spawner.update(
                dt=1.0,
                camera_x=0.0, camera_y=0.0,
                total_inimigos_vivos=0
            )
            for inim in novos:
                if getattr(inim, "is_elite", False):
                    elites.append((t, inim))

        self.assertEqual(len(elites), 4)
        tempos = [e[0] for e in elites]
        self.assertEqual(tempos, [60, 120, 180, 240])


if __name__ == "__main__":
    unittest.main()
