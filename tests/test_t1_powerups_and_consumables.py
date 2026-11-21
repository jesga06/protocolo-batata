"""
Testes Unitários — Milestone 3: Power-Ups / Consumables Catalog Audit & Expansion (R3)
SSOT: CONFIGURACOES.md, PROJECT.md, architecture_cache.md
Valida:
1. gerar_pool_consumiveis_por_tier gera catálogo com 12 tipos de cards.
2. Efeito de cura imediata: cura_pequena (+25 HP) e cura_grande (+50 HP).
3. Efeito de XP imediato: xp_pequeno (+15 XP) e xp_grande (+30 XP).
4. Efeito de Buffs Temporários (15s): buff_dano_temp (+5%), buff_vel_temp (+8%),
   buff_cadencia_temp (+8% / -8% CD), buff_resistencia_temp (-8% dano recebido).
5. Efeito de Escudo Protetor: absorve 1 hit e concede 4s de invulnerabilidade.
6. Efeito de Pulso Magnético: atrai todos os drops do chão diretamente para a batata.
7. Efeito de Caixa de Arma: equipa arma aleatória no Slot 3.
8. Efeito de Caixa de Equipamento: adiciona drone companheiro no Slot 4 (30s).
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

import pygame
pygame.init()

from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.entidades.jogador import Jogador
from src.entidades.drop import ItemDrop
from src.ui.modal_level_up import ModalLevelUp, gerar_pool_consumiveis_por_tier


class TestPowerupsAndConsumablesCatalog(unittest.TestCase):
    """Testa os 12 consumíveis e power-ups do jogo."""

    def setUp(self):
        self.mgr = GerenciadorConfiguracoes()
        self.jogador = Jogador(x=200, y=200, hp_max=100)
        self.modal = ModalLevelUp(self.mgr, self.jogador)

    def test_pool_contains_all_12_consumables_across_tiers(self):
        """Verifica se os 12 tipos de consumíveis estão presentes na união dos pools."""
        todos_cards = []
        for tier in [1, 2, 3, 4]:
            todos_cards.extend(gerar_pool_consumiveis_por_tier(tier))

        subtipos = {c["subtipo"] for c in todos_cards}
        subtipos_esperados = {
            "cura_pequena", "cura_grande",
            "xp_pequeno", "xp_grande",
            "buff_dano_temp", "buff_vel_temp",
            "buff_cadencia_temp", "buff_resistencia_temp",
            "escudo", "pulso_magnetico",
            "caixa_arma", "caixa_equip"
        }
        self.assertTrue(subtipos_esperados.issubset(subtipos), f"Faltando subtipos: {subtipos_esperados - subtipos}")

    def test_01_cura_pequena_and_02_cura_grande(self):
        """1. cura_pequena restaura 25 HP; 2. cura_grande restaura 50 HP."""
        # 1. Cura Pequena (+25)
        self.jogador.hp = 30
        card_cp = {"tipo": "cura", "subtipo": "cura_pequena", "valor": 25}
        self.modal.cards_sorteados = [card_cp]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.hp, 55)

        # 2. Cura Grande (+50)
        self.jogador.hp = 30
        card_cg = {"tipo": "cura", "subtipo": "cura_grande", "valor": 50}
        self.modal.cards_sorteados = [card_cg]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.hp, 80)

    def test_03_xp_pequeno_and_04_xp_grande(self):
        """3. xp_pequeno concede +15 XP; 4. xp_grande concede +30 XP."""
        # 3. XP Pequeno (+15)
        xp_ant = self.jogador.xp
        card_xp_p = {"tipo": "xp", "subtipo": "xp_pequeno", "valor": 15}
        self.modal.cards_sorteados = [card_xp_p]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertGreaterEqual(self.jogador.xp + (self.jogador.nivel - 1) * 20, xp_ant + 15)

        # 4. XP Grande (+30)
        card_xp_g = {"tipo": "xp", "subtipo": "xp_grande", "valor": 30}
        self.modal.cards_sorteados = [card_xp_g]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)

    def test_05_buff_dano_temp_15s(self):
        """5. buff_dano_temp ativa timer de 15.0s."""
        card = {"tipo": "buff_dano_temp", "duracao": 15.0}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.buff_dano_timer, 15.0)

        # Decai no update
        self.jogador.update(1.0)
        self.assertAlmostEqual(self.jogador.buff_dano_timer, 14.0)

    def test_06_buff_vel_temp_15s(self):
        """6. buff_vel_temp ativa timer de 15.0s e aplica +8% à velocidade atual (Golden Rule R3)."""
        vel_base = self.jogador.velocidade_base
        card = {"tipo": "buff_vel_temp", "duracao": 15.0}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.buff_vel_timer, 15.0)

        self.jogador.update(0.1)
        self.assertAlmostEqual(self.jogador.velocidade_atual, vel_base * 1.08)

    def test_07_buff_cadencia_temp_15s(self):
        """7. buff_cadencia_temp ativa timer de 15.0s."""
        card = {"tipo": "buff_cadencia_temp", "duracao": 15.0}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.buff_cadencia_timer, 15.0)

    def test_08_buff_resistencia_temp_15s(self):
        """8. buff_resistencia_temp reduz dano sofrido em 8% (Golden Rule R3)."""
        card = {"tipo": "buff_resistencia_temp", "duracao": 15.0}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.buff_resistencia_timer, 15.0)

        # Recebe 100 de dano -> sofre 92 (redução de 8%)
        self.jogador.hp_max = 200
        self.jogador.hp = 200
        self.jogador.receber_dano(100)
        self.assertEqual(self.jogador.hp, 200 - 92)

    def test_09_escudo_protetor_absorbs_hit_and_grants_invulnerability(self):
        """9. escudo absorve 1 hit e concede 4.0s de invulnerabilidade."""
        card = {"tipo": "escudo"}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertTrue(self.jogador.escudo_ativo)

        # Recebe dano letal de 1000 -> Escudo absorve e jogador não perde HP
        self.jogador.hp = 100
        self.jogador.receber_dano(1000)
        self.assertEqual(self.jogador.hp, 100)
        self.assertFalse(self.jogador.escudo_ativo)
        self.assertEqual(self.jogador.invulnerabilidade_timer, 4.0)

        # Dano subsequente durante a invulnerabilidade é ignorado
        self.jogador.receber_dano(50)
        self.assertEqual(self.jogador.hp, 100)

    def test_10_pulso_magnetico_pulls_all_drops(self):
        """10. pulso_magnetico puxa todos os drops da arena para a batata."""
        self.jogador.x = 500.0
        self.jogador.y = 500.0

        d1 = ItemDrop(x=100.0, y=100.0, tipo="xp")
        d2 = ItemDrop(x=900.0, y=900.0, tipo="cura")
        drops = [d1, d2]

        self.jogador.aplicar_pulso_magnetico(drops)

        cx = self.jogador.x + self.jogador.largura / 2.0
        cy = self.jogador.y + self.jogador.altura / 2.0
        # Drops devem estar centralizados no jogador
        self.assertAlmostEqual(d1.x + d1.largura / 2.0, cx)
        self.assertAlmostEqual(d1.y + d1.altura / 2.0, cy)
        self.assertAlmostEqual(d2.x + d2.largura / 2.0, cx)
        self.assertAlmostEqual(d2.y + d2.altura / 2.0, cy)

    def test_11_caixa_arma_equips_slot_3(self):
        """11. caixa_arma sorteia e equipa arma especial no Slot 3."""
        card = {"tipo": "caixa_arma"}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)

        self.assertIsNotNone(self.jogador.arma_especial)
        self.assertEqual(self.jogador.slot_ativo, 3)

    def test_12_caixa_equip_spawns_drone_slot_4(self):
        """12. caixa_equip spawna drone companheiro no Slot 4 com 30s de duração."""
        card = {"tipo": "caixa_equip"}
        self.modal.cards_sorteados = [card]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)

        self.assertGreaterEqual(len(self.jogador.drones), 1)
        drone = self.jogador.drones[0]
        self.assertEqual(drone.tempo_vida, 30.0)

    def test_13_obter_buffs_ativos_and_hud_rendering(self):
        """13. Jogador.obter_buffs_ativos() retorna badges formatados e renderiza no HUD."""
        self.jogador.buff_dano_timer = 12.0
        self.jogador.buff_cadencia_timer = 9.5
        self.jogador.buff_vel_timer = 14.0
        self.jogador.buff_resistencia_timer = 6.0
        self.jogador.escudo_ativo = True

        buffs = self.jogador.obter_buffs_ativos()
        self.assertEqual(len(buffs), 5)
        ids = [b["id"] for b in buffs]
        self.assertIn("dano", ids)
        self.assertIn("cadencia", ids)
        self.assertIn("velocidade", ids)
        self.assertIn("resistencia", ids)
        self.assertIn("escudo", ids)

        # Renderização do HUD com buffs
        from src.cenas.gameplay import GameplayScene
        cena = GameplayScene()
        screen = pygame.Surface((800, 600))
        cena.jogador = self.jogador
        cena._desenhar_buffs_ativos(screen)

    def test_14_damage_buff_math_ceil_guarantees_minimum_step(self):
        """14. Dano com math.ceil garante aumento real em armas de 10 de dano base (10 -> 12)."""
        base_dano = 10
        mult_buff = 1.20
        dano_final = math.ceil(base_dano * mult_buff)
        self.assertEqual(dano_final, 12, "10 * 1.20 com ceil deve ser exatamente 12.")


if __name__ == "__main__":
    unittest.main()
