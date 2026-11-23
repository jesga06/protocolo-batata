"""
Testes Unitários do Cone Melee Direcional (R1) — Protocolo: Batata
Valida a filtragem geométrica por arco direcional de 45°, alcance de 84px (~2x batata),
dano de 10 por golpe (5 golpes para abater inimigo de 50 HP),
repulsão de 360.0 px/s nos 2 alvos mais próximos e compatibilidade.
"""

import math
import os
import sys
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.armas.melee import Melee
from src.entidades.inimigo_padrao import InimigoPadrao
from src.utils.constantes import (
    MELEE_DANO, MELEE_ALCANCE, MELEE_KNOCKBACK,
    MELEE_ARCO_GRAUS, INIMIGO_PADRAO_HP
)


class TestMeleeDirectionalCone(unittest.TestCase):
    """Testes para o ataque Melee em cone de 45 graus e alcance de 84px."""

    def setUp(self):
        self.melee = Melee(
            dano=10,
            cooldown=0.6,
            alcance=84.0,
            knockback_forca=360.0,
            max_alvos_knockback=2,
            arco_graus=45.0
        )
        self.origem_x = 500.0
        self.origem_y = 500.0

    def test_melee_defaults_match_constants(self):
        """Verifica se os valores padrão do Melee batem com as constantes atualizadas."""
        melee_padrao = Melee()
        self.assertEqual(melee_padrao.dano, 10)
        self.assertEqual(melee_padrao.alcance, 109.0)
        self.assertEqual(melee_padrao.knockback_forca, 360.0)
        self.assertEqual(melee_padrao.max_alvos_knockback, 2)
        self.assertEqual(melee_padrao.arco_graus, 90.0)

    def test_directional_filtering_in_cone(self):
        """
        Testa alvos em diferentes ângulos para mira horizontal à direita (0 radianos):
        - Inimigo 1: 0° (em linha reta, dist 50px) -> Dentro do cone (+0° <= 22.5°) -> Atingido
        - Inimigo 2: +15° (dist 50px) -> Dentro do cone (+15° <= 22.5°) -> Atingido
        - Inimigo 3: -15° (dist 50px) -> Dentro do cone (-15° >= -22.5°) -> Atingido
        - Inimigo 4: +30° (dist 50px) -> Fora do cone (+30° > 22.5°) -> Não atingido
        - Inimigo 5: 90° (perpendicular, dist 50px) -> Fora do cone -> Não atingido
        - Inimigo 6: 180° (atrás, dist 50px) -> Fora do cone -> Não atingido
        """
        # Mira apontando para a direita (0 radianos): (600, 500) a partir de (500, 500)
        mira_x = 600.0
        mira_y = 500.0

        dist = 50.0
        # Inimigo 1: 0 graus
        e1 = InimigoPadrao(x=self.origem_x + dist * math.cos(0.0) - 14, y=self.origem_y + dist * math.sin(0.0) - 14)
        # Inimigo 2: +15 graus
        rad_15 = math.radians(15.0)
        e2 = InimigoPadrao(x=self.origem_x + dist * math.cos(rad_15) - 14, y=self.origem_y + dist * math.sin(rad_15) - 14)
        # Inimigo 3: -15 graus
        rad_neg15 = math.radians(-15.0)
        e3 = InimigoPadrao(x=self.origem_x + dist * math.cos(rad_neg15) - 14, y=self.origem_y + dist * math.sin(rad_neg15) - 14)
        # Inimigo 4: +30 graus
        rad_30 = math.radians(30.0)
        e4 = InimigoPadrao(x=self.origem_x + dist * math.cos(rad_30) - 14, y=self.origem_y + dist * math.sin(rad_30) - 14)
        # Inimigo 5: +90 graus
        rad_90 = math.radians(90.0)
        e5 = InimigoPadrao(x=self.origem_x + dist * math.cos(rad_90) - 14, y=self.origem_y + dist * math.sin(rad_90) - 14)
        # Inimigo 6: 180 graus
        rad_180 = math.radians(180.0)
        e6 = InimigoPadrao(x=self.origem_x + dist * math.cos(rad_180) - 14, y=self.origem_y + dist * math.sin(rad_180) - 14)

        todos = [e1, e2, e3, e4, e5, e6]
        afetados = self.melee.executar_ataque(
            self.origem_x, self.origem_y, todos,
            mira_x=mira_x, mira_y=mira_y
        )

        self.assertEqual(len(afetados), 3)
        self.assertIn(e1, afetados)
        self.assertIn(e2, afetados)
        self.assertIn(e3, afetados)
        self.assertNotIn(e4, afetados)
        self.assertNotIn(e5, afetados)
        self.assertNotIn(e6, afetados)

    def test_reach_boundary_84px(self):
        """
        Verifica o limite de alcance de 84.0px na direção de mira:
        - Inimigo a 84.0px é atingido.
        - Inimigo a 85.0px não é atingido.
        """
        # Mira na direção de 90° (para baixo)
        mira_x = self.origem_x
        mira_y = self.origem_y + 100.0

        # Inimigo a exatamente 84.0px
        e_dentro = InimigoPadrao(x=self.origem_x - 14, y=self.origem_y + 84.0 - 14)
        # Inimigo a 85.0px (fora)
        e_fora = InimigoPadrao(x=self.origem_x - 14, y=self.origem_y + 85.0 - 14)

        afetados = self.melee.executar_ataque(
            self.origem_x, self.origem_y, [e_dentro, e_fora],
            mira_x=mira_x, mira_y=mira_y
        )

        self.assertEqual(len(afetados), 1)
        self.assertIn(e_dentro, afetados)
        self.assertNotIn(e_fora, afetados)

    def test_four_hits_kill_standard_40hp_enemy(self):
        """
        Valida que um inimigo padrão com 40 HP é destruído com exatamente 4 golpes de 10 de dano.
        """
        inimigo = InimigoPadrao(x=self.origem_x + 40 - 14, y=self.origem_y - 14)
        self.assertEqual(inimigo.hp, 40)
        self.assertTrue(inimigo.vivo)

        mira_x = self.origem_x + 100.0
        mira_y = self.origem_y

        for hit in range(1, 5):
            self.melee.tempo_recarga_restante = 0.0  # Reset cooldown para teste sequencial
            afetados = self.melee.executar_ataque(
                self.origem_x, self.origem_y, [inimigo],
                mira_x=mira_x, mira_y=mira_y
            )
            self.assertEqual(len(afetados), 1)
            self.assertEqual(inimigo.hp, 40 - (hit * 10))
            if hit < 4:
                self.assertTrue(inimigo.vivo)
            else:
                self.assertFalse(inimigo.vivo)

    def test_knockback_applied_to_closest_two_enemies_with_360_force(self):
        """
        Verifica que o impulso de knockback (360.0 px/s) é aplicado estritamente
        aos 2 alvos mais próximos dentro do cone, e outros alvos sofrem dano sem knockback.
        """
        mira_x = self.origem_x + 100.0
        mira_y = self.origem_y

        # Cria 4 inimigos no cone a distâncias: 20px, 40px, 60px, 80px
        e1 = InimigoPadrao(x=self.origem_x + 20 - 14, y=self.origem_y - 14)
        e2 = InimigoPadrao(x=self.origem_x + 40 - 14, y=self.origem_y - 14)
        e3 = InimigoPadrao(x=self.origem_x + 60 - 14, y=self.origem_y - 14)
        e4 = InimigoPadrao(x=self.origem_x + 80 - 14, y=self.origem_y - 14)

        afetados = self.melee.executar_ataque(
            self.origem_x, self.origem_y, [e4, e1, e3, e2],
            mira_x=mira_x, mira_y=mira_y
        )

        self.assertEqual(len(afetados), 4)

        # e1 (20px) e e2 (40px) devem receber knockback
        self.assertAlmostEqual(e1.vx_knockback, 360.0, places=1)
        self.assertAlmostEqual(e2.vx_knockback, 360.0, places=1)

        # e3 (60px) e e4 (80px) não devem receber knockback
        self.assertEqual(e3.vx_knockback, 0.0)
        self.assertEqual(e4.vx_knockback, 0.0)

    def test_backwards_compatibility_when_no_aim_given(self):
        """
        Quando nem mira_x/mira_y nem angulo_mira são fornecidos,
        o ataque opera radialmente (360°) em todos os inimigos no raio de alcance.
        """
        e_dir = InimigoPadrao(x=self.origem_x + 50 - 14, y=self.origem_y - 14)
        e_esq = InimigoPadrao(x=self.origem_x - 50 - 14, y=self.origem_y - 14)

        afetados = self.melee.executar_ataque(
            self.origem_x, self.origem_y, [e_dir, e_esq]
        )

        self.assertEqual(len(afetados), 2)
        self.assertIn(e_dir, afetados)
        self.assertIn(e_esq, afetados)


if __name__ == "__main__":
    unittest.main()
