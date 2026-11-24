"""
Testes Unitários de Armas Especiais (Slot 3) — Protocolo: Batata
Valida Minigun, Shotgun, Rifle de Assalto, Lança-Foguetes, Lança-Granadas,
esgotamento de munição, descarte automático, troca para Slot 2 e modificadores da Config 5.
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

from src.armas import (
    ArmaBase, Pistola, Melee,
    Minigun, Shotgun, RifleAssalto,
    LancaFoguetes, LancaGranadas, Railgun
)
from src.entidades.projetil import Projetil
from src.equipamentos.drone_cura import DroneCura
from src.equipamentos.drone_combate import DroneCombate
from src.equipamentos.drone_suporte import DroneSuporte
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.drop import ItemDrop
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.config_sistema import GerenciadorConfiguracoes


class TestMinigun(unittest.TestCase):
    """Testa a Minigun (300 munições, 0.08s cooldown, dano 6, alta cadência)."""

    def test_minigun_inicializacao_e_atributos(self):
        m = Minigun()
        self.assertEqual(m.nome, "Minigun")
        self.assertEqual(m.dano, 6)
        self.assertEqual(m.cooldown, 0.08)
        self.assertEqual(m.municao_max, 300)
        self.assertEqual(m.municao_atual, 300)
        self.assertFalse(m.municao_infinita)
        self.assertEqual(m.slot, 3)

    def test_minigun_disparo_consumo_e_esgotamento(self):
        m = Minigun()
        # Dispara 300 vezes com update de cooldown entre disparos
        for i in range(300):
            self.assertTrue(m.pode_atirar())
            tiros = m.disparar(100.0, 100.0, 300.0, 100.0)
            self.assertEqual(len(tiros), 1)
            self.assertEqual(tiros[0].dano, 6)
            self.assertEqual(tiros[0].sprite_key, "projetil_minigun")
            self.assertEqual(m.municao_atual, 300 - (i + 1))
            m.update(0.08)

        # Munição zerada: não pode mais atirar
        self.assertEqual(m.municao_atual, 0)
        self.assertFalse(m.pode_atirar())
        tiros_bloqueados = m.disparar(100.0, 100.0, 300.0, 100.0)
        self.assertEqual(len(tiros_bloqueados), 0)


class TestShotgun(unittest.TestCase):
    """Testa a Escopeta (60 cartuchos, 0.70s cooldown, 9 pellets em leque de 0.45 rad, dano 10/pellet)."""

    def test_shotgun_inicializacao_e_atributos(self):
        s = Shotgun()
        self.assertEqual(s.nome, "Escopeta")
        self.assertEqual(s.dano, 10)
        self.assertEqual(s.cooldown, 0.70)
        self.assertEqual(s.municao_max, 60)
        self.assertEqual(s.municao_atual, 60)
        self.assertEqual(s.pellets, 9)
        self.assertAlmostEqual(s.spread_angulo, 0.45)

    def test_shotgun_disparo_9_pellets_simetricos(self):
        s = Shotgun()
        self.assertTrue(s.pode_atirar())

        # Disparo horizontal para a direita: (100, 100) -> (300, 100)
        tiros = s.disparar(100.0, 100.0, 300.0, 100.0)
        self.assertEqual(len(tiros), 9)
        self.assertEqual(s.municao_atual, 59)

        # Valida que todos os pellets têm dano 10 e sprite correto
        for proj in tiros:
            self.assertEqual(proj.dano, 10)
            self.assertEqual(proj.sprite_key, "projetil_shotgun")

        # Valida dispersão angular simétrica
        angulos = [math.atan2(p.dir_y, p.dir_x) for p in tiros]
        self.assertAlmostEqual(min(angulos), -0.225, places=3)
        self.assertAlmostEqual(max(angulos), 0.225, places=3)
        self.assertAlmostEqual(angulos[4], 0.0, places=3)


class TestRifleAssalto(unittest.TestCase):
    """Testa o Rifle de Assalto (120 tiros, 0.18s cooldown, dano 18, 650 px/s)."""

    def test_rifle_inicializacao_e_disparo_preciso(self):
        r = RifleAssalto()
        self.assertEqual(r.dano, 18)
        self.assertEqual(r.cooldown, 0.18)
        self.assertEqual(r.municao_max, 120)
        self.assertEqual(r.municao_atual, 120)

        tiros = r.disparar(100.0, 200.0, 500.0, 200.0)
        self.assertEqual(len(tiros), 1)
        proj = tiros[0]
        self.assertEqual(proj.dano, 18)
        self.assertEqual(proj.velocidade, 650.0)
        self.assertEqual(proj.sprite_key, "projetil_rifle")
        self.assertAlmostEqual(proj.dir_x, 1.0)
        self.assertAlmostEqual(proj.dir_y, 0.0)


class TestArmasExplosivas(unittest.TestCase):
    """Testa Lança-Foguetes e Lança-Granadas com dano em área (AoE) e multiplicadores."""

    def test_lanca_foguetes_aoe_detonacao(self):
        foguetes = LancaFoguetes()
        self.assertEqual(foguetes.dano, 60)
        self.assertEqual(foguetes.raio_explosao, 80.0)
        self.assertEqual(foguetes.municao_max, 24)

        tiros = foguetes.disparar(100.0, 100.0, 300.0, 100.0)
        self.assertEqual(len(tiros), 1)
        proj = tiros[0]
        self.assertTrue(proj.explosivo)
        self.assertEqual(proj.raio_explosao, 80.0)

        # Testa detonação AoE contra 3 inimigos
        e1 = InimigoPadrao(x=120.0, y=100.0, hp=50)   # 20px de distância (dentro de 80px)
        e2 = InimigoPadrao(x=150.0, y=100.0, hp=50)   # 50px de distância (dentro de 80px)
        e3 = InimigoPadrao(x=350.0, y=100.0, hp=50)   # 250px de distância (fora de 80px)

        afetados = proj.explodir([e1, e2, e3])
        self.assertEqual(len(afetados), 2)
        self.assertIn(e1, afetados)
        self.assertIn(e2, afetados)
        self.assertNotIn(e3, afetados)
        self.assertFalse(e1.vivo)
        self.assertFalse(e2.vivo)
        self.assertEqual(e3.hp, 50)

    def test_lanca_granadas_aoe_e_config5_scaling(self):
        granadas = LancaGranadas()
        self.assertEqual(granadas.dano, 45)
        self.assertEqual(granadas.raio_explosao, 65.0)
        self.assertEqual(granadas.municao_max, 32)

        tiros = granadas.disparar(100.0, 100.0, 200.0, 100.0)
        proj = tiros[0]
        self.assertTrue(proj.explosivo)

        # Com Config 5 ativa (Tremor de Tela), dano de explosivos tem +20% (45 * 1.20 = 54)
        e = InimigoPadrao(x=130.0, y=100.0, hp=100)
        proj.explodir([e], mult_dano_explosivo=1.20)
        self.assertEqual(e.hp, 100 - 54)  # 46 HP restante


class TestSlot3LifecycleAndAmmoDepletion(unittest.TestCase):
    """Testa coleta de drop de arma, equip no Slot 3, dobro de munição sob Config 15 e auto-swap ao zerar."""

    def setUp(self):
        self.jogador = Jogador(x=400.0, y=300.0)
        self.sistema_drops = SistemaDrops()

    def test_coleta_drop_arma_equipa_slot_3(self):
        drop = ItemDrop(x=400.0, y=300.0, tipo="arma")
        self.sistema_drops.drops.append(drop)

        eventos = self.sistema_drops.coletar_jogador(self.jogador)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo"], "arma")
        self.assertIsNotNone(self.jogador.arma_especial)
        self.assertEqual(self.jogador.slot_ativo, 3)
        self.assertIsInstance(self.jogador.obter_arma_ativa(), ArmaBase)

    def test_coleta_inimiga_config15_dobra_municao(self):
        drop = ItemDrop(x=400.0, y=300.0, tipo="arma")
        self.sistema_drops.drops.append(drop)

        # Config 15 ativa: mult_valor_drop = 2.0
        self.sistema_drops.coletar_jogador(self.jogador, mult_valor_drop=2.0)
        arma = self.jogador.arma_especial
        self.assertIsNotNone(arma)
        # Se for minigun: 300 * 2 = 600; se railgun: 10 * 2 = 20, etc.
        self.assertGreaterEqual(arma.municao_atual, 20)
        self.assertEqual(arma.municao_atual, arma.municao_max)

    def test_esgotamento_de_municao_auto_swap_para_slot_2(self):
        # Equipa arma com apenas 1 munição
        arma = Minigun(municao_max=1)
        self.jogador.arma_especial = arma
        self.jogador.selecionar_slot(3)
        self.assertEqual(self.jogador.slot_ativo, 3)

        # Dispara o último tiro
        arma.disparar(400.0, 300.0, 500.0, 300.0)
        self.assertEqual(arma.municao_atual, 0)

        # Update do jogador deve detectar munição zero, descartar a arma e retornar ao Slot 2 (Pistola)
        self.jogador.update(dt=0.016)
        self.assertIsNone(self.jogador.arma_especial)
        self.assertEqual(self.jogador.slot_ativo, 2)
        self.assertIsInstance(self.jogador.obter_arma_ativa(), Pistola)

    def test_parry_melee_reflete_projetil_inimigo(self):
        """Valida que Melee.rebater_projeteis rebate projétil inimigo aumentando velocidade e dano em 2.5x."""
        melee = Melee()
        proj_inimigo = Projetil(
            x=430.0,
            y=300.0,
            dir_x=-1.0,
            dir_y=0.0,
            velocidade=200.0,
            dano=10,
            dono="inimigo"
        )
        proj_inimigo.ativo = True

        rebatidos = melee.rebater_projeteis(
            origem_x=400.0,
            origem_y=300.0,
            lista_projeteis=[proj_inimigo],
            mira_x=500.0,
            mira_y=300.0
        )
        self.assertEqual(len(rebatidos), 1)
        p = rebatidos[0]
        self.assertEqual(p.dono, "jogador")
        self.assertTrue(p.parried)
        self.assertEqual(p.dano, 25)  # 10 * 2.5 = 25
        self.assertGreaterEqual(p.velocidade, 320.0)

    def test_fusao_drones_mk_progression(self):
        """Valida a progressão MK dos drones (MK-I -> MK-II -> MK-III) ao adicionar repetidos."""
        jog = self.jogador
        d1 = DroneCombate()
        self.assertEqual(d1.nivel_mk, 1)

        jog.adicionar_drone(d1)
        self.assertEqual(len(jog.drones), 1)
        self.assertEqual(jog.drones[0].nivel_mk, 1)

        # Adiciona segundo drone combate: deve evoluir para MK-II
        d2 = DroneCombate()
        jog.adicionar_drone(d2)
        self.assertEqual(len(jog.drones), 1)
        self.assertEqual(jog.drones[0].nivel_mk, 2)

        # Adiciona terceiro drone combate: deve evoluir para MK-III
        d3 = DroneCombate()
        jog.adicionar_drone(d3)
        self.assertEqual(len(jog.drones), 1)
        self.assertEqual(jog.drones[0].nivel_mk, 3)

        # Adiciona quarto: satura em MK-III
        d4 = DroneCombate()
        jog.adicionar_drone(d4)
        self.assertEqual(len(jog.drones), 1)
        self.assertEqual(jog.drones[0].nivel_mk, 3)

    def test_imas_nao_puxam_capsulas_powerup(self):
        """Valida que nem aplicar_pulso_magnetico nem DroneSuporte atraem capsula_powerup."""
        from src.equipamentos.drone_suporte import DroneSuporte
        cap = ItemDrop(x=500.0, y=300.0, tipo="capsula_powerup", subtipo="cura")
        gema = ItemDrop(x=480.0, y=300.0, tipo="xp", valor=5)
        self.jogador.aplicar_pulso_magnetico([cap, gema])
        self.assertEqual(cap.x, 500.0)
        self.assertNotEqual(gema.x, 480.0)

        drone_sup = DroneSuporte()
        gema2 = ItemDrop(x=470.0, y=300.0, tipo="xp", valor=5)
        drone_sup.update(0.1, jogador=self.jogador, drops=[cap, gema2])
        self.assertEqual(cap.x, 500.0)
        self.assertLess(gema2.x, 470.0)


if __name__ == "__main__":
    unittest.main()
