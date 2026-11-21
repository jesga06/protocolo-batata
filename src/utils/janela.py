"""
Módulo de Gerenciamento de Janela e Escalonamento Nativo — Protocolo: Batata
Implementa uma camada nativa em Pygame puro com suporte a:
- Resolução virtual fixa (800x600) com canvas virtual em alta definição.
- Escalonamento com Letterboxing preciso (manutenção rigorosa de Aspect Ratio).
- Conversão segura e clampada de coordenadas do mouse (Windowed e Fullscreen).
- Alternância robusta de tela cheia (F11 e Alt+Enter sem conflito de flags).
- Controle de taxa de quadros (FPS Cap) e delta_time calibrado (clamp <= 0.1s).
- Compatibilidade integral com a interface PPlay Window e Keyboard.
"""

import sys
import os
import ctypes
import pygame
from pygame.locals import (
    QUIT, KEYDOWN, K_F11, K_RETURN, K_LALT, K_RALT,
    KMOD_LALT, KMOD_RALT, KMOD_ALT,
    DOUBLEBUF, RESIZABLE, FULLSCREEN,
    VIDEORESIZE
)
from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, FPS_PADRAO
from src.utils.math_utils import clamp


class TecladoNativo:
    """
    Controlador Nativo de Teclado com suporte estendido a teclas Pygame.
    Resolve teclas especiais (TAB, F1..F12, KP1..KP9, BACKQUOTE) mantendo
    compatibilidade total com as interfaces key_pressed e key_down.
    """
    def __init__(self, janela=None):
        self._janela = janela
        self.mapa: dict[str, int] = {
            "LEFT": pygame.K_LEFT,
            "RIGHT": pygame.K_RIGHT,
            "UP": pygame.K_UP,
            "DOWN": pygame.K_DOWN,
            "SPACE": pygame.K_SPACE,
            "ESC": pygame.K_ESCAPE,
            "ESCAPE": pygame.K_ESCAPE,
            "ENTER": pygame.K_RETURN,
            "RETURN": pygame.K_RETURN,
            "TAB": pygame.K_TAB,
            "BACKQUOTE": pygame.K_BACKQUOTE,
            "`": pygame.K_BACKQUOTE,
            "~": pygame.K_BACKQUOTE,
            "TILDE": pygame.K_BACKQUOTE,
            "LSHIFT": pygame.K_LSHIFT,
            "RSHIFT": pygame.K_RSHIFT,
            "LCTRL": pygame.K_LCTRL,
            "RCTRL": pygame.K_RCTRL,
            "LALT": pygame.K_LALT,
            "RALT": pygame.K_RALT,
            "BACKSPACE": pygame.K_BACKSPACE,
            "DELETE": pygame.K_DELETE,
            "INSERT": pygame.K_INSERT,
            "HOME": pygame.K_HOME,
            "END": pygame.K_END,
            "PAGEUP": pygame.K_PAGEUP,
            "PAGEDOWN": pygame.K_PAGEDOWN,
        }
        # Mapeamento dinâmico de teclas de função F1 a F12
        for i in range(1, 13):
            k_f = getattr(pygame, f"K_F{i}", None)
            if k_f is not None:
                self.mapa[f"F{i}"] = k_f
        # Mapeamento de teclado numérico KP0..KP9 e números normais
        for i in range(10):
            k_kp = getattr(pygame, f"K_KP{i}", getattr(pygame, f"K_KP_{i}", None))
            if k_kp is not None:
                self.mapa[f"KP{i}"] = k_kp
                self.mapa[f"KP_{i}"] = k_kp
                self.mapa[f"[{i}]"] = k_kp
            k_num = getattr(pygame, f"K_{i}", None)
            if k_num is not None:
                self.mapa[str(i)] = k_num

    def _get_janela(self):
        if self._janela is not None:
            return self._janela
        return Janela.get_instance()

    def _get_code(self, key):
        if isinstance(key, int):
            return key
        if isinstance(key, str):
            k = key.strip()
            ku = k.upper()
            if ku in self.mapa:
                return self.mapa[ku]
            if k in self.mapa:
                return self.mapa[k]
            code = getattr(pygame, f"K_{k.lower()}", None)
            if code is not None:
                return code
            code = getattr(pygame, f"K_{ku}", None)
            if code is not None:
                return code
        return None

    def key_pressed(self, key) -> bool:
        """Verifica se a tecla está sendo segurada (Input contínuo)."""
        codigo = self._get_code(key)
        if codigo is None:
            return False
        try:
            pressionadas = pygame.key.get_pressed()
            if codigo < 0 or codigo >= len(pressionadas):
                return False
            return bool(pressionadas[codigo])
        except (IndexError, TypeError):
            return False

    def key_down(self, key) -> bool:
        """Verifica se a tecla foi apertada NESTE frame (Único)."""
        codigo = self._get_code(key)
        if codigo is None:
            return False
        janela = self._get_janela()
        eventos = getattr(janela, "eventos", []) or []
        for evento in eventos:
            if evento.type == KEYDOWN and evento.key == codigo:
                return True
        return False

    def show_key_pressed(self):
        """Debug legada: imprime tecla pressionada no frame."""
        janela = self._get_janela()
        for evento in getattr(janela, "eventos", []) or []:
            if evento.type == KEYDOWN:
                print(evento.key)

    def draw_debug(self, x: int = 10, y: int = 10):
        """Debug: Renderiza na janela as teclas detectadas no frame."""
        janela = self._get_janela()
        for evento in getattr(janela, "eventos", []) or []:
            if evento.type == KEYDOWN:
                nome_tecla = pygame.key.name(evento.key)
                janela.draw_text(f"Tecla: {nome_tecla}", x, y, cor="red")


class JanelaMeta(type):
    """
    Metaclasse para impedir que bibliotecas externas (como PPlay.retro_bridge)
    sobrescrevam Janela.draw_text com implementações incompatíveis.
    """
    def __setattr__(cls, name, value):
        if name == "draw_text":
            return
        super().__setattr__(name, value)


class Janela(metaclass=JanelaMeta):
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
        pixel_art: bool = True
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
        self.pixel_art = bool(pixel_art)
        self.is_fullscreen = False

        self._clock = pygame.time.Clock()
        self._delta_time = 0.0
        self.fps_alvo = FPS_PADRAO
        self.eventos = []
        self.cor_fundo = (18, 22, 30)

        # Flag indicando se processar_eventos() foi invocado no frame atual
        self._eventos_processados_frame = False

        # Resolução padrão da Janela (1280x720 HD) e detecção de display
        desktop_info = pygame.display.Info()
        self.tela_nativa_largura = max(1280, getattr(desktop_info, "current_w", 1280))
        self.tela_nativa_altura = max(720, getattr(desktop_info, "current_h", 720))

        self.largura_janela_atual = 1280
        self.altura_janela_atual = 720

        # Configura flags de vídeo sem HWSURFACE legado
        self._flags_janela = DOUBLEBUF
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
        self._fontes_cache: dict[tuple[str, int, bool, bool], pygame.font.Font] = {}

        # Inicializa subsistemas
        self.keyboard = TecladoNativo(self)
        from PPlay.mouse import Mouse
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

    @classmethod
    def get_keyboard(cls):
        return cls.get_instance().keyboard

    @classmethod
    def get_mouse(cls):
        return cls.get_instance().mouse

    @property
    def width(self) -> int:
        """Largura do canvas virtual para compatibilidade com PPlay Window."""
        return self.largura

    @property
    def height(self) -> int:
        """Altura do canvas virtual para compatibilidade com PPlay Window."""
        return self.altura

    def set_title(self, titulo: str):
        """Define o título da janela."""
        self.titulo = str(titulo)
        pygame.display.set_caption(self.titulo)

    def delay(self, ms: int):
        """Pausa a execução pelo tempo especificado em milissegundos."""
        pygame.time.delay(int(ms))

    def time_elapsed(self) -> int:
        """Retorna o tempo decorrido desde o início do Pygame em milissegundos."""
        return pygame.time.get_ticks()

    def clear(self):
        """Limpa o buffer virtual com fundo branco e atualiza a tela."""
        self.set_background_color((255, 255, 255))
        self.update()

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
                flags = self._flags_janela & ~FULLSCREEN
                self.real_screen = pygame.display.set_mode(
                    (self.largura_janela_atual, self.altura_janela_atual),
                    flags
                )
            except Exception:
                pass

    def alternar_fullscreen(self):
        """Alterna de forma limpa entre modo Janela e Tela Cheia sem crash ou perda de Aspect Ratio."""
        self.is_fullscreen = not self.is_fullscreen
        sucesso = False
        try:
            sucesso = bool(pygame.display.toggle_fullscreen())
        except Exception:
            sucesso = False

        if not sucesso:
            # Fallback seguro com re-set de modo
            if self.is_fullscreen:
                # Remove RESIZABLE para evitar conflito com FULLSCREEN e descarta HWSURFACE
                flags = (self._flags_janela & ~RESIZABLE) | FULLSCREEN
                desktop_info = pygame.display.Info()
                w = getattr(desktop_info, "current_w", self.tela_nativa_largura) or self.tela_nativa_largura
                h = getattr(desktop_info, "current_h", self.tela_nativa_altura) or self.tela_nativa_altura
                try:
                    self.real_screen = pygame.display.set_mode((w, h), flags)
                except Exception:
                    pass
            else:
                flags = self._flags_janela & ~FULLSCREEN
                try:
                    self.real_screen = pygame.display.set_mode(
                        (self.largura_janela_atual, self.altura_janela_atual),
                        flags
                    )
                except Exception:
                    pass

    def _calcular_viewport(self, lw: int, lh: int) -> tuple[int, int, int, int, float]:
        """
        Calcula as dimensões e offset do canvas virtual com letterboxing/pillarboxing.
        Retorna (pos_x, pos_y, nova_w, nova_h, ratio).
        """
        if lw < 1 or lh < 1:
            return 0, 0, self.largura, self.altura, 1.0

        ratio = min(lw / float(self.largura), lh / float(self.altura))
        nova_w = max(1, int(round(self.largura * ratio)))
        nova_h = max(1, int(round(self.altura * ratio)))
        pos_x = (lw - nova_w) // 2
        pos_y = (lh - nova_h) // 2
        return pos_x, pos_y, nova_w, nova_h, ratio

    def screen_to_virtual_coords(self, px: float, py: float) -> tuple[float, float]:
        """
        Converte as coordenadas de tela real do mouse para o espaço virtual (800x600).
        Aplica clamping automático para manter as coordenadas dentro do canvas do jogo.
        """
        lw, lh = self.real_screen.get_size()
        if lw < 1 or lh < 1:
            return px, py

        pos_x, pos_y, nova_w, nova_h, ratio = self._calcular_viewport(lw, lh)
        if ratio <= 0.0:
            return px, py

        vx = (px - pos_x) / ratio
        vy = (py - pos_y) / ratio

        return clamp(vx, 0.0, float(self.largura)), clamp(vy, 0.0, float(self.altura))

    def processar_eventos(self) -> list[pygame.event.Event]:
        """
        Coleta e processa os eventos do Pygame para o frame atual.
        Trata atalhos globais (F11, Alt+Enter), redimensionamento de janela e QUIT.
        Consome F11 e Alt+Enter sem vazar o evento ENTER para as cenas.
        """
        self.eventos = list(pygame.event.get())
        self._eventos_processados_frame = True

        eventos_filtrados = []
        keys_pressed = pygame.key.get_pressed()
        alt_pressionado = bool(keys_pressed[K_LALT] or keys_pressed[K_RALT])

        WINDOWRESIZED = getattr(pygame, "WINDOWRESIZED", None)
        WINDOWSIZECHANGED = getattr(pygame, "WINDOWSIZECHANGED", None)

        for ev in self.eventos:
            if ev.type == QUIT:
                self.close()
                continue

            if ev.type in (pygame.VIDEORESIZE, WINDOWRESIZED, WINDOWSIZECHANGED):
                nw = getattr(ev, "w", getattr(ev, "x", None))
                nh = getattr(ev, "h", getattr(ev, "y", None))
                if hasattr(ev, "size"):
                    try:
                        nw, nh = ev.size
                    except Exception:
                        pass
                if nw is not None and nh is not None and nw > 0 and nh > 0:
                    self.largura_janela_atual = int(nw)
                    self.altura_janela_atual = int(nh)
                    if not self.is_fullscreen:
                        try:
                            flags = self._flags_janela & ~FULLSCREEN
                            self.real_screen = pygame.display.set_mode(
                                (self.largura_janela_atual, self.altura_janela_atual),
                                flags
                            )
                        except Exception:
                            pass
                eventos_filtrados.append(ev)
                continue

            if ev.type == KEYDOWN:
                if ev.key == K_F11:
                    self.alternar_fullscreen()
                    # Consumido: NÃO vaza F11 para as cenas
                    continue

                mod = getattr(ev, "mod", 0)
                alt_mod = bool(mod & (KMOD_LALT | KMOD_RALT | KMOD_ALT))
                if (alt_pressionado or alt_mod) and ev.key in (K_RETURN, getattr(pygame, "K_KP_ENTER", K_RETURN)):
                    self.alternar_fullscreen()
                    # Consumido: NÃO vaza ENTER para as cenas!
                    continue

            eventos_filtrados.append(ev)

        self.eventos = eventos_filtrados
        return self.eventos

    def update(self, fps_alvo: int | None = None):
        """
        Apresenta o buffer virtual na janela real com letterboxing e sincroniza o relógio de física.
        """
        # Se os eventos ainda não foram processados neste frame (chamada direta de update()),
        # processa-os agora para manter compatibilidade total.
        if not self._eventos_processados_frame:
            self.processar_eventos()

        largura_real, altura_real = self.real_screen.get_size()

        # Proteção contra janela minimizada (processa QUIT e eventos mesmo minimizado)
        if largura_real < 1 or altura_real < 1:
            pygame.display.flip()
            limite_fps = int(fps_alvo or self.fps_alvo)
            ms_passados = self._clock.tick(limite_fps)
            self._delta_time = min(0.1, max(0.0, ms_passados / 1000.0))
            self._eventos_processados_frame = False
            return

        # 1. Cálculo de Aspect Ratio e Dimensões de Letterboxing
        pos_x, pos_y, nova_w, nova_h, ratio = self._calcular_viewport(largura_real, altura_real)

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

        # 6. Sincronização do Relógio (FPS Cap e Delta Time clampado <= 0.1)
        limite_fps = int(fps_alvo or self.fps_alvo)
        ms_passados = self._clock.tick(limite_fps)
        self._delta_time = min(0.1, max(0.0, ms_passados / 1000.0))

        # Reseta flag de eventos para o próximo frame
        self._eventos_processados_frame = False

    def delta_time(self) -> float:
        """Retorna o tempo decorrido no último frame em segundos."""
        return self._delta_time

    def get_fps(self) -> float:
        """Retorna a taxa atual de quadros por segundo."""
        return self._clock.get_fps()

    def draw_text(
        self,
        texto: str = "",
        x: int = 0,
        y: int = 0,
        tamanho: int | None = None,
        cor: tuple | str | None = None,
        fonte: str | None = None,
        *args,
        **kwargs
    ):
        """
        Renderiza texto com cache de fontes para evitar I/O desnecessário.
        Aceita argumentos posicionais e nomeados (tamanho/size, cor/color, fonte/font_name).
        """
        if not texto and "text" in kwargs:
            texto = kwargs.pop("text")
        if "x" in kwargs:
            x = kwargs.pop("x")
        if "y" in kwargs:
            y = kwargs.pop("y")

        extra_pos = list(args)
        if tamanho is None and extra_pos:
            tamanho = extra_pos.pop(0)
        if cor is None and extra_pos:
            cor = extra_pos.pop(0)
        if fonte is None and extra_pos:
            fonte = extra_pos.pop(0)
        bold = extra_pos.pop(0) if extra_pos else kwargs.pop("bold", False)
        italic = extra_pos.pop(0) if extra_pos else kwargs.pop("italic", False)

        if tamanho is None:
            tamanho = kwargs.pop("size", kwargs.pop("tamanho", 20))
        if cor is None:
            cor = kwargs.pop("color", kwargs.pop("cor", (255, 255, 255)))
        if fonte is None:
            fonte = kwargs.pop("font_name", kwargs.pop("fonte", "Arial"))

        if isinstance(cor, str):
            try:
                cor = pygame.Color(cor)
            except Exception:
                cor = (255, 255, 255)

        chave = (str(fonte), int(tamanho), bool(bold), bool(italic))
        if chave not in self._fontes_cache:
            try:
                self._fontes_cache[chave] = pygame.font.SysFont(str(fonte), int(tamanho), bool(bold), bool(italic))
            except Exception:
                self._fontes_cache[chave] = pygame.font.Font(None, int(tamanho))

        f = self._fontes_cache[chave]
        try:
            img = f.render(str(texto), True, cor)
            self.screen.blit(img, (x, y))
        except Exception:
            pass

    def close(self):
        """Finaliza o Pygame e encerra a aplicação com segurança."""
        pygame.quit()
        sys.exit()


# Aliases para compatibilidade total com PPlay
Window = Janela
Keyboard = TecladoNativo
