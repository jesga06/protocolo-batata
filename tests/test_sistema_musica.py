"""
Testes automatizados para o SistemaMusica (trilha sonora dinâmica estilo Payday 2).
Cobre integridade dos assets WAV, paridade de frames normal/muffled, máquina de estados,
enfileiramento gapless (lookahead), spotlight abafado, cortes abruptos e handoff do boss.
"""

import os
import unittest
import wave

from src.sistemas.sistema_musica import SistemaMusica
from src.utils.constantes import (
    ASSET_PATHS,
    MUSICA_LOOKAHEAD_SEGUNDOS,
    MUSICA_TEMPO_ASSAULT,
    MUSICA_TRANSICAO_ABAFADO_SEGUNDOS,
    MUSICA_VOLUME_BASE,
    obter_caminho_asset,
)


class FakeSound:
    def __init__(self, nome: str, duracao: float):
        self.nome = nome
        self._duracao = float(duracao)

    def get_length(self) -> float:
        return self._duracao


class FakeClock:
    def __init__(self, inicial: float = 0.0):
        self.t = float(inicial)

    def __call__(self) -> float:
        return self.t

    def avancar(self, delta: float) -> float:
        self.t += float(delta)
        return self.t


class FakeChannel:
    """Simula um pygame.mixer.Channel com reprodução, fila (1 slot), fadeout e tempo real."""

    def __init__(self, clock: FakeClock):
        self._clock = clock
        self.som_atual = None
        self.fila = None
        self.loops = 0
        self.fim_atual = 0.0
        self.volume = 1.0
        self.play_calls = []
        self.queue_calls = []
        self.fadeout_calls = []
        self.stop_calls = 0

    def _sincronizar_tempo(self):
        agora = self._clock()
        while self.som_atual is not None and self.loops == 0 and agora >= self.fim_atual:
            if self.fila is not None:
                self.som_atual = self.fila
                self.fila = None
                self.fim_atual += self.som_atual.get_length()
            else:
                self.som_atual = None
                self.fim_atual = 0.0

    def play(self, sound, loops: int = 0):
        self.som_atual = sound
        self.fila = None
        self.loops = loops
        self.fim_atual = self._clock() + sound.get_length()
        self.play_calls.append((sound.nome, loops))

    def queue(self, sound):
        self._sincronizar_tempo()
        self.fila = sound
        self.queue_calls.append(sound.nome)

    def get_queue(self):
        self._sincronizar_tempo()
        return self.fila

    def get_busy(self) -> bool:
        self._sincronizar_tempo()
        return self.som_atual is not None

    @property
    def som_tocando(self):
        self._sincronizar_tempo()
        return self.som_atual

    def set_volume(self, value: float):
        self.volume = float(value)

    def stop(self):
        self.som_atual = None
        self.fila = None
        self.loops = 0
        self.fim_atual = 0.0
        self.stop_calls += 1

    def fadeout(self, ms: int):
        self.fadeout_calls.append(int(ms))
        self.fila = None


def _criar_sistema_teste():
    clock = FakeClock(100.0)
    ch_normal = FakeChannel(clock)
    ch_abafado = FakeChannel(clock)
    sons = {
        "musica_menu": FakeSound("menu", 47.408),
        "musica_anticipation": FakeSound("anticipation", 35.556),
        "musica_anticipation_muffled": FakeSound("anticipation_muffled", 35.556),
        "musica_hold": FakeSound("hold", 5.925),
        "musica_hold_muffled": FakeSound("hold_muffled", 5.925),
        "musica_assault_intro": FakeSound("assault_intro", 5.925),
        "musica_assault_intro_muffled": FakeSound("assault_intro_muffled", 5.925),
        "musica_assault": FakeSound("assault", 94.814),
        "musica_assault_muffled": FakeSound("assault_muffled", 94.814),
    }
    sistema = SistemaMusica(
        clock=clock,
        canal_normal=ch_normal,
        canal_abafado=ch_abafado,
        sons_injetados=sons,
    )
    return sistema, clock, ch_normal, ch_abafado


class TestAssetsMusicaDinamica(unittest.TestCase):
    """Garante integridade física e paridade exata de frames nos arquivos WAV dinâmicos."""

    def test_chaves_registradas_e_arquivos_existem(self):
        chaves = [
            "musica_menu",
            "musica_anticipation",
            "musica_anticipation_muffled",
            "musica_hold",
            "musica_hold_muffled",
            "musica_assault_intro",
            "musica_assault_intro_muffled",
            "musica_assault",
            "musica_assault_muffled",
        ]
        for chave in chaves:
            self.assertIn(chave, ASSET_PATHS)
            caminho = obter_caminho_asset(chave)
            self.assertTrue(os.path.isfile(caminho), f"Arquivo ausente para '{chave}': {caminho}")
            with wave.open(caminho, "rb") as wav_file:
                self.assertEqual(wav_file.getframerate(), 44100, f"{chave} deve ser 44100Hz")
                self.assertEqual(wav_file.getnchannels(), 2, f"{chave} deve ser estéreo (2ch)")
                self.assertEqual(wav_file.getsampwidth(), 2, f"{chave} deve ser 16-bit PCM")
                self.assertGreater(wav_file.getnframes(), 0)

    def test_paridade_exata_de_frames_normal_e_abafado(self):
        pares = [
            ("musica_anticipation", "musica_anticipation_muffled"),
            ("musica_hold", "musica_hold_muffled"),
            ("musica_assault_intro", "musica_assault_intro_muffled"),
            ("musica_assault", "musica_assault_muffled"),
        ]
        for normal, abafado in pares:
            with wave.open(obter_caminho_asset(normal), "rb") as wn, wave.open(
                obter_caminho_asset(abafado), "rb"
            ) as wm:
                self.assertEqual(
                    wn.getnframes(),
                    wm.getnframes(),
                    f"Par '{normal}' / '{abafado}' deve ter exatamente o mesmo número de frames!",
                )


class TestSistemaMusicaFSM(unittest.TestCase):
    """Valida máquina de estados, enfileiramento por frase, muffle e cortes abruptos."""

    def test_menu_idempotente_e_corte_abrupto_para_gameplay(self):
        sistema, clock, ch_n, ch_m = _criar_sistema_teste()

        sistema.tocar_menu()
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_MENU)
        self.assertEqual(ch_n.play_calls, [("menu", -1)])
        self.assertEqual(ch_m.play_calls, [])
        self.assertAlmostEqual(ch_n.volume, MUSICA_VOLUME_BASE)
        self.assertAlmostEqual(ch_m.volume, 0.0)

        # Chamar novamente (ex.: retorno da TutorialScene) não reinicia a faixa
        clock.avancar(10.0)
        sistema.tocar_menu()
        self.assertEqual(len(ch_n.play_calls), 1)

        # Iniciar partida faz corte abrupto para anticipation + anticipation_muffled
        sistema.iniciar_partida()
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)
        self.assertEqual(ch_n.play_calls[-1], ("anticipation", 0))
        self.assertEqual(ch_m.play_calls[-1], ("anticipation_muffled", 0))
        self.assertAlmostEqual(ch_n.volume, MUSICA_VOLUME_BASE)
        self.assertAlmostEqual(ch_m.volume, 0.0)

    def test_progressao_completa_com_hold_em_loop_e_transicao_somente_no_fim_da_frase(self):
        sistema, clock, ch_n, ch_m = _criar_sistema_teste()
        sistema.iniciar_partida()

        # Avança até 1s antes do fim de anticipation: ainda não deve enfileirar hold
        clock.avancar(34.5)
        sistema.atualizar(tempo_sobrevivencia=34.5, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls, [])

        # Entra na janela de lookahead (restante = 0.256s <= 0.35s) -> enfileira hold
        clock.avancar(0.8)  # total 35.3s
        sistema.atualizar(tempo_sobrevivencia=35.3, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls, ["hold"])
        self.assertEqual(ch_m.queue_calls, ["hold_muffled"])
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)

        # Passa do ponto exato de handoff (35.556s) -> estado vira HOLD
        clock.avancar(0.3)  # total 35.6s
        sistema.atualizar(tempo_sobrevivencia=35.6, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)
        self.assertEqual(ch_n.som_tocando.nome, "hold")
        self.assertEqual(ch_m.som_tocando.nome, "hold_muffled")

        # Loop 1 de hold (fim em 35.556 + 5.925 = 41.481s), tempo_sobrevivencia < 50s -> repete hold
        clock.avancar(5.7)  # total 41.3s (restante ~0.181s)
        sistema.atualizar(tempo_sobrevivencia=41.3, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "hold")
        self.assertEqual(ch_m.queue_calls[-1], "hold_muffled")

        clock.avancar(0.3)  # total 41.6s -> entrou no loop 2 de hold
        sistema.atualizar(tempo_sobrevivencia=41.6, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)

        # Pausa durante o loop 2 de hold (tempo_sobrevivencia congela em 42.0s) -> continua em hold abafado!
        clock.avancar(5.6)  # total 47.2s (restante ~0.206s para 47.406s)
        sistema.atualizar(tempo_sobrevivencia=42.0, abafado=True, dt=0.1)
        self.assertEqual(ch_n.queue_calls[-1], "hold")
        self.assertAlmostEqual(ch_n.volume, 0.0)
        self.assertAlmostEqual(ch_m.volume, MUSICA_VOLUME_BASE)

        clock.avancar(0.3)  # total 47.5s -> loop 3 de hold (47.406s -> 53.331s)
        sistema.atualizar(tempo_sobrevivencia=42.0, abafado=False, dt=0.1)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)

        # Tempo de sobrevivência cruza 50.0s no MEIO da frase de hold -> NÃO corta nem enfileira ainda!
        clock.avancar(2.0)  # total 49.5s (restante ~3.831s)
        sistema.atualizar(tempo_sobrevivencia=50.5, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)
        self.assertEqual(ch_n.som_atual.nome, "hold")
        self.assertEqual(len(ch_n.queue_calls), 3)  # nenhum queue novo

        # Chega ao fim da frase de hold (53.331s - 0.231s = 53.1s) -> enfileira assault_intro!
        clock.avancar(3.6)  # total 53.1s
        sistema.atualizar(tempo_sobrevivencia=54.1, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "assault_intro")
        self.assertEqual(ch_m.queue_calls[-1], "assault_intro_muffled")

        # Handoff para ASSAULT_INTRO (53.331s -> 59.256s)
        clock.avancar(0.3)  # total 53.4s
        sistema.atualizar(tempo_sobrevivencia=54.4, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT_INTRO)
        self.assertEqual(ch_n.som_tocando.nome, "assault_intro")
        self.assertEqual(ch_m.som_tocando.nome, "assault_intro_muffled")

        # Fim de ASSAULT_INTRO -> enfileira ASSAULT
        clock.avancar(5.65)  # total 59.05s (restante ~0.206s)
        sistema.atualizar(tempo_sobrevivencia=60.05, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "assault")
        self.assertEqual(ch_m.queue_calls[-1], "assault_muffled")

        # Handoff para ASSAULT
        clock.avancar(0.3)  # total 59.35s
        sistema.atualizar(tempo_sobrevivencia=60.35, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)
        self.assertEqual(ch_n.som_tocando.nome, "assault")
        self.assertEqual(ch_m.som_tocando.nome, "assault_muffled")

        # Fim de ASSAULT (59.256 + 94.814 = 154.070s) -> entrelaça de volta para ANTICIPATION
        clock.avancar(94.55)  # total 153.90s (restante ~0.17s)
        sistema.atualizar(tempo_sobrevivencia=154.9, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "anticipation")
        self.assertEqual(ch_m.queue_calls[-1], "anticipation_muffled")

        clock.avancar(0.3)  # total 154.20s -> entrou em ANTICIPATION (2o ciclo)
        sistema.atualizar(tempo_sobrevivencia=155.2, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)

        # Fim de ANTICIPATION (154.070 + 35.556 = 189.626s) -> entra em HOLD (1/2)
        clock.avancar(35.3)  # total 189.50s
        sistema.atualizar(tempo_sobrevivencia=190.5, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "hold")

        clock.avancar(0.25)  # total 189.75s -> HOLD 1/2
        sistema.atualizar(tempo_sobrevivencia=190.75, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)

        # Fim de HOLD 1/2 (189.626 + 5.925 = 195.551s) -> repete HOLD (2/2) mesmo com tempo > 50s!
        clock.avancar(5.65)  # total 195.40s
        sistema.atualizar(tempo_sobrevivencia=196.4, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "hold")

        clock.avancar(0.25)  # total 195.65s -> HOLD 2/2
        sistema.atualizar(tempo_sobrevivencia=196.65, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)

        # Fim de HOLD 2/2 (195.551 + 5.925 = 201.476s) -> avança para ASSAULT_INTRO -> ASSAULT
        clock.avancar(5.65)  # total 201.30s
        sistema.atualizar(tempo_sobrevivencia=202.3, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "assault_intro")

        clock.avancar(0.25)  # total 201.55s -> ASSAULT_INTRO
        sistema.atualizar(tempo_sobrevivencia=202.55, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT_INTRO)

        clock.avancar(5.75)  # total 207.30s (fim de ASSAULT_INTRO em 207.401s)
        sistema.atualizar(tempo_sobrevivencia=208.3, abafado=False, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "assault")

        clock.avancar(0.2)  # total 207.50s -> ASSAULT (2o ciclo)
        sistema.atualizar(tempo_sobrevivencia=208.5, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)

    def test_resiliencia_a_15_fps_na_janela_de_lookahead(self):
        sistema, clock, ch_n, _ = _criar_sistema_teste()
        sistema.iniciar_partida()
        dt_15fps = 1.0 / 15.0

        # Simula 15 FPS até cruzar o fim de anticipation (35.556s) e 1o loop de hold
        tempo_jogo = 0.0
        enfileirou_hold = False
        while tempo_jogo < 36.0:
            clock.avancar(dt_15fps)
            tempo_jogo += dt_15fps
            sistema.atualizar(tempo_sobrevivencia=tempo_jogo, abafado=False, dt=dt_15fps)
            if "hold" in ch_n.queue_calls:
                enfileirou_hold = True

        self.assertTrue(enfileirou_hold, "Janela de lookahead deve capturar a transição mesmo em 15 FPS")
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)
        self.assertEqual(len(ch_n.play_calls), 1, "Não deve precisar de fallback play(); deve ser gapless via queue()")

    def test_crossblend_abafado_e_sliders_de_volume(self):
        sistema, clock, ch_n, ch_m = _criar_sistema_teste()
        sistema.atualizar_volume(vol_master=50, vol_musica=50)
        vol_esperado = MUSICA_VOLUME_BASE * 0.5 * 0.5  # 0.1

        sistema.iniciar_partida()
        self.assertAlmostEqual(ch_n.volume, vol_esperado)
        self.assertAlmostEqual(ch_m.volume, 0.0)

        # Metade da transição de abafamento (30ms de 60ms)
        metade = MUSICA_TRANSICAO_ABAFADO_SEGUNDOS / 2.0
        clock.avancar(metade)
        sistema.atualizar(tempo_sobrevivencia=1.0, abafado=True, dt=metade)
        self.assertAlmostEqual(ch_n.volume, vol_esperado * 0.5, places=5)
        self.assertAlmostEqual(ch_m.volume, vol_esperado * 0.5, places=5)

        # Completa transição para 100% abafado
        clock.avancar(metade)
        sistema.atualizar(tempo_sobrevivencia=1.0, abafado=True, dt=metade)
        self.assertAlmostEqual(ch_n.volume, 0.0, places=5)
        self.assertAlmostEqual(ch_m.volume, vol_esperado, places=5)

        # Alterar volume enquanto abafado preserva o spotlight no canal abafado
        sistema.atualizar_volume(vol_master=100, vol_musica=100)
        self.assertAlmostEqual(ch_n.volume, 0.0, places=5)
        self.assertAlmostEqual(ch_m.volume, MUSICA_VOLUME_BASE, places=5)

    def test_cortes_abruptos_restart_menu_e_boss_handoff(self):
        sistema, clock, ch_n, ch_m = _criar_sistema_teste()
        sistema.iniciar_partida()

        # Fadeout para boss
        sistema.fadeout_para_boss(1600)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_BOSS)
        self.assertEqual(ch_n.fadeout_calls, [1600])
        self.assertEqual(ch_m.fadeout_calls, [1600])

        # atualizar() durante ESTADO_BOSS não interfere nem re-enfileira nada
        clock.avancar(5.0)
        sistema.atualizar(tempo_sobrevivencia=270.0, abafado=False, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_BOSS)
        self.assertEqual(ch_n.queue_calls, [])

        # Restart direto (ex.: Game Over / Vitória) corta abruptamente para ANTICIPATION
        sistema.iniciar_partida()
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)
        self.assertEqual(ch_n.play_calls[-1], ("anticipation", 0))
        self.assertEqual(ch_m.play_calls[-1], ("anticipation_muffled", 0))

        # Voltar ao menu corta abruptamente para MENU
        sistema.tocar_menu()
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_MENU)
        self.assertEqual(ch_n.play_calls[-1], ("menu", -1))

        # Parada imediata para spawn direto de boss via debug
        sistema.parar_dinamica(entrar_estado_boss=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_BOSS)
        self.assertFalse(ch_n.get_busy())
        self.assertFalse(ch_m.get_busy())


if __name__ == "__main__":
    unittest.main()
