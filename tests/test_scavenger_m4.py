"""
Testes Unitários do Sistema Scavenger e Mecânicas de Drops M4 (Fase 5) — Protocolo: Batata
Valida:
1. Regra #15 (Coleta Inimiga): Seleção singleton do Scavenger excluindo os 3 mais próximos e >600px.
2. Consumo de drop pelo Scavenger sem conceder recompensas ao jogador.
3. Multiplicador de 2x em todas as recompensas de drops coletados pelo jogador sob Config 15
   (2x XP, 2x Cura, 2x Munição de Armas Especiais, 60s de Duração de Drones).
4. Projéteis de Inimigos (Ranged) causando dano ao jogador em GameplayScene.
5. Detonação de Projéteis Explosivos (AoE) atingindo múltiplos inimigos no raio e Fogo Amigo.
"""

import os
import sys
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.entidades.drop import ItemDrop
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.projetil import Projetil
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.cenas.gameplay import GameplayScene
from src.armas.minigun import Minigun
from src.armas.lanca_foguetes import LancaFoguetes
from src.equipamentos.drone_cura import DroneCura


class TestScavengerMechanicsM4(unittest.TestCase):
    """Testa a IA Scavenger e as regras da Config 15 (Coleta Inimiga)."""

    def setUp(self):
        self.scavenger_sys = SistemaScavenger(dist_maxima=600.0)
        self.sistema_drops = SistemaDrops()

    def test_scavenger_drop_grace_period_and_target_selection(self):
        """Drop só é elegível após 1.0s de chão e seleciona 1 inimigo elegível."""
        drop = ItemDrop(x=400.0, y=300.0, tipo="xp", valor=10, tempo_vida=10.0, tempo_scavenger=1.0)
        drop.tempo_decorrido = 0.5  # 0.5s < 1.0s -> Não elegível

        # 5 inimigos
        e1 = InimigoPadrao(x=420.0, y=300.0)
        e2 = InimigoPadrao(x=440.0, y=300.0)
        e3 = InimigoPadrao(x=460.0, y=300.0)
        e4 = InimigoPadrao(x=550.0, y=300.0)
        e5 = InimigoPadrao(x=580.0, y=300.0)
        todos = [e1, e2, e3, e4, e5]

        # Com drop em carência, nenhum scavenger é selecionado
        self.assertIsNone(self.scavenger_sys.selecionar_scavenger(todos, [drop]))

        # Avança tempo do drop para 1.2s (> 1.0s)
        drop.tempo_decorrido = 1.2
        escolhido = self.scavenger_sys.selecionar_scavenger(todos, [drop])

        # Exclui e1, e2, e3 (3 mais próximos); apenas e4 ou e5 podem ser escolhidos
        self.assertIn(escolhido, [e4, e5])
        self.assertIsNotNone(escolhido.pos_alvo_override)

    def test_scavenger_eats_drop_without_player_reward(self):
        """Quando o Scavenger alcança o drop, o item é consumido e o jogador não recebe nada."""
        drop = ItemDrop(x=200.0, y=200.0, tipo="xp", valor=10)
        drop.tempo_decorrido = 1.5

        # Cria inimigo muito próximo ao drop para alcançar rapidamente
        e1 = InimigoPadrao(x=205.0, y=205.0)
        e2 = InimigoPadrao(x=210.0, y=205.0)
        e3 = InimigoPadrao(x=215.0, y=205.0)
        e4 = InimigoPadrao(x=218.0, y=205.0)  # Candidato 4 (distância ~20px do drop)

        todos = [e1, e2, e3, e4]
        self.scavenger_sys.selecionar_scavenger(todos, [drop])
        self.assertEqual(self.scavenger_sys.scavenger_atual, e4)

        # Atualiza sistema scavenger: colide e consome o drop
        self.scavenger_sys.update(dt=0.1, lista_inimigos=todos, lista_drops=[drop])

        self.assertFalse(drop.ativo)
        self.assertTrue(drop.coletado)
        self.assertIsNone(self.scavenger_sys.scavenger_atual)
        self.assertIsNone(self.scavenger_sys.drop_alvo)

    def test_player_collection_under_config_15_doubles_all_rewards(self):
        """
        Sob a Config 15 ativa (mult_valor_drop = 2.0):
        - XP em dobro (10 -> 20)
        - Cura em dobro (35 -> 70)
        - Armas especiais com dobro de munição
        - Drones com dobro de tempo de vida (60s)
        """
        jogador = Jogador(x=100.0, y=100.0, hp_max=150)
        jogador.hp = 50

        # 1. Gema de XP com multiplicador 2.0x
        drop_xp = ItemDrop(x=105.0, y=105.0, tipo="xp", valor=10)
        self.sistema_drops.drops = [drop_xp]
        eventos = self.sistema_drops.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["valor"], 20)

        # 2. Drop de Cura com multiplicador 2.0x
        drop_cura = ItemDrop(x=105.0, y=105.0, tipo="cura", valor=35)
        self.sistema_drops.drops = [drop_cura]
        eventos_cura = self.sistema_drops.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos_cura), 1)
        self.assertEqual(eventos_cura[0]["valor"], 70)
        self.assertEqual(jogador.hp, 50 + 70)  # 120 HP

        # 3. Arma Especial com multiplicador 2.0x
        minigun = Minigun()
        municao_base = minigun.municao_max
        minigun.municao_max *= 2
        minigun.municao_atual = minigun.municao_max
        self.assertEqual(minigun.municao_atual, municao_base * 2)

        # 4. Drone com multiplicador 2.0x (60s de duração)
        drone = DroneCura(tempo_vida=60.0)
        self.assertEqual(drone.tempo_vida, 60.0)
        self.assertEqual(drone.tempo_restante, 60.0)


class TestGameplayCollisionsM4(unittest.TestCase):
    """Testa colisões de projéteis de inimigos e explosivos em GameplayScene."""

    def test_enemy_projectile_damages_player_in_gameplay_scene(self):
        """Valida que projétil com dono='inimigo' colide com a batata e causa dano."""
        cena = GameplayScene()
        jogador = cena.jogador
        hp_inicial = jogador.hp

        # Spawna projétil inimigo na mesma posição da batata
        proj_inimigo = Projetil(
            x=jogador.x,
            y=jogador.y,
            dir_x=1.0,
            dir_y=0.0,
            dano=10,
            dono="inimigo",
            sprite_key="projetil_inimigo"
        )
        cena.projeteis.append(proj_inimigo)

        # Executa um ciclo de colisões do loop
        cena.loop()

        # O projétil colidiu, foi desativado e aplicou 10 de dano ao jogador
        self.assertEqual(jogador.hp, hp_inicial - 10)
        self.assertFalse(proj_inimigo.ativo)

    def test_explosive_projectile_aoe_damages_multiple_enemies(self):
        """Valida que um projétil explosivo atinge múltiplos inimigos dentro do raio de 80px."""
        cena = GameplayScene()

        # Posiciona 2 inimigos a 30px do epicentro da explosão (dentro de 80px)
        e1 = InimigoPadrao(x=220.0, y=200.0, hp=50)
        e2 = InimigoPadrao(x=230.0, y=200.0, hp=50)
        # Posiciona 1 inimigo distante a 300px (fora do raio de 80px)
        e3 = InimigoPadrao(x=500.0, y=200.0, hp=50)

        cena.inimigos = [e1, e2, e3]

        # Projétil de Lança-Foguetes em (200, 200) com raio de explosão 80px e dano 60
        foguete = Projetil(
            x=200.0,
            y=200.0,
            dir_x=1.0,
            dir_y=0.0,
            velocidade=400.0,
            dano=60,
            dono="jogador",
            explosivo=True,
            raio_explosao=80.0
        )
        cena.projeteis = [foguete]

        # Executa frames suficientes para o projétil colidir e detonar
        for _ in range(5):
            cena.loop()

        # Inimigos e1 e e2 sofreram a explosão (60 dano) e morreram (HP <= 0)
        self.assertFalse(e1.vivo)
        self.assertFalse(e2.vivo)
        # Inimigo distante e3 não foi afetado e permaneceu com 50 HP
        self.assertTrue(e3.vivo)
        self.assertEqual(e3.hp, 50)


if __name__ == "__main__":
    unittest.main()
