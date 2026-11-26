"""
Suíte de Regressão — Configuração Velocidade do Jogo (velocidade_jogo)
Cobre: catálogo/R1/Firmware, separação dt_real vs dt_sim, sub-stepping + isolamento de input,
drops em tempo real, mecânicas 50%..200% (incl. 0,6s freeze real e punição de whiff em 200%),
FSM musical sem HOLD (1x >100%, 2x <100%, troca mid-run) e renderização do relógio duplo.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, CategoriaConfig
from src.sistemas.config_efeitos import calcular_modificadores
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_musica import SistemaMusica
from src.sistemas.sistema_drops import SistemaDrops
from src.entidades.drop import ItemDrop
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.projetil import Projetil
from src.utils.constantes import DASH_COOLDOWN


class _FakeSound:
    def __init__(self, dur: float):
        self._dur = float(dur)

    def get_length(self) -> float:
        return self._dur


class _FakeChannel:
    def __init__(self):
        self.busy = False
        self.queued = None
        self.vol = 1.0

    def play(self, sound, loops=0):
        self.busy = True
        self.queued = None

    def queue(self, sound):
        self.queued = sound

    def get_queue(self):
        return self.queued

    def get_busy(self):
        return self.busy

    def set_volume(self, v):
        self.vol = v

    def stop(self):
        self.busy = False
        self.queued = None

    def fadeout(self, ms):
        self.busy = False


class _DummyTecladoBorda:
    def __init__(self, down_keys=None, pressed_keys=None):
        self._down = set(down_keys or ())
        self._pressed = set(pressed_keys or ())

    def key_down(self, k):
        return k in self._down

    def key_pressed(self, k):
        return k in self._pressed


class TestVelocidadeJogoCatalogoEFirmware(unittest.TestCase):
    def test_catalogo_opcoes_categoria_e_r1(self):
        self.assertIn("velocidade_jogo", CONFIGURACOES_GAMEPLAY)
        cdef = CONFIGURACOES_GAMEPLAY["velocidade_jogo"]
        self.assertEqual(cdef.categoria, CategoriaConfig.EXPERIMENTAL)
        self.assertEqual(cdef.valor_padrao, "100%")
        self.assertEqual(cdef.opcoes["100%"].label, "Padrão")
        self.assertEqual(cdef.opcoes["100%"].modificadores, {})
        self.assertEqual(
            list(cdef.opcoes.keys()),
            ["50%", "75%", "100%", "125%", "150%", "200%"],
        )

    def test_todas_opcoes_nao_neutras_contam_para_firmware(self):
        cfg = GerenciadorConfiguracoes()
        cfg.desbloquear_config("velocidade_jogo")
        self.assertEqual(cfg.contar_configs_nao_neutras(), 0)
        for opt in ("50%", "75%", "125%", "150%", "200%"):
            cfg.definir_valor("velocidade_jogo", opt)
            self.assertEqual(cfg.contar_configs_nao_neutras(), 1, f"{opt} deve contar como não-neutra")
        cfg.definir_valor("velocidade_jogo", "100%")
        self.assertEqual(cfg.contar_configs_nao_neutras(), 0)


class TestVelocidadeJogoMusicaSemHold(unittest.TestCase):
    def _criar_musica(self):
        t = [0.0]
        sons = {
            "musica_menu": _FakeSound(10.0),
            "musica_anticipation": _FakeSound(35.0),
            "musica_anticipation_muffled": _FakeSound(35.0),
            "musica_hold": _FakeSound(6.0),
            "musica_hold_muffled": _FakeSound(6.0),
            "musica_assault_intro": _FakeSound(6.0),
            "musica_assault_intro_muffled": _FakeSound(6.0),
            "musica_assault": _FakeSound(90.0),
            "musica_assault_muffled": _FakeSound(90.0),
        }
        sm = SistemaMusica(
            clock=lambda: t[0],
            canal_normal=_FakeChannel(),
            canal_abafado=_FakeChannel(),
            sons_injetados=sons,
        )
        sm.iniciar_partida()
        return sm, t

    def test_maior_100_pula_hold_com_anticipation_1x(self):
        sm, _t = self._criar_musica()
        sm.atualizar(tempo_sobrevivencia=10.0, dt=0.016, velocidade_jogo_mult=2.0)
        self.assertEqual(sm._decidir_proximo_estado(10.0), SistemaMusica.ESTADO_ASSAULT_INTRO)

    def test_menor_100_pula_hold_com_anticipation_2x(self):
        sm, _t = self._criar_musica()
        sm.atualizar(tempo_sobrevivencia=10.0, dt=0.016, velocidade_jogo_mult=0.5)
        self.assertEqual(sm._decidir_proximo_estado(10.0), SistemaMusica.ESTADO_ANTICIPATION)
        sm._ao_entrar_estado(SistemaMusica.ESTADO_ANTICIPATION, SistemaMusica.ESTADO_ANTICIPATION)
        self.assertEqual(sm._decidir_proximo_estado(35.0), SistemaMusica.ESTADO_ASSAULT_INTRO)

    def test_troca_mid_run_em_hold_sai_para_assault_intro(self):
        sm, _t = self._criar_musica()
        sm.estado = SistemaMusica.ESTADO_HOLD
        sm.atualizar(tempo_sobrevivencia=15.0, dt=0.016, velocidade_jogo_mult=1.5)
        self.assertEqual(sm._decidir_proximo_estado(15.0), SistemaMusica.ESTADO_ASSAULT_INTRO)


class TestVelocidadeJogoGameplayEEdgeCases(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._save_path = os.path.join(self._tmpdir.name, "save.json")
        self._patch_save = patch("src.utils.constantes.SAVE_FILE_PATH", self._save_path)
        self._patch_save.start()

        from src.utils.janela import Janela
        from src.cenas.gameplay import GameplayScene
        self.janela = Janela(1280, 720, "Teste Velocidade")
        self.cena = GameplayScene()
        self.cena.config_sistema.desbloquear_config("velocidade_jogo")
        self.cena.jogador.dash_desbloqueado = True

    def tearDown(self):
        self._patch_save.stop()
        self._tmpdir.cleanup()

    def _ativar_vel(self, opt: str):
        self.cena.config_sistema.definir_valor("velocidade_jogo", opt)
        self.cena.aplicar_modificadores()

    def test_dt_sim_vs_dt_real_hitstop_iframes_e_15fps(self):
        self._ativar_vel("200%")
        self.cena.config_sistema.desbloquear_config("fps_cap")
        self.cena.config_sistema.definir_valor("fps_cap", "15")

        self.cena.jogador.invulnerabilidade_timer = 0.20
        self.cena.loop(dt=0.05)
        # 200%: dt_sim = 0.10 (2 substeps de 0.05), dt_real = 0.05
        self.assertAlmostEqual(self.cena.tempo_sobrevivencia, 0.10, places=4)
        self.assertAlmostEqual(self.cena.tempo_real_partida, 0.05, places=4)
        self.assertAlmostEqual(self.cena.tempo_15fps_acumulado, 0.05, places=4)
        self.assertAlmostEqual(self.cena.jogador.invulnerabilidade_timer, 0.10, places=4)

        # Hitstop deve rodar em dt_real e congelar tempo_sobrevivencia
        t_sim_antes = self.cena.tempo_sobrevivencia
        self.cena.hitstop_timer = 0.10
        self.cena.loop(dt=0.05)
        self.assertAlmostEqual(self.cena.hitstop_timer, 0.05, places=4)
        self.assertAlmostEqual(self.cena.tempo_sobrevivencia, t_sim_antes, places=4)

    def test_substepping_nao_duplica_evento_de_borda_autofire_f(self):
        self._ativar_vel("200%")
        self.cena.auto_fire_toggle_ativo = False
        self.cena.teclado = _DummyTecladoBorda(down_keys={"f"})
        # dt_real=0.05 em 200% gera 2 sub-steps de 0.05; F deve alternar APENAS 1x
        self.cena.loop(dt=0.05)
        self.assertTrue(self.cena.auto_fire_toggle_ativo)

    def test_50pct_dash_cooldown_e_drops_despawn_real(self):
        self._ativar_vel("50%")
        self.assertTrue(self.cena.jogador.iniciar_dash(1.0, 0.0))
        self.assertAlmostEqual(self.cena.jogador.dash_cooldown_restante, DASH_COOLDOWN * 1.30, places=4)

        drop = ItemDrop(100, 100, tipo="xp", valor=5, tempo_vida=60.0)
        drop.pickup_cooldown = 0.65
        self.cena.sistema_drops.drops = [drop]
        self.cena.loop(dt=0.04)
        # Em 50%: dt_sim = 0.02, dt_despawn = 0.04 * 1.5 = 0.06, dt_pickup = 0.04
        self.assertAlmostEqual(drop.tempo_decorrido, 0.02, places=4)
        self.assertAlmostEqual(drop.tempo_despawn, 0.06, places=4)
        self.assertAlmostEqual(drop.tempo_pickup, 0.04, places=4)

    def test_125pct_cadencia_movimento_real_vs_parede(self):
        self._ativar_vel("125%")
        self.cena.jogador.x = 0.0
        self.cena.jogador.y = 100.0
        # Segurando esquerda encostado na parede x=0 -> deslocamento 0 -> sem bônus
        self.cena.jogador.processar_input(
            _DummyTecladoBorda(pressed_keys={"a"}),
            None,
            0.016,
            config_sistema=self.cena.config_sistema,
            limite_arena=(self.cena.largura_arena, self.cena.altura_arena),
        )
        self.assertFalse(self.cena.jogador.em_movimento_real)

        # Andando para direita -> deslocamento > 0.5px -> bônus ativo
        self.cena.jogador.processar_input(
            _DummyTecladoBorda(pressed_keys={"d"}),
            None,
            0.016,
            config_sistema=self.cena.config_sistema,
            limite_arena=(self.cena.largura_arena, self.cena.altura_arena),
        )
        self.assertTrue(self.cena.jogador.em_movimento_real)

    def test_150pct_e_200pct_abate_reduz_cd_e_nightcore_parry_freeze_real_e_whiff(self):
        self._ativar_vel("200%")
        self.cena.jogador.dash_cooldown_restante = 1.5
        arma_m = self.cena._obter_arma_melee()
        arma_m.tempo_recarga_restante = 1.0
        inim = InimigoPadrao(200, 200)
        inim.vivo = False
        self.cena._registrar_abate_inimigo(inim)
        self.assertAlmostEqual(self.cena.jogador.dash_cooldown_restante, 1.15, places=4)
        self.assertAlmostEqual(arma_m.tempo_recarga_restante, 0.65, places=4)

        # Erro de Parry em 200% dobra cooldown
        arma_m.tempo_recarga_restante = 0.8
        self.cena._ao_errar_parry()
        self.assertAlmostEqual(arma_m.tempo_recarga_restante, 1.6, places=4)

        # Acerto de Parry em 200% ativa freeze de 0,6s REAIS
        self.cena.hitstop_timer = 0.0
        cx = self.cena.jogador.x + self.cena.jogador.largura / 2.0
        cy = self.cena.jogador.y + self.cena.jogador.altura / 2.0
        proj = Projetil(cx + 20, cy, -1.0, 0.0, velocidade=200.0, dano=10, dono="inimigo")
        self.cena.projeteis = [proj]
        arma_m.parry_janela_restante = 0.12
        arma_m.parry_angulo = 0.0
        rebatidos = self.cena._processar_parry_ativo(arma_m, cx, cy, angulo_mira=0.0)
        self.assertTrue(len(rebatidos) >= 1)
        self.assertAlmostEqual(self.cena.nightcore_freeze_timer, 0.6, places=4)
        self.cena.hitstop_timer = 0.0
        # Avança 0.05s real (0.10s sim): nightcore_freeze_timer deve cair apenas 0.05s (tempo real!)
        self.cena.loop(dt=0.05)
        self.assertAlmostEqual(self.cena.nightcore_freeze_timer, 0.55, places=4)

    def test_render_relogio_duplo_hud_vitoria_e_gameover(self):
        for opt in ("50%", "150%", "200%"):
            self._ativar_vel(opt)
            self.cena.tempo_sobrevivencia = 135.0
            self.cena.tempo_real_partida = 68.0
            self.cena.draw()
        self.cena.vitoria = True
        self.cena.draw()
        self.cena.vitoria = False
        self.cena.game_over = True
        self.cena.draw()


if __name__ == "__main__":
    unittest.main()
