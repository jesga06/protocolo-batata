"""
Testes da FSM bidirecional Música-Onda (Onda 1 - W1) e invariantes de desacoplamento.
"""

import ast
import os
import unittest

from src.sistemas.sistema_musica import SistemaMusica
from tests.test_sistema_musica import FakeChannel, FakeClock, FakeSound, _criar_sistema_teste


class TestMusicaOndaSync(unittest.TestCase):
    """Valida eventos de borda, trava_assault, pausar_transicao, headless e desacoplamento."""

    def test_lookahead_padrao_minimo_500ms(self):
        sistema, _, _, _ = _criar_sistema_teste()
        self.assertGreaterEqual(sistema._lookahead_segundos, 0.50)

    def test_transicao_dispara_evento_assault_intro_uma_unica_vez_e_fase_onda(self):
        sistema, clock, ch_n, _ = _criar_sistema_teste()
        sistema.iniciar_partida()
        self.assertEqual(sistema.fase_onda_atual, "calm")
        self.assertFalse(sistema.consumir_evento_assault_intro())

        # ANTICIPATION (35.556s) -> HOLD
        clock.avancar(35.3)
        sistema.atualizar(tempo_sobrevivencia=35.3, dt=0.016)
        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=35.6, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)
        self.assertEqual(sistema.fase_onda_atual, "calm")
        self.assertFalse(sistema.consumir_evento_assault_intro())

        # HOLD (5.925s -> fim em 41.481s), tempo >= 50s -> ASSAULT_INTRO
        clock.avancar(5.6)
        sistema.atualizar(tempo_sobrevivencia=52.0, dt=0.016)
        self.assertEqual(ch_n.queue_calls[-1], "assault_intro")
        self.assertFalse(sistema.consumir_evento_assault_intro())

        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=52.3, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT_INTRO)
        self.assertEqual(sistema.fase_onda_atual, "assault")
        self.assertTrue(sistema.consumir_evento_assault_intro())
        # Segundo consumo deve retornar False (evento de borda)
        self.assertFalse(sistema.consumir_evento_assault_intro())

        # ASSAULT_INTRO (5.925s -> fim em 47.406s) -> ASSAULT
        clock.avancar(5.65)
        sistema.atualizar(tempo_sobrevivencia=57.95, dt=0.016)
        clock.avancar(0.35)
        sistema.atualizar(tempo_sobrevivencia=58.3, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)
        self.assertEqual(sistema.fase_onda_atual, "assault")
        self.assertFalse(sistema.consumir_evento_assault_intro())

    def test_trava_assault_mantem_loop_gapless_ate_liberacao(self):
        sistema, clock, ch_n, ch_m = _criar_sistema_teste()
        sistema.iniciar_partida()

        # Avança até entrar em ASSAULT
        clock.avancar(35.3)
        sistema.atualizar(tempo_sobrevivencia=35.3, dt=0.016)
        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=35.6, dt=0.016)
        clock.avancar(5.6)
        sistema.atualizar(tempo_sobrevivencia=52.0, dt=0.016)
        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=52.3, dt=0.016)
        self.assertTrue(sistema.consumir_evento_assault_intro())
        clock.avancar(5.65)
        sistema.atualizar(tempo_sobrevivencia=57.95, dt=0.016)
        clock.avancar(0.35)
        sistema.atualizar(tempo_sobrevivencia=58.3, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)

        stops_antes = ch_n.stop_calls
        stops_m_antes = ch_m.stop_calls

        # Fim de ASSAULT (94.814s) com trava_assault=True -> repete ASSAULT via queue()
        clock.avancar(94.4)
        sistema.atualizar(tempo_sobrevivencia=152.7, dt=0.016, trava_assault=True)
        self.assertEqual(ch_n.queue_calls[-1], "assault")
        self.assertEqual(ch_m.queue_calls[-1], "assault_muffled")

        clock.avancar(0.4)
        sistema.atualizar(tempo_sobrevivencia=153.1, dt=0.016, trava_assault=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)
        self.assertEqual(sistema.ciclos_assault_concluidos, 0)
        self.assertEqual(ch_n.stop_calls, stops_antes)
        self.assertEqual(ch_m.stop_calls, stops_m_antes)

        # Libera trava_assault=False no fim da 2a frase -> volta para ANTICIPATION e incrementa ciclos
        clock.avancar(94.4)
        sistema.atualizar(tempo_sobrevivencia=247.5, dt=0.016, trava_assault=False)
        self.assertEqual(ch_n.queue_calls[-1], "anticipation")
        clock.avancar(0.4)
        sistema.atualizar(tempo_sobrevivencia=247.9, dt=0.016, trava_assault=False)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)
        self.assertEqual(sistema.ciclos_assault_concluidos, 1)
        self.assertEqual(ch_n.stop_calls, stops_antes)

    def test_pausar_transicao_mantem_estado_abafado_e_realinha_ao_despausar(self):
        sistema, clock, ch_n, _ = _criar_sistema_teste()
        sistema.iniciar_partida()

        # Avança para HOLD
        clock.avancar(35.3)
        sistema.atualizar(tempo_sobrevivencia=35.3, dt=0.016)
        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=35.6, dt=0.016)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)

        # Entra na janela de lookahead com pausar_transicao=True e tempo >= 50s
        clock.avancar(5.6)
        sistema.atualizar(tempo_sobrevivencia=60.0, abafado=True, dt=0.016, pausar_transicao=True)
        self.assertEqual(ch_n.queue_calls[-1], "hold")

        # Completa a frase ainda pausado -> continua em HOLD e realinha _inicio_faixa
        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=60.0, abafado=True, dt=0.016, pausar_transicao=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)
        self.assertEqual(sistema.fase_onda_atual, "calm")

        # Ao despausar logo em seguida, NÃO deve transicionar imediatamente (frase recém começou)
        queues_antes = len(ch_n.queue_calls)
        clock.avancar(0.5)
        sistema.atualizar(tempo_sobrevivencia=60.5, abafado=False, dt=0.016, pausar_transicao=False)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)
        self.assertEqual(len(ch_n.queue_calls), queues_antes)

    def test_pausar_transicao_com_proximo_ja_enfileirado_nao_faz_transicao_falsa(self):
        sistema, clock, ch_n, _ = _criar_sistema_teste()
        sistema.iniciar_partida()

        # Quase no fim de ANTICIPATION: enfileira HOLD normalmente
        clock.avancar(35.3)
        sistema.atualizar(tempo_sobrevivencia=35.3, dt=0.016, pausar_transicao=False)
        self.assertEqual(ch_n.queue_calls[-1], "hold")

        # Jogador pausa exatamente antes do handoff
        clock.avancar(0.3)
        sistema.atualizar(tempo_sobrevivencia=35.3, abafado=True, dt=0.016, pausar_transicao=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)
        # Ao despausar, _inicio_faixa foi realinhado e não dispara queue imediato
        queues_antes = len(ch_n.queue_calls)
        clock.avancar(0.1)
        sistema.atualizar(tempo_sobrevivencia=35.4, abafado=False, dt=0.016, pausar_transicao=False)
        self.assertEqual(len(ch_n.queue_calls), queues_antes)

    def test_fadeout_para_boss_tem_precedencia_absoluta_sobre_trava_assault(self):
        sistema, clock, _, _ = _criar_sistema_teste()
        sistema.iniciar_partida()
        sistema.estado = SistemaMusica.ESTADO_ASSAULT
        sistema.atualizar(tempo_sobrevivencia=120.0, dt=0.016, trava_assault=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)

        sistema.fadeout_para_boss(fade_ms=800)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_BOSS)

        clock.avancar(10.0)
        sistema.atualizar(tempo_sobrevivencia=130.0, dt=0.016, trava_assault=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_BOSS)

    def test_re_enfileiramento_defensivo_quando_get_queue_retorna_none(self):
        sistema, clock, ch_n, _ = _criar_sistema_teste()
        sistema.iniciar_partida()

        # Simula falha transitória na primeira tentativa dentro da janela de lookahead
        orig_queue = ch_n.queue

        def _falha_uma_vez(sound):
            ch_n.queue = orig_queue
            raise RuntimeError("SDL busy")

        ch_n.queue = _falha_uma_vez
        clock.avancar(35.2)
        sistema.atualizar(tempo_sobrevivencia=35.2, dt=0.016)
        self.assertIsNone(ch_n.get_queue())
        self.assertEqual(ch_n.queue_calls, [])

        # No próximo tick dentro da janela, get_queue() is None -> re-enfileira com sucesso
        clock.avancar(0.1)
        sistema.atualizar(tempo_sobrevivencia=35.3, dt=0.016)
        self.assertEqual(ch_n.queue_calls, ["hold"])

    def test_fallback_deterministico_headless_avanca_todos_estados_por_dt(self):
        sistema = SistemaMusica()
        sistema._inicializado = True
        sistema.iniciar_partida()
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)
        self.assertEqual(sistema._duracao_atual, 0.0)

        # Em pausa não avança relógio headless
        sistema.atualizar(tempo_sobrevivencia=10.0, dt=10.0, pausar_transicao=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)

        # ANTICIPATION (8.0s) -> HOLD
        sistema.atualizar(tempo_sobrevivencia=10.0, dt=8.0)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_HOLD)

        # HOLD (16.0s) com tempo >= 50s -> ASSAULT_INTRO
        sistema.atualizar(tempo_sobrevivencia=55.0, dt=16.0)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT_INTRO)
        self.assertTrue(sistema.consumir_evento_assault_intro())

        # ASSAULT_INTRO (6.0s) -> ASSAULT
        sistema.atualizar(tempo_sobrevivencia=61.0, dt=6.0)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)

        # ASSAULT (20.0s) com trava_assault=True permanece em ASSAULT
        sistema.atualizar(tempo_sobrevivencia=81.0, dt=20.0, trava_assault=True)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ASSAULT)
        self.assertEqual(sistema.ciclos_assault_concluidos, 0)

        # ASSAULT (20.0s) com trava_assault=False -> ANTICIPATION e incrementa ciclo
        sistema.atualizar(tempo_sobrevivencia=101.0, dt=20.0, trava_assault=False)
        self.assertEqual(sistema.estado, SistemaMusica.ESTADO_ANTICIPATION)
        self.assertEqual(sistema.ciclos_assault_concluidos, 1)

    def test_desacoplamento_estatico_ast_musica_e_spawn(self):
        raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        caminho_musica = os.path.join(raiz, "src", "sistemas", "sistema_musica.py")
        caminho_spawn = os.path.join(raiz, "src", "sistemas", "sistema_spawn.py")

        def _extrair_imports(caminho: str) -> set[str]:
            with open(caminho, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=caminho)
            modulos = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        modulos.add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modulos.add(node.module)
            return modulos

        imports_musica = _extrair_imports(caminho_musica)
        imports_spawn = _extrair_imports(caminho_spawn)

        for mod in imports_musica:
            self.assertNotIn("sistema_spawn", mod)
            self.assertNotIn("gameplay", mod)
            self.assertNotIn("entidades", mod)

        for mod in imports_spawn:
            self.assertNotIn("sistema_musica", mod)
            self.assertNotIn("pygame.mixer", mod)


if __name__ == "__main__":
    unittest.main()
