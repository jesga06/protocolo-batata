import unittest
from src.armas.bastao_choque import BastaoChoque
from src.armas.smg_compacta import SMGCompacta
from src.armas.rifle_arco import RifleArco
from src.armas.lanca_chamas import LancaChamas
from src.entidades.jogador import Jogador
from src.utils.constantes import MELEE_COOLDOWN


class _InimigoStub:
    def __init__(self, x: float, y: float, largura: int = 28, altura: int = 28, hp: int = 100):
        self.x = float(x)
        self.y = float(y)
        self.largura = largura
        self.altura = altura
        self.hp = hp
        self.vivo = True
        self.em_fase = False
        self.dano_recebido = 0
        self.knockbacks = []

    def receber_dano(self, qtd, **_kwargs):
        self.dano_recebido += qtd
        self.hp -= qtd
        if self.hp <= 0:
            self.vivo = False

    def aplicar_knockback(self, dx, dy, forca):
        self.knockbacks.append((dx, dy, forca))


class _ProjetilStub:
    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        self.largura = 8
        self.altura = 8
        self.ativo = True
        self.dono = "inimigo"
        self.velocidade = 300.0
        self.dano = 10
        self.dir_x = -1.0
        self.dir_y = 0.0
        self.tempo_vida = 1.0
        self.tempo_vida_restante = 1.0
        self.alvos_atingidos = set()


class TestNovasArmas(unittest.TestCase):
    def test_bastao_choque_atributos_e_parry(self):
        bastao = BastaoChoque()
        self.assertEqual(bastao.slot, 1)
        self.assertEqual(bastao.arco_graus, 95.0)
        self.assertLess(bastao.cooldown, MELEE_COOLDOWN)

        inimigo = _InimigoStub(30.0, -14.0)
        atingidos = bastao.executar_ataque(0.0, 0.0, [inimigo], mira_x=100.0, mira_y=0.0)
        self.assertEqual(len(atingidos), 1)
        self.assertEqual(inimigo.dano_recebido, bastao.dano)

        bastao.tempo_recarga_restante = 0.0
        self.assertTrue(bastao.executar_parry(angulo=0.0))
        proj = _ProjetilStub(40.0, -4.0)
        refletidos = bastao.tentar_parry_projeteis(0.0, 0.0, [proj], angulo_mira=0.0)
        self.assertEqual(len(refletidos), 1)
        self.assertEqual(proj.dono, "jogador")

    def test_smg_compacta_calor_zona_ideal_e_trava(self):
        smg = SMGCompacta()
        self.assertEqual(smg.slot, 2)
        self.assertTrue(smg.municao_infinita)
        self.assertTrue(smg.usa_calor)

        # Dispara até entrar na zona ideal (65..95)
        smg.calor_atual = 70.0
        self.assertTrue(smg.em_zona_ideal)
        projs = smg.disparar(0.0, 0.0, 100.0, 0.0)
        self.assertEqual(len(projs), 1)
        self.assertTrue(projs[0].superaquecido)
        self.assertGreater(projs[0].dano, smg.dano)

        # Superaquecimento em 100% trava por 1.0s
        smg.tempo_recarga_restante = 0.0
        smg.calor_atual = 95.0
        smg.disparar(0.0, 0.0, 100.0, 0.0)
        self.assertTrue(smg.superaquecida)
        self.assertFalse(smg.pode_atirar())

        smg.update(0.5)
        self.assertTrue(smg.superaquecida)
        smg.update(0.6)
        self.assertFalse(smg.superaquecida)
        self.assertEqual(smg.calor_atual, 0.0)

    def test_rifle_arco_beam_continuo(self):
        rifle = RifleArco()
        self.assertTrue(rifle.eh_continua)
        self.assertEqual(rifle.slot, 3)

        alvo_perto_mira = _InimigoStub(120.0, -14.0)
        alvo_fora_cone = _InimigoStub(0.0, 150.0)
        mun_inicial = rifle.municao_atual

        eventos = rifle.atualizar_fluxo(0.10, True, 0.0, 0.0, 200.0, 0.0, [alvo_fora_cone, alvo_perto_mira])
        self.assertTrue(rifle.feixe_ativo)
        self.assertIs(rifle.alvo_travado, alvo_perto_mira)
        self.assertLess(rifle.municao_atual, mun_inicial)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo_fluxo"], "arco")
        self.assertGreater(eventos[0]["aplicar_slow"], 0.0)
        self.assertGreater(eventos[0]["bonus_crit_overvolt"], 0.0)

    def test_lanca_chamas_cone_continuo(self):
        lc = LancaChamas()
        self.assertTrue(lc.eh_continua)
        self.assertEqual(lc.slot, 3)

        dentro_1 = _InimigoStub(80.0, -14.0)
        dentro_2 = _InimigoStub(100.0, 10.0)
        longe = _InimigoStub(350.0, 0.0)
        mun_inicial = lc.municao_atual

        eventos = lc.atualizar_fluxo(0.10, True, 0.0, 0.0, 200.0, 0.0, [dentro_1, dentro_2, longe])
        self.assertTrue(lc.fluxo_ativo)
        self.assertLess(lc.municao_atual, mun_inicial)
        self.assertEqual(len(eventos), 2)
        self.assertTrue(all(ev["tipo_fluxo"] == "chama" and ev["aplicar_queimadura"] > 0.0 for ev in eventos))

    def test_jogador_loadout_preserva_smg_no_slot2(self):
        j = Jogador(100.0, 100.0)
        j.aplicar_loadout("bastao_choque", "smg_compacta")
        self.assertEqual(type(j.armas[0]).__name__, "BastaoChoque")
        self.assertEqual(type(j.armas[1]).__name__, "SMGCompacta")

        j.update(0.016)
        self.assertEqual(type(j.armas[1]).__name__, "SMGCompacta")


if __name__ == "__main__":
    unittest.main()
