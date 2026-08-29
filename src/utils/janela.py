"""
Módulo de Gerenciamento de Janela e Escalonamento Nativo — Protocolo: Batata
Implementa uma camada nativa em Pygame puro com suporte a:
- Resolução virtual fixa (800x600) com canvas virtual em alta definição.
- Escalonamento com Letterboxing preciso (manutenção rigorosa de Aspect Ratio).
- Conversão segura e clampada de coordenadas do mouse (Windowed e Fullscreen).
- Alternância robusta de tela cheia (F11 e Alt+Enter).
- Controle de taxa de quadros (FPS Cap) e delta_time calibrado.
- Compatibilidade integral com a interface PPlay Window.
"""

import sys
import os
import ctypes
import pygame
from pygame.locals import (
    QUIT, KEYDOWN, K_F11, K_RETURN, K_LALT, K_RALT,
    DOUBLEBUF, HWSURFACE, RESIZABLE, FULLSCREEN
)
from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, FPS_PADRAO
from src.utils.math_utils import clamp


class Janela:
    """
    Controlador de Janela e Renderização Nativa Pygame com Resolução Virtual.
    Singleton com suporte a High-DPI, Fullscreen e Letterbox limpo.
    """
    _instance = None
    screen = None
    _fontes_cache: dict = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Janela, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        largura_virtual: int = LARGURA_TELA,
        altura_virtual: int = ALTURA_TELA,
        titulo: str = TITULO_JOGO,
        resizavel: bool = True,
        pixel_art: bool = False
    ):
        if hasattr(self, "_already_init") and self._already_init:
            return

        if not pygame.get_init():
            pygame.init()

        # Configura High-DPI no Windows para nitidez máxima
        try:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        self.largura = int(largura_virtual)
        self.altura = int(altura_virtual)
        self.titulo = str(titulo)
        self.resizavel = bool(resizavel)
        self.pixel_art = True  # Renderização nítida via Nearest-Neighbor para eliminar textos borrados
        self.is_fullscreen = False

        self._clock = pygame.time.Clock()
        self._delta_time = 0.0
        self.fps_alvo = FPS_PADRAO
        self.eventos = []
        self.cor_fundo = (18, 22, 30)

        # Resolução padrão da Janela (1280x720 HD) e detecção de display
        desktop_info = pygame.display.Info()
        self.tela_nativa_largura = max(1280, getattr(desktop_info, "current_w", 1280))
        self.tela_nativa_altura = max(720, getattr(desktop_info, "current_h", 720))

        self.largura_janela_atual = 1280
        self.altura_janela_atual = 720

        # Configura flags de vídeo
        self._flags_janela = DOUBLEBUF | HWSURFACE
        if self.resizavel:
            self._flags_janela |= RESIZABLE

        # Janela do Sistema Operacional criada em 1280x720
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        self.real_screen = pygame.display.set_mode(
            (self.largura_janela_atual, self.altura_janela_atual),
            self._flags_janela
        )
        pygame.display.set_caption(self.titulo)

        # Buffer Virtual do Jogo (Canvas interno)
        self.screen = pygame.Surface((self.largura, self.altura))
        Janela.screen = self.screen

        # Cache interno de fontes para draw_text
        self._fontes_cache: dict[tuple[str, int], pygame.font.Font] = {}

        # Inicializa subsistemas
        from PPlay.keyboard import Keyboard
        from PPlay.mouse import Mouse
        self.keyboard = Keyboard()
        self.mouse = Mouse()

        self._already_init = True

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            Janela()
        return cls._instance

    @classmethod
    def get_screen(cls):
        return cls.get_instance().screen

    def set_background_color(self, cor):
        """Define a cor de limpeza de fundo do buffer virtual."""
        if isinstance(cor, str):
            try:
                self.cor_fundo = pygame.Color(cor)
            except Exception:
                self.cor_fundo = (18, 22, 30)
        else:
            self.cor_fundo = cor

    def definir_resolucao(self, opcao_res: str):
        """
        Ajusta a resolução real da janela para resoluções menores ou iguais a 1280x720.
        Opções suportadas: '100%' (1280x720), '75%' (960x540), '50%' (640x360), '25%' (320x180).
        """
        mapa = {
            "100%": (1280, 720),
            "75%": (960, 540),
            "50%": (640, 360),
            "25%": (320, 180),
            "1280x720": (1280, 720),
            "960x540": (960, 540),
            "640x360": (640, 360),
            "320x180": (320, 180),
        }
        res = mapa.get(str(opcao_res), (1280, 720))
        self.largura_janela_atual, self.altura_janela_atual = res

        if not self.is_fullscreen:
            try:
                self.real_screen = pygame.display.set_mode(
                    (self.largura_janela_atual, self.altura_janela_atual),
                    self._flags_janela
                )
            except Exception:
                pass

    def alternar_fullscreen(self):
        """Alterna de forma limpa entre modo Janela e Tela Cheia sem crash ou perda de Aspect Ratio."""
        self.is_fullscreen = not self.is_fullscreen
        try:
            pygame.display.toggle_fullscreen()
        except Exception:
            # Fallback seguro com re-set de modo
            if self.is_fullscreen:
                self.real_screen = pygame.display.set_mode(
                    (self.tela_nativa_largura, self.tela_nativa_altura),
                    self._flags_janela | FULLSCREEN
                )
            else:
                self.real_screen = pygame.display.set_mode(
                    (self.largura_janela_atual, self.altura_janela_atual),
                    self._flags_janela
                )

    def screen_to_virtual_coords(self, px: float, py: float) -> tuple[float, float]:
        """
        Converte as coordenadas de tela real do mouse para o espaço virtual (800x600).
        Aplica clamping automático para manter as coordenadas dentro do canvas do jogo.
        """
        lw, lh = self.real_screen.get_size()
        if lw < 1 or lh < 1:
            return px, py

        ratio = min(lw / float(self.largura), lh / float(self.altura))
        nova_w = self.largura * ratio
        nova_h = self.altura * ratio
        offset_x = (lw - nova_w) / 2.0
        offset_y = (lh - nova_h) / 2.0

        vx = (px - offset_x) / ratio
        vy = (py - offset_y) / ratio

        return clamp(vx, 0.0, float(self.largura)), clamp(vy, 0.0, float(self.altura))

    def update(self, fps_alvo: int | None = None):
        """
        Apresenta o buffer virtual na janela real com letterboxing e sincroniza o relógio de física.
        """
        largura_real, altura_real = self.real_screen.get_size()

        # Proteção contra janela minimizada
        if largura_real < 1 or altura_real < 1:
            pygame.display.flip()
            self._clock.tick(fps_alvo or self.fps_alvo)
            self.eventos = pygame.event.get()
            return

        # 1. Cálculo de Aspect Ratio e Dimensões de Letterboxing
        ratio = min(largura_real / float(self.largura), altura_real / float(self.altura))
        nova_w = max(1, int(round(self.largura * ratio)))
        nova_h = max(1, int(round(self.altura * ratio)))
        pos_x = (largura_real - nova_w) // 2
        pos_y = (altura_real - nova_h) // 2

        # 2. Preenchimento de barras pretas (Letterbox / Pillarbox)
        self.real_screen.fill((0, 0, 0))

        # 3. Escalonamento e Projeção na Tela Real
        try:
            if self.pixel_art:
                scaled = pygame.transform.scale(self.screen, (nova_w, nova_h))
            else:
                scaled = pygame.transform.smoothscale(self.screen, (nova_w, nova_h))
            self.real_screen.blit(scaled, (pos_x, pos_y))
        except Exception:
            self.real_screen.blit(self.screen, (0, 0))

        # 4. Apresentação de Vídeo
        pygame.display.flip()

        # 5. Limpeza do buffer virtual para o próximo frame
        self.screen.fill(self.cor_fundo)

        # 6. Processamento de Eventos de Janela e Atalhos Globais
        self.eventos = pygame.event.get()
        keys_pressed = pygame.key.get_pressed()
        alt_pressionado = keys_pressed[K_LALT] or keys_pressed[K_RALT]

        for ev in self.eventos:
            if ev.type == QUIT:
                self.close()
            elif ev.type == KEYDOWN:
                if ev.key == K_F11 or (alt_pressionado and ev.key == K_RETURN):
                    self.alternar_fullscreen()

        # 7. Sincronização do Relógio (FPS Cap e Delta Time)
        limite_fps = int(fps_alvo or self.fps_alvo)
        ms_passados = self._clock.tick(limite_fps)
        self._delta_time = ms_passados / 1000.0

    def delta_time(self) -> float:
        """Retorna o tempo decorrido no último frame em segundos."""
        return self._delta_time

    def get_fps(self) -> float:
        """Retorna a taxa atual de quadros por segundo."""
        return self._clock.get_fps()

    def draw_text(self, texto: str, x: int, y: int, tamanho: int = 20, cor=(255, 255, 255), fonte: str = "Arial"):
        """Renderiza texto com cache de fontes para evitar I/O desnecessário."""
        chave = (str(fonte), int(tamanho))
        if chave not in self._fontes_cache:
            try:
                self._fontes_cache[chave] = pygame.font.SysFont(fonte, tamanho)
            except Exception:
                self._fontes_cache[chave] = pygame.font.Font(None, tamanho)

        f = self._fontes_cache[chave]
        img = f.render(str(texto), True, cor)
        self.screen.blit(img, (x, y))

    def close(self):
        """Finaliza o Pygame e encerra a aplicação com segurança."""
        pygame.quit()
        sys.exit()


# Alias para compatibilidade total com PPlay.window.Window
Window = Janela

try:
    import PPlay.window
    PPlay.window.Window = Janela
except Exception:
    pass
