"""
Testes Unitários de Drones Companheiros (Slot 4) — Protocolo: Batata
Valida DroneBase (física orbital, 30s de duração, fogo amigo), DroneCura (5 HP / 3s),
DroneCombate (mira no mais próximo dentro de 350px / 1s), DroneSuporte (+15% velocidade e atração magnética),
e ciclo de vida no Slot 4 sob multiplicadores de drop.
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

from src.equipamentos import DroneBase, DroneCura, DroneCombate, DroneSuporte
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.drop import ItemDrop
from src.sistemas.sistema_drops import SistemaDrops


class TestDroneBaseAndOrbitalPhysics(unittest.TestCase):
    """Testa a classe DroneBase, matemática orbital trigonométrica, tempo de vida e fogo amigo."""

    def setUp(self):
        self.jogador = Jogador(x=400.0, y=300.0)

    def test_drone_orbital_positioning_math(self):
        drone = DroneBase(raio_orbita=48.0, velocidade_angular=2.5, largura=24, altura=24)
        cx = self.jogador.x + self.jogador.largura / 2.0  # 416.0
        cy = self.jogador.y + self.jogador.altura / 2.0   # 316.0

        # Frame 0 (theta = 0.0) -> pos x = cx + 48 - 12 = 452.0, pos y = cy + 0 - 12 = 304.0
        drone.update(dt=0.0, jogador=self.jogador)
        self.assertAlmostEqual(drone.x, cx + 48.0 - 12.0)
        self.assertAlmostEqual(drone.y, cy - 12.0)

        # Avança tempo para theta = pi/2 (90 graus) -> dt = (pi/2) / 2.5
        dt_90 = (math.pi / 2.0) / 2.5
        drone.update(dt=dt_90, jogador=self.jogador)
        self.assertAlmostEqual(drone.x, cx - 12.0, places=3)
        self.assertAlmostEqual(drone.y, cy + 48.0 - 12.0, places=3)

    def test_drone_expiration_after_30s(self):
        drone = DroneBase(tempo_vida=30.0)
        self.assertTrue(drone.ativo)
        self.assertEqual(drone.tempo_restante, 30.0)

        # Avança 29.5s -> ainda ativo
        drone.update(dt=29.5, jogador=self.jogador)
        self.assertTrue(drone.ativo)

        # Avança mais 1.0s -> total 30.5s -> expirado
        drone.update(dt=1.0, jogador=self.jogador)
        self.assertFalse(drone.ativo)
        self.assertLessEqual(drone.tempo_restante, 0.0)

    def test_drone_friendly_fire_destruction(self):
        drone = DroneBase(hp=1)
        self.assertTrue(drone.ativo)
        self.assertEqual(drone.hp, 1)

        # Recebe 10 de dano -> destruição instantânea (1 HP)
        drone.receber_dano(10)
        self.assertEqual(drone.hp, 0)
        self.assertFalse(drone.ativo)


class TestDroneCura(unittest.TestCase):
    """Testa o Drone de Cura (restaura 5 HP a cada 3.0s até o teto de hp_max)."""

    def test_drone_cura_periodica_e_teto_hp_max(self):
        jogador = Jogador(x=400.0, y=300.0, hp_max=150)
        jogador.hp = 135  # Falta 15 HP para a vida máxima

        drone = DroneCura(intervalo_cura=3.0, valor_cura=5)

        # Avança 2.0s -> ainda não cura
        drone.update(dt=2.0, jogador=jogador)
        self.assertEqual(jogador.hp, 135)

        # Avança mais 1.0s (total 3.0s) -> primeiro pulso de cura (+5 HP -> 140)
        drone.update(dt=1.0, jogador=jogador)
        self.assertEqual(jogador.hp, 140)

        # Mais 3.0s -> segundo pulso (+5 HP -> 145)
        drone.update(dt=3.0, jogador=jogador)
        self.assertEqual(jogador.hp, 145)

        # Mais 3.0s -> terceiro pulso (+5 HP -> 150)
        drone.update(dt=3.0, jogador=jogador)
        self.assertEqual(jogador.hp, 150)

        # Mais 3.0s -> não ultrapassa o teto de hp_max
        drone.update(dt=3.0, jogador=jogador)
        self.assertEqual(jogador.hp, 150)


class TestDroneCombate(unittest.TestCase):
    """Testa o Drone de Combate (adquire o alvo mais próximo em 350px e dispara a cada 1.0s)."""

    def test_drone_combate_target_acquisition_and_shooting(self):
        jogador = Jogador(x=400.0, y=300.0)
        drone = DroneCombate(cooldown_tiro=1.0, alcance_deteccao=350.0, dano=8)
        drone.update(dt=0.0, jogador=jogador)

        # Inimigo 1: mais próximo (100px à direita)
        e1 = InimigoPadrao(x=516.0, y=316.0, hp=50)
        # Inimigo 2: intermediário (200px acima)
        e2 = InimigoPadrao(x=416.0, y=116.0, hp=50)
        # Inimigo 3: fora do alcance (500px de distância)
        e3 = InimigoPadrao(x=950.0, y=316.0, hp=50)

        inimigos = [e1, e2, e3]

        # Em 0.5s -> não atira ainda
        tiros_0 = drone.update(dt=0.5, jogador=jogador, inimigos=inimigos)
        self.assertEqual(len(tiros_0), 0)

        # Em 1.0s -> dispara exatamente contra e1 (mais próximo)
        tiros_1 = drone.update(dt=0.5, jogador=jogador, inimigos=inimigos)
        self.assertEqual(len(tiros_1), 1)
        proj = tiros_1[0]
        self.assertEqual(proj.dano, 8)
        self.assertEqual(proj.dono, "jogador")

        # Valida que o projétil aponta exatamente para o centro de e1
        from src.utils.math_utils import vetor_direcao
        d_cx = drone.x + drone.largura / 2.0
        d_cy = drone.y + drone.altura / 2.0
        e_cx = e1.x + e1.largura / 2.0
        e_cy = e1.y + e1.altura / 2.0
        exp_dx, exp_dy = vetor_direcao(d_cx, d_cy, e_cx, e_cy)

        self.assertAlmostEqual(proj.dir_x, exp_dx, places=4)
        self.assertAlmostEqual(proj.dir_y, exp_dy, places=4)

    def test_drone_combate_ignora_inimigos_fora_de_alcance(self):
        jogador = Jogador(x=400.0, y=300.0)
        drone = DroneCombate(cooldown_tiro=1.0, alcance_deteccao=350.0)
        drone.update(dt=0.0, jogador=jogador)

        # Apenas inimigo a 600px de distância
        e_longe = InimigoPadrao(x=1000.0, y=300.0)
        tiros = drone.update(dt=1.0, jogador=jogador, inimigos=[e_longe])
        self.assertEqual(len(tiros), 0)


class TestDroneSuporte(unittest.TestCase):
    """Testa o Drone de Suporte (+15% de velocidade e atração magnética em raio de 150px)."""

    def test_drone_suporte_speed_buff(self):
        jogador = Jogador(x=400.0, y=300.0, velocidade=200.0)
        drone = DroneSuporte(bonus_velocidade=0.15)
        jogador.drone = drone

        # Update do jogador com o drone ativo aplica +15% na velocidade
        jogador.update(dt=0.016)
        self.assertAlmostEqual(jogador.velocidade_atual, 230.0)

        # Se o drone for desativado/destruído, velocidade retorna para a base
        drone.ativo = False
        jogador.update(dt=0.016)
        self.assertIsNone(jogador.drone)
        self.assertAlmostEqual(jogador.velocidade_atual, 200.0)

    def test_drone_suporte_magnetic_drop_attraction(self):
        jogador = Jogador(x=400.0, y=300.0)  # centro (416, 316)
        drone = DroneSuporte(raio_magnetico=150.0, velocidade_magnetica=250.0)
        jogador.drone = drone

        # Drop 1: a 80px de distância (dentro do raio de 150px)
        drop_perto = ItemDrop(x=496.0, y=316.0 - 21.0, tipo="xp")
        # Drop 2: a 300px de distância (fora do raio magnético)
        drop_longe = ItemDrop(x=800.0, y=316.0 - 21.0, tipo="xp")
        drops = [drop_perto, drop_longe]

        pos_inicial_x_perto = drop_perto.x
        pos_inicial_x_longe = drop_longe.x

        # Avança 0.2s -> drop_perto é puxado em direção ao jogador (x diminui)
        drone.update(dt=0.2, jogador=jogador, drops=drops)

        self.assertLess(drop_perto.x, pos_inicial_x_perto)
        # Drop longe não se move
        self.assertEqual(drop_longe.x, pos_inicial_x_longe)


class TestSlot4EquipmentLifecycle(unittest.TestCase):
    """Testa a coleta de drop_equipamento, duração de 30s (ou 60s sob Config 15) e descarte."""

    def test_coleta_drop_equipamento_ativa_drone(self):
        jogador = Jogador(x=400.0, y=300.0)
        drops_sis = SistemaDrops()
        drop_eq = ItemDrop(x=400.0, y=300.0, tipo="equipamento")
        drops_sis.drops.append(drop_eq)

        eventos = drops_sis.coletar_jogador(jogador)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo"], "equipamento")
        self.assertIsNotNone(jogador.drone)
        self.assertIsInstance(jogador.drone, DroneBase)
        self.assertEqual(jogador.drone.tempo_vida, 30.0)

    def test_coleta_inimiga_config15_dobra_duracao_drone(self):
        jogador = Jogador(x=400.0, y=300.0)
        drops_sis = SistemaDrops()
        drop_eq = ItemDrop(x=400.0, y=300.0, tipo="equipamento")
        drops_sis.drops.append(drop_eq)

        # Com Config 15 (mult_valor_drop = 2.0), duração passa de 30s para 60s
        drops_sis.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertIsNotNone(jogador.drone)
        self.assertEqual(jogador.drone.tempo_vida, 60.0)
        self.assertEqual(jogador.drone.tempo_restante, 60.0)


if __name__ == "__main__":
    unittest.main()
