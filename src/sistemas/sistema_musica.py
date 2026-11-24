"""
Sistema de Música Dinâmica — Protocolo: Batata

Máquina de estados com dois canais reservados do mixer do Pygame-CE para
reprodução em lock-step de faixas limpas e abafadas (muffled) com transições
gapless orientadas por frase musical (lookahead queue), mantendo a trilha da
Geladeira Tsunami em pygame.mixer.music intacta.
"""

from __future__ import annotations

import os
import time
from typing import Callable, Optional

import pygame

from src.utils.constantes import (
    MUSICA_LOOKAHEAD_SEGUNDOS,
    MUSICA_TEMPO_ASSAULT,
    MUSICA_TRANSICAO_ABAFADO_SEGUNDOS,
    MUSICA_VOLUME_BASE,
    obter_caminho_asset,
)


class SistemaMusica:
    """
    Gerenciador centralizado de trilha sonora dinâmica.

    Fluxo de estados:
        MENU (8bit-control, loop)
          --[corte abrupto: iniciar_partida]--> ANTICIPATION (1x)
          --[fim da frase, gapless]-----------> HOLD (loop até tempo_sobrevivencia >= 50s)
          --[fim da frase hold, gapless]------> ASSAULT_INTRO (1x)
          --[fim da frase, gapless]-----------> ASSAULT (loop até cutscene do boss)
          --[fadeout_para_boss / parar]-------> BOSS (geladeira tsunami via mixer.music)
    """

    ESTADO_PARADO = "parado"
    ESTADO_MENU = "menu"
    ESTADO_ANTICIPATION = "anticipation"
    ESTADO_HOLD = "hold"
    ESTADO_ASSAULT_INTRO = "assault_intro"
    ESTADO_ASSAULT = "assault"
    ESTADO_BOSS = "boss"

    _ESTADOS_GAMEPLAY = (
        ESTADO_ANTICIPATION,
        ESTADO_HOLD,
        ESTADO_ASSAULT_INTRO,
        ESTADO_ASSAULT,
    )

    _MAPA_FAIXAS: dict[str, tuple[str, Optional[str]]] = {
        ESTADO_MENU: ("musica_menu", None),
        ESTADO_ANTICIPATION: ("musica_anticipation", "musica_anticipation_muffled"),
        ESTADO_HOLD: ("musica_hold", "musica_hold_muffled"),
        ESTADO_ASSAULT_INTRO: ("musica_assault_intro", "musica_assault_intro_muffled"),
        ESTADO_ASSAULT: ("musica_assault", "musica_assault_muffled"),
    }

    _CANAIS_MINIMOS = 16
    _CANAIS_RESERVADOS = 2
    _DURACOES_FALLBACK_HEADLESS: dict[str, float] = {
        ESTADO_ANTICIPATION: 8.0,
        ESTADO_HOLD: 16.0,
        ESTADO_ASSAULT_INTRO: 6.0,
        ESTADO_ASSAULT: 20.0,
    }

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        canal_normal=None,
        canal_abafado=None,
        sons_injetados: Optional[dict[str, object]] = None,
        tempo_assault: float = MUSICA_TEMPO_ASSAULT,
        lookahead_segundos: Optional[float] = None,
        transicao_abafado_segundos: float = MUSICA_TRANSICAO_ABAFADO_SEGUNDOS,
    ):
        self._clock = clock
        self._canal_normal = canal_normal
        self._canal_abafado = canal_abafado
        self._sons: dict[str, object] = dict(sons_injetados) if sons_injetados is not None else {}
        self._duracoes: dict[str, float] = {}
        self._injetado = sons_injetados is not None or canal_normal is not None

        self._tempo_assault = float(tempo_assault)
        if lookahead_segundos is None:
            self._lookahead_segundos = max(float(MUSICA_LOOKAHEAD_SEGUNDOS), 0.50)
        else:
            self._lookahead_segundos = float(lookahead_segundos)
        self._transicao_abafado_segundos = float(transicao_abafado_segundos)

        self._inicializado = False
        self.estado: str = self.ESTADO_PARADO
        self._proximo_enfileirado: Optional[str] = None
        self._inicio_faixa: float = 0.0
        self._duracao_atual: float = 0.0
        self._ultimo_tick: float = 0.0
        self._ciclo_assault_iniciado: bool = False
        self._hold_restantes: int = 0
        self._evento_assault_intro_pendente: bool = False
        self.ciclos_assault_concluidos: int = 0
        self._relogio_headless: float = 0.0

        self._volume_master: float = 100.0
        self._volume_musica: float = 100.0
        self._fator_abafado: float = 0.0
        self._abafado_alvo: bool = False

        if sons_injetados is not None:
            for chave, som in sons_injetados.items():
                self._duracoes[chave] = float(som.get_length())
            self._inicializado = True

    def inicializar(self) -> bool:
        """
        Inicializa o mixer, reserva os dois canais dedicados de música e faz o
        pré-carregamento em memória das faixas dinâmicas (zero I/O durante o jogo).
        """
        if self._inicializado:
            return True

        try:
            from PPlay.sound import SoundManager
            SoundManager.inicializar()
        except Exception:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.pre_init(44100, -16, 2, 512)
                    pygame.mixer.init()
            except Exception:
                return False

        try:
            if not pygame.mixer.get_init():
                return False
            if pygame.mixer.get_num_channels() < self._CANAIS_MINIMOS:
                pygame.mixer.set_num_channels(self._CANAIS_MINIMOS)
            pygame.mixer.set_reserved(self._CANAIS_RESERVADOS)
            if self._canal_normal is None:
                self._canal_normal = pygame.mixer.Channel(0)
            if self._canal_abafado is None:
                self._canal_abafado = pygame.mixer.Channel(1)
        except Exception:
            return False

        chaves_unicas: set[str] = set()
        for chave_normal, chave_abafada in self._MAPA_FAIXAS.values():
            chaves_unicas.add(chave_normal)
            if chave_abafada is not None:
                chaves_unicas.add(chave_abafada)

        for chave in sorted(chaves_unicas):
            if chave in self._sons:
                continue
            try:
                caminho = obter_caminho_asset(chave)
                if os.path.isfile(caminho):
                    som = pygame.mixer.Sound(caminho)
                    self._sons[chave] = som
                    self._duracoes[chave] = float(som.get_length())
            except Exception:
                continue

        self._inicializado = True
        return True

    def calcular_volume_efetivo(self, base: float = MUSICA_VOLUME_BASE) -> float:
        """Calcula o volume efetivo da música: base * (musica/100) * (master/100)."""
        return float(
            max(0.0, min(1.0, base * (self._volume_musica / 100.0) * (self._volume_master / 100.0)))
        )

    def atualizar_volume(self, vol_master: float, vol_musica: float) -> None:
        """Sincroniza os volumes configurados nos canais dinâmicos e no pygame.mixer.music."""
        try:
            self._volume_master = max(0.0, min(100.0, float(vol_master)))
        except (ValueError, TypeError):
            self._volume_master = 100.0
        try:
            self._volume_musica = max(0.0, min(100.0, float(vol_musica)))
        except (ValueError, TypeError):
            self._volume_musica = 100.0

        self._aplicar_volumes_canais()

        if not self._injetado:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.set_volume(self.calcular_volume_efetivo())
            except Exception:
                pass

    def _aplicar_volumes_canais(self) -> None:
        vol_total = self.calcular_volume_efetivo()
        if self.estado == self.ESTADO_MENU:
            vol_normal = vol_total
            vol_abafado = 0.0
        elif self.estado in self._ESTADOS_GAMEPLAY:
            vol_normal = vol_total * (1.0 - self._fator_abafado)
            vol_abafado = vol_total * self._fator_abafado
        else:
            vol_normal = 0.0
            vol_abafado = 0.0

        try:
            if self._canal_normal is not None:
                self._canal_normal.set_volume(vol_normal)
            if self._canal_abafado is not None:
                self._canal_abafado.set_volume(vol_abafado)
        except Exception:
            pass

    def _parar_mixer_music(self) -> None:
        if self._injetado:
            return
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music._current_track = None
        except Exception:
            pass

    def _parar_canais(self) -> None:
        try:
            if self._canal_normal is not None:
                self._canal_normal.stop()
            if self._canal_abafado is not None:
                self._canal_abafado.stop()
        except Exception:
            pass

    def _obter_par_sons(self, estado: str) -> tuple[Optional[object], Optional[object]]:
        chave_normal, chave_abafada = self._MAPA_FAIXAS.get(estado, ("", None))
        som_normal = self._sons.get(chave_normal)
        som_abafado = self._sons.get(chave_abafada) if chave_abafada is not None else None
        return som_normal, som_abafado

    def _obter_duracao_estado(self, estado: str) -> float:
        chave_normal, _ = self._MAPA_FAIXAS.get(estado, ("", None))
        return float(self._duracoes.get(chave_normal, 0.0))

    @property
    def fase_onda_atual(self) -> str:
        """Retorna a fase macro de onda sincronizada com a trilha ('assault' ou 'calm')."""
        if self.estado in (self.ESTADO_ASSAULT_INTRO, self.ESTADO_ASSAULT):
            return "assault"
        return "calm"

    def consumir_evento_assault_intro(self) -> bool:
        """Consome o gatilho de borda gerado na entrada de ESTADO_ASSAULT_INTRO."""
        if self._evento_assault_intro_pendente:
            self._evento_assault_intro_pendente = False
            return True
        return False

    def _ao_entrar_estado(self, estado_anterior: str, novo_estado: str) -> None:
        if novo_estado == self.ESTADO_ASSAULT_INTRO:
            self._ciclo_assault_iniciado = True
            self._hold_restantes = 0
            if estado_anterior != self.ESTADO_ASSAULT_INTRO:
                self._evento_assault_intro_pendente = True
        elif novo_estado == self.ESTADO_HOLD and self._ciclo_assault_iniciado:
            if estado_anterior == self.ESTADO_ANTICIPATION:
                # 1ª passagem de hold no ciclo: resta mais 1 repetição (total 2x)
                self._hold_restantes = 1
            elif estado_anterior == self.ESTADO_HOLD:
                self._hold_restantes = max(0, self._hold_restantes - 1)
        if estado_anterior == self.ESTADO_ASSAULT and novo_estado == self.ESTADO_ANTICIPATION:
            self.ciclos_assault_concluidos += 1

    def _tocar_par_estado(self, estado: str, loops: int = 0) -> None:
        som_normal, som_abafado = self._obter_par_sons(estado)
        self._parar_canais()

        estado_anterior = self.estado
        agora = self._clock()
        self.estado = estado
        self._ao_entrar_estado(estado_anterior, estado)
        self._proximo_enfileirado = None
        self._inicio_faixa = agora
        self._ultimo_tick = agora
        self._duracao_atual = self._obter_duracao_estado(estado)

        try:
            if self._canal_normal is not None and som_normal is not None:
                self._canal_normal.play(som_normal, loops=loops)
            if self._canal_abafado is not None and som_abafado is not None:
                self._canal_abafado.play(som_abafado, loops=loops)
        except Exception:
            pass

        self._aplicar_volumes_canais()

    def tocar_menu(self) -> None:
        """
        Toca a faixa de menu (8bit-control) em loop.
        Mantém a reprodução contínua se o menu já estiver tocando (ex.: volta do Tutorial),
        mas faz corte abrupto se vier de qualquer estado de gameplay ou boss.
        """
        if not self._inicializado:
            self.inicializar()

        self._parar_mixer_music()

        if self.estado == self.ESTADO_MENU and self._canal_normal is not None:
            try:
                if self._canal_normal.get_busy():
                    self._aplicar_volumes_canais()
                    return
            except Exception:
                pass

        self._fator_abafado = 0.0
        self._abafado_alvo = False
        self._ciclo_assault_iniciado = False
        self._hold_restantes = 0
        self._evento_assault_intro_pendente = False
        self.ciclos_assault_concluidos = 0
        self._relogio_headless = 0.0
        self._tocar_par_estado(self.ESTADO_MENU, loops=-1)

    def iniciar_partida(self) -> None:
        """
        Faz corte abrupto de qualquer trilha anterior (menu, assault, boss)
        e inicia a sequência de gameplay em ANTICIPATION (limpo + abafado em lock-step).
        """
        if not self._inicializado:
            self.inicializar()

        self._parar_mixer_music()
        self._fator_abafado = 0.0
        self._abafado_alvo = False
        self._ciclo_assault_iniciado = False
        self._hold_restantes = 0
        self._evento_assault_intro_pendente = False
        self.ciclos_assault_concluidos = 0
        self._relogio_headless = 0.0
        self._tocar_par_estado(self.ESTADO_ANTICIPATION, loops=0)

    def _decidir_proximo_estado(
        self,
        tempo_sobrevivencia: float,
        trava_assault: bool = False,
        pausar_transicao: bool = False,
    ) -> str:
        if pausar_transicao:
            return self.estado
        if self.estado == self.ESTADO_ANTICIPATION:
            return self.ESTADO_HOLD
        if self.estado == self.ESTADO_HOLD:
            if self._ciclo_assault_iniciado:
                return self.ESTADO_HOLD if self._hold_restantes > 0 else self.ESTADO_ASSAULT_INTRO
            if tempo_sobrevivencia >= self._tempo_assault:
                return self.ESTADO_ASSAULT_INTRO
            return self.ESTADO_HOLD
        if self.estado == self.ESTADO_ASSAULT_INTRO:
            return self.ESTADO_ASSAULT
        if self.estado == self.ESTADO_ASSAULT:
            if trava_assault:
                return self.ESTADO_ASSAULT
            return self.ESTADO_ANTICIPATION
        return self.estado

    def _enfileirar_estado(self, proximo_estado: str) -> None:
        som_normal, som_abafado = self._obter_par_sons(proximo_estado)
        try:
            if self._canal_normal is not None and som_normal is not None:
                self._canal_normal.queue(som_normal)
            if self._canal_abafado is not None and som_abafado is not None:
                self._canal_abafado.queue(som_abafado)
        except Exception:
            return
        self._proximo_enfileirado = proximo_estado

    def atualizar(
        self,
        tempo_sobrevivencia: float,
        abafado: bool = False,
        dt: Optional[float] = None,
        trava_assault: bool = False,
        pausar_transicao: bool = False,
    ) -> None:
        """
        Atualiza o cross-blend normal/abafado e gerencia o enfileiramento gapless
        entre frases musicais durante o gameplay.
        """
        if self.estado not in self._ESTADOS_GAMEPLAY:
            return

        agora = self._clock()
        passo_dt = dt if (dt is not None and dt > 0.0) else max(0.0, agora - self._ultimo_tick)
        self._ultimo_tick = agora

        # 1. Cross-blend suave entre trilha limpa e abafada (evita clique digital)
        self._abafado_alvo = bool(abafado)
        alvo = 1.0 if self._abafado_alvo else 0.0
        fator_anterior = self._fator_abafado
        if self._transicao_abafado_segundos <= 0.0:
            self._fator_abafado = alvo
        else:
            delta_max = passo_dt / self._transicao_abafado_segundos
            if self._fator_abafado < alvo:
                self._fator_abafado = min(alvo, self._fator_abafado + delta_max)
            elif self._fator_abafado > alvo:
                self._fator_abafado = max(alvo, self._fator_abafado - delta_max)
        if self._fator_abafado != fator_anterior:
            self._aplicar_volumes_canais()

        # Fallback determinístico headless (sem sons carregados no mixer)
        if not self._injetado and self._duracao_atual <= 0.0:
            if not pausar_transicao:
                self._relogio_headless += passo_dt
                duracao_fallback = self._DURACOES_FALLBACK_HEADLESS.get(self.estado, 10.0)
                if self._relogio_headless >= duracao_fallback:
                    self._relogio_headless = 0.0
                    proximo = self._decidir_proximo_estado(
                        tempo_sobrevivencia,
                        trava_assault=trava_assault,
                        pausar_transicao=pausar_transicao,
                    )
                    estado_anterior = self.estado
                    self.estado = proximo
                    self._ao_entrar_estado(estado_anterior, self.estado)
                    self._aplicar_volumes_canais()
            return

        # 2. Detecta conclusão do handoff gapless no mixer
        if self._proximo_enfileirado is not None and self._canal_normal is not None:
            try:
                fila_atual = self._canal_normal.get_queue()
            except Exception:
                fila_atual = None
            if fila_atual is None:
                novo_inicio = self._inicio_faixa + self._duracao_atual
                # Se houve stall extremo maior que uma frase inteira, realinha ao relógio atual
                if abs(agora - novo_inicio) > max(1.0, self._duracao_atual):
                    novo_inicio = agora
                if pausar_transicao:
                    # Em pausa, mantém estado atual e realinha _inicio_faixa para evitar transição falsa ao despausar
                    self._inicio_faixa = novo_inicio
                    self._duracao_atual = self._obter_duracao_estado(self.estado)
                    self._proximo_enfileirado = None
                    self._aplicar_volumes_canais()
                else:
                    estado_anterior = self.estado
                    self.estado = self._proximo_enfileirado
                    self._ao_entrar_estado(estado_anterior, self.estado)
                    self._inicio_faixa = novo_inicio
                    self._duracao_atual = self._obter_duracao_estado(self.estado)
                    self._proximo_enfileirado = None
                    self._aplicar_volumes_canais()

        # 3. Recuperação caso o canal tenha parado (ex.: suspensão do SO em Pause + Alt-Tab ou fim da frase)
        decorrido = agora - self._inicio_faixa
        if self._canal_normal is not None and (self._duracao_atual > 0.0 or self._injetado):
            try:
                ocupado = self._canal_normal.get_busy()
            except Exception:
                ocupado = True
            if not ocupado:
                self._proximo_enfileirado = None
                proximo = (
                    self.estado
                    if pausar_transicao
                    else self._decidir_proximo_estado(
                        tempo_sobrevivencia,
                        trava_assault=trava_assault,
                        pausar_transicao=pausar_transicao,
                    )
                )
                self._tocar_par_estado(proximo, loops=0)
                return

        # 4. Janela de lookahead: enfileira a próxima frase (ou re-enfileira se get_queue() is None)
        fila_vazia = False
        if self._canal_normal is not None:
            try:
                fila_vazia = self._canal_normal.get_queue() is None
            except Exception:
                fila_vazia = True
        if self._duracao_atual > 0.0 and (self._proximo_enfileirado is None or fila_vazia):
            restante = self._duracao_atual - decorrido
            if restante <= self._lookahead_segundos:
                proximo = self._decidir_proximo_estado(
                    tempo_sobrevivencia,
                    trava_assault=trava_assault,
                    pausar_transicao=pausar_transicao,
                )
                self._enfileirar_estado(proximo)

    def fadeout_para_boss(self, fade_ms: int = 1600) -> None:
        """
        Inicia o fade-out dos canais dinâmicos para entregar o áudio à trilha
        da Geladeira Tsunami (que permanece em pygame.mixer.music).
        """
        self.estado = self.ESTADO_BOSS
        self._proximo_enfileirado = None
        self._evento_assault_intro_pendente = False
        self._relogio_headless = 0.0
        try:
            if self._canal_normal is not None:
                self._canal_normal.fadeout(int(fade_ms))
            if self._canal_abafado is not None:
                self._canal_abafado.fadeout(int(fade_ms))
        except Exception:
            pass

    def parar_dinamica(self, entrar_estado_boss: bool = False) -> None:
        """Interrompe imediatamente os canais dinâmicos."""
        self._proximo_enfileirado = None
        self._evento_assault_intro_pendente = False
        self._relogio_headless = 0.0
        self._parar_canais()
        self.estado = self.ESTADO_BOSS if entrar_estado_boss else self.ESTADO_PARADO


_INSTANCIA_SISTEMA_MUSICA: Optional[SistemaMusica] = None


def obter_sistema_musica() -> SistemaMusica:
    """Retorna a instância singleton global do SistemaMusica."""
    global _INSTANCIA_SISTEMA_MUSICA
    if _INSTANCIA_SISTEMA_MUSICA is None:
        _INSTANCIA_SISTEMA_MUSICA = SistemaMusica()
    return _INSTANCIA_SISTEMA_MUSICA
