"""
Testes Unitários de Drops, Scavenger e Progressão de XP (R2) — Protocolo: Batata
Valida ciclo de vida dos drops (10s), período de carência (1s), fórmula de XP (XP_prox = 10 + 5 * level),
overflow multi-nível, teto de nível 20 e seleção de IA Scavenger.
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
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_xp import SistemaXP
from src.sistemas.sistema_scavenger import SistemaScavenger


class TestDropsAndItemLifecycle(unittest.TestCase):
    """Testa a entidade ItemDrop e o SistemaDrops."""

    def test_drop_lifetime_and_scavenger_grace_period(self):
        """
        Drop possui tempo de vida total de 10.0s e carência de 1.0s para scavenger.
        """
        drop = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10, tempo_vida=10.0, tempo_scavenger=1.0)
        self.assertTrue(drop.ativo)
        self.assertFalse(drop.elegivel_scavenger())
        self.assertEqual(drop.tempo_restante, 10.0)

        # Avança 0.5s -> Ainda em carência (0.5s < 1.0s)
        drop.update(0.5)
        self.assertTrue(drop.ativo)
        self.assertFalse(drop.elegivel_scavenger())
        self.assertEqual(drop.tempo_restante, 9.5)

        # Avança mais 0.5s -> 1.0s decorrido -> Agora elegível para Scavenger
        drop.update(0.5)
        self.assertTrue(drop.ativo)
        self.assertTrue(drop.elegivel_scavenger())

        # Avança até 9.9s -> Ainda ativo
        drop.update(8.9)
        self.assertTrue(drop.ativo)
        self.assertAlmostEqual(drop.tempo_restante, 0.1, places=2)

        # Avança mais 0.2s -> 10.1s -> Expira e desativa
        drop.update(0.2)
        self.assertFalse(drop.ativo)
        self.assertFalse(drop.elegivel_scavenger())

    def test_player_collection_and_coleta_inimiga_multiplier(self):
        """
        Valida coleta pelo jogador e suporte ao multiplicador de 2x da regra #15 (Coleta Inimiga).
        """
        sistema = SistemaDrops()
        jogador = Jogador(x=100.0, y=100.0, hp_max=100)
        jogador.hp = 50  # Danificado para testar cura

        # Spawna 1 gema de XP (valor 10) e 1 drop de cura (valor 35)
        drop_xp = ItemDrop(x=105.0, y=105.0, tipo="xp", valor=10)
        drop_cura = ItemDrop(x=110.0, y=110.0, tipo="cura", valor=35)
        sistema.drops.extend([drop_xp, drop_cura])

        # Coleta normal (mult = 1.0)
        eventos = sistema.coletar_jogador(jogador, mult_valor_drop=1.0)
        self.assertEqual(len(eventos), 2)
        self.assertTrue(drop_xp.coletado)
        self.assertTrue(drop_cura.coletado)
        # HP do jogador foi curado em 35 (50 + 35 = 85)
        self.assertEqual(jogador.hp, 85)

        # Spawna novo drop de cura com multiplicador de Coleta Inimiga (2.0x)
        drop_cura2 = ItemDrop(x=105.0, y=105.0, tipo="cura", valor=35)
        sistema.drops.append(drop_cura2)

        eventos2 = sistema.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos2), 1)
        self.assertEqual(eventos2[0]["valor"], 70)
        # 85 + 70 = 155, limitado a hp_max (100)
        self.assertEqual(jogador.hp, 100)


class TestXPProgressionSystem(unittest.TestCase):
    """Testa a lógica matemática e o gerenciamento de níveis do SistemaXP."""

    def test_xp_formula_scaling(self):
        """
        Valida a fórmula quadrática com suavização de 25% para níveis > 10:
        - Níveis 1..10 (base): base = 20 + 10*level + 5*(level^2)
          - Nível 1 -> 35 XP
          - Nível 2 -> 60 XP
          - Nível 3 -> 95 XP
          - Nível 4 -> 140 XP
          - Nível 10 -> 620 XP
        - Níveis > 10: int(round(base * 0.75))
          - Nível 11 -> 551 XP (base 735 * 0.75)
          - Nível 19 -> 1511 XP (base 2015 * 0.75)
          - Nível 20 -> 1665 XP (base 2220 * 0.75)
        """
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(1), 77)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(2), 144)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(3), 238)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(4), 358)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(10), 2200)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(11), 1960)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(19), 5410)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(20), 5962)

    def test_multi_level_overflow_carryover(self):
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        subidas = xp_sys.adicionar_xp(241)  # 77 + 144 = 221 -> sobra 20

        self.assertEqual(subidas, [2, 3])
        self.assertEqual(xp_sys.nivel, 3)
        self.assertEqual(xp_sys.xp_atual, 20)
        self.assertEqual(xp_sys.xp_total, 241)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(), 238)

    def test_level_up_callback_notification(self):
        """Valida se o callback registrado é acionado a cada nível ganho."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        notificacoes = []

        def on_level_up(novo_nivel):
            notificacoes.append(novo_nivel)

        xp_sys.registrar_callback_level_up(on_level_up)
        xp_sys.adicionar_xp(103)  # Atinge nível 2

        self.assertEqual(notificacoes, [2])

    def test_max_level_cap_at_20(self):
        """Valida que o sistema trava o nível máximo em 20."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        # Concede XP massivo (100000 XP)
        xp_sys.adicionar_xp(100000)

        self.assertEqual(xp_sys.nivel, 20)
        self.assertEqual(xp_sys.progresso_normalizado(), 1.0)


class TestScavengerAISelector(unittest.TestCase):
    """Testa a lógica de seleção do inimigo Scavenger."""

    def test_scavenger_singleton_and_exclusion_rules(self):
        """
        Regras do Scavenger:
        1. Exclui os 3 inimigos mais próximos ao drop.
        2. Exclui inimigos com distância > 600px.
        3. Apenas 1 inimigo pode ser Scavenger globalmente.
        """
        scavenger_sys = SistemaScavenger(dist_maxima=600.0)

        drop = ItemDrop(x=500.0, y=500.0, tipo="xp", valor=10)
        drop.tempo_decorrido = 10.5  # Elegível (>=10.0s)

        # Inimigos a distâncias: 50, 100, 150 (3 mais próximos - DEVEM SER EXCLUÍDOS)
        e1 = InimigoPadrao(x=550.0 - 14, y=500.0 - 14)
        e2 = InimigoPadrao(x=600.0 - 14, y=500.0 - 14)
        e3 = InimigoPadrao(x=650.0 - 14, y=500.0 - 14)

        # Inimigo 4 a 300px (4º mais próximo - ÚNICO ELEGÍVEL)
        e4 = InimigoPadrao(x=800.0 - 14, y=500.0 - 14)

        # Inimigo 5 a 700px (> 600px - DEVE SER EXCLUÍDO POR DISTÂNCIA)
        e5 = InimigoPadrao(x=1200.0 - 14, y=500.0 - 14)

        todos_inimigos = [e1, e2, e3, e4, e5]

        escolhido = scavenger_sys.selecionar_scavenger(todos_inimigos, [drop])

        # Apenas e4 atende a todos os critérios (não é top 3 e está a <= 600px)
        self.assertEqual(escolhido, e4)
        self.assertEqual(scavenger_sys.scavenger_atual, e4)
        self.assertEqual(scavenger_sys.drop_alvo, drop)

        # Se chamar novamente com o scavenger ativo, mantém o singleton
        escolhido_segunda_vez = scavenger_sys.selecionar_scavenger(todos_inimigos, [drop])
        self.assertEqual(escolhido_segunda_vez, e4)


if __name__ == "__main__":
    unittest.main()
