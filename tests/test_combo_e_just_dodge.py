import unittest
from src.armas.melee import Melee
from src.entidades.jogador import Jogador
from src.sistemas.sistema_combo import SistemaCombo


class TestComboEJustDodge(unittest.TestCase):
    def test_separacao_lmb_rmb_melee(self):
        melee = Melee()
        whiffs = []
        melee.whiff_callback = lambda: whiffs.append(True)

        # LMB (executar_ataque) não abre janela de parry e não pune whiff
        melee.executar_ataque(0.0, 0.0, [], mira_x=50.0, mira_y=0.0)
        self.assertFalse(melee.parry_ativo)
        melee.atualizar(0.25)
        self.assertEqual(len(whiffs), 0)

        # RMB (executar_parry / iniciar_golpe_parry) abre janela e pune whiff ao expirar
        melee.tempo_recarga_restante = 0.0
        ok = melee.executar_parry(angulo=0.0, punir_whiff=True)
        self.assertTrue(ok)
        self.assertTrue(melee.parry_ativo)
        self.assertEqual(melee.parry_janela_id, 1)
        # Spam imediato bloqueado por cooldown
        self.assertFalse(melee.executar_parry(angulo=0.0))

        melee.atualizar(0.20)
        self.assertFalse(melee.parry_ativo)
        self.assertEqual(len(whiffs), 1)

    def test_just_dodge_deterministico_e_propulsor_instavel(self):
        j = Jogador(100.0, 100.0)
        j.dash_desbloqueado = True

        # Invulnerabilidade pós-dano sem Dash NÃO gera Just-Dodge
        j.receber_dano(10)
        self.assertGreater(j.invulnerabilidade_timer, 0.0)
        self.assertFalse(j.em_dash_iframes)
        self.assertFalse(j.consumir_just_dodge())

        # Limpa invuln e executa Dash normal
        j.invulnerabilidade_timer = 0.0
        self.assertTrue(j.iniciar_dash(1.0, 0.0))
        self.assertTrue(j.em_dash_iframes)
        self.assertTrue(j.consumir_just_dodge())
        # Só pode ser consumido 1 vez por Dash
        self.assertFalse(j.consumir_just_dodge())

        # propulsor_instavel (dash_sem_iframes=True) nunca gera Just-Dodge
        j.dash_cooldown_restante = 0.0
        j.dash_ativo_timer = 0.0
        j.dash_iframes_timer = 0.0
        j.dash_cargas_atuais = 1
        j.dash_sem_iframes = True
        self.assertTrue(j.iniciar_dash(1.0, 0.0))
        self.assertFalse(j.em_dash_iframes)
        self.assertFalse(j.consumir_just_dodge())

    def test_trava_anti_bullet_hell_combo(self):
        combo = SistemaCombo()
        self.assertTrue(combo.registrar_parry(janela_id=1))
        self.assertFalse(combo.registrar_parry(janela_id=1))
        self.assertEqual(combo.contagem, 3)

        self.assertTrue(combo.registrar_just_dodge(dash_id=7))
        self.assertFalse(combo.registrar_just_dodge(dash_id=7))
        self.assertEqual(combo.contagem, 6)

    def test_abates_drone_excluidos(self):
        combo = SistemaCombo()
        self.assertFalse(combo.registrar_abate(origem="drone"))
        self.assertEqual(combo.contagem, 0)

        self.assertTrue(combo.registrar_abate(origem="arma"))
        self.assertEqual(combo.contagem, 1)

    def test_unificacao_medidor_estilo_ranks_e_overdrive(self):
        combo = SistemaCombo()
        self.assertEqual(combo.rank, "")

        combo.definir_modo_estilo(True)
        self.assertEqual(combo.rank, "D")

        for _ in range(5):
            combo.registrar_abate("arma")
        self.assertEqual(combo.rank, "C")

        for _ in range(7):
            combo.registrar_abate("arma")
        self.assertEqual(combo.rank, "B")

        for _ in range(10):
            combo.registrar_abate("arma")
        self.assertEqual(combo.rank, "A")
        self.assertFalse(combo.consumir_pulso_overdrive())

        for _ in range(13):
            combo.registrar_abate("arma")
        self.assertEqual(combo.rank, "S")
        self.assertTrue(combo.consumir_pulso_overdrive())
        self.assertFalse(combo.consumir_pulso_overdrive())


if __name__ == "__main__":
    unittest.main()
