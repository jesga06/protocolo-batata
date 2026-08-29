"""
Testes Unitários — Mini-Bosses Elites, Agendamento de Ondas, Drops Garantidos e HUD de Boss
Valida o escalonamento 3x HP, 10x pontuação e 50 XP dos inimigos elites,
o disparo a cada 60s do spawner, os drops em anel e a barra de vida dedicada.
"""

import os
import unittest
import pygame
from src.entidades.inimigo_base import InimigoBase
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_tank import InimigoTank
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_drops import SistemaDrops
from src.ui.hud import HUD


class TestEliteBossesAndWaves(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def test_escalonamento_atributos_elite(self):
        """Valida que instâncias com is_elite=True multiplicam HP por 3, score por 10 e fixam XP em 50."""
        inim_normal = InimigoPadrao(0, 0)
        inim_elite = InimigoPadrao(0, 0, is_elite=True, nome_elite="MINI-BOSS: ESTAGIÁRIO SÊNIOR")

        self.assertEqual(inim_normal.hp, 40)
        self.assertEqual(inim_normal.hp_max, 40)
        self.assertEqual(inim_normal.score_valor, 100)
        self.assertEqual(inim_normal.xp_valor, 5)

        self.assertTrue(inim_elite.is_elite)
        self.assertEqual(inim_elite.hp, 120)
        self.assertEqual(inim_elite.hp_max, 120)
        self.assertEqual(inim_elite.score_valor, 1000)
        self.assertEqual(inim_elite.xp_valor, 50)
        self.assertEqual(inim_elite.nome_elite, "MINI-BOSS: ESTAGIÁRIO SÊNIOR")

    def test_tank_elite_stats(self):
        """Valida escalonamento específico do Tank Elite (360 HP, 3000 pts)."""
        tank_normal = InimigoTank(0, 0)
        tank_elite = InimigoTank(0, 0, is_elite=True, nome_elite="MINI-BOSS: GELADEIRA INDUSTRIAL TURBO")

        self.assertEqual(tank_normal.hp, 120)
        self.assertEqual(tank_elite.hp, 360)
        self.assertEqual(tank_elite.hp_max, 360)
        self.assertEqual(tank_elite.score_valor, 3000)
        self.assertEqual(tank_elite.xp_valor, 50)

    def test_agendamento_spawner_elites_a_cada_60s(self):
        """Valida que o SistemaSpawn gera exatamente um Mini-Boss a cada marca de 60s."""
        spawner = SistemaSpawn()

        # Avança até 59.5s -> Nenhum elite
        spawner.update(59.5, camera_x=0, camera_y=0, total_inimigos_vivos=0)
        self.assertEqual(spawner.ultimo_minuto_elite, 0)

        # Avança 1.0s atingindo 60.5s -> Spawna 1 Mini-Boss Elite do minuto 1
        novos = spawner.update(1.0, camera_x=0, camera_y=0, total_inimigos_vivos=0)
        elites = [e for e in novos if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites), 1)
        self.assertEqual(spawner.ultimo_minuto_elite, 1)
        self.assertIn("ESTAGIÁRIO SÊNIOR", elites[0].nome_elite)

        # Avança mais 10s no minuto 1 -> Não gera outro elite no mesmo minuto
        novos_depois = spawner.update(10.0, camera_x=0, camera_y=0, total_inimigos_vivos=len(novos))
        elites_depois = [e for e in novos_depois if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites_depois), 0)

        # Avança até 120.5s (Minuto 2) -> Spawna Mini-Boss do minuto 2 (Geladeira Turbo)
        novos_m2 = spawner.update(50.0, camera_x=0, camera_y=0, total_inimigos_vivos=len(novos))
        elites_m2 = [e for e in novos_m2 if getattr(e, "is_elite", False)]
        self.assertEqual(len(elites_m2), 1)
        self.assertEqual(spawner.ultimo_minuto_elite, 2)
        self.assertIn("GELADEIRA INDUSTRIAL TURBO", elites_m2[0].nome_elite)

    def test_drops_garantidos_elite(self):
        """Valida que a morte de um elite gera +50 XP (5 gemas de 10 XP), 1 caixa de arma e 1 de equipamento."""
        sistema_drops = SistemaDrops()
        drops_gerados = sistema_drops.gerar_drop_morte_inimigo(
            x=200.0,
            y=200.0,
            is_elite=True
        )

        xp_drops = [d for d in drops_gerados if d.tipo == "xp"]
        arma_drops = [d for d in drops_gerados if d.tipo == "arma"]
        equip_drops = [d for d in drops_gerados if d.tipo == "equipamento"]

        self.assertEqual(len(xp_drops), 5)
        total_xp = sum(d.valor for d in xp_drops)
        self.assertEqual(total_xp, 50)

        self.assertEqual(len(arma_drops), 1)
        self.assertEqual(len(equip_drops), 1)

    def test_hud_barra_boss_rendering(self):
        """Valida renderização sem exceções da barra de boss para 100%, 50% e 0% HP."""
        hud = HUD()
        screen = pygame.Surface((800, 600))
        boss = InimigoTank(100, 100, is_elite=True, nome_elite="MINI-BOSS: GELADEIRA TESTE")

        # 100% HP
        hud.desenhar_barra_boss(screen, boss, visivel=True)

        # 50% HP
        boss.hp = 180
        hud.desenhar_barra_boss(screen, boss, visivel=True)

        # 0% HP
        boss.hp = 0
        hud.desenhar_barra_boss(screen, boss, visivel=True)

        # Invisível / Morto
        boss.vivo = False
        hud.desenhar_barra_boss(screen, boss, visivel=False)


if __name__ == "__main__":
    unittest.main()
