"""
Módulo de Gerenciamento de Janela e Escalonamento Nativo — Protocolo: Batata
Implementa uma camada nativa em Pygame puro com suporte a:
- Resolução virtual fixa (1280x720) com canvas virtual em alta definição.
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
from collections import OrderedDict
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, FPS_PADRAO, DT_CLAMP_MAX
)
from src.utils.math_utils import clamp


class SpriteScaleCache:
    """
    Cache LRU de escalonamento nearest-neighbor para sprites em renderização nativa.
    Evita re-escalonamento de software por frame quando render_scale != 1.0.
    """

    def __init__(self, max_entries: int = 512):
        self.max_entries = max(16, int(max_entries))
        self._cache: OrderedDict[tuple, pygame.Surface] = OrderedDict()

    def obter(
        self,
        surface: pygame.Surface,
        largura: int,
        altura: int,
        chave_extra=None
    ) -> pygame.Surface:
        w = max(1, int(largura))
        h = max(1, int(altura))
        if surface.get_width() == w and surface.get_height() == h:
            return surface

        chave = (id(surface), surface.get_size(), w, h, chave_extra)
        if chave in self._cache:
            self._cache.move_to_end(chave)
            return self._cache[chave]

        scaled = pygame.transform.scale(surface, (w, h))
        self._cache[chave] = scaled
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)
        return scaled

    def obter_escala(
        self,
        surface: pygame.Surface,
        escala: float,
        chave_extra=None
    ) -> pygame.Surface:
        if abs(float(escala) - 1.0) < 1e-4:
            return surface
        w = max(1, int(round(surface.get_width() * float(escala))))
        h = max(1, int(round(surface.get_height() * float(escala))))
        return self.obter(surface, w, h, chave_extra=chave_extra)

    def limpar(self):
        self._cache.clear()


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
        pixel_art: bool = True,
        vsync: bool = True
    ):
        if hasattr(self, "_already_init") and self._already_init:
            return

        # Garante filtragem nearest-neighbor no backend SDL antes de inicializar o vídeo
        os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")

        # Configura High-DPI no Windows antes de criar a janela
        try:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        if not pygame.get_init():
            pygame.init()

        self.largura = int(largura_virtual)
        self.altura = int(altura_virtual)
        self.titulo = str(titulo)
        self.resizavel = bool(resizavel)
        self.pixel_art = bool(pixel_art)
        self.is_fullscreen = False
        self.vsync_ativo = bool(vsync)
        self._vsync_efetivo = False
        self.escala_resolucao_mundo = 1.0

        self._clock = pygame.time.Clock()
        self._delta_time = 0.0
        self._delta_time_real = 0.0
        self.fps_alvo = FPS_PADRAO
        self.eventos = []
        self.cor_fundo = (18, 22, 30)

        # Flag indicando se processar_eventos() foi invocado no frame atual
        self._eventos_processados_frame = False

        # Detecção real do display
        desktop_info = pygame.display.Info()
        raw_w = getattr(desktop_info, "current_w", 0) or 0
        raw_h = getattr(desktop_info, "current_h", 0) or 0
        self.tela_nativa_largura = raw_w if raw_w > 0 else self.largura
        self.tela_nativa_altura = raw_h if raw_h > 0 else self.altura

        if self._is_dummy_driver():
            # Em driver headless dummy, mantém 1280x720 determinístico para a suíte de testes
            self.largura_janela_atual = self.largura
            self.altura_janela_atual = self.altura
        elif raw_w > 0 and raw_h > 0:
            # Em displays reais, abre diretamente na resolução nativa da tela/janela
            self.largura_janela_atual = int(raw_w)
            self.altura_janela_atual = int(raw_h)
        else:
            self.largura_janela_atual = self.largura
            self.altura_janela_atual = self.altura

        # Configura flags de vídeo sem HWSURFACE legado
        self._flags_janela = DOUBLEBUF
        if self.resizavel:
            self._flags_janela |= RESIZABLE

        os.environ["SDL_VIDEO_CENTERED"] = "1"
        self.real_screen = self._set_mode_seguro(
            (self.largura_janela_atual, self.altura_janela_atual),
            self._flags_janela,
            vsync=self.vsync_ativo
        )
        pygame.display.set_caption(self.titulo)

        # Renderização nativa direta (elimina upscaling prematuro em 720p)
        self.screen = self.real_screen
        Janela.screen = self.screen
        self.sprite_scale_cache = SpriteScaleCache()
        self.render_scale = 1.0
        self.viewport_offset = (0, 0)
        self.viewport_rect = (0, 0, self.largura, self.altura)
        self._atualizar_metricas_viewport()

        # Cache interno de fontes para draw_text
        self._fontes_cache: dict[tuple[str, int, bool, bool], pygame.font.Font] = {}

        # Inicializa subsistemas
        self.keyboard = TecladoNativo(self)
        from PPlay.mouse import Mouse
        self.mouse = Mouse()

        self._already_init = True

    @staticmethod
    def _is_dummy_driver() -> bool:
        return os.environ.get("SDL_VIDEODRIVER", "").strip().lower() == "dummy"

    def _set_mode_seguro(
        self,
        tamanho: tuple[int, int],
        flags: int,
        vsync: bool | None = None
    ) -> pygame.Surface:
        """Cria/reconfigura a superfície de display com suporte seguro a vsync=1 e fallback para vsync=0."""
        usar_vsync = self.vsync_ativo if vsync is None else bool(vsync)
        if usar_vsync and not self._is_dummy_driver():
            try:
                surf = pygame.display.set_mode(tamanho, flags, vsync=1)
                self._vsync_efetivo = True
                return surf
            except (pygame.error, TypeError):
                pass
        self._vsync_efetivo = False
        try:
            return pygame.display.set_mode(tamanho, flags, vsync=0)
        except TypeError:
            return pygame.display.set_mode(tamanho, flags)

    def _atualizar_metricas_viewport(self):
        """Atualiza render_scale, viewport_offset e viewport_rect a partir do tamanho real da tela."""
        if self.real_screen is None:
            self.render_scale = 1.0
            self.viewport_offset = (0, 0)
            self.viewport_rect = (0, 0, self.largura, self.altura)
            return
        rw, rh = self.real_screen.get_size()
        pos_x, pos_y, nova_w, nova_h, ratio = self._calcular_viewport(rw, rh)
        self.render_scale = float(ratio)
        self.viewport_offset = (int(pos_x), int(pos_y))
        self.viewport_rect = (int(pos_x), int(pos_y), int(nova_w), int(nova_h))

    def _aplicar_novo_real_screen(self, nova_superficie: pygame.Surface):
        """Atualiza self.real_screen preservando binding nativo de self.screen e métricas de viewport."""
        estava_nativo = (self.screen is self.real_screen)
        self.real_screen = nova_superficie
        if estava_nativo:
            self.screen = self.real_screen
            Janela.screen = self.screen
        self._atualizar_metricas_viewport()

    def logical_to_screen(self, lx: float, ly: float) -> tuple[float, float]:
        """Converte coordenadas lógicas (1280x720) para coordenadas da superfície nativa."""
        ox, oy = self.viewport_offset
        escala = self.render_scale
        return (ox + float(lx) * escala, oy + float(ly) * escala)

    def sx(self, lx: float) -> int:
        """Projeta coordenada X lógica (0..1280) para pixel nativo da viewport."""
        return int(round(self.viewport_offset[0] + float(lx) * self.render_scale))

    def sy(self, ly: float) -> int:
        """Projeta coordenada Y lógica (0..720) para pixel nativo da viewport."""
        return int(round(self.viewport_offset[1] + float(ly) * self.render_scale))

    def sw(self, lw: float) -> int:
        """Escala largura lógica para pixels nativos."""
        if lw <= 0:
            return 0
        return max(1, int(round(float(lw) * self.render_scale)))

    def sh(self, lh: float) -> int:
        """Escala altura lógica para pixels nativos."""
        if lh <= 0:
            return 0
        return max(1, int(round(float(lh) * self.render_scale)))

    def srect(self, x: float, y: float, w: float, h: float) -> pygame.Rect:
        """Projeta um retângulo lógico (1280x720) para pygame.Rect nativo."""
        return pygame.Rect(self.sx(x), self.sy(y), self.sw(w), self.sh(h))

    def obter_fonte_nativa(
        self,
        nome: str,
        tamanho_logico: float,
        bold: bool = False,
        italic: bool = False
    ) -> pygame.font.Font:
        """Retorna fonte Pygame em DPI nativo escalada por render_scale, cacheada por (nome, px_size, bold, italic)."""
        px_size = max(8, int(round(float(tamanho_logico) * self.render_scale)))
        chave = (str(nome), px_size, bool(bold), bool(italic))
        if chave not in self._fontes_cache:
            try:
                self._fontes_cache[chave] = pygame.font.SysFont(str(nome), px_size, bool(bold), bool(italic))
            except Exception:
                self._fontes_cache[chave] = pygame.font.Font(None, px_size)
        return self._fontes_cache[chave]

    def definir_vsync(self, ativo: bool):
        """Alterna vsync em tempo de execução recriando o modo de vídeo com fallback seguro."""
        novo_estado = bool(ativo)
        if novo_estado == self.vsync_ativo:
            return
        self.vsync_ativo = novo_estado
        if self.real_screen is None:
            return
        if self.is_fullscreen:
            flags = (self._flags_janela & ~RESIZABLE) | FULLSCREEN
            tamanho = self.real_screen.get_size()
        else:
            flags = self._flags_janela & ~FULLSCREEN
            tamanho = (self.largura_janela_atual, self.altura_janela_atual)
        try:
            nova = self._set_mode_seguro(tamanho, flags, vsync=self.vsync_ativo)
            self._aplicar_novo_real_screen(nova)
        except Exception:
            pass

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
        Ajusta a escala de resolução do mundo (world pixelation pass) sem encolher a janela do SO.
        Opções suportadas: '100%' (1.0), '75%' (0.75), '50%' (0.50), '25%' (0.25).
        """
        mapa_escala = {
            "100%": 1.0,
            "75%": 0.75,
            "50%": 0.50,
            "25%": 0.25,
            "1280x720": 1.0,
            "960x540": 0.75,
            "640x360": 0.50,
            "320x180": 0.25,
        }
        self.escala_resolucao_mundo = float(mapa_escala.get(str(opcao_res), 1.0))

    def _obter_tamanho_fullscreen(self) -> tuple[int, int]:
        """Retorna a dimensão alvo para fullscreen ((0, 0) = desktop nativo em displays reais)."""
        if self._is_dummy_driver():
            return self.largura, self.altura
        try:
            desktop_sizes = pygame.display.get_desktop_sizes()
            if desktop_sizes and desktop_sizes[0][0] > 0 and desktop_sizes[0][1] > 0:
                self.tela_nativa_largura, self.tela_nativa_altura = int(desktop_sizes[0][0]), int(desktop_sizes[0][1])
        except Exception:
            pass
        # Em SDL2/Pygame-CE, (0, 0) + FULLSCREEN ativa FULLSCREEN_DESKTOP na resolução exata do compositor,
        # evitando dessincronização de escala/viewport entre pygame.mouse.get_pos() e real_screen.
        return (0, 0)

    def entrar_fullscreen(self):
        """Entra em tela cheia usando a resolução nativa real do monitor."""
        if self.is_fullscreen:
            return
        self.is_fullscreen = True
        flags = (self._flags_janela & ~RESIZABLE) | FULLSCREEN
        w, h = self._obter_tamanho_fullscreen()
        try:
            nova = self._set_mode_seguro((w, h), flags, vsync=self.vsync_ativo)
            self._aplicar_novo_real_screen(nova)
        except Exception:
            pass

    def alternar_fullscreen(self):
        """Alterna de forma limpa entre modo Janela e Tela Cheia mantendo real_screen sincronizado."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            flags = (self._flags_janela & ~RESIZABLE) | FULLSCREEN
            w, h = self._obter_tamanho_fullscreen()
            try:
                nova = self._set_mode_seguro((w, h), flags, vsync=self.vsync_ativo)
                self._aplicar_novo_real_screen(nova)
            except Exception:
                pass
        else:
            flags = self._flags_janela & ~FULLSCREEN
            try:
                nova = self._set_mode_seguro(
                    (self.largura_janela_atual, self.altura_janela_atual),
                    flags,
                    vsync=self.vsync_ativo
                )
                self._aplicar_novo_real_screen(nova)
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
        Converte as coordenadas de tela real do mouse para o espaço virtual (1280x720).
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
                    nw_int, nh_int = int(nw), int(nh)
                    if not self.is_fullscreen:
                        self.largura_janela_atual = nw_int
                        self.altura_janela_atual = nh_int
                    # Em SDL2/Pygame-CE, a superfície do display já é atualizada pelo backend;
                    # chamar set_mode() dentro do evento de resize cria loop infinito de janelas no Wayland/X11.
                    nova = pygame.display.get_surface()
                    if nova is not None and nova is not self.real_screen:
                        self._aplicar_novo_real_screen(nova)
                    else:
                        self._atualizar_metricas_viewport()
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
            limite_fps = int(self.fps_alvo if fps_alvo is None else fps_alvo)
            ms_passados = self._clock.tick(limite_fps)
            dt_real = min(0.25, max(0.0, ms_passados / 1000.0))
            self._delta_time_real = dt_real
            self._delta_time = min(DT_CLAMP_MAX, dt_real)
            self._eventos_processados_frame = False
            return

        self._atualizar_metricas_viewport()

        # Quando self.screen é a própria real_screen (renderização nativa direta),
        # preenche apenas barras de letterbox/pillarbox (se houver) e apresenta diretamente.
        if self.screen is self.real_screen:
            ox, oy, vw, vh = self.viewport_rect
            if ox > 0:
                self.real_screen.fill((0, 0, 0), rect=(0, 0, ox, altura_real))
                dir_x = ox + vw
                if dir_x < largura_real:
                    self.real_screen.fill((0, 0, 0), rect=(dir_x, 0, largura_real - dir_x, altura_real))
            if oy > 0:
                self.real_screen.fill((0, 0, 0), rect=(0, 0, largura_real, oy))
                inf_y = oy + vh
                if inf_y < altura_real:
                    self.real_screen.fill((0, 0, 0), rect=(0, inf_y, largura_real, altura_real - inf_y))
        else:
            # 1. Cálculo de Aspect Ratio e Dimensões de Letterboxing
            pos_x, pos_y, nova_w, nova_h, ratio = self._calcular_viewport(largura_real, altura_real)

            # 2. Preenchimento de barras pretas (Letterbox / Pillarbox)
            self.real_screen.fill((0, 0, 0))

            # 3. Escalonamento e Projeção na Tela Real
            try:
                if nova_w == self.largura and nova_h == self.altura:
                    self.real_screen.blit(self.screen, (pos_x, pos_y))
                elif self.pixel_art:
                    scaled = pygame.transform.scale(self.screen, (nova_w, nova_h))
                    self.real_screen.blit(scaled, (pos_x, pos_y))
                else:
                    scaled = pygame.transform.smoothscale(self.screen, (nova_w, nova_h))
                    self.real_screen.blit(scaled, (pos_x, pos_y))
            except Exception:
                self.real_screen.blit(self.screen, (0, 0))

        # 4. Apresentação de Vídeo
        # Alguns drivers SDL/Windows podem falhar em flip() mesmo mantendo o loop ativo.
        # update() é uma apresentação compatível para este caso.
        try:
            pygame.display.flip()
        except pygame.error as exc:
            if not getattr(self, "_aviso_apresentacao", False):
                print(f"[Protocolo Batata] pygame.display.flip falhou: {exc}. Usando pygame.display.update().", file=sys.stderr)
                self._aviso_apresentacao = True
            try:
                pygame.display.update()
            except pygame.error as fallback_exc:
                if not getattr(self, "_aviso_fallback_apresentacao", False):
                    print(f"[Protocolo Batata] pygame.display.update também falhou: {fallback_exc}", file=sys.stderr)
                    self._aviso_fallback_apresentacao = True

        # 5. Limpeza do buffer para o próximo frame
        self.screen.fill(self.cor_fundo)

        # 6. Sincronização do Relógio (FPS Cap e Delta Time clampado <= DT_CLAMP_MAX)
        limite_fps = int(self.fps_alvo if fps_alvo is None else fps_alvo)
        ms_passados = self._clock.tick(limite_fps)
        dt_real = min(0.25, max(0.0, ms_passados / 1000.0))
        self._delta_time_real = dt_real
        self._delta_time = min(DT_CLAMP_MAX, dt_real)

        # Reseta flag de eventos para o próximo frame
        self._eventos_processados_frame = False

    def delta_time(self) -> float:
        """Retorna o tempo decorrido no último frame em segundos (clampado por DT_CLAMP_MAX)."""
        return self._delta_time

    def delta_time_real(self) -> float:
        """Retorna o tempo decorrido real no último frame em segundos (clamp de segurança 0.25s)."""
        return self._delta_time_real if getattr(self, "_delta_time_real", 0.0) > 0.0 else self._delta_time

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
