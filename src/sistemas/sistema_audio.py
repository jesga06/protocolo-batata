"""
Sistema de Áudio e DSP — Protocolo: Batata

Fornece:
- GerenciadorAudio: pool pré-processado de variações de pitch (±5–10%, 7 variantes
  via numpy.interp) para tiros e pickups, reprodução simultânea sem corte de canais
  ativos, síntese procedural de clang metálico de parry e tiro sobrecarregado, e
  rampa suave de volume (~20 ms) com headroom dedicado para música (0.40) e SFX (0.85).
- AnalisadorFFTBoss: análise espectral determinística por FFT (Hann + bandas
  logarítmicas + suavização exponencial) sobre a trilha original do chefe
  (`geladeira tsunami.wav`).
"""

from __future__ import annotations

import math
import os
import random
import wave
from typing import Optional

import numpy as np
import pygame

from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset

# =============================================================================
# CONSTANTES DE ÁUDIO E DSP
# =============================================================================

HEADROOM_MUSICA: float = 0.40
HEADROOM_SFX: float = 0.85
TEMPO_RAMPA_VOLUME: float = 0.02  # ~20 ms

FATORES_PITCH_PADRAO: tuple[float, ...] = (0.91, 0.94, 0.97, 1.00, 1.03, 1.06, 1.09)

CHAVES_PITCH_ARMAS: tuple[str, ...] = (
    "tiro_pistola",
    "tiro_minigun",
    "tiro_shotgun",
    "tiro_rifle",
    "tiro_foguete",
    "tiro_granada",
    "ataque_melee",
)

CHAVES_PITCH_PICKUPS: tuple[str, ...] = (
    "pickup_xp",
    "pickup_cura",
    "pickup_arma",
    "pickup_equipamento",
)

CHAVES_PITCH_POOL: tuple[str, ...] = CHAVES_PITCH_ARMAS + CHAVES_PITCH_PICKUPS

CANAIS_SFX_MINIMOS: int = 32


def _clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _normalizar_chave_sfx(asset_key: str) -> str:
    """Normaliza chaves com ou sem prefixo 'sfx_' para a forma canônica."""
    chave = str(asset_key).strip()
    if chave.startswith("sfx_"):
        return chave[4:]
    return chave


def _resolver_caminho_sfx(asset_key: str) -> Optional[str]:
    """Resolve o caminho absoluto de um arquivo SFX a partir da chave."""
    canon = _normalizar_chave_sfx(asset_key)
    chave_catalogo = f"sfx_{canon}"
    if chave_catalogo in ASSET_PATHS:
        return obter_caminho_asset(chave_catalogo)
    if asset_key in ASSET_PATHS:
        return obter_caminho_asset(asset_key)
    candidato = os.path.join(ASSETS_DIR, "audio", "sfx", f"{canon}.wav")
    if os.path.isfile(candidato):
        return candidato
    return None


def _carregar_wav_float32(caminho: str) -> tuple[np.ndarray, int]:
    """
    Carrega um arquivo WAV PCM via stdlib `wave` + `numpy`.

    Retorna:
        (amostras_float32, taxa_amostragem)
        onde `amostras_float32` possui shape `(num_frames, num_canais)` em [-1.0, 1.0].
    """
    with wave.open(caminho, "rb") as wf:
        n_canais = wf.getnchannels()
        largura = wf.getsampwidth()
        taxa = wf.getframerate()
        n_frames = wf.getnframes()
        bruto = wf.readframes(n_frames)

    if n_frames == 0 or not bruto:
        return np.zeros((0, max(1, n_canais)), dtype=np.float32), taxa

    if largura == 1:
        dados = (np.frombuffer(bruto, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif largura == 2:
        dados = np.frombuffer(bruto, dtype=np.int16).astype(np.float32) / 32768.0
    elif largura == 4:
        dados = np.frombuffer(bruto, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Largura de amostra WAV não suportada: {largura} bytes em {caminho}")

    if n_canais > 1:
        dados = dados.reshape(-1, n_canais)
    else:
        dados = dados.reshape(-1, 1)

    return dados, taxa


def _float32_para_array_mixer(amostras: np.ndarray, canais_mixer: int) -> np.ndarray:
    """Converte array float32 (N,) ou (N, C) para int16 compatível com o mixer ativo."""
    if amostras.ndim == 1:
        mono = amostras
        if canais_mixer == 1:
            saida = mono
        else:
            saida = np.column_stack([mono] * canais_mixer)
    else:
        n_canais_src = amostras.shape[1]
        if canais_mixer == 1:
            saida = amostras.mean(axis=1)
        elif n_canais_src == canais_mixer:
            saida = amostras
        elif n_canais_src == 1:
            saida = np.repeat(amostras, canais_mixer, axis=1)
        else:
            mono = amostras.mean(axis=1)
            saida = np.column_stack([mono] * canais_mixer)

    escalado = np.clip(saida * 32767.0, -32768.0, 32767.0).astype(np.int16)
    return np.ascontiguousarray(escalado)


def _reamostrar_pitch(
    amostras: np.ndarray,
    taxa_origem: int,
    taxa_destino: int,
    fator_pitch: float,
) -> np.ndarray:
    """Reamostra áudio via `numpy.interp` aplicando deslocamento de pitch."""
    n_frames = amostras.shape[0]
    if n_frames <= 1 or fator_pitch <= 0.0:
        return amostras

    escala = (float(taxa_origem) / float(max(1, taxa_destino))) * float(fator_pitch)
    novo_len = max(1, int(round(n_frames / escala)))

    x_orig = np.arange(n_frames, dtype=np.float32)
    x_novo = np.linspace(0.0, float(n_frames - 1), novo_len, dtype=np.float32)

    n_canais = amostras.shape[1]
    resultado = np.empty((novo_len, n_canais), dtype=np.float32)
    for c in range(n_canais):
        resultado[:, c] = np.interp(x_novo, x_orig, amostras[:, c]).astype(np.float32)
    return resultado


class GerenciadorAudio:
    """
    Gerenciador de efeitos sonoros, síntese procedural e rampa suave de volume.

    Mantém intactas as músicas originais da v1 (`heavy is the bit.wav`,
    `geladeira tsunami.wav`) e nunca interrompe canais SFX ativos ao reproduzir
    novos efeitos sobrepostos.
    """

    def __init__(
        self,
        fatores_pitch: tuple[float, ...] = FATORES_PITCH_PADRAO,
        tempo_rampa: float = TEMPO_RAMPA_VOLUME,
        headroom_musica: float = HEADROOM_MUSICA,
        headroom_sfx: float = HEADROOM_SFX,
        rng: Optional[random.Random] = None,
        inicializar_automaticamente: bool = True,
    ):
        self._fatores_pitch: tuple[float, ...] = tuple(fatores_pitch)
        self._tempo_rampa: float = max(1e-4, float(tempo_rampa))
        self._headroom_musica: float = _clamp(float(headroom_musica), 0.0, 1.0)
        self._headroom_sfx: float = _clamp(float(headroom_sfx), 0.0, 1.0)
        self._rng: random.Random = rng if rng is not None else random.Random()

        self._mixer_disponivel: bool = False
        self._taxa_mixer: int = 44100
        self._canais_mixer: int = 2

        # Pools pré-gerados: chave canônica -> lista de pygame.mixer.Sound
        self._pool_pitch: dict[str, list[pygame.mixer.Sound]] = {}
        self._ultimo_indice_pitch: dict[str, int] = {}
        self._sons_simples: dict[str, pygame.mixer.Sound] = {}

        # Sons sintetizados proceduralmente
        self._som_parry_clang: Optional[pygame.mixer.Sound] = None
        self._sons_parry_clang_pitch: dict[str, Optional[pygame.mixer.Sound]] = {}
        self._som_parry_whiff: Optional[pygame.mixer.Sound] = None
        self._som_tiro_sobrecarregado: Optional[pygame.mixer.Sound] = None

        # Estado de rampa suave de volume (~20 ms)
        self._volume_musica_atual: float = self._headroom_musica
        self._volume_sfx_atual: float = self._headroom_sfx
        self._volume_musica_alvo: float = self._headroom_musica
        self._volume_sfx_alvo: float = self._headroom_sfx
        self._rampa_musica_inicio: float = self._headroom_musica
        self._rampa_sfx_inicio: float = self._headroom_sfx
        self._rampa_progresso: float = 1.0

        if inicializar_automaticamente:
            self.inicializar()

    # ------------------------------------------------------------------
    # Propriedades de inspeção
    # ------------------------------------------------------------------

    @property
    def mixer_disponivel(self) -> bool:
        return self._mixer_disponivel

    @property
    def pool_pitch(self) -> dict[str, list[pygame.mixer.Sound]]:
        return self._pool_pitch

    @property
    def volume_musica_atual(self) -> float:
        return self._volume_musica_atual

    @property
    def volume_sfx_atual(self) -> float:
        return self._volume_sfx_atual

    @property
    def volume_musica_alvo(self) -> float:
        return self._volume_musica_alvo

    @property
    def volume_sfx_alvo(self) -> float:
        return self._volume_sfx_alvo

    @property
    def som_parry_clang(self) -> Optional[pygame.mixer.Sound]:
        return self._som_parry_clang

    @property
    def som_tiro_sobrecarregado(self) -> Optional[pygame.mixer.Sound]:
        return self._som_tiro_sobrecarregado

    # ------------------------------------------------------------------
    # Inicialização e pré-processamento
    # ------------------------------------------------------------------

    def inicializar(self) -> bool:
        """Inicializa o mixer (se necessário), gera os pools de pitch e sintetiza SFX."""
        self._mixer_disponivel = self._garantir_mixer()
        if not self._mixer_disponivel:
            return False

        self._pre_gerar_pools_pitch()
        self._som_parry_clang = self._sintetizar_parry_clang(1.0)
        self._sons_parry_clang_pitch = {
            "1.0": self._som_parry_clang,
            "1.25": self._sintetizar_parry_clang(1.25),
            "1.5": self._sintetizar_parry_clang(1.5),
        }
        self._som_parry_whiff = self._sintetizar_parry_whiff()
        self._som_tiro_sobrecarregado = self._sintetizar_tiro_sobrecarregado()
        return True

    def _garantir_mixer(self) -> bool:
        try:
            init_info = pygame.mixer.get_init()
            if not init_info:
                pygame.mixer.pre_init(44100, -16, 2, 512)
                pygame.mixer.init()
                init_info = pygame.mixer.get_init()
            if not init_info:
                return False

            self._taxa_mixer = int(init_info[0])
            self._canais_mixer = max(1, int(init_info[2]))

            if pygame.mixer.get_num_channels() < CANAIS_SFX_MINIMOS:
                pygame.mixer.set_num_channels(CANAIS_SFX_MINIMOS)
            return True
        except Exception:
            return False

    def _pre_gerar_pools_pitch(self) -> None:
        """Pré-gera as 7 variações de pitch (0.91..1.09) para tiros e pickups."""
        for chave in CHAVES_PITCH_POOL:
            caminho = _resolver_caminho_sfx(chave)
            if not caminho or not os.path.isfile(caminho):
                continue
            variantes = self._criar_variantes_pitch(caminho)
            if variantes:
                self._pool_pitch[chave] = variantes

    def _criar_variantes_pitch(self, caminho_wav: str) -> list[pygame.mixer.Sound]:
        variantes: list[pygame.mixer.Sound] = []
        try:
            amostras, taxa_origem = _carregar_wav_float32(caminho_wav)
            if amostras.shape[0] == 0:
                return variantes
            for fator in self._fatores_pitch:
                reamostrado = _reamostrar_pitch(
                    amostras, taxa_origem, self._taxa_mixer, fator
                )
                arr_mixer = _float32_para_array_mixer(reamostrado, self._canais_mixer)
                som = pygame.sndarray.make_sound(arr_mixer)
                variantes.append(som)
        except Exception:
            return []
        return variantes

    def _sintetizar_parry_clang(self, pitch_mult: float = 1.0) -> Optional[pygame.mixer.Sound]:
        """Sintetiza clang metálico dual-tone de parry via numpy + sndarray com variação de pitch."""
        if not self._mixer_disponivel:
            return None
        try:
            duracao = 0.22
            n = max(1, int(round(self._taxa_mixer * duracao)))
            t = np.linspace(0.0, duracao, n, endpoint=False, dtype=np.float32)

            p = float(pitch_mult)
            tom_principal = np.sin(2.0 * np.pi * 1180.0 * p * t)
            tom_metalico = np.sin(2.0 * np.pi * 2890.0 * p * t)
            transiente = np.sin(2.0 * np.pi * 4320.0 * p * t) * np.exp(-t * 50.0)

            env_corpo = np.exp(-t * 16.0)
            ataque = np.minimum(1.0, t / 0.002)

            onda = ataque * (
                (0.55 * tom_principal + 0.45 * tom_metalico) * env_corpo
                + 0.35 * transiente
            )
            pico = float(np.max(np.abs(onda)))
            if pico > 1e-6:
                onda = (onda / pico) * 0.85

            arr = _float32_para_array_mixer(onda.astype(np.float32), self._canais_mixer)
            return pygame.sndarray.make_sound(arr)
        except Exception:
            return None

    def _sintetizar_parry_whiff(self) -> Optional[pygame.mixer.Sound]:
        """Sintetiza efeito sonoro descendente de falha/whiff no parry."""
        if not self._mixer_disponivel:
            return None
        try:
            duracao = 0.26
            n = max(1, int(round(self._taxa_mixer * duracao)))
            t = np.linspace(0.0, duracao, n, endpoint=False, dtype=np.float32)

            freq = 290.0 - (175.0 * (t / duracao))
            fase = 2.0 * np.pi * np.cumsum(freq) / float(self._taxa_mixer)
            env = np.minimum(1.0, t / 0.01) * np.exp(-t * 8.5)
            onda = (0.65 * np.sin(fase) + 0.35 * np.sin(fase * 1.5)) * env
            pico = float(np.max(np.abs(onda)))
            if pico > 1e-6:
                onda = (onda / pico) * 0.75

            arr = _float32_para_array_mixer(onda.astype(np.float32), self._canais_mixer)
            return pygame.sndarray.make_sound(arr)
        except Exception:
            return None

    def _sintetizar_tiro_sobrecarregado(self) -> Optional[pygame.mixer.Sound]:
        """Sintetiza disparo sobrecarregado agudo/estalado da pistola via numpy + sndarray."""
        if not self._mixer_disponivel:
            return None
        try:
            duracao = 0.14
            n = max(1, int(round(self._taxa_mixer * duracao)))
            t = np.linspace(0.0, duracao, n, endpoint=False, dtype=np.float32)

            # Sweep de frequência rápido + estalo harmônico agudo
            freq_inst = 240.0 + 1650.0 * np.exp(-t * 42.0)
            fase = 2.0 * np.pi * np.cumsum(freq_inst) / float(self._taxa_mixer)
            sweep = np.sin(fase)

            estalo = (
                0.55 * np.sin(2.0 * np.pi * 1480.0 * t)
                + 0.45 * np.sin(2.0 * np.pi * 2760.0 * t)
            ) * np.exp(-t * 38.0)

            # Ruído determinístico curto para ataque seco
            gerador = np.random.default_rng(42)
            ruido = gerador.uniform(-1.0, 1.0, size=n).astype(np.float32) * np.exp(-t * 65.0)

            ataque = np.minimum(1.0, t / 0.001)
            env = np.exp(-t * 24.0)
            onda = ataque * (0.55 * sweep * env + 0.35 * estalo + 0.25 * ruido)

            pico = float(np.max(np.abs(onda)))
            if pico > 1e-6:
                onda = (onda / pico) * 0.88

            arr = _float32_para_array_mixer(onda.astype(np.float32), self._canais_mixer)
            return pygame.sndarray.make_sound(arr)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Reprodução SFX (sobreposta, sem cancelar canais ativos)
    # ------------------------------------------------------------------

    def _obter_som_simples(self, canon: str, asset_key: str) -> Optional[pygame.mixer.Sound]:
        if canon in self._sons_simples:
            return self._sons_simples[canon]
        caminho = _resolver_caminho_sfx(asset_key)
        if not caminho or not os.path.isfile(caminho):
            return None
        try:
            som = pygame.mixer.Sound(caminho)
            self._sons_simples[canon] = som
            return som
        except Exception:
            return None

    def _reproduzir_som(
        self,
        som: Optional[pygame.mixer.Sound],
        volume_mult: float = 1.0,
    ) -> Optional[pygame.mixer.Channel]:
        """
        Reproduz um Sound em um canal livre sem jamais parar canais já ativos.
        """
        if som is None or not self._mixer_disponivel:
            return None
        try:
            if not pygame.mixer.get_init():
                return None
            vol = _clamp(self._volume_sfx_atual * max(0.0, float(volume_mult)), 0.0, 1.0)
            canal = pygame.mixer.find_channel(False)
            if canal is None:
                return None
            canal.set_volume(vol)
            canal.play(som)
            return canal
        except Exception:
            return None

    def tocar_sfx(
        self,
        asset_key: str,
        pitch_aleatorio: bool = True,
        volume_mult: float = 1.0,
    ) -> Optional[pygame.mixer.Channel]:
        """
        Reproduz um efeito sonoro de forma segura em áudio real e SDL_AUDIODRIVER=dummy.

        Se `asset_key` possuir pool de pitch pré-gerado e `pitch_aleatorio=True`,
        escolhe uma variante aleatória (evitando repetir a mesma imediatamente).
        Nunca interrompe canais ativos.
        """
        if not self._mixer_disponivel:
            return None

        canon = _normalizar_chave_sfx(asset_key)
        pool = self._pool_pitch.get(canon)
        if pool:
            if pitch_aleatorio and len(pool) > 1:
                anterior = self._ultimo_indice_pitch.get(canon, -1)
                idx = self._rng.randrange(len(pool))
                if idx == anterior:
                    idx = (idx + 1) % len(pool)
                self._ultimo_indice_pitch[canon] = idx
                som = pool[idx]
            else:
                som = pool[len(pool) // 2]
        else:
            som = self._obter_som_simples(canon, asset_key)

        return self._reproduzir_som(som, volume_mult=volume_mult)

    def tocar_parry_clang(self, volume_mult: float = 1.0, pitch_mult: float = 1.0) -> Optional[pygame.mixer.Channel]:
        """Reproduz o clang metálico sintetizado de parry (com variação de pitch para duelos)."""
        som = self._som_parry_clang
        if pitch_mult >= 1.4 and self._sons_parry_clang_pitch.get("1.5") is not None:
            som = self._sons_parry_clang_pitch["1.5"]
        elif pitch_mult >= 1.2 and self._sons_parry_clang_pitch.get("1.25") is not None:
            som = self._sons_parry_clang_pitch["1.25"]
        return self._reproduzir_som(som, volume_mult=volume_mult)

    def tocar_parry_whiff(self, volume_mult: float = 1.0) -> Optional[pygame.mixer.Channel]:
        """Reproduz o efeito sonoro de falha/whiff no parry (no-op seguro sem mixer)."""
        return self._reproduzir_som(self._som_parry_whiff, volume_mult=volume_mult)

    def tocar_tiro_sobrecarregado(self, volume_mult: float = 1.0) -> Optional[pygame.mixer.Channel]:
        """Reproduz o estalo sintetizado do 4º tiro sobrecarregado (no-op seguro sem mixer)."""
        return self._reproduzir_som(self._som_tiro_sobrecarregado, volume_mult=volume_mult)

    # ------------------------------------------------------------------
    # Rampa suave de volume (~20 ms)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalizar_escala_volumes(
        master: float, musica: float, sfx: float
    ) -> tuple[float, float, float]:
        """Aceita tanto escala 0..1 quanto 0..100 e normaliza para [0.0, 1.0]."""
        m = float(master)
        mus = float(musica)
        s = float(sfx)
        if max(m, mus, s) > 1.0:
            m /= 100.0
            mus /= 100.0
            s /= 100.0
        return _clamp(m, 0.0, 1.0), _clamp(mus, 0.0, 1.0), _clamp(s, 0.0, 1.0)

    def definir_volumes_alvo(self, master: float, musica: float, sfx: float) -> None:
        """
        Define os volumes-alvo (0..100 ou 0.0..1.0) aplicando headroom dedicado
        (música 0.40, SFX 0.85) e iniciando a rampa suave de ~20 ms.
        """
        m_norm, mus_norm, sfx_norm = self._normalizar_escala_volumes(master, musica, sfx)

        novo_alvo_musica = _clamp(
            m_norm * mus_norm * self._headroom_musica, 0.0, self._headroom_musica
        )
        novo_alvo_sfx = _clamp(
            m_norm * sfx_norm * self._headroom_sfx, 0.0, self._headroom_sfx
        )

        self._rampa_musica_inicio = self._volume_musica_atual
        self._rampa_sfx_inicio = self._volume_sfx_atual
        self._volume_musica_alvo = novo_alvo_musica
        self._volume_sfx_alvo = novo_alvo_sfx
        self._rampa_progresso = 0.0

    def atualizar(self, dt: float) -> None:
        """Avança a rampa suave de volume (~20 ms) e sincroniza com pygame.mixer.music."""
        dt_val = max(0.0, float(dt))
        if self._rampa_progresso < 1.0 and dt_val > 0.0:
            self._rampa_progresso = min(1.0, self._rampa_progresso + (dt_val / self._tempo_rampa))
            t = self._rampa_progresso
            self._volume_musica_atual = _clamp(
                self._rampa_musica_inicio + (self._volume_musica_alvo - self._rampa_musica_inicio) * t,
                0.0,
                self._headroom_musica,
            )
            self._volume_sfx_atual = _clamp(
                self._rampa_sfx_inicio + (self._volume_sfx_alvo - self._rampa_sfx_inicio) * t,
                0.0,
                self._headroom_sfx,
            )

        if self._mixer_disponivel:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.set_volume(self._volume_musica_atual)
            except Exception:
                pass


class AnalisadorFFTBoss:
    """
    Analisador espectral determinístico (FFT) para a trilha do chefe Geladeira Tsunami.

    Carrega `assets/audio/musica/geladeira tsunami.wav` uma única vez em memória
    como float32 mono normalizado e calcula bandas logarítmicas em [0.0, 1.0]
    via `numpy.fft.rfft` com janela de Hann e suavização exponencial.
    """

    def __init__(
        self,
        caminho_wav: Optional[str] = None,
        tamanho_fft: int = 1024,
        tau_ataque: float = 0.025,
        tau_queda: float = 0.090,
    ):
        self._caminho_wav: str = (
            caminho_wav if caminho_wav is not None else obter_caminho_asset("musica_boss")
        )
        self._tamanho_fft: int = max(64, int(tamanho_fft))
        self._tau_ataque: float = max(1e-4, float(tau_ataque))
        self._tau_queda: float = max(1e-4, float(tau_queda))

        self._amostras: np.ndarray = np.zeros(0, dtype=np.float32)
        self._taxa_amostragem: int = 22050
        self._duracao_ms: float = 0.0
        self._carregado: bool = False

        self._janela_hann: np.ndarray = np.hanning(self._tamanho_fft).astype(np.float32)
        self._freqs: np.ndarray = np.fft.rfftfreq(
            self._tamanho_fft, d=1.0 / float(self._taxa_amostragem)
        )
        self._cache_limites_bandas: dict[int, list[tuple[int, int]]] = {}
        self._bandas_suavizadas: list[float] = []

        self._carregar_trilha()

    @property
    def carregado(self) -> bool:
        return self._carregado

    @property
    def taxa_amostragem(self) -> int:
        return self._taxa_amostragem

    @property
    def duracao_ms(self) -> float:
        return self._duracao_ms

    def _carregar_trilha(self) -> None:
        if not self._caminho_wav or not os.path.isfile(self._caminho_wav):
            self._carregado = False
            return
        try:
            dados, taxa = _carregar_wav_float32(self._caminho_wav)
            if dados.shape[0] == 0:
                self._carregado = False
                return
            mono = dados.mean(axis=1).astype(np.float32) if dados.shape[1] > 1 else dados[:, 0]
            pico = float(np.max(np.abs(mono)))
            if pico > 1.0:
                mono = mono / pico

            self._amostras = np.ascontiguousarray(mono, dtype=np.float32)
            self._taxa_amostragem = int(taxa)
            self._duracao_ms = (len(self._amostras) / float(self._taxa_amostragem)) * 1000.0
            self._freqs = np.fft.rfftfreq(
                self._tamanho_fft, d=1.0 / float(self._taxa_amostragem)
            )
            self._cache_limites_bandas.clear()
            self._carregado = True
        except Exception:
            self._carregado = False

    def _obter_limites_bandas(self, num_bandas: int) -> list[tuple[int, int]]:
        if num_bandas in self._cache_limites_bandas:
            return self._cache_limites_bandas[num_bandas]

        n_bins = len(self._freqs)
        f_min = 40.0
        f_max = min(10000.0, self._taxa_amostragem * 0.48)
        if f_max <= f_min:
            f_max = max(f_min + 1.0, self._taxa_amostragem * 0.5)

        bordas = np.geomspace(f_min, f_max, num_bandas + 1)
        limites: list[tuple[int, int]] = []
        for i in range(num_bandas):
            lo = int(np.searchsorted(self._freqs, bordas[i], side="left"))
            hi = int(np.searchsorted(self._freqs, bordas[i + 1], side="right"))
            lo = max(1, min(lo, n_bins - 1))
            hi = max(lo + 1, min(hi, n_bins))
            limites.append((lo, hi))

        self._cache_limites_bandas[num_bandas] = limites
        return limites

    def resetar(self) -> None:
        """Limpa o estado suavizado das bandas."""
        self._bandas_suavizadas = []

    def obter_bandas(
        self,
        pos_ms: float,
        dt: float = 0.016,
        num_bandas: int = 28,
    ) -> list[float]:
        """
        Retorna `num_bandas` intensidades normalizadas em [0.0, 1.0] para a
        posição `pos_ms` da trilha, suavizadas exponencialmente entre frames.
        """
        n_bandas = int(num_bandas)
        if n_bandas <= 0:
            return []

        if not self._carregado or len(self._amostras) == 0:
            return [0.0] * n_bandas

        if len(self._bandas_suavizadas) != n_bandas:
            self._bandas_suavizadas = [0.0] * n_bandas

        total = len(self._amostras)
        pos_seg = max(0.0, float(pos_ms)) / 1000.0
        idx_inicio = int(pos_seg * self._taxa_amostragem) % total
        idx_fim = idx_inicio + self._tamanho_fft

        if idx_fim <= total:
            bloco = self._amostras[idx_inicio:idx_fim]
        else:
            parte1 = self._amostras[idx_inicio:total]
            restante = self._tamanho_fft - len(parte1)
            if restante <= total:
                parte2 = self._amostras[:restante]
                bloco = np.concatenate((parte1, parte2))
            else:
                bloco = np.resize(self._amostras, self._tamanho_fft)

        espectro = np.abs(np.fft.rfft(bloco * self._janela_hann)) / (self._tamanho_fft * 0.5)
        limites = self._obter_limites_bandas(n_bandas)

        dt_val = max(0.0, float(dt))
        alpha_ataque = 1.0 - math.exp(-dt_val / self._tau_ataque) if dt_val > 0.0 else 0.0
        alpha_queda = 1.0 - math.exp(-dt_val / self._tau_queda) if dt_val > 0.0 else 0.0

        db_min = -60.0
        db_max = -6.0
        db_range = db_max - db_min

        saida: list[float] = []
        for i, (lo, hi) in enumerate(limites):
            fatia = espectro[lo:hi]
            energia = float(np.sqrt(np.mean(fatia * fatia))) if fatia.size > 0 else 0.0
            db = 20.0 * math.log10(energia + 1e-6)
            bruto = _clamp((db - db_min) / db_range, 0.0, 1.0)

            anterior = self._bandas_suavizadas[i]
            alpha = alpha_ataque if bruto >= anterior else alpha_queda
            suavizado = _clamp(anterior + (bruto - anterior) * alpha, 0.0, 1.0)
            self._bandas_suavizadas[i] = suavizado
            saida.append(suavizado)

        return saida

    def obter_energia_grave(self, pos_ms: float, dt: float = 0.016, num_bandas: int = 28) -> float:
        """Retorna a energia normalizada [0.0, 1.0] das bandas graves (sub-bass/kick) da trilha do Boss."""
        bandas = self.obter_bandas(pos_ms, dt=dt, num_bandas=num_bandas)
        if not bandas:
            return 0.0
        graves = bandas[:min(5, len(bandas))]
        return float(sum(graves) / float(len(graves)))
