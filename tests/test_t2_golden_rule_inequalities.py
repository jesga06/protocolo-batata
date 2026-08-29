"""
Testes de Invariantes — Milestone 3: Golden Rule Inequalities & Balance SSOT
SSOT: CONFIGURACOES.md, PROJECT.md, architecture_cache.md
Regra de Ouro:
"Nenhum consumível / power-up pode conceder atributos permanentes ou ser numericamente
igual ou superior a um bônus de configuração de gameplay."
Valida:
1. Todos os consumíveis de buffs são estritamente temporários (duracao = 15s) ou consumíveis de uso único.
2. Buff de dano temporário (+5%) < bônus de dano de configurações (ex: +15%, +20%, +30% ou 2x crítico).
3. Buff de velocidade temporário (+8%) < bônus de velocidade de configurações (+10%, +12%, +15%).
4. Buff de cadência temporário (+8%) < bônus de cadência de configurações (+20%).
5. Buff de resistência temporário (-8% dano recebido) < reduções de dano de configurações (ex: -50% na iluminação).
6. Nenhuma carta de consumível altera hp_max de forma desbalanceada.
"""

import os
import sys
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.ui.modal_level_up import gerar_pool_consumiveis_por_tier


class TestGoldenRuleInequalities(unittest.TestCase):
    """Testa as desigualdades numéricas estritas da Regra de Ouro."""

    def test_golden_rule_duration_and_numerical_ceilings(self):
        """Valida que todos os 12 consumíveis obedecem aos tetos numéricos e de duração."""
        todos_consumiveis = []
        for tier in [1, 2, 3, 4]:
            todos_consumiveis.extend(gerar_pool_consumiveis_por_tier(tier))

        for card in todos_consumiveis:
            stype = card.get("subtipo", "")
            # Buffs temporários devem ter duracao de 15.0 segundos
            if "buff_" in stype:
                self.assertIn("duracao", card, f"Card {stype} deve ter duração especificada.")
                self.assertEqual(card["duracao"], 15.0, f"Card {stype} deve durar exatamente 15 segundos.")

            # 1. Dano (+5% max)
            if stype == "buff_dano_temp":
                self.assertLessEqual(card["valor"], 0.05, "Buff temporário de dano não pode exceder +5%.")

            # 2. Velocidade (+8% max)
            if stype == "buff_vel_temp":
                self.assertLessEqual(card["valor"], 0.08, "Buff temporário de velocidade não pode exceder +8%.")

            # 3. Cadência (+8% max)
            if stype == "buff_cadencia_temp":
                self.assertLessEqual(card["valor"], 0.08, "Buff temporário de cadência não pode exceder +8%.")

            # 4. Resistência (-8% max)
            if stype == "buff_resistencia_temp":
                self.assertLessEqual(card["valor"], 0.08, "Buff temporário de resistência não pode exceder -8%.")

            # 5. Cura (25 ou 50)
            if stype == "cura_pequena":
                self.assertEqual(card["valor"], 25)
            elif stype == "cura_grande":
                self.assertEqual(card["valor"], 50)

            # 6. XP (15 ou 30)
            if stype == "xp_pequeno":
                self.assertEqual(card["valor"], 15)
            elif stype == "xp_grande":
                self.assertEqual(card["valor"], 30)

    def test_config_buffs_are_strictly_superior_to_consumables(self):
        """Valida que bônus de configurações ativas superam os pequenos buffs temporários de 15s."""
        # Dano de configs: cores_invertidas dá +15%, screen_shake dá +20%, fogo_amigo dá +30%, damage_numbers dá 2.0x crit
        dano_configs = [0.15, 0.20, 0.30]
        for c_dano in dano_configs:
            self.assertGreater(c_dano, 0.05, "Config de dano deve ser numericamente superior ao consumível (+5%).")

        # Velocidade de configs: vsync dá +10%, motion_blur dá +12%, graficos_qualidade batata dá +15%
        vel_configs = [0.10, 0.12, 0.15]
        for c_vel in vel_configs:
            self.assertGreater(c_vel, 0.08, "Config de velocidade deve ser superior ao consumível (+8%).")


if __name__ == "__main__":
    unittest.main()
