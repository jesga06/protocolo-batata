import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.conquistas_dados import CHIPS_FIRMWARE
from src.ui.hud import HUD
from src.ui.menu_conquistas import MenuConquistas
from src.utils.constantes import ALTURA_TELA, LARGURA_TELA


class _MockMouseVirtual:
    def __init__(self, pos=(0, 0), down=False):
        self._pos = pos
        self._down = down

    def get_position(self):
        return self._pos

    def button_down(self, btn):
        return btn == 1 and self._down


class _MockKeyboard:
    def __init__(self, down_keys=None, pressed_keys=None):
        self._down = set(down_keys or [])
        self._pressed = set(pressed_keys or [])

    def key_down(self, key):
        return key in self._down

    def key_pressed(self, key):
        return key in self._pressed


class TestPlaytest2UI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.font.init()

    def test_01_menu_conquistas_1080p_draw_and_virtual_1280x720_hit_testing(self):
        cfg = GerenciadorConfiguracoes()
        sys_conq = cfg.sistema_conquistas
        primeiro_chip = next(iter(CHIPS_FIRMWARE.keys()))
        sys_conq.recompensas["modificador_run"].add(primeiro_chip)

        menu = MenuConquistas(cfg, sys_conq, em_jogo=False)
        menu.abrir(aba=0)
        menu.cooldown_input = 0.0

        screen_1080p = pygame.Surface((1920, 1080))
        expected_ox = (LARGURA_TELA - menu.largura_modal) // 2
        expected_oy = (ALTURA_TELA - menu.altura_modal) // 2

        # Primeiro draw aquece cache de fontes na escala 1.5x; offset_x/y devem permanecer em 1280x720!
        menu.draw(screen_1080p)
        self.assertEqual(menu.offset_x, expected_ox)
        self.assertEqual(menu.offset_y, expected_oy)

        # Segundo draw em 1080p não deve alocar nenhuma fonte nova
        with patch("pygame.font.SysFont", side_effect=AssertionError("SysFont não deve ser chamado por frame!")):
            menu.draw(screen_1080p)

        # 1. Clicar na Aba 1 (CHIPS DE FIRMWARE) usando coords virtuais 1280x720
        aba0, aba1, btn_fechar = menu._obter_rects_topo()
        menu.update(0.016, mouse=_MockMouseVirtual(aba1.center, down=True))
        self.assertEqual(menu.aba_atual, 1)

        # 2. Clicar no primeiro card de Firmware
        card_w = (menu.largura_modal - 72) // 2
        card_rect = pygame.Rect(menu.offset_x + 28, menu.offset_y + 132, card_w, 98)
        menu.update(0.016, mouse=_MockMouseVirtual(card_rect.center, down=True))
        self.assertIn(primeiro_chip, sys_conq.modificadores_equipados)

        # 3. Voltar para Aba 0 (CONQUISTAS)
        menu.update(0.016, mouse=_MockMouseVirtual(aba0.center, down=True))
        self.assertEqual(menu.aba_atual, 0)

        # 4. Clicar no botão FIXAR do primeiro card
        btn_pin = pygame.Rect(menu.offset_x + menu.largura_modal - 134, menu.offset_y + 132 + 28, 96, 28)
        pins_antes = len(sys_conq.fixadas)
        menu.update(0.016, mouse=_MockMouseVirtual(btn_pin.center, down=True))
        self.assertNotEqual(len(sys_conq.fixadas), pins_antes)

        # 5. Clicar na área do card (fora do botão) também alterna pin
        card_conq_rect = pygame.Rect(menu.offset_x + 28, menu.offset_y + 132, menu.largura_modal - 56, 92)
        pins_antes_card = len(sys_conq.fixadas)
        menu.update(0.016, mouse=_MockMouseVirtual((card_conq_rect.x + 40, card_conq_rect.centery), down=True))
        self.assertNotEqual(len(sys_conq.fixadas), pins_antes_card)

        # 6. Clicar em FECHAR
        menu.update(0.016, mouse=_MockMouseVirtual(btn_fechar.center, down=True))
        self.assertFalse(menu.ativo)

    def test_02_menu_conquistas_tab_debounce_no_spam(self):
        cfg = GerenciadorConfiguracoes()
        menu = MenuConquistas(cfg, cfg.sistema_conquistas, em_jogo=False)
        menu.abrir(aba=0)
        menu.cooldown_input = 0.0

        # Segurar TAB (key_pressed=True, key_down=False) por vários frames NÃO deve trocar de aba
        kb_hold = _MockKeyboard(down_keys=set(), pressed_keys={"TAB"})
        for _ in range(10):
            menu.update(0.016, teclado=kb_hold, mouse=_MockMouseVirtual((0, 0), down=False))
        self.assertEqual(menu.aba_atual, 0)

        # key_down("TAB") troca uma vez e ativa debounce de 0.18s
        kb_down = _MockKeyboard(down_keys={"TAB"}, pressed_keys={"TAB"})
        menu.update(0.016, teclado=kb_down, mouse=_MockMouseVirtual((0, 0), down=False))
        self.assertEqual(menu.aba_atual, 1)

        # Novo key_down dentro de 0.18s é ignorado
        menu.update(0.05, teclado=kb_down, mouse=_MockMouseVirtual((0, 0), down=False))
        self.assertEqual(menu.aba_atual, 1)

        # Após passar 0.18s, key_down("TAB") volta para aba 0
        menu.update(0.20, teclado=kb_down, mouse=_MockMouseVirtual((0, 0), down=False))
        self.assertEqual(menu.aba_atual, 0)

    def test_03_menu_conquistas_mousewheel_via_window_eventos(self):
        cfg = GerenciadorConfiguracoes()
        menu = MenuConquistas(cfg, cfg.sistema_conquistas, em_jogo=False)
        menu.abrir(aba=0)
        menu.cooldown_input = 0.0

        fake_window = SimpleNamespace(
            eventos=[SimpleNamespace(type=pygame.MOUSEWHEEL, y=-2)]
        )
        with patch("PPlay.window.Window.get_instance", return_value=fake_window):
            menu.update(0.016, mouse=_MockMouseVirtual((640, 360), down=False))

        self.assertGreater(menu.scroll_y, 0.0)
        self.assertLessEqual(menu.scroll_y, menu._obter_max_scroll())

        # Scroll para cima volta para 0.0 (clampado)
        fake_window.eventos = [SimpleNamespace(type=pygame.MOUSEWHEEL, y=10)]
        with patch("PPlay.window.Window.get_instance", return_value=fake_window):
            menu.update(0.016, mouse=_MockMouseVirtual((640, 360), down=False))

        self.assertEqual(menu.scroll_y, 0.0)

    def test_04_hud_desenhar_banners_desbloqueio_and_zero_font_alloc(self):
        hud = HUD()
        screen_720 = pygame.Surface((1280, 720))
        screen_1080 = pygame.Surface((1920, 1080))
        banners = [
            {
                "titulo": "Mestre da Chave Inglesa (M1)",
                "subtitulo": "Desbloqueia: Dash + SMG Compacta",
                "tempo": 3.85,
                "tempo_max": 4.0,
            },
            {
                "titulo": "Sobrevivente do Turno",
                "subtitulo": "Desbloqueia: Firmware Cache L1",
                "tempo": 2.0,
                "tempo_max": 4.0,
                "cor": (34, 211, 238),
            },
            {
                "titulo": "Saindo da Tela",
                "subtitulo": "Troféu Permanente",
                "tempo": 0.12,
                "tempo_max": 4.0,
            },
        ]

        # Primeiro render aquece cache de fontes na escala 1.0x e 1.5x
        hud.desenhar_banners_desbloqueio(screen_720, banners)
        hud.desenhar_banners_desbloqueio(screen_1080, banners)

        # Chamadas subsequentes devem ter ZERO alocações de fontes
        with patch("pygame.font.SysFont", side_effect=AssertionError("SysFont não deve ser chamado por frame!")):
            hud.desenhar_banners_desbloqueio(screen_720, banners)
            hud.desenhar_banners_desbloqueio(screen_1080, banners)
            hud.desenhar_banners_desbloqueio(screen_1080, [])


if __name__ == "__main__":
    unittest.main()
