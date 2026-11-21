"""
Testes Unitários Dedicados do SistemaXP — Protocolo: Batata
Valida com rigor matemático:
1. Curva padrão exata para níveis 1 a 10 (base = 20 + 10*lvl + 5*(lvl^2)).
2. Redução de 25% na exigência de XP para níveis > 10 (int(round(base * 0.75))).
3. Métodos e aliases: calcular_xp_para_nivel, calcular_xp_necessario, xp_para_proximo_nivel, xp_necessario.
4. Acúmulo de XP, subidas de nível unitárias e multi-nível (transbordo / carryover).
5. Limite máximo (teto de nível 20) e normalização de progresso.
6. Multiplicador de XP e tratamento de valores não-positivos.
7. Callbacks de notificação de level-up.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.sistemas.sistema_xp import SistemaXP


class TestSistemaXPProgression(unittest.TestCase):
    """Testes completos da progressão de XP e cálculo de níveis."""

    def test_curva_padrao_niveis_1_a_10(self):
        """
        Valida que os níveis 1 a 10 mantêm a curva padrão exata:
        base = 20 + 10 * lvl + 5 * (lvl ^ 2)
        """
        valores_esperados_1_a_10 = {
            1: 35,     # 20 + 10 + 5
            2: 60,     # 20 + 20 + 20
            3: 95,     # 20 + 30 + 45
            4: 140,    # 20 + 40 + 80
            5: 195,    # 20 + 50 + 125
            6: 260,    # 20 + 60 + 180
            7: 335,    # 20 + 70 + 245
            8: 420,    # 20 + 80 + 320
            9: 515,    # 20 + 90 + 405
            10: 620,   # 20 + 100 + 500
        }

        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        for lvl, xp_esperado in valores_esperados_1_a_10.items():
            base_calculada = 20 + 10 * lvl + 5 * (lvl ** 2)
            self.assertEqual(xp_esperado, base_calculada)
            self.assertEqual(xp_sys.xp_para_proximo_nivel(lvl), xp_esperado, f"Nível {lvl} falhou")
            self.assertEqual(xp_sys.calcular_xp_necessario(lvl), xp_esperado, f"Nível {lvl} via alias falhou")
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), xp_esperado, f"Nível {lvl} estático falhou")

    def test_curva_reduzida_25_porcento_niveis_acima_de_10(self):
        """
        Valida que os níveis > 10 recebem redução exata de 25%:
        int(round(base * 0.75))
        """
        valores_esperados_11_a_20 = {
            11: 551,   # base = 735 -> 735 * 0.75 = 551.25 -> 551
            12: 645,   # base = 860 -> 860 * 0.75 = 645.0 -> 645
            13: 746,   # base = 995 -> 995 * 0.75 = 746.25 -> 746
            14: 855,   # base = 1140 -> 1140 * 0.75 = 855.0 -> 855
            15: 971,   # base = 1295 -> 1295 * 0.75 = 971.25 -> 971
            16: 1095,  # base = 1460 -> 1460 * 0.75 = 1095.0 -> 1095
            17: 1226,  # base = 1635 -> 1635 * 0.75 = 1226.25 -> 1226
            18: 1365,  # base = 1820 -> 1820 * 0.75 = 1365.0 -> 1365
            19: 1511,  # base = 2015 -> 2015 * 0.75 = 1511.25 -> 1511
            20: 1665,  # base = 2220 -> 2220 * 0.75 = 1665.0 -> 1665
        }

        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        for lvl, xp_esperado in valores_esperados_11_a_20.items():
            base = 20 + 10 * lvl + 5 * (lvl ** 2)
            calculo_manual = int(round(base * 0.75))
            self.assertEqual(xp_esperado, calculo_manual)
            self.assertEqual(xp_sys.xp_para_proximo_nivel(lvl), xp_esperado, f"Nível {lvl} falhou")
            self.assertEqual(xp_sys.calcular_xp_necessario(lvl), xp_esperado, f"Nível {lvl} via alias falhou")
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), xp_esperado, f"Nível {lvl} estático falhou")

    def test_property_xp_necessario_retorna_nivel_atual(self):
        """Verifica se a propriedade xp_necessario reflete o nível corrente."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        self.assertEqual(xp_sys.xp_necessario, 35)

        xp_sys.nivel = 10
        self.assertEqual(xp_sys.xp_necessario, 620)

        xp_sys.nivel = 11
        self.assertEqual(xp_sys.xp_necessario, 551)

        xp_sys.nivel = 19
        self.assertEqual(xp_sys.xp_necessario, 1511)

    def test_ganho_xp_e_subida_de_nivel_simples(self):
        """Valida avanço para o próximo nível com valor exato."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        subidas = xp_sys.adicionar_xp(35)

        self.assertEqual(subidas, [2])
        self.assertEqual(xp_sys.nivel, 2)
        self.assertEqual(xp_sys.xp_atual, 0)
        self.assertEqual(xp_sys.xp_total, 35)

    def test_multi_level_carryover(self):
        """
        Valida que o transbordo de XP avança múltiplos níveis consecutivamente:
        Nível 1 (custo 35) + Nível 2 (custo 60) + Nível 3 (custo 95) = 190 XP.
        Recebendo 200 XP:
        - 1 -> 2 (restam 165)
        - 2 -> 3 (restam 105)
        - 3 -> 4 (restam 10)
        - Nível final: 4, xp_atual: 10 / 140
        """
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        subidas = xp_sys.ganhar_xp(200)

        self.assertEqual(subidas, [2, 3, 4])
        self.assertEqual(xp_sys.nivel, 4)
        self.assertEqual(xp_sys.xp_atual, 10)
        self.assertEqual(xp_sys.xp_total, 200)

    def test_teto_nivel_maximo_20(self):
        """Valida que o nível nunca ultrapassa o teto máximo (20)."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        xp_sys.adicionar_xp(500000)

        self.assertEqual(xp_sys.nivel, 20)
        self.assertEqual(xp_sys.progresso_normalizado(), 1.0)

    def test_multiplicador_de_xp(self):
        """Valida aplicação de modificadores de ganho de XP (ex: buffs de configs)."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        # 20 XP com multiplicador 1.5x -> 30 XP
        subidas = xp_sys.adicionar_xp(20, mult_xp=1.5)

        self.assertEqual(subidas, [])
        self.assertEqual(xp_sys.xp_atual, 30)
        self.assertEqual(xp_sys.xp_total, 30)

    def test_adicao_xp_invalido_ou_zero(self):
        """Valida que XP <= 0 é ignorado com segurança."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        subidas = xp_sys.adicionar_xp(0)
        self.assertEqual(subidas, [])
        self.assertEqual(xp_sys.xp_atual, 0)

        subidas_neg = xp_sys.adicionar_xp(-50)
        self.assertEqual(subidas_neg, [])
        self.assertEqual(xp_sys.xp_atual, 0)

    def test_callbacks_de_level_up(self):
        """Valida que todos os callbacks registrados são invocados na subida de nível."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        notificacoes = []

        def callback_a(lvl):
            notificacoes.append(f"A:{lvl}")

        def callback_b(lvl):
            notificacoes.append(f"B:{lvl}")

        xp_sys.registrar_callback_level_up(callback_a)
        xp_sys.registrar_callback_level_up(callback_b)

        xp_sys.adicionar_xp(100)  # Sobe de 1 para 2 e para 3

        self.assertEqual(notificacoes, ["A:2", "B:2", "A:3", "B:3"])


if __name__ == "__main__":
    unittest.main()
