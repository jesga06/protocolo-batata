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
    """Cria a janela do jogo perfeitamente centralizada na tela com alta definição e suporte a High-DPI."""
    import pygame
    os.environ["SDL_VIDEO_CENTERED"] = "1"

    # Habilita suporte a High-DPI no Windows para evitar borrão de DPI scaling
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

    if not pygame.get_init():
        pygame.init()

    janela = Window(
        largura_virtual=LARGURA_TELA,
        altura_virtual=ALTURA_TELA,
        titulo=TITULO_JOGO,
        resizavel=True,
        pixel_art=False
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

        # 3. Limita taxa de quadros conforme a configuração de fps_cap (60, 45, 30, 15)
        cena_atual = getattr(SceneManager, "_current_scene", None)
        fps_alvo = FPS_PADRAO
        if cena_atual and hasattr(cena_atual, "gerenciador_config"):
            val_fps = cena_atual.gerenciador_config.obter_valor("fps_cap")
            try:
                fps_alvo = int(val_fps)
            except Exception:
                fps_alvo = FPS_PADRAO
        elif cena_atual and hasattr(cena_atual, "config_sistema"):
            val_fps = cena_atual.config_sistema.obter_valor("fps_cap")
            try:
                fps_alvo = int(val_fps)
            except Exception:
                fps_alvo = FPS_PADRAO

        if hasattr(janela, "_clock"):
            janela._clock.tick(fps_alvo)

        frame_count += 1
        if limite_frames is not None and frame_count >= limite_frames:
            break


if __name__ == "__main__":
    main()
