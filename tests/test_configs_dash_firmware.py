from types import SimpleNamespace
import unittest

from src.entidades.holograma import EntidadeHolograma
from src.entidades.projetil import Projetil
from src.sistemas.config_efeitos import ModificadoresGameplay
from src.sistemas.efeitos_combate import ContextoCombate, GerenciadorEfeitosCombate


def _criar_ctx(inimigos=None, projeteis=None, jogador=None):
    jog = jogador or SimpleNamespace(
        x=100.0,
        y=100.0,
        largura=32,
        altura=32,
        hp=150,
        hp_max=150,
        dash_cooldown_restante=2.0,
        dash_cargas_max=1,
        dash_recarga_mult=1.0,
        dash_sem_iframes=False,
        enraizado_timer=0.0,
        riposte_invuln_timer=0.0,
        mira_x=350.0,
        mira_y=100.0,
        arma_especial=SimpleNamespace(municao_atual=10, municao_max=100),
    )
    return ContextoCombate(
        cena=None,
        jogador=jog,
        inimigos=inimigos if inimigos is not None else [],
        projeteis=projeteis if projeteis is not None else [],
        drops=[],
        hologramas=[],
    )


class TestConfigsDashFirmware(unittest.TestCase):
    def test_sombra_espelho_guarda_anti_recursao_e_teto_12(self):
        mods = ModificadoresGameplay(dash_protocolo="sombra_espelho")
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        ctx = _criar_ctx()
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (220.0, 100.0))
        self.assertEqual(len(ctx.hologramas), 1)

        # Dispara 20 projéteis originais -> teto rígido de 12 réplicas
        originais = [
            Projetil(x=100.0, y=100.0, dir_x=1.0, dir_y=0.0, dano=20)
            for _ in range(20)
        ]
        replicas = ger.disparar_ao_disparo(ctx, None, originais)
        self.assertEqual(len(replicas), 12)
        for rep in replicas:
            self.assertTrue(rep.origem_holograma)
            self.assertTrue(rep.eh_replica)
            self.assertEqual(rep.dano, 11)

        # Passar réplicas de volta em disparar_ao_disparo deve retornar [] (zero recursão)
        self.assertEqual(ger.disparar_ao_disparo(ctx, None, replicas), [])

        # profundidade_recursao >= 1 também bloqueia
        ctx.profundidade_recursao = 1
        self.assertEqual(ger.disparar_ao_disparo(ctx, None, originais), [])

    def test_rollback_estado_ring_buffer_e_restauracao(self):
        mods = ModificadoresGameplay(dash_protocolo="rollback_estado")
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])
        ctx = _criar_ctx()

        # Grava snapshot inicial em (100, 100, 150)
        ger.disparar_ao_tick(ctx, 0.10)
        # Jogador se move e perde HP
        ctx.jogador.x = 500.0
        ctx.jogador.y = 400.0
        ctx.jogador.hp = 50
        ger.disparar_ao_tick(ctx, 0.10)

        ger.disparar_ao_dash(ctx, (500.0, 400.0), (550.0, 400.0))
        self.assertEqual(ctx.jogador.x, 100.0)
        self.assertEqual(ctx.jogador.y, 100.0)
        self.assertEqual(ctx.jogador.hp, 100)

    def test_thread_fantasma_clone_agro_e_explosao(self):
        mods = ModificadoresGameplay(dash_rastro="thread_fantasma")
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        inim = SimpleNamespace(x=150.0, y=100.0, largura=32, altura=32, vivo=True, pos_alvo_override=None)
        ctx = _criar_ctx(inimigos=[inim])
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (200.0, 100.0))
        self.assertEqual(len(ctx.hologramas), 1)
        clone: EntidadeHolograma = ctx.hologramas[0]

        res_vivo = clone.update(0.5, [inim])
        self.assertEqual(res_vivo, {})
        self.assertIsNotNone(inim.pos_alvo_override)

        res_exp = clone.update(2.5, [inim])
        self.assertTrue(res_exp.get("explodir"))
        self.assertIsNone(inim.pos_alvo_override)

    def test_propulsor_instavel_e_parry_avancado(self):
        mods = ModificadoresGameplay(
            dash_protocolo="propulsor_instavel",
            parry_precisao="postura_riposte",
            parry_efeito="firewall_estatico",
        )
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])
        proj = Projetil(x=145.0, y=100.0, dir_x=-1.0, dir_y=0.0, dono="inimigo")
        ctx = _criar_ctx(projeteis=[proj])

        ger.disparar_ao_tick(ctx, 0.016)
        self.assertEqual(ctx.jogador.dash_cargas_max, 2)
        self.assertTrue(ctx.jogador.dash_sem_iframes)

        ger.disparar_ao_parry(ctx, [])
        self.assertAlmostEqual(ctx.jogador.enraizado_timer, 0.45)
        self.assertAlmostEqual(ctx.jogador.riposte_invuln_timer, 0.45)

        ger.disparar_ao_tick(ctx, 0.05)
        self.assertFalse(proj.ativo)

    def test_subprocesso_atrasado_segue_posicao_atual_do_jogador(self):
        mods = ModificadoresGameplay(dash_rastro="subprocesso_atrasado")
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        inim_no_trajeto_novo = SimpleNamespace(x=240.0, y=284.0, largura=32, altura=32, vivo=True, hp=100, stun_timer=0.0)
        inim_destino_antigo = SimpleNamespace(x=204.0, y=84.0, largura=32, altura=32, vivo=True, hp=100, stun_timer=0.0)
        ctx = _criar_ctx(inimigos=[inim_no_trajeto_novo, inim_destino_antigo])
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (220.0, 100.0))

        # Jogador anda para (400, 500) antes do feixe disparar
        ctx.jogador.x = 400.0
        ctx.jogador.y = 500.0
        ger.disparar_ao_tick(ctx, 0.80)

        ef_rastro = ger.obter_efeito("dash_rastro")
        self.assertEqual(len(ef_rastro.feixes_subprocesso), 1)
        feixe = ef_rastro.feixes_subprocesso[0]
        self.assertAlmostEqual(feixe["destino"][0], 416.0)
        self.assertAlmostEqual(feixe["destino"][1], 516.0)
        self.assertLess(inim_no_trajeto_novo.hp, 100)
        self.assertEqual(inim_destino_antigo.hp, 100)

    def test_sombra_espelho_atira_na_mira_cena_e_replica_parry(self):
        mods = ModificadoresGameplay(dash_protocolo="sombra_espelho")
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        jog_sem_mira = SimpleNamespace(
            x=100.0,
            y=100.0,
            largura=32,
            altura=32,
            hp=150,
            hp_max=150,
            dash_cooldown_restante=1.0,
            arma_melee=SimpleNamespace(parry_janela_id=7, parry_alcance=110.0, parry_duracao=0.25),
        )
        cena_mock = SimpleNamespace(
            largura_arena=2240.0,
            altura_arena=1560.0,
            _ultimo_mouse_mundo=(236.0, 500.0),
        )
        proj_perto_sombra = Projetil(x=220.0, y=120.0, dir_x=0.0, dir_y=-1.0, dono="inimigo", dano=20)
        ctx = ContextoCombate(
            cena=cena_mock,
            jogador=jog_sem_mira,
            inimigos=[],
            projeteis=[proj_perto_sombra],
            drops=[],
            hologramas=[],
        )
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (236.0, 100.0))
        self.assertEqual(len(ctx.hologramas), 1)

        # Disparo deve mirar para baixo em direção a (236, 500), não horizontalmente
        orig = [Projetil(x=100.0, y=100.0, dir_x=1.0, dir_y=0.0, dano=20)]
        reps = ger.disparar_ao_disparo(ctx, None, orig)
        self.assertEqual(len(reps), 1)
        self.assertAlmostEqual(reps[0].dir_x, 0.0, places=2)
        self.assertGreater(reps[0].dir_y, 0.95)

        # Parry deve ser replicado ao redor da sombra, rebatendo proj_perto_sombra na mira
        ger.disparar_ao_parry(ctx, [])
        self.assertEqual(proj_perto_sombra.dono, "jogador")
        self.assertTrue(proj_perto_sombra.refletido_parry)
        self.assertGreater(proj_perto_sombra.dir_y, 0.95)

    def test_todos_8_chips_de_firmware(self):
        chips = [
            "gatilho_duplo",
            "recarga_tatica",
            "adrenalina_overclock",
            "canhoes_perimetrais",
            "sobrecarga_estrutural",
            "overclock_termico",
            "sandbox_isolada",
            "reset_voraz",
        ]

        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(ModificadoresGameplay(), chips)
        for cid in chips:
            self.assertIsNotNone(ger.obter_efeito(cid))

        proj_inim = Projetil(x=120.0, y=100.0, dir_x=-1.0, dir_y=0.0, dono="inimigo")
        inim_elite = SimpleNamespace(
            x=200.0, y=100.0, largura=32, altura=32, hp=200, hp_max=200,
            vivo=True, eh_elite=True, sprite_key="inimigo_blindado",
        )
        ctx = _criar_ctx(inimigos=[inim_elite], projeteis=[proj_inim])

        ger.disparar_ao_tick(ctx, 0.016)

        # recarga_tatica: 3 dashes recuperam munição Slot 3 (municao_atual)
        for _ in range(3):
            ger.disparar_ao_dash(ctx, (100.0, 100.0), (150.0, 100.0))
        self.assertEqual(ctx.jogador.arma_especial.municao_atual, 35)

        # sandbox_isolada: parry cria cúpula fixa no chão e bloqueia projétil inimigo
        ger.disparar_ao_parry(ctx, [])
        ctx.jogador.x = 900.0  # Jogador se afasta; cúpula permanece fixa na posição do parry
        ger.disparar_ao_tick(ctx, 0.05)
        self.assertFalse(proj_inim.ativo)

        # gatilho_duplo + canhoes_perimetrais no disparo
        tiro = Projetil(x=900.0, y=100.0, dir_x=1.0, dir_y=0.0, dano=20)
        extras = ger.disparar_ao_disparo(ctx, None, [tiro])
        self.assertEqual(len(extras), 5)
        pellets_canhao = [e for e in extras if getattr(e, "aplicar_queimadura", 0.0) > 0.0]
        self.assertEqual(len(pellets_canhao), 4)
        self.assertAlmostEqual(pellets_canhao[0].knockback_forca, 15.75)

        # sobrecarga_estrutural no impacto
        res_imp = ger.disparar_ao_impacto(ctx, inim_elite, 20, fonte=tiro)
        self.assertTrue(res_imp.get("vulneravel"))

        # overclock_termico no dano recebido
        ger.disparar_ao_dano_recebido(ctx, 10)
        self.assertGreater(ger.obter_efeito("overclock_termico").carga_residual, 0.0)

        # reset_voraz + adrenalina_overclock no abate
        ctx.jogador.dash_cooldown_restante = 2.0
        ger.disparar_ao_abate(ctx, inim_elite)
        self.assertAlmostEqual(ctx.jogador.dash_cooldown_restante, 1.0)
        self.assertGreater(ger.obter_efeito("adrenalina_overclock").timer, 0.0)

    def test_dash_teleporte_exaustao_vacuo_subprocesso_e_ventoinha_e_is_boss(self):
        # 1. teleporte_buffer + exaustao_termica
        dano_log = []
        inim = SimpleNamespace(
            x=150.0, y=100.0, largura=32, altura=32, vivo=True, is_boss=False,
            slow_timer=0.0, slow_fator=1.0,
            receber_dano=lambda q: dano_log.append(q),
        )
        boss = SimpleNamespace(
            x=150.0, y=100.0, largura=32, altura=32, vivo=True, is_boss=True,
            pos_alvo_override=None,
        )
        holo = EntidadeHolograma(x=100.0, y=100.0, modo="clone_agro")
        holo.update(0.1, [inim, boss])
        self.assertIsNotNone(inim.pos_alvo_override)
        self.assertIsNone(boss.pos_alvo_override)

        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(ModificadoresGameplay(dash_protocolo="teleporte_buffer", dash_rastro="exaustao_termica"), [])
        ctx = _criar_ctx(inimigos=[inim])
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (250.0, 100.0))
        self.assertEqual(ctx.jogador.x, 250.0)
        self.assertGreater(len(dano_log), 0)
        self.assertGreater(ger.obter_efeito("dash_rastro").sobreaquecimento_timer, 0.0)

        # 2. vacuo_io + subprocesso_atrasado + ventoinha_360
        ger.reconstruir(ModificadoresGameplay(dash_rastro="vacuo_io"), [])
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (160.0, 100.0))
        ger.disparar_ao_tick(ctx, 0.05)
        self.assertAlmostEqual(ctx.jogador.dash_alcance_mult, 0.75)

        ger.reconstruir(ModificadoresGameplay(dash_rastro="subprocesso_atrasado", parry_efeito="ventoinha_360"), [])
        ger.disparar_ao_dash(ctx, (100.0, 100.0), (220.0, 100.0))
        ger.disparar_ao_tick(ctx, 0.80)
        self.assertGreater(inim.slow_timer, 0.0)
        self.assertEqual(inim.slow_fator, 0.0)

        ger.disparar_ao_parry(ctx, [])
        self.assertGreater(ger.obter_efeito("parry_avancado").ventoinha_timer, 0.0)


if __name__ == "__main__":
    unittest.main()
