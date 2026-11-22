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
        base = 35 + 20 * lvl + 10 * (lvl ^ 2)
        """
        valores_esperados_1_a_10 = {
            1: 65,     # 35 + 20 + 10
            2: 115,    # 35 + 40 + 40
            3: 185,    # 35 + 60 + 90
            4: 275,    # 35 + 80 + 160
            5: 385,    # 35 + 100 + 250
            6: 515,    # 35 + 120 + 360
            7: 665,    # 35 + 140 + 490
            8: 835,    # 35 + 160 + 640
            9: 1025,   # 35 + 180 + 810
            10: 1235,  # 35 + 200 + 1000
        }

        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        for lvl, xp_esperado in valores_esperados_1_a_10.items():
            base_calculada = 35 + 20 * lvl + 10 * (lvl ** 2)
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
            11: 1099,  # base = 1465 -> 1465 * 0.75 = 1098.75 -> 1099
            12: 1286,  # base = 1715 -> 1715 * 0.75 = 1286.25 -> 1286
            13: 1489,  # base = 1985 -> 1985 * 0.75 = 1488.75 -> 1489
            14: 1706,  # base = 2275 -> 2275 * 0.75 = 1706.25 -> 1706
            15: 1939,  # base = 2585 -> 2585 * 0.75 = 1938.75 -> 1939
            16: 2186,  # base = 2915 -> 2915 * 0.75 = 2186.25 -> 2186
            17: 2449,  # base = 3265 -> 3265 * 0.75 = 2448.75 -> 2449
            18: 2726,  # base = 3635 -> 3635 * 0.75 = 2726.25 -> 2726
            19: 3019,  # base = 4025 -> 4025 * 0.75 = 3018.75 -> 3019
            20: 3326,  # base = 4435 -> 4435 * 0.75 = 3326.25 -> 3326
        }

        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        for lvl, xp_esperado in valores_esperados_11_a_20.items():
            base = 35 + 20 * lvl + 10 * (lvl ** 2)
            calculo_manual = int(round(base * 0.75))
            self.assertEqual(xp_esperado, calculo_manual)
            self.assertEqual(xp_sys.xp_para_proximo_nivel(lvl), xp_esperado, f"Nível {lvl} falhou")
            self.assertEqual(xp_sys.calcular_xp_necessario(lvl), xp_esperado, f"Nível {lvl} via alias falhou")
            self.assertEqual(SistemaXP.calcular_xp_para_nivel(lvl), xp_esperado, f"Nível {lvl} estático falhou")

    def test_property_xp_necessario_retorna_nivel_atual(self):
        """Verifica se a propriedade xp_necessario reflete o nível corrente."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        self.assertEqual(xp_sys.xp_necessario, 65)

        xp_sys.nivel = 10
        self.assertEqual(xp_sys.xp_necessario, 1235)

        xp_sys.nivel = 11
        self.assertEqual(xp_sys.xp_necessario, 1099)

        xp_sys.nivel = 19
        self.assertEqual(xp_sys.xp_necessario, 3019)

    def test_ganho_xp_e_subida_de_nivel_simples(self):
        """Valida avanço para o próximo nível com valor exato."""
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        subidas = xp_sys.adicionar_xp(65)

        self.assertEqual(subidas, [2])
        self.assertEqual(xp_sys.nivel, 2)
        self.assertEqual(xp_sys.xp_atual, 0)
        self.assertEqual(xp_sys.xp_total, 65)

    def test_multi_level_carryover(self):
        """
        Valida que o transbordo de XP avança múltiplos níveis consecutivamente:
        Nível 1 (custo 65) + Nível 2 (custo 115) + Nível 3 (custo 185) = 365 XP.
        Recebendo 380 XP:
        - 1 -> 2 (restam 315)
        - 2 -> 3 (restam 200)
        - 3 -> 4 (restam 15)
        - Nível final: 4, xp_atual: 15 / 275
        """
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        subidas = xp_sys.ganhar_xp(380)

        self.assertEqual(subidas, [2, 3, 4])
        self.assertEqual(xp_sys.nivel, 4)
        self.assertEqual(xp_sys.xp_atual, 15)
        self.assertEqual(xp_sys.xp_total, 380)

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

        xp_sys.adicionar_xp(180)  # Sobe de 1 para 2 (65) e para 3 (115)

        self.assertEqual(notificacoes, ["A:2", "B:2", "A:3", "B:3"])


if __name__ == "__main__":
    unittest.main()
