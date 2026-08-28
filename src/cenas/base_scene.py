"""
Cena Base — Protocolo: Batata
Classe base para todas as cenas do jogo, estendendo PPlay.scenemanager.Scene.
"""

from PPlay.scenemanager import Scene
from PPlay.window import Window


class BaseScene(Scene):
    """
    Cena base que provê acesso facilitado à Janela Virtual, Teclado, Mouse e Delta Time.
    """
    def __init__(self):
        super().__init__()
        self.janela = Window.get_instance()
        self.teclado = self.janela.keyboard
        self.mouse = self.janela.mouse

    def loop(self):
        """Lógica da cena executada a cada frame."""
        pass

    def draw(self):
        """Renderização gráfica da cena na tela virtual."""
        pass
