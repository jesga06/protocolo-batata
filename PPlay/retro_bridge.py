"""
===============================================================================
POWER PPLAY 2.0 - RETRO-COMPATIBILITY BRIDGE v2.2
===============================================================================
Correção de Métodos de Classe e Atributos Estáticos.
Mapeia o comportamento da 1.0 injetando lógica na 2.0.
===============================================================================
"""
import pygame

def aplicar_retrocompatibilidade():
    try:
        from .window import Window
        from .mouse import Mouse
        from .keyboard import Keyboard
        from .animation import Animation
        from .sound import Sound
        from .sprite import Sprite
        from .gameimage import GameImage
        from .collision import Collision
    except ImportError:
        return

    # --- 1. WINDOW: TRADUÇÃO DE ATRIBUTOS E CLASSMETHODS ---
    
    # Redireciona Window.width -> Window.largura (Instância)
    Window.width = property(lambda self: self.largura)
    Window.height = property(lambda self: self.altura)

    # Injeção de Métodos de Classe (Corrigindo o erro de missing 'cls')
    Window.get_keyboard = classmethod(lambda cls: cls.get_instance().keyboard)
    Window.get_mouse = classmethod(lambda cls: cls.get_instance().mouse)
    
    # Métodos de Instância Legados
    Window.set_title = lambda self, t: pygame.display.set_caption(t)
    Window.delay = lambda self, ms: pygame.time.delay(ms)
    Window.time_elapsed = lambda self: pygame.time.get_ticks()
    Window.clear = lambda self: [self.set_background_color((255,255,255)), self.update()]

    # Draw Text Híbrido com Cache de Fontes para Alto Desempenho
    def draw_text_compat(self, text, x, y, **kwargs):
        size = kwargs.get('size', kwargs.get('tamanho', 12))
        color = kwargs.get('color', kwargs.get('cor', (0,0,0)))
        font_name = kwargs.get('font_name', kwargs.get('fonte', "Arial"))
        bold = kwargs.get('bold', False)
        italic = kwargs.get('italic', False)
        
        chave = (str(font_name), int(size), bool(bold), bool(italic))
        if not hasattr(self, '_fontes_cache') or self._fontes_cache is None:
            self._fontes_cache = {}
        if chave not in self._fontes_cache:
            try:
                self._fontes_cache[chave] = pygame.font.SysFont(font_name, size, bold, italic)
            except Exception:
                self._fontes_cache[chave] = pygame.font.Font(None, size)
                
        f = self._fontes_cache[chave]
        self.screen.blit(f.render(str(text), True, color), [x, y])
    Window.draw_text = draw_text_compat

    # --- 2. INPUTS: TRADUÇÃO DE TECLAS E BOTÕES ---
    Keyboard.key_pressed_legacy = lambda self, k: self.key_pressed(k)
    def show_key_legacy(self):
        for e in Window.get_instance().eventos:
            if e.type == pygame.KEYDOWN: print(e.key)
    Keyboard.show_key_pressed = show_key_legacy

    # Constantes do Mouse
    Mouse.BUTTON_LEFT = 1; Mouse.BUTTON_MIDDLE = 2; Mouse.BUTTON_RIGHT = 3
    Mouse.WHEEL_UP = 4; Mouse.WHEEL_DOWN = 5
    Mouse.is_button_pressed = lambda self, b: self.button_pressed(1 if b is True else b)
    Mouse.set_position = lambda self, x, y: pygame.mouse.set_pos([x, y])
    Mouse.hide = lambda self: pygame.mouse.set_visible(False)
    Mouse.unhide = lambda self: pygame.mouse.set_visible(True)
    Mouse.is_over_area = lambda self, sp, ep: (sp[0] <= self.get_position()[0] <= ep[0]) and (sp[1] <= self.get_position()[1] <= ep[1])

    # --- 3. ANIMAÇÃO E SPRITE ---
    def set_sequence_time_legacy(self, start, end, duration, loop=True):
        self.set_total_duration(duration)
        self.set_loop(loop)
        self.frame_atual = start

    Animation.set_sequence_time = set_sequence_time_legacy
    Animation.set_sequence = lambda self, s, e, l=True: self.set_loop(l)
    Animation.set_curr_frame = lambda self, f: setattr(self, 'frame_atual', f)
    Animation.hide = lambda self: setattr(self, 'drawable', False)
    Animation.unhide = lambda self: setattr(self, 'drawable', True)

    def draw_compat(self, *args, **kwargs):
        if not hasattr(self, 'drawable') or self.drawable:
            self.draw_old(*args, **kwargs)

    Sprite.draw_old = Sprite.draw
    Sprite.draw = draw_compat
    GameImage.draw_old = GameImage.draw
    GameImage.draw = draw_compat

    if hasattr(Collision, "perfect_collision"):
        Collision.collided_perfect = Collision.perfect_collision
