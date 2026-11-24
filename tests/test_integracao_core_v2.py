import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame

from src.armas import (
    BastaoChoque,
    LancaChamas,
    RifleArco,
    SMGCompacta,
)
from src.cenas.gameplay import GameplayScene
from src.sistemas.sistema_conquistas import SistemaConquistas
from src.sistemas.sistema_drops import SistemaDrops
from src.utils import constantes as C


class TestIntegracaoCoreV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        if not pygame.get_init():
            pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((C.LARGURA_TELA, C.ALTURA_TELA))

    def test_constantes_v2_e_asset_paths(self):
        self.assertEqual(C.INIMIGO_PADRAO_HP, 18)
        self.assertEqual(C.INIMIGO_RAPIDO_HP, 10)
        self.assertEqual(C.MELEE_DANO, 20)
        self.assertEqual(C.MELEE_ALVOS_MAX, 6)
        self.assertEqual(C.MELEE_ARCO_GRAUS, 120.0)
        self.assertEqual(C.PISTOLA_DANO, 12)
        self.assertEqual(C.SPAWN_MAX_ATIVOS, 95)
        self.assertEqual(C.SPAWN_MAX_RANGED, 4)
        self.assertEqual(C.SPAWN_MAX_IMPRESSORA, 2)
        self.assertEqual(C.SPAWN_MAX_TANK, 3)
        self.assertEqual(C.DASH_PARRY_META, 15)
        self.assertEqual(C.BOSS_GELADEIRA_HP_BASE, 68000)
        self.assertEqual(C.GELADEIRA_TSUNAMI_HP, 68000)
        self.assertAlmostEqual(C.MUSICA_LOOKAHEAD_SEGUNDOS, 0.50)
        self.assertAlmostEqual(C.LATENCIA_PING_ATRASO_S, 0.08)
        self.assertEqual(C.TOTAL_CONFIGS_GAMEPLAY, 28)
        self.assertEqual(C.MINIBOSS_CICLOS_RUN, 3)
        self.assertEqual(C.MINIBOSS_ESCALA_HP_CICLOS, (1.0, 1.25, 1.50))

        for chave in (
            "arma_bastao_choque",
            "arma_smg_compacta",
            "arma_rifle_arco",
            "arma_lanca_chamas",
            "icon_dash_protocolo",
            "icon_dash_rastro",
            "icon_garbage_collector",
            "icon_latencia_ping",
            "icon_modo_wireframe",
        ):
            self.assertIn(chave, C.ASSET_PATHS)

    def test_sistema_drops_pool_armas_especiais_gating_e_micro_sucata(self):
        drops = SistemaDrops()
        pool_base = drops.obter_pool_armas_especiais(sistema_conquistas=None)
        self.assertNotIn(RifleArco, pool_base)
        self.assertNotIn(LancaChamas, pool_base)

        sc = SistemaConquistas()
        sc.recompensas["arma"].add("rifle_arco")
        sc.recompensas["arma"].add("lanca_chamas")
        pool_desbloq = drops.obter_pool_armas_especiais(sistema_conquistas=sc)
        self.assertIn(RifleArco, pool_desbloq)
        self.assertIn(LancaChamas, pool_desbloq)

        arma_esp = SimpleNamespace(municao_max=100, municao_atual=50)
        jogador = SimpleNamespace(
            x=100.0,
            y=100.0,
            largura=32,
            altura=32,
            vivo=True,
            arma_especial=arma_esp,
            armas=[],
            ganhar_xp=MagicMock(),
        )
        criados = drops.gerar_micro_sucata(116.0, 116.0, quantidade=1)
        criados[0].x = 105.0
        criados[0].y = 105.0
        eventos = drops.coletar_jogador(jogador, sistema_conquistas=sc)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo"], "micro_sucata")
        self.assertEqual(arma_esp.municao_atual, 60)

    def test_gameplay_scene_init_bastao_sfx_musica_hitstop_e_boss_ciclo3(self):
        cena = GameplayScene()
        self.assertEqual(cena.spawner.max_ativos, C.SPAWN_MAX_ATIVOS)
        self.assertIsNotNone(cena.sistema_combo)
        self.assertIsNotNone(cena.efeitos_combate)
        self.assertEqual(cena.hologramas, [])

        # Preserva BastaoChoque _arco_graus_base e _cooldown_base em aplicar_modificadores()
        bastao = BastaoChoque()
        cena.jogador.armas[0] = bastao
        cena.aplicar_modificadores()
        self.assertAlmostEqual(bastao.arco_graus, 95.0)
        self.assertAlmostEqual(bastao.cooldown, 0.42)

        # Mapeamento SFX das 4 novas armas
        self.assertIsNotNone(cena._obter_sfx_arma(BastaoChoque()))
        self.assertIsNotNone(cena._obter_sfx_arma(SMGCompacta()))
        self.assertIsNotNone(cena._obter_sfx_arma(RifleArco()))
        self.assertIsNotNone(cena._obter_sfx_arma(LancaChamas()))

        # Musica atualiza mesmo durante hitstop_timer > 0 com trava_assault quando ha elite
        cena.hitstop_timer = 0.25
        elite_stub = SimpleNamespace(is_elite=True, vivo=True, is_boss=False)
        cena.inimigos = [elite_stub]
        with patch.object(cena.sistema_musica, "atualizar") as mock_mus:
            cena.loop(dt=1.0 / 60.0)
            mock_mus.assert_called_once()
            kwargs = mock_mus.call_args.kwargs
            self.assertTrue(kwargs["trava_assault"])
            self.assertFalse(kwargs["pausar_transicao"])

        # Gatilho de Boss no 3o ciclo musical (Opcao A)
        cena.hitstop_timer = 0.0
        cena.inimigos = []
        cena.sistema_musica.ciclos_assault_concluidos = C.MINIBOSS_CICLOS_RUN
        cena.teclado = MagicMock()
        cena.teclado.key_down.return_value = False
        cena.teclado.key_pressed.return_value = False
        cena.mouse = MagicMock()
        cena.mouse.button_down.return_value = False
        cena.mouse.button_pressed.return_value = False
        cena.mouse.get_position.return_value = (640, 360)
        with patch.object(cena.sistema_musica, "consumir_evento_assault_intro", return_value=True):
            cena.loop(dt=1.0 / 60.0)
        self.assertTrue(cena.boss_grace_period_ativo)
        self.assertGreater(cena.pulso_assault_intro_timer, 0.0)

    def test_holograma_clone_agro_propulsor_e_vitoria_boss_ctx(self):
        from src.entidades.holograma import EntidadeHolograma

        cena = GameplayScene()
        # 1. propulsor_instavel deve acelerar recarga (1.35), nao reduzir (0.70)
        cena.gerenciador_config.desbloqueadas.add("dash_protocolo")
        cena.gerenciador_config.definir_valor("dash_protocolo", "propulsor_instavel")
        cena.aplicar_modificadores()
        self.assertEqual(cena.jogador.dash_cargas_max, 2)
        self.assertAlmostEqual(cena.jogador.dash_recarga_mult, 1.35)

        # 2. EntidadeHolograma.update(dt, inimigos=...) + explosao clone_agro + pruning via vivo
        holo = EntidadeHolograma(x=100.0, y=100.0, modo="clone_agro", duracao=0.01)
        inim = SimpleNamespace(
            x=110.0,
            y=110.0,
            largura=28,
            altura=28,
            vivo=True,
            velocidade=0.0,
            vx_knockback=0.0,
            vy_knockback=0.0,
            cooldown_contato_atual=0.0,
            update=MagicMock(),
            receber_dano=MagicMock(),
        )
        cena.inimigos = [inim]
        cena.hologramas = [holo]
        cena.teclado = MagicMock()
        cena.teclado.key_down.return_value = False
        cena.teclado.key_pressed.return_value = False
        cena.mouse = MagicMock()
        cena.mouse.button_down.return_value = False
        cena.mouse.button_pressed.return_value = False
        cena.mouse.get_position.return_value = (640, 360)
        cena.loop(dt=0.02)
        inim.receber_dano.assert_called_once_with(45)
        self.assertEqual(cena.hologramas, [])

        # 3. _registrar_fim_partida(vitoria=True) envia chaves canonicas de vitoria_boss
        cena.gerenciador_config.desbloqueadas.update(["cores_invertidas", "vsync"])
        cena.gerenciador_config.definir_valor("cores_invertidas", "ligado")
        cena.gerenciador_config.definir_valor("vsync", "desligado")
        cena.partida_registrada = False
        with patch.object(cena.gerenciador_config, "salvar_arquivo"):
            with patch.object(cena.sistema_conquistas, "registrar_evento", return_value=[]) as mock_reg:
                cena._registrar_fim_partida(vitoria=True)
                mock_reg.assert_called_once()
                evento_nome, _, ctx = mock_reg.call_args.args
                self.assertEqual(evento_nome, "vitoria_boss")
                self.assertTrue(ctx["cores_invertidas"])
                self.assertTrue(ctx["vsync_desligado"])
                self.assertIn("configs_nao_neutras", ctx)
                self.assertIn("sem_dano_f3", ctx)


if __name__ == "__main__":
    unittest.main()
