"""
Protocolo: Batata — Ponto de Entrada Principal (Main)
Inicializa a Janela PPlay 2.0, subsistemas e orquestra o loop principal de cenas.
"""

import os
import sys

# Garante que o diretório raiz esteja no sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PPlay.window import Window
from PPlay.scenemanager import SceneManager
from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, FPS_PADRAO
from src.cenas.menu_principal import MenuPrincipalScene


def inicializar_jogo():
    """Cria a janela do PPlay e configura a cena inicial."""
    janela = Window(
        largura_virtual=LARGURA_TELA,
        altura_virtual=ALTURA_TELA,
        titulo=TITULO_JOGO,
        resizavel=True,
        pixel_art=True
    )
    janela.set_background_color((18, 22, 30))

    cena_inicial = MenuPrincipalScene()
    SceneManager.change_scene(cena_inicial)
    return janela


def main(limite_frames: int | None = None):
    """
    Loop principal do jogo.
    Se limite_frames for definido (ex: em testes headless), executa a quantidade de frames e retorna.
    """
    janela = inicializar_jogo()
    frame_count = 0

    while True:
        # 1. Executa ciclo da cena ativa (loop + draw)
        SceneManager.run()

        # 2. Atualiza a tela virtual e apresenta na tela real com letterbox
        janela.update()

        frame_count += 1
        if limite_frames is not None and frame_count >= limite_frames:
            break


if __name__ == "__main__":
    main()
