"""
Testes Unitários para o Gerenciador de Janela e Escalonamento Nativo (src/utils/janela.py).
"""

import unittest
import pygame
from unittest.mock import patch
from src.utils.janela import Janela


class TestJanelaNativa(unittest.TestCase):
    """Valida o funcionamento do controlador de Janela nativa em Pygame."""

    @classmethod
    def setUpClass(cls):
        if not pygame.get_init():
            pygame.init()

    def test_singleton_e_resolucao_virtual(self):
        """Verifica se a Janela mantém resolução virtual 1280x720 e comportamento Singleton."""
        j1 = Janela.get_instance()
        j2 = Janela()
        self.assertIs(j1, j2)
        self.assertEqual(j1.largura, 1280)
        self.assertEqual(j1.altura, 720)
        self.assertEqual(j1.screen.get_size(), (1280, 720))

    def test_screen_to_virtual_coords_clamping(self):
        """Verifica se a conversão de coordenadas mapeia e clampa o mouse aos limites do canvas."""
        janela = Janela.get_instance()
        rw, rh = janela.real_screen.get_size()

        # Coordenadas no centro da tela real devem mapear para o centro do canvas virtual (640, 360)
        vx, vy = janela.screen_to_virtual_coords(rw / 2.0, rh / 2.0)
        self.assertAlmostEqual(vx, 640.0, delta=2.0)
        self.assertAlmostEqual(vy, 360.0, delta=2.0)

        # Coordenadas fora da janela (nas bordas pretas) devem ser clampadas em [0, 1280] e [0, 720]
        vx_neg, vy_neg = janela.screen_to_virtual_coords(-500.0, -500.0)
        self.assertGreaterEqual(vx_neg, 0.0)
        self.assertGreaterEqual(vy_neg, 0.0)

        vx_max, vy_max = janela.screen_to_virtual_coords(rw + 500.0, rh + 500.0)
        self.assertLessEqual(vx_max, 1280.0)
        self.assertLessEqual(vy_max, 720.0)

    def test_draw_text_cached_fonts(self):
        """Verifica se o método draw_text utiliza cache interno sem recriar fontes."""
        janela = Janela.get_instance()
        janela.draw_text("TESTE FPS", 10, 10, tamanho=14, cor=(255, 255, 255))
        self.assertTrue(any("Arial" in str(k) and 14 in k for k in janela._fontes_cache.keys()))

    def test_alternar_fullscreen(self):
        """Verifica a alternância de estado do modo tela cheia."""
        janela = Janela.get_instance()
        estado_antigo = janela.is_fullscreen
        janela.alternar_fullscreen()
        self.assertNotEqual(janela.is_fullscreen, estado_antigo)
        janela.alternar_fullscreen()
        self.assertEqual(janela.is_fullscreen, estado_antigo)

    def test_definir_resolucao_menores_que_720p(self):
        """Valida que definir_resolucao ajusta escala_resolucao_mundo sem encolher a janela do SO."""
        janela = Janela.get_instance()
        janela.definir_resolucao("75%")
        self.assertAlmostEqual(janela.escala_resolucao_mundo, 0.75)
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (1280, 720))

        janela.definir_resolucao("50%")
        self.assertAlmostEqual(janela.escala_resolucao_mundo, 0.50)
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (1280, 720))

        janela.definir_resolucao("25%")
        self.assertAlmostEqual(janela.escala_resolucao_mundo, 0.25)
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (1280, 720))

        janela.definir_resolucao("100%")
        self.assertAlmostEqual(janela.escala_resolucao_mundo, 1.0)
        self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (1280, 720))

    def test_fps_ilimitado_zero_passado_ao_clock(self):
        """fps_alvo=0 (ilimitado) deve chamar clock.tick(0) sem fallback para valor positivo."""
        from unittest.mock import MagicMock
        from src.main import _parse_fps_alvo

        self.assertEqual(_parse_fps_alvo("ilimitado"), 0)
        self.assertEqual(_parse_fps_alvo("45"), 45)

        janela = Janela(largura_virtual=1280, altura_virtual=720, titulo="Teste FPS")
        janela.fps_alvo = 30
        janela._clock = MagicMock()
        janela._clock.tick.return_value = 4
        janela.update(fps_alvo=0)
        janela._clock.tick.assert_called_once_with(0)

    def test_flip_falha_usa_update_sem_quebrar_loop(self):
        janela = Janela.get_instance()
        janela._aviso_apresentacao = False
        janela._aviso_fallback_apresentacao = False
        with patch("pygame.display.flip", side_effect=pygame.error("driver test")) as flip_mock, \
             patch("pygame.display.update") as update_mock:
            janela.update(fps_alvo=30)
            flip_mock.assert_called_once()
            update_mock.assert_called_once()


class TestNativeDPIProjection(unittest.TestCase):
    """Regressão Option B: projeção nativa em HiDPI (2560x1440) e ultrawide (3440x1440)."""

    @classmethod
    def setUpClass(cls):
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

    @staticmethod
    def _quadrantes_com_conteudo(surf: pygame.Surface, cor_fundo: tuple[int, int, int]) -> dict[str, bool]:
        """Verifica se há pixels distintos da cor_fundo em cada um dos 4 quadrantes (TL, TR, BL, BR)."""
        w, h = surf.get_size()
        mx, my = w // 2, h // 2
        quadrantes = {
            "TL": (0, mx, 0, my),
            "TR": (mx, w, 0, my),
            "BL": (0, mx, my, h),
            "BR": (mx, w, my, h),
        }
        resultado = {}
        for nome, (x0, x1, y0, y1) in quadrantes.items():
            achou = False
            for y in range(y0, y1, 8):
                for x in range(x0, x1, 8):
                    if surf.get_at((x, y))[:3] != cor_fundo:
                        achou = True
                        break
                if achou:
                    break
            resultado[nome] = achou
        return resultado

    def test_projection_helpers_align_1_to_1_2560x1440_and_3440x1440(self):
        """sx/sy/sw/sh/srect e screen_to_virtual_coords alinham 1:1 em 2560x1440 e 3440x1440."""
        janela = Janela.get_instance()
        old_real = janela.real_screen
        old_screen = janela.screen
        old_w = janela.largura_janela_atual
        old_h = janela.altura_janela_atual
        try:
            for (rw, rh, exp_ox, exp_oy, exp_scale) in (
                (2560, 1440, 0, 0, 2.0),
                (3440, 1440, 440, 0, 2.0),
            ):
                surf = pygame.Surface((rw, rh))
                janela.real_screen = surf
                janela.screen = surf
                janela.largura_janela_atual = rw
                janela.altura_janela_atual = rh
                ox, oy, vw, vh, scale = janela._calcular_viewport(rw, rh)
                janela.render_scale = scale
                janela.viewport_offset = (ox, oy)
                janela.viewport_rect = (ox, oy, vw, vh)

                self.assertEqual((ox, oy), (exp_ox, exp_oy))
                self.assertAlmostEqual(scale, exp_scale, places=4)
                self.assertEqual(janela.sw(100), int(round(100 * exp_scale)))
                self.assertEqual(janela.sh(50), int(round(50 * exp_scale)))

                rect = janela.srect(100, 200, 300, 150)
                self.assertEqual(rect, pygame.Rect(exp_ox + 200, exp_oy + 400, 600, 300))

                # Round-trip exact 1:1 alignment with screen_to_virtual_coords()
                for lx, ly in ((0.0, 0.0), (640.0, 360.0), (1279.0, 719.0), (320.0, 540.0)):
                    px = janela.sx(lx)
                    py = janela.sy(ly)
                    vx, vy = janela.screen_to_virtual_coords(px, py)
                    self.assertAlmostEqual(vx, lx, delta=1.0)
                    self.assertAlmostEqual(vy, ly, delta=1.0)

                # Native-DPI font caching returns identical Font instance without re-allocating
                f1 = janela.obter_fonte_nativa("arial", 16, bold=True)
                f2 = janela.obter_fonte_nativa("arial", 16, bold=True)
                self.assertIs(f1, f2)
        finally:
            janela.real_screen = old_real
            janela.screen = old_screen
            janela.largura_janela_atual = old_w
            janela.altura_janela_atual = old_h
            ox, oy, vw, vh, scale = janela._calcular_viewport(old_w, old_h)
            janela.render_scale = scale
            janela.viewport_offset = (ox, oy)
            janela.viewport_rect = (ox, oy, vw, vh)

    def test_hud_menus_and_modals_fill_all_4_quadrants_at_2560x1440(self):
        """HUD, MenuPrincipalScene, TutorialScene, MenuConfigs, ModalLevelUp e ModalOverclock preenchem TL/TR/BL/BR em 2560x1440."""
        from src.cenas.menu_principal import MenuPrincipalScene
        from src.cenas.tutorial import TutorialScene
        from src.entidades.inimigo_padrao import InimigoPadrao
        from src.entidades.jogador import Jogador
        from src.sistemas.config_sistema import GerenciadorConfiguracoes
        from src.sistemas.sistema_xp import SistemaXP
        from src.ui.hud import HUD
        from src.ui.menu_configs import MenuConfigs
        from src.ui.modal_level_up import ModalLevelUp
        from src.ui.modal_overclock import ModalOverclock

        janela = Janela.get_instance()
        old_real = janela.real_screen
        old_screen = janela.screen
        old_w = janela.largura_janela_atual
        old_h = janela.altura_janela_atual

        sentinel = (1, 2, 3)
        surf_4k = pygame.Surface((2560, 1440))
        try:
            janela.real_screen = surf_4k
            janela.screen = surf_4k
            janela.largura_janela_atual = 2560
            janela.altura_janela_atual = 1440
            ox, oy, vw, vh, scale = janela._calcular_viewport(2560, 1440)
            janela.render_scale = scale
            janela.viewport_offset = (ox, oy)
            janela.viewport_rect = (ox, oy, vw, vh)

            # 1. HUD (vitals top-left, XP & boss bar spanning across top-center into TR)
            surf_4k.fill(sentinel)
            hud = HUD()
            jogador = Jogador(x=500.0, y=500.0)
            jogador.dash_desbloqueado = True
            xp_sys = SistemaXP()
            xp_sys.ganhar_xp(20)
            elite = InimigoPadrao(x=600.0, y=600.0)
            elite.is_elite = True
            elite.nome_elite = "ESTAGIÁRIO SÊNIOR"
            hud.desenhar_painel_vitais(surf_4k, jogador)
            hud.desenhar_barra_xp(surf_4k, xp_sys)
            hud.desenhar_barra_boss(surf_4k, elite)
            q_hud = self._quadrantes_com_conteudo(surf_4k, sentinel)
            self.assertTrue(q_hud["TL"], f"HUD não desenhou em TL: {q_hud}")
            self.assertTrue(q_hud["TR"], f"HUD não desenhou em TR: {q_hud}")

            # 2. MenuPrincipalScene
            surf_4k.fill(sentinel)
            menu_p = MenuPrincipalScene()
            menu_p.draw()
            q_mp = self._quadrantes_com_conteudo(surf_4k, (7, 9, 14))
            self.assertEqual(q_mp, {"TL": True, "TR": True, "BL": True, "BR": True}, f"MenuPrincipalScene falhou 4 quadrantes: {q_mp}")

            # 3. TutorialScene
            surf_4k.fill(sentinel)
            tut = TutorialScene()
            tut.draw()
            q_tut = self._quadrantes_com_conteudo(surf_4k, (7, 9, 14))
            self.assertEqual(q_tut, {"TL": True, "TR": True, "BL": True, "BR": True}, f"TutorialScene falhou 4 quadrantes: {q_tut}")

            # 4. MenuConfigs (Gameplay)
            surf_4k.fill(sentinel)
            cfg = GerenciadorConfiguracoes()
            menu_cfg = MenuConfigs(cfg, em_jogo=True)
            menu_cfg.abrir()
            menu_cfg.draw(surf_4k)
            q_cfg = self._quadrantes_com_conteudo(surf_4k, sentinel)
            self.assertEqual(q_cfg, {"TL": True, "TR": True, "BL": True, "BR": True}, f"MenuConfigs falhou 4 quadrantes: {q_cfg}")

            # 5. ModalLevelUp
            surf_4k.fill(sentinel)
            modal_lvl = ModalLevelUp(cfg, jogador)
            modal_lvl.abrir(nivel=5)
            modal_lvl.tempo_transicao_entrada = 0.0
            modal_lvl.draw(surf_4k)
            q_lvl = self._quadrantes_com_conteudo(surf_4k, sentinel)
            self.assertEqual(q_lvl, {"TL": True, "TR": True, "BL": True, "BR": True}, f"ModalLevelUp falhou 4 quadrantes: {q_lvl}")

            # 6. ModalOverclock
            surf_4k.fill(sentinel)
            modal_oc = ModalOverclock(jogador)
            modal_oc.abrir()
            modal_oc.tempo_transicao_entrada = 0.0
            modal_oc.draw(surf_4k)
            q_oc = self._quadrantes_com_conteudo(surf_4k, sentinel)
            self.assertEqual(q_oc, {"TL": True, "TR": True, "BL": True, "BR": True}, f"ModalOverclock falhou 4 quadrantes: {q_oc}")
        finally:
            janela.real_screen = old_real
            janela.screen = old_screen
            janela.largura_janela_atual = old_w
            janela.altura_janela_atual = old_h
            ox, oy, vw, vh, scale = janela._calcular_viewport(old_w, old_h)
            janela.render_scale = scale
            janela.viewport_offset = (ox, oy)
            janela.viewport_rect = (ox, oy, vw, vh)

    def test_definir_vsync_nao_recria_janela_quando_inalterado(self):
        from unittest.mock import patch
        janela = Janela.get_instance()
        estado_inicial = bool(janela.vsync_ativo)
        with patch.object(janela, "_set_mode_seguro") as mock_set_mode:
            janela.definir_vsync(estado_inicial)
            mock_set_mode.assert_not_called()

    def test_gameplay_ignora_lmb_segurado_do_menu_ate_soltar(self):
        from unittest.mock import MagicMock, patch
        from src.cenas.gameplay import GameplayScene

        janela = Janela.get_instance()
        old_mouse = janela.mouse
        fake_mouse = MagicMock()
        fake_mouse.get_position.return_value = (700.0, 400.0)
        fake_mouse.button_down.return_value = False
        fake_mouse.button_pressed.return_value = True
        janela.mouse = fake_mouse
        try:
            with patch.object(janela, "definir_vsync") as mock_vsync:
                cena = GameplayScene()
                mock_vsync.assert_not_called()
            self.assertTrue(cena._aguardando_soltar_lmb)
            cena.pausado = False
            cena.update(0.016)
            self.assertEqual(len(cena.projeteis), 0, "Não deve disparar enquanto LMB do menu não for solto")
            self.assertTrue(cena._aguardando_soltar_lmb)

            # Solta o botão: libera a trava
            fake_mouse.button_pressed.return_value = False
            cena.update(0.016)
            self.assertFalse(cena._aguardando_soltar_lmb)

            # Novo clique dispara normalmente
            fake_mouse.button_pressed.return_value = True
            cena.update(0.016)
            self.assertGreater(len(cena.projeteis), 0)
        finally:
            janela.mouse = old_mouse

    def test_fullscreen_resize_sync_e_tamanho_desktop(self):
        """Em fullscreen, eventos de resize atualizam real_screen sem sobrescrever largura_janela_atual."""
        from unittest.mock import patch

        janela = Janela.get_instance()
        old_fs = janela.is_fullscreen
        old_real = janela.real_screen
        old_screen = janela.screen
        old_w = janela.largura_janela_atual
        old_h = janela.altura_janela_atual
        try:
            janela.is_fullscreen = True
            janela.largura_janela_atual = 1280
            janela.altura_janela_atual = 720
            fake_surf = pygame.Surface((1920, 1080))
            ev = pygame.event.Event(pygame.VIDEORESIZE, {"w": 1920, "h": 1080})
            with patch("pygame.event.get", return_value=[ev]), \
                 patch("pygame.display.get_surface", return_value=fake_surf), \
                 patch.object(janela, "_set_mode_seguro", return_value=fake_surf) as mock_mode:
                janela.processar_eventos()
                mock_mode.assert_not_called()
            self.assertEqual(janela.real_screen.get_size(), (1920, 1080))
            self.assertEqual((janela.largura_janela_atual, janela.altura_janela_atual), (1280, 720))

            with patch.object(janela, "_is_dummy_driver", return_value=False), \
                 patch("pygame.display.get_desktop_sizes", return_value=[(2560, 1440)]):
                self.assertEqual(janela._obter_tamanho_fullscreen(), (0, 0))
                self.assertEqual((janela.tela_nativa_largura, janela.tela_nativa_altura), (2560, 1440))
        finally:
            janela.is_fullscreen = old_fs
            janela.real_screen = old_real
            janela.screen = old_screen
            janela.largura_janela_atual = old_w
            janela.altura_janela_atual = old_h
            janela._atualizar_metricas_viewport()


if __name__ == "__main__":
    unittest.main()
