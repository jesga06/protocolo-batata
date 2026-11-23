"""
Testes unitários para o Sistema de Áudio e DSP (Stage 1 Phase 1.4) — Protocolo: Batata.

Valida:
- Pré-geração de 7 variantes de pitch (0.91..1.09) para armas e pickups.
- Reprodução sobreposta segura sem nunca cancelar canais ativos.
- Rampa suave de volume (~20 ms) com headroom de música (0.40) e SFX (0.85).
- Síntese procedural de parry clang e tiro sobrecarregado + fallback sem mixer.
- AnalisadorFFTBoss determinístico sobre o arquivo real `geladeira tsunami.wav`.
"""

from __future__ import annotations

import os
import random
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.sistemas.sistema_audio import (
    CHAVES_PITCH_ARMAS,
    CHAVES_PITCH_PICKUPS,
    CHAVES_PITCH_POOL,
    FATORES_PITCH_PADRAO,
    HEADROOM_MUSICA,
    HEADROOM_SFX,
    AnalisadorFFTBoss,
    GerenciadorAudio,
)
from src.utils.constantes import obter_caminho_asset


class TestGerenciadorAudioPitchPool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()

    def setUp(self):
        self.audio = GerenciadorAudio(rng=random.Random(12345))

    def test_musicas_originais_v1_preservadas(self):
        self.assertTrue(os.path.isfile(obter_caminho_asset("musica_fase")))
        self.assertTrue(os.path.isfile(obter_caminho_asset("musica_boss")))

    def test_pool_pitch_armas_e_pickups_com_7_variantes(self):
        self.assertTrue(self.audio.mixer_disponivel)
        esperadas = set(CHAVES_PITCH_ARMAS) | set(CHAVES_PITCH_PICKUPS)
        self.assertEqual(set(self.audio.pool_pitch.keys()), esperadas)

        for chave in CHAVES_PITCH_POOL:
            variantes = self.audio.pool_pitch[chave]
            self.assertEqual(len(variantes), 7, f"Pool de '{chave}' deve ter 7 variantes")
            for som in variantes:
                self.assertIsInstance(som, pygame.mixer.Sound)
                self.assertGreater(som.get_length(), 0.0)

    def test_variantes_pitch_tem_duracao_decrescente_com_fator(self):
        # Fator 0.91 (mais grave) deve ser mais longo que fator 1.09 (mais agudo)
        variantes = self.audio.pool_pitch["tiro_pistola"]
        duracoes = [s.get_length() for s in variantes]
        self.assertGreater(duracoes[0], duracoes[-1])
        for i in range(len(duracoes) - 1):
            self.assertGreaterEqual(duracoes[i], duracoes[i + 1])

    def test_tocar_sfx_aceita_chave_com_e_sem_prefixo_e_fallback_simples(self):
        canal1 = self.audio.tocar_sfx("tiro_pistola", pitch_aleatorio=True)
        canal2 = self.audio.tocar_sfx("sfx_tiro_pistola", pitch_aleatorio=False)
        canal3 = self.audio.tocar_sfx("explosao", pitch_aleatorio=False, volume_mult=0.7)
        canal_invalido = self.audio.tocar_sfx("sfx_que_nao_existe")

        self.assertIsNotNone(canal1)
        self.assertIsNotNone(canal2)
        self.assertIsNotNone(canal3)
        self.assertIsNone(canal_invalido)


class TestGerenciadorAudioSobreposicao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()

    def test_reproducao_sobreposta_nunca_para_canais_ativos(self):
        audio = GerenciadorAudio(rng=random.Random(7))

        canais_mock = []
        for _ in range(8):
            c = MagicMock()
            c.stop = MagicMock()
            canais_mock.append(c)

        indice = {"i": 0}

        def fake_find_channel(force=False):
            # Garante que nunca foi chamado com force=True (que cortaria canal ativo)
            self.assertFalse(force)
            if indice["i"] >= len(canais_mock):
                return None
            c = canais_mock[indice["i"]]
            indice["i"] += 1
            return c

        with patch("pygame.mixer.find_channel", side_effect=fake_find_channel):
            for _ in range(10):
                audio.tocar_sfx("tiro_minigun", pitch_aleatorio=True)

        # Os 8 canais receberam play() e NENHUM recebeu stop()
        for c in canais_mock:
            c.play.assert_called_once()
            c.stop.assert_not_called()


class TestGerenciadorAudioRampaVolume(unittest.TestCase):
    def setUp(self):
        self.audio = GerenciadorAudio(inicializar_automaticamente=False)

    def test_rampa_suave_20ms_e_headroom_sem_clipping(self):
        # Inicializa no máximo (100, 100, 100) -> headroom 0.40 e 0.85
        self.assertAlmostEqual(self.audio.volume_musica_atual, HEADROOM_MUSICA, places=6)
        self.assertAlmostEqual(self.audio.volume_sfx_atual, HEADROOM_SFX, places=6)

        # Define alvo 50% master, 50% música, 50% sfx (escala 0..100)
        self.audio.definir_volumes_alvo(50.0, 50.0, 50.0)
        esperado_mus = 0.5 * 0.5 * HEADROOM_MUSICA  # 0.10
        esperado_sfx = 0.5 * 0.5 * HEADROOM_SFX     # 0.2125
        self.assertAlmostEqual(self.audio.volume_musica_alvo, esperado_mus, places=6)
        self.assertAlmostEqual(self.audio.volume_sfx_alvo, esperado_sfx, places=6)

        # Após 5 ms (25% da rampa de 20 ms): intermediário, sem salto brusco
        self.audio.atualizar(0.005)
        self.assertLess(self.audio.volume_musica_atual, HEADROOM_MUSICA)
        self.assertGreater(self.audio.volume_musica_atual, esperado_mus)
        self.assertLess(self.audio.volume_sfx_atual, HEADROOM_SFX)
        self.assertGreater(self.audio.volume_sfx_atual, esperado_sfx)

        # Após +5 ms (10 ms total = 50% da rampa)
        self.audio.atualizar(0.005)
        meio_mus = (HEADROOM_MUSICA + esperado_mus) * 0.5
        meio_sfx = (HEADROOM_SFX + esperado_sfx) * 0.5
        self.assertAlmostEqual(self.audio.volume_musica_atual, meio_mus, places=6)
        self.assertAlmostEqual(self.audio.volume_sfx_atual, meio_sfx, places=6)

        # Após +10 ms (20 ms total = 100% da rampa): atinge exatamente o alvo
        self.audio.atualizar(0.010)
        self.assertAlmostEqual(self.audio.volume_musica_atual, esperado_mus, places=6)
        self.assertAlmostEqual(self.audio.volume_sfx_atual, esperado_sfx, places=6)

    def test_clamping_e_escala_normalizada_sem_clipping(self):
        # Escala normalizada 0..1
        self.audio.definir_volumes_alvo(1.0, 0.8, 0.5)
        self.audio.atualizar(0.025)
        self.assertAlmostEqual(self.audio.volume_musica_atual, 0.8 * HEADROOM_MUSICA, places=6)
        self.assertAlmostEqual(self.audio.volume_sfx_atual, 0.5 * HEADROOM_SFX, places=6)

        # Valores acima de 100 ou negativos são clampados sem clipping
        self.audio.definir_volumes_alvo(250.0, 200.0, 180.0)
        self.audio.atualizar(0.025)
        self.assertLessEqual(self.audio.volume_musica_atual, HEADROOM_MUSICA)
        self.assertLessEqual(self.audio.volume_sfx_atual, HEADROOM_SFX)

        self.audio.definir_volumes_alvo(-10.0, -5.0, -1.0)
        self.audio.atualizar(0.025)
        self.assertEqual(self.audio.volume_musica_atual, 0.0)
        self.assertEqual(self.audio.volume_sfx_atual, 0.0)


class TestGerenciadorAudioSinteseEFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()

    def test_sintese_parry_clang_e_tiro_sobrecarregado(self):
        audio = GerenciadorAudio()
        self.assertIsInstance(audio.som_parry_clang, pygame.mixer.Sound)
        self.assertIsInstance(audio.som_tiro_sobrecarregado, pygame.mixer.Sound)

        self.assertGreater(audio.som_parry_clang.get_length(), 0.15)
        self.assertGreater(audio.som_tiro_sobrecarregado.get_length(), 0.08)

        self.assertIsNotNone(audio.tocar_parry_clang())
        self.assertIsNotNone(audio.tocar_tiro_sobrecarregado())

    def test_fallback_seguro_quando_mixer_indisponivel(self):
        with patch("pygame.mixer.get_init", return_value=None), patch(
            "pygame.mixer.init", side_effect=pygame.error("no audio device")
        ):
            audio = GerenciadorAudio()

        self.assertFalse(audio.mixer_disponivel)
        self.assertIsNone(audio.som_parry_clang)
        self.assertIsNone(audio.som_tiro_sobrecarregado)
        self.assertEqual(audio.pool_pitch, {})

        # Todas as chamadas devem ser no-op seguras sem lançar exceções
        self.assertIsNone(audio.tocar_sfx("tiro_pistola"))
        self.assertIsNone(audio.tocar_parry_clang())
        self.assertIsNone(audio.tocar_tiro_sobrecarregado())
        audio.definir_volumes_alvo(80.0, 60.0, 70.0)
        audio.atualizar(0.020)
        self.assertAlmostEqual(audio.volume_musica_atual, 0.8 * 0.6 * HEADROOM_MUSICA, places=6)
        self.assertAlmostEqual(audio.volume_sfx_atual, 0.8 * 0.7 * HEADROOM_SFX, places=6)


class TestAnalisadorFFTBoss(unittest.TestCase):
    def test_carrega_geladeira_tsunami_e_retorna_bandas_normalizadas(self):
        fft = AnalisadorFFTBoss()
        self.assertTrue(fft.carregado)
        self.assertEqual(fft.taxa_amostragem, 22050)
        self.assertGreater(fft.duracao_ms, 50000.0)

        bandas = fft.obter_bandas(15000.0, dt=0.016, num_bandas=28)
        self.assertEqual(len(bandas), 28)
        for v in bandas:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)
        self.assertGreater(max(bandas), 0.1)

    def test_determinismo_headless_e_suavizacao_exponencial(self):
        fft_a = AnalisadorFFTBoss()
        fft_b = AnalisadorFFTBoss()

        seq_ms = [1000.0, 5000.0, 12000.0, 24000.0]
        for ms in seq_ms:
            ba = fft_a.obter_bandas(ms, dt=0.016, num_bandas=28)
            bb = fft_b.obter_bandas(ms, dt=0.016, num_bandas=28)
            self.assertEqual(ba, bb)

        # Suavização exponencial: ao repetir o mesmo instante ativo a partir do zero,
        # o segundo frame deve subir em relação ao primeiro (convergência suave)
        fft_a.resetar()
        frame1 = fft_a.obter_bandas(25000.0, dt=0.016, num_bandas=28)
        frame2 = fft_a.obter_bandas(25000.0, dt=0.016, num_bandas=28)
        self.assertGreater(sum(frame2), sum(frame1))

    def test_fronteiras_loop_wrap_e_arquivo_inexistente(self):
        fft = AnalisadorFFTBoss()
        # Wrap-around além do final da faixa e pos_ms negativo
        b_wrap = fft.obter_bandas(fft.duracao_ms + 5000.0, dt=0.016, num_bandas=16)
        b_neg = fft.obter_bandas(-100.0, dt=0.016, num_bandas=16)
        b_vazio = fft.obter_bandas(1000.0, dt=0.016, num_bandas=0)

        self.assertEqual(len(b_wrap), 16)
        self.assertEqual(len(b_neg), 16)
        self.assertEqual(b_vazio, [])
        self.assertTrue(all(0.0 <= v <= 1.0 for v in b_wrap))
        self.assertTrue(all(0.0 <= v <= 1.0 for v in b_neg))

        # Fallback seguro se arquivo não existir
        fft_missing = AnalisadorFFTBoss(caminho_wav="/caminho/inexistente/boss.wav")
        self.assertFalse(fft_missing.carregado)
        self.assertEqual(fft_missing.obter_bandas(5000.0, num_bandas=28), [0.0] * 28)


if __name__ == "__main__":
    unittest.main()
