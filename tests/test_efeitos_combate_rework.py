import math
from types import SimpleNamespace
import unittest

from src.entidades.projetil import Projetil
from src.sistemas.config_efeitos import ModificadoresGameplay
from src.sistemas.efeitos_combate import ContextoCombate, GerenciadorEfeitosCombate
from src.sistemas.sistema_conquistas import SistemaConquistas


def _criar_ctx(inimigos=None, projeteis=None, jogador=None, conquistas=None):
    jog = jogador or SimpleNamespace(
        x=100.0,
        y=100.0,
        largura=32,
        altura=32,
        hp=150,
        hp_max=150,
        dash_cooldown_restante=2.0,
        mira_x=300.0,
        mira_y=100.0,
    )
    return ContextoCombate(
        cena=None,
        jogador=jog,
        inimigos=inimigos if inimigos is not None else [],
        projeteis=projeteis if projeteis is not None else [],
        drops=[],
        sistema_conquistas=conquistas,
        hologramas=[],
    )


class TestEfeitosCombateRework(unittest.TestCase):
    def test_reconstruir_neutro_instancia_zero_handlers(self):
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(ModificadoresGameplay(), [])
        self.assertEqual(len(ger.efeitos), 0)
        self.assertIsNone(ger.obter_efeito("latencia_ping"))

    def test_decisao_2_latencia_ping_80ms_todas_acoes_e_eco(self):
        mods = ModificadoresGameplay(latencia_ping=True)
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        ef = ger.obter_efeito("latencia_ping")
        self.assertIsNotNone(ef)
        self.assertAlmostEqual(ef.atraso_s, 0.080, places=3)

        for tipo in ("disparo", "melee", "parry", "dash"):
            ef.agendar_acao(tipo, {"ok": True}, (100.0, 100.0), 0.5)

        # Aos 0.05s nenhuma ação deve ter disparado
        self.assertEqual(ef.consumir_acoes_prontas(0.050), [])
        # Aos 0.085s todas as 4 disparam em ordem FIFO
        prontas = ef.consumir_acoes_prontas(0.035)
        self.assertEqual([a["tipo"] for a in prontas], ["disparo", "melee", "parry", "dash"])

        # Eco de pacote (+30% dano após 0.30s sem recursão)
        inim = SimpleNamespace(x=200.0, y=100.0, largura=32, altura=32, hp=100, vivo=True)
        ctx = _criar_ctx(inimigos=[inim])
        ger.disparar_ao_impacto(ctx, inim, 100, fonte="arma")
        ger.disparar_ao_tick(ctx, 0.20)
        self.assertEqual(inim.hp, 100)
        ger.disparar_ao_tick(ctx, 0.15)
        self.assertEqual(inim.hp, 70)

    def test_inercia_cinetica_somente_derrapando(self):
        mods = ModificadoresGameplay(inercia_cinetica_nivel=2)
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        parado_a = SimpleNamespace(x=100.0, y=100.0, largura=32, altura=32, hp=50, vivo=True, vx_knockback=0.0, vy_knockback=0.0)
        parado_b = SimpleNamespace(x=110.0, y=100.0, largura=32, altura=32, hp=50, vivo=True, vx_knockback=0.0, vy_knockback=0.0)
        ctx = _criar_ctx(inimigos=[parado_a, parado_b])

        # Sem derrapagem, nenhuma colisão ocorre
        ger.disparar_ao_tick(ctx, 0.016)
        self.assertEqual(parado_a.hp, 50)
        self.assertEqual(parado_b.hp, 50)

        # Com derrapagem, parado_a atinge parado_b
        parado_a.em_derrapagem_cinetica = True
        parado_a.vx_knockback = 250.0
        ger.disparar_ao_tick(ctx, 0.016)
        self.assertLess(parado_b.hp, 50)

    def test_garbage_collector_ciclo_e_conquista(self):
        mods = ModificadoresGameplay(garbage_collector=True)
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])
        gc = ger.obter_efeito("garbage_collector")
        self.assertIsNotNone(gc)

        conq = SistemaConquistas()
        proj_inimigos = [
            Projetil(x=120.0, y=120.0, dir_x=-1.0, dir_y=0.0, dono="inimigo")
            for _ in range(15)
        ]
        ctx = _criar_ctx(projeteis=proj_inimigos, conquistas=conq)

        # Enche RAM em 12s
        ger.disparar_ao_tick(ctx, 12.0)
        self.assertTrue(gc.disparos_travados)
        # Conclui pausa de 0.8s
        ger.disparar_ao_tick(ctx, 0.85)
        self.assertFalse(gc.disparos_travados)
        self.assertGreater(gc.buff_cadencia_timer, 0.0)
        self.assertTrue(all(not p.ativo for p in proj_inimigos))
        self.assertIn("limpeza_de_disco", conq.unicas_concluidas)

    def test_reworks_zoom_flick_bullet_hell_pinhata_clarao_polaridade_wireframe(self):
        mods = ModificadoresGameplay(
            zoom_balistica_longa=True,
            zoom_queima_roupa_mult=0.85,
            zoom_execucao_cd_red=1.0,
            zoom_execucao_limiar_hp=0.20,
            flick_shot_ativo=True,
            inimigos_ranged_bullet_hell=True,
            pinhata_hardware_nivel=1,
            clarao_fotossensivel=True,
            polaridade_invertida=True,
            modo_wireframe=True,
        )
        ger = GerenciadorEfeitosCombate()
        ger.reconstruir(mods, [])

        inim = SimpleNamespace(
            x=600.0,
            y=100.0,
            largura=32,
            altura=32,
            hp=15,
            hp_max=100,
            vivo=True,
            sprite_key="inimigo_blindado",
            atordoado_timer=0.0,
        )
        ctx = _criar_ctx(inimigos=[inim])

        flick = ger.obter_efeito("flick_shot")
        flick.registrar_movimento_mira(0.0, True)
        flick.registrar_movimento_mira(math.radians(90.0), False)
        self.assertTrue(flick.flick_pronto)

        ger.disparar_ao_parry(ctx, [])
        p = Projetil(x=100.0, y=100.0, dir_x=1.0, dir_y=0.0, velocidade=400.0, dano=20)
        ger.disparar_ao_disparo(ctx, None, [p])
        self.assertGreater(p.velocidade, 400.0)
        self.assertTrue(p.sobrecarregado)

        res = ger.disparar_ao_impacto(ctx, inim, p.dano, fonte=p)
        self.assertTrue(res.get("executar"))
        self.assertTrue(res.get("critico_forcado"))
        self.assertGreater(res.get("dano_extra", 0), 0)
        self.assertEqual(res.get("micro_sucata"), 2)  # 85% HP perdido -> cruzou 33% e 66%

        ger.disparar_ao_abate(ctx, inim)
        self.assertLess(ctx.jogador.dash_cooldown_restante, 2.0)


if __name__ == "__main__":
    unittest.main()
