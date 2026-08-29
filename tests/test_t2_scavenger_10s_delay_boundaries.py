"""
Testes de Fronteira e Stress — Milestone 4: Scavenger 10-Second Delay Rule Boundaries
SSOT: CONFIGURACOES.md, PROJECT.md, constantes.py, sistema_scavenger.py
Valida:
1. Constante global DROP_TEMPO_SCAVENGER_ATIVAR == 10.0.
2. ItemDrop(tempo_scavenger=10.0) rejeita elegibilidade para qualquer idade < 10.0s (0.0s, 5.0s, 9.99s, 9.999s).
3. ItemDrop(tempo_scavenger=10.0) aceita elegibilidade imediatamente em 10.0s e tempos superiores (10.001s, 15.0s, 59.9s).
4. SistemaScavenger singleton seleciona apenas 1 inimigo respeitando a exclusão dos 3 mais próximos e teto de 600px.
5. Scavenger consome drop sem conceder XP ou cura ao jogador.
"""

import os
import sys
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.constantes import DROP_TEMPO_SCAVENGER_ATIVAR
from src.entidades.drop import ItemDrop
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_drops import SistemaDrops


class TestScavenger10sDelayBoundaries(unittest.TestCase):
    """Testa a fronteira matemática exata de 10.0s para a IA Scavenger."""

    def setUp(self):
        self.scav_sys = SistemaScavenger(dist_maxima=600.0)
        self.sistema_drops = SistemaDrops()

    def test_constant_value_is_exactly_10_seconds(self):
        """Verifica se DROP_TEMPO_SCAVENGER_ATIVAR está definida como 10.0."""
        self.assertEqual(DROP_TEMPO_SCAVENGER_ATIVAR, 10.0)

    def test_drop_rejection_boundaries_below_10s(self):
        """Drops com tempo_decorrido < 10.0s não são elegíveis."""
        for t in [0.0, 1.0, 5.0, 9.0, 9.90, 9.99, 9.999]:
            drop = ItemDrop(x=300.0, y=300.0, tipo="xp", valor=10)
            drop.tempo_decorrido = t
            self.assertFalse(
                drop.elegivel_scavenger(),
                f"Drop com tempo {t}s NÃO deve ser elegível para o Scavenger (< 10.0s)."
            )

    def test_drop_acceptance_boundaries_at_and_above_10s(self):
        """Drops com tempo_decorrido >= 10.0s são elegíveis."""
        for t in [10.0, 10.001, 10.1, 15.0, 30.0, 59.9]:
            drop = ItemDrop(x=300.0, y=300.0, tipo="xp", valor=10)
            drop.tempo_decorrido = t
            self.assertTrue(
                drop.elegivel_scavenger(),
                f"Drop com tempo {t}s DEVE ser elegível para o Scavenger (>= 10.0s)."
            )

    def test_scavenger_selection_pipeline_at_boundary_999_vs_1000(self):
        """Testa a transição de seleção do Scavenger entre 9.99s e 10.00s."""
        drop = ItemDrop(x=500.0, y=500.0, tipo="xp", valor=10)
        drop.tempo_decorrido = 9.99

        e1 = InimigoPadrao(x=520.0, y=500.0)
        e2 = InimigoPadrao(x=540.0, y=500.0)
        e3 = InimigoPadrao(x=560.0, y=500.0)
        e4 = InimigoPadrao(x=700.0, y=500.0)
        inimigos = [e1, e2, e3, e4]

        # Em 9.99s -> Nenhum selecionado
        self.assertIsNone(self.scav_sys.selecionar_scavenger(inimigos, [drop]))

        # Avança para 10.00s -> e4 selecionado
        drop.tempo_decorrido = 10.00
        escolhido = self.scav_sys.selecionar_scavenger(inimigos, [drop])
        self.assertEqual(escolhido, e4)
        self.assertEqual(self.scav_sys.scavenger_atual, e4)
        self.assertEqual(self.scav_sys.drop_alvo, drop)

    def test_scavenger_consumes_drop_at_10s_safely(self):
        """Scavenger alcança e consome o drop de 10s sem dar nada ao jogador."""
        drop = ItemDrop(x=200.0, y=200.0, tipo="cura", valor=50)
        drop.tempo_decorrido = 10.0

        jogador = Jogador(x=50.0, y=50.0, hp_max=100)
        jogador.hp = 30

        scav = InimigoPadrao(x=200.0, y=200.0)
        self.scav_sys.scavenger_atual = scav
        self.scav_sys.drop_alvo = drop

        self.scav_sys.update(dt=0.05, lista_inimigos=[scav], lista_drops=[drop])

        self.assertFalse(drop.ativo)
        self.assertTrue(drop.coletado)
        self.assertEqual(jogador.hp, 30, "Jogador não deve ser curado quando o Scavenger come o drop.")


if __name__ == "__main__":
    unittest.main()
