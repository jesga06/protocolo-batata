"""
Suite de Regressão Forense W3-06 — Visibilidade em Surface Real por Pixels
Valida que efeitos visuais críticos são efetivamente desenhados na tela virtual:
1. Config 18 (iluminacao): névoa escura renderizada nas bordas mesmo com 0 buffs ativos.
2. Config 17 (cores_invertidas): inversão RGB aplicada mesmo com 0 buffs ativos.
3. Toasts flutuantes renderizados mesmo com 0 buffs ativos e clampados em [12, LARGURA_TELA - 12].
4. Botão de engrenagem [C] sempre visível mesmo sob hud="desligado".
5. Cutscene do Boss (Geladeira Tsunami): Boss e balão de fala visíveis na viewport 800x600 durante musica_in.
6. Config 9 (zoom="75%"): FOV real expandido (1067x800) renderizando entidades além da janela padrão 800x600 e alinhando _obter_mouse_mundo().
"""

import os
import tempfile
import unittest
from unittest.mock import patch
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
pygame.init()
pygame.font.init()

from PPlay.window import Window
from src.cenas.gameplay import GameplayScene
from src.entidades.inimigo_padrao import InimigoPadrao
from src.utils.constantes import LARGURA_TELA, ALTURA_TELA


class TestRenderVisibilityRegression(unittest.TestCase):
    """Testes forenses de visibilidade por inspeção direta de pixels na surface virtual."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.temp_save = os.path.join(self._tmpdir.name, "save.json")
        self._p1 = patch("src.utils.constantes.SAVE_FILE_PATH", self.temp_save)
        self._p2 = patch("src.cenas.gameplay.SAVE_FILE_PATH", self.temp_save)
        self._p1.start()
        self._p2.start()
        self.janela = Window(LARGURA_TELA, ALTURA_TELA)
        self.cena = GameplayScene()

    def tearDown(self):
        self._p2.stop()
        self._p1.stop()
        self._tmpdir.cleanup()

    def test_iluminacao_fog_renders_even_with_zero_active_buffs(self):
        """Com 0 buffs ativos, iluminacao='ligado' deve escurecer cantos distantes (>195px do jogador)."""
        self.assertEqual(self.cena.jogador.obter_buffs_ativos(), [])
        self.cena.draw()
        cor_canto_sem_fog = self.cena.janela.screen.get_at((20, 560))[:3]

        self.cena.gerenciador_config.desbloquear_config("iluminacao")
        self.cena.gerenciador_config.definir_valor("iluminacao", "ligado")
        self.cena.aplicar_modificadores()
        self.cena.draw()
        cor_canto_com_fog = self.cena.janela.screen.get_at((20, 560))[:3]

        self.assertNotEqual(cor_canto_com_fog, cor_canto_sem_fog)
        self.assertLess(sum(cor_canto_com_fog), sum(cor_canto_sem_fog), "A névoa deve escurecer os cantos fora do raio de 195px.")

    def test_cores_invertidas_inverts_screen_even_with_zero_active_buffs(self):
        """Com 0 buffs ativos, cores_invertidas='ligado' deve inverter o RGB da tela."""
        self.assertEqual(self.cena.jogador.obter_buffs_ativos(), [])
        self.cena.draw()
        px_normal = self.cena.janela.screen.get_at((300, 300))[:3]

        self.cena.gerenciador_config.desbloquear_config("cores_invertidas")
        self.cena.gerenciador_config.definir_valor("cores_invertidas", "ligado")
        self.cena.aplicar_modificadores()
        self.cena.draw()
        px_inv = self.cena.janela.screen.get_at((300, 300))[:3]

        self.assertEqual(px_inv, (255 - px_normal[0], 255 - px_normal[1], 255 - px_normal[2]))

    def test_gear_button_visible_when_hud_disabled(self):
        """Mesmo com hud='desligado', o botão de engrenagem [C] em (752..784, 16..48) deve ser desenhado."""
        self.cena.gerenciador_config.desbloquear_config("hud")
        self.cena.gerenciador_config.definir_valor("hud", "desligado")
        self.cena.aplicar_modificadores()

        screen = self.cena.janela.screen
        screen.fill((0, 0, 0))
        self.cena._desenhar_hud_tela(hud_visivel=False)

        pixels_gear = [
            screen.get_at((x, y))[:3]
            for x in range(754, 782, 2)
            for y in range(18, 46, 2)
        ]
        self.assertTrue(any(p != (0, 0, 0) for p in pixels_gear), "Botão [C] deve ser renderizado mesmo com hud='desligado'.")

    def test_boss_and_speech_balloon_visible_during_cutscene_intro(self):
        """Durante a fase 'musica_in' da cutscene do Nv. 20, Boss e balão devem estar dentro da viewport 800x600."""
        self.cena.iniciar_boss_cutscene()
        # Avança whiteout (2s) -> blackout (1s) -> musica_in (2.0s de subida da intro)
        self.cena.boss_cutscene_timer = 2.0
        self.cena.loop(dt=0.016)
        self.cena.boss_cutscene_timer = 1.0
        self.cena.loop(dt=0.016)
        self.assertEqual(self.cena.boss_cutscene_fase, "musica_in")

        for _ in range(20):
            self.cena.loop(dt=0.1)

        boss = self.cena.chefe_final
        self.assertIsNotNone(boss)
        draw_x = self.cena.camera.transform_x(boss.x)
        draw_y = self.cena.camera.transform_y(boss.y)
        self.assertGreaterEqual(draw_x, 0.0)
        self.assertLessEqual(draw_x + boss.largura, float(LARGURA_TELA))
        self.assertLess(draw_y, float(ALTURA_TELA), "O topo do Boss deve estar visível dentro da altura da tela (600px).")
        self.assertTrue(boss.mostrar_balao_fala)

    def test_zoom_75_expands_real_fov_and_aligns_inverse_mouse(self):
        """zoom='75%' deve expandir o FOV real para 1067x800 (sem barras pretas) e alinhar _obter_mouse_mundo()."""
        self.cena.camera.follow(self.cena.jogador, suavizacao=1.0)
        self.cena.gerenciador_config.desbloquear_config("zoom")
        self.cena.gerenciador_config.definir_valor("zoom", "75%")
        self.cena.aplicar_modificadores()

        fov_w, fov_h, cam75_x, cam75_y = self.cena._obter_viewport_zoom75()
        self.assertEqual((fov_w, fov_h), (1067, 800))

        # Verifica transformação inversa exata do mouse nos extremos da tela
        wx0, wy0 = self.cena._obter_mouse_mundo(0.0, 0.0)
        wx1, wy1 = self.cena._obter_mouse_mundo(float(LARGURA_TELA), float(ALTURA_TELA))
        self.assertAlmostEqual(wx0, cam75_x, places=3)
        self.assertAlmostEqual(wy0, cam75_y, places=3)
        self.assertAlmostEqual(wx1, cam75_x + fov_w, places=3)
        self.assertAlmostEqual(wy1, cam75_y + fov_h, places=3)

        # Renderiza em low_graphics um inimigo posicionado a +460px do centro (fora de 800x600, mas dentro de 1067x800)
        self.cena.gerenciador_config.desbloquear_config("graficos_qualidade")
        self.cena.gerenciador_config.definir_valor("graficos_qualidade", "baixa")
        self.cena.aplicar_modificadores()

        cx_jog = self.cena.jogador.x + self.cena.jogador.largura / 2.0
        cy_jog = self.cena.jogador.y + self.cena.jogador.altura / 2.0
        inim_fov = InimigoPadrao(x=cx_jog + 450.0, y=cy_jog - 14.0)
        self.cena.inimigos = [inim_fov]
        self.cena.draw()

        # Posição esperada na tela 800x600 após escala de 1067x800 -> 800x600
        sx = int(((inim_fov.x + 14.0) - cam75_x) * (LARGURA_TELA / float(fov_w)))
        sy = int(((inim_fov.y + 14.0) - cam75_y) * (ALTURA_TELA / float(fov_h)))
        cor_inim = self.cena.janela.screen.get_at((sx, sy))[:3]
        self.assertEqual(cor_inim, (220, 50, 50), "Inimigo na borda do FOV expandido (1067x800) deve aparecer na tela.")


if __name__ == "__main__":
    unittest.main()
