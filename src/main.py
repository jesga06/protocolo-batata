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

from src.utils.janela import Janela as Window
from PPlay.scenemanager import SceneManager
from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, FPS_PADRAO
from src.cenas.menu_principal import MenuPrincipalScene


def inicializar_jogo():
    """Cria a janela do jogo perfeitamente centralizada na tela com alta definição e suporte a High-DPI."""
    import pygame
    os.environ["SDL_VIDEO_CENTERED"] = "1"
    os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "0")

    # Habilita suporte a High-DPI antes de pygame.init() para evitar borrão de DPI scaling
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

    # Inicializa canais do mixer com buffer expandido (32 canais) antes da criação das cenas
    try:
        if not pygame.mixer.get_init():
            try:
                from PPlay.sound import SoundManager
                SoundManager.inicializar()
            except Exception:
                pygame.mixer.init()
        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(32)
    except Exception:
        pass

    vsync_inicial = True
    try:
        from src.sistemas.config_sistema import GerenciadorConfiguracoes
        from src.utils.constantes import SAVE_FILE_PATH
        cfg_inicial = GerenciadorConfiguracoes()
        cfg_inicial.carregar_arquivo(SAVE_FILE_PATH)
        val_vsync = str(cfg_inicial.obter_valor("vsync")).strip().lower()
        vsync_inicial = val_vsync not in ("desligado", "false", "0", "off")
    except Exception:
        vsync_inicial = True

    janela = Window(
        largura_virtual=LARGURA_TELA,
        altura_virtual=ALTURA_TELA,
        titulo=TITULO_JOGO,
        resizavel=True,
        pixel_art=True,
        vsync=vsync_inicial
    )
    if getattr(janela, "vsync_ativo", True) != vsync_inicial and hasattr(janela, "definir_vsync"):
        janela.definir_vsync(vsync_inicial)
    # Nunca força FULLSCREEN na inicialização. Alguns drivers Windows (especialmente
    # na transição desktop -> modo exclusivo) aceitam set_mode(), mas não apresentam
    # nenhum frame. F11/Alt+Enter continua disponível sem tornar o jogo injogável.
    janela.set_background_color((18, 22, 30))

    cena_inicial = MenuPrincipalScene()
    SceneManager.change_scene(cena_inicial)
    return janela


def _parse_fps_alvo(val_fps) -> int:
    """Converte o valor de fps_cap para inteiro (0 = ilimitado)."""
    if val_fps is None or str(val_fps).strip().lower() == "ilimitado":
        return 0
    try:
        return int(val_fps)
    except Exception:
        return FPS_PADRAO


def main(limite_frames: int | None = None):
    """
    Loop principal do jogo.
    Se limite_frames for definido (ex: em testes headless), executa a quantidade de frames e retorna.
    """
    janela = inicializar_jogo()
    frame_count = 0

    while True:
        # 1. Processa eventos do sistema e atalhos globais no topo do loop
        janela.processar_eventos()

        # 2. Executa ciclo da cena ativa (loop + draw)
        SceneManager.run()

        # 3. Obtém limite de taxa de quadros (FPS Cap configurado: ilimitado [0], 45, 30, 15)
        # Suporta GameplayScene, MenuPrincipalScene, TutorialScene e quaisquer cenas com gerenciador de config
        cena_atual = getattr(SceneManager, "_current_scene", None)
        fps_alvo = FPS_PADRAO
        if cena_atual and hasattr(cena_atual, "gerenciador_config") and cena_atual.gerenciador_config:
            fps_alvo = _parse_fps_alvo(cena_atual.gerenciador_config.obter_valor("fps_cap"))
        elif cena_atual and hasattr(cena_atual, "config_sistema") and cena_atual.config_sistema:
            fps_alvo = _parse_fps_alvo(cena_atual.config_sistema.obter_valor("fps_cap"))
        else:
            # Fallback para cenas como TutorialScene que podem não instanciar seu próprio gerenciador
            try:
                from src.sistemas.config_sistema import GerenciadorConfiguracoes
                from src.utils.constantes import SAVE_FILE_PATH
                cfg = GerenciadorConfiguracoes()
                cfg.carregar_arquivo(SAVE_FILE_PATH)
                fps_alvo = _parse_fps_alvo(cfg.obter_valor("fps_cap"))
            except Exception:
                fps_alvo = FPS_PADRAO

        # 4. Atualiza a tela virtual e apresenta na tela real com letterbox e sincronização de clock
        janela.update(fps_alvo=fps_alvo)

        frame_count += 1
        if limite_frames is not None and frame_count >= limite_frames:
            break


if __name__ == "__main__":
    main()
