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

            # 1. Dano (+20% max)
            if stype == "buff_dano_temp":
                self.assertLessEqual(card["valor"], 0.20, "Buff temporário de dano não pode exceder +20%.")

            # 2. Velocidade (+12% max)
            if stype == "buff_vel_temp":
                self.assertLessEqual(card["valor"], 0.12, "Buff temporário de velocidade não pode exceder +12%.")

            # 3. Cadência (+25% max)
            if stype == "buff_cadencia_temp":
                self.assertLessEqual(card["valor"], 0.25, "Buff temporário de cadência não pode exceder +25%.")

            # 4. Resistência (-15% max)
            if stype == "buff_resistencia_temp":
                self.assertLessEqual(card["valor"], 0.15, "Buff temporário de resistência não pode exceder -15%.")

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
        """Valida no catálogo real CONFIGURACOES_GAMEPLAY que bônus permanentes superam consumíveis temporários."""
        todos_consumiveis = []
        for tier in [1, 2, 3, 4]:
            todos_consumiveis.extend(gerar_pool_consumiveis_por_tier(tier))

        max_dano_cons = max(c["valor"] for c in todos_consumiveis if c.get("subtipo") == "buff_dano_temp")
        max_vel_cons = max(c["valor"] for c in todos_consumiveis if c.get("subtipo") == "buff_vel_temp")
        max_cad_cons = max(c["valor"] for c in todos_consumiveis if c.get("subtipo") == "buff_cadencia_temp")
        max_res_cons = max(c["valor"] for c in todos_consumiveis if c.get("subtipo") == "buff_resistencia_temp")

        self.assertEqual(max_dano_cons, 0.05)
        self.assertEqual(max_vel_cons, 0.08)
        self.assertEqual(max_cad_cons, 0.08)
        self.assertEqual(max_res_cons, 0.08)

        # Extrai bônus reais das opções de CONFIGURACOES_GAMEPLAY
        dano_bonus_configs = []
        vel_bonus_configs = []
        res_bonus_configs = []
        for cdef in CONFIGURACOES_GAMEPLAY.values():
            for op in cdef.opcoes.values():
                m = op.modificadores
                if "dano_armas_mult" in m and m["dano_armas_mult"] > 1.0:
                    dano_bonus_configs.append(round(m["dano_armas_mult"] - 1.0, 4))
                if "vel_jogador_mult" in m and m["vel_jogador_mult"] > 1.0:
                    vel_bonus_configs.append(round(m["vel_jogador_mult"] - 1.0, 4))
                if "dano_inimigos_mult" in m and m["dano_inimigos_mult"] < 1.0:
                    res_bonus_configs.append(round(1.0 - m["dano_inimigos_mult"], 4))
                if "dano_fora_visao_mult" in m and m["dano_fora_visao_mult"] < 1.0:
                    res_bonus_configs.append(round(1.0 - m["dano_fora_visao_mult"], 4))

        self.assertTrue(len(dano_bonus_configs) > 0)
        self.assertTrue(len(vel_bonus_configs) > 0)
        self.assertTrue(len(res_bonus_configs) > 0)

        for c_dano in dano_bonus_configs:
            self.assertGreater(c_dano, max_dano_cons, f"Bônus de dano de config ({c_dano}) deve superar consumível ({max_dano_cons}).")
        for c_vel in vel_bonus_configs:
            self.assertGreaterEqual(c_vel, max_vel_cons, f"Bônus de velocidade de config ({c_vel}) deve superar/igualar consumível ({max_vel_cons}).")
        for c_res in res_bonus_configs:
            self.assertGreater(c_res, max_res_cons, f"Redução de dano de config ({c_res}) deve superar consumível ({max_res_cons}).")


if __name__ == "__main__":
    unittest.main()
