"""
Testes de regressão para fontes embutidas (OPPO Sans 4.0 e JetBrains Mono NL)
e fallback seguro de SysFont em ambientes Windows 11 sem fontes Linux.
"""

import os
import unittest
import warnings
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.utils import fontes as mod_fontes
from src.ui.hud import HUD
from src.ui.menu_conquistas import MenuConquistas
from src.sistemas.config_sistema import GerenciadorConfiguracoes


class TestFontesEmbutidasEEscala(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

    def setUp(self):
        mod_fontes.limpar_cache_fontes()

    def tearDown(self):
        mod_fontes.limpar_cache_fontes()

    def test_arquivos_ttf_embutidos_existem(self):
        self.assertTrue(os.path.isfile(mod_fontes.ARQUIVO_FONTE_SANS), "OPPO_Sans_4.0.ttf ausente em assets/fonts/")
        self.assertTrue(os.path.isfile(mod_fontes.ARQUIVO_FONTE_MONO_REGULAR), "JetBrainsMonoNL-Regular.ttf ausente")
        self.assertTrue(os.path.isfile(mod_fontes.ARQUIVO_FONTE_MONO_BOLD), "JetBrainsMonoNL-Bold.ttf ausente")

    def test_fontes_embutidas_carregam_com_metricas_cheias_sem_fontes_sistema(self):
        """Mesmo sem nenhuma fonte de sistema disponível, deve carregar os TTFs embutidos com altura plena."""
        f_default = pygame.font.Font(None, 16)
        with mock.patch("pygame.font.match_font", return_value=None), \
             warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            f_sans = mod_fontes.carregar_fonte_sans(16, bold=True)
            f_mono_reg = mod_fontes.carregar_fonte_mono(16, bold=False)
            f_mono_bold = mod_fontes.carregar_fonte_mono(16, bold=True)

        # Altura real muito superior ao fallback minúsculo freesansbold.ttf (h=11 em sz=16)
        self.assertGreater(f_sans.get_height(), f_default.get_height() + 4)
        self.assertGreater(f_mono_reg.get_height(), f_default.get_height() + 6)
        self.assertGreater(f_mono_bold.get_height(), f_default.get_height() + 6)
        # Nenhum UserWarning de fonte de sistema ausente
        self.assertEqual([w for w in avisos if issubclass(w.category, UserWarning)], [])

    def test_fallback_sysfont_alcanca_fontes_windows_quando_ttf_ausente(self):
        """
        Regressão do bug original: se os TTFs embutidos faltarem e só existirem fontes Windows
        (arial/consolas), match_font() garante que não cai em freesansbold.ttf na 1ª fonte Linux ausente.
        """
        def fake_match(nome, bold=False, italic=False):
            n = str(nome).lower().replace(" ", "")
            if n in ("arial", "consolas"):
                return f"/fake/windows/{n}.ttf"
            return None

        chamadas_sysfont: list[str] = []

        def fake_sysfont(nome, sz, bold=False, italic=False):
            chamadas_sysfont.append(str(nome).lower())
            return pygame.font.Font(None, sz)

        with mock.patch.object(mod_fontes, "ARQUIVO_FONTE_SANS", "/inexistente/sans.ttf"), \
             mock.patch.object(mod_fontes, "ARQUIVO_FONTE_MONO_REGULAR", "/inexistente/mono.ttf"), \
             mock.patch.object(mod_fontes, "ARQUIVO_FONTE_MONO_BOLD", "/inexistente/mono_bold.ttf"), \
             mock.patch("pygame.font.match_font", side_effect=fake_match), \
             mock.patch("pygame.font.SysFont", side_effect=fake_sysfont):
            mod_fontes.carregar_fonte_sans(16, bold=True)
            mod_fontes.carregar_fonte_mono(16, bold=True)

        self.assertEqual(chamadas_sysfont, ["arial", "consolas"])

    def test_cache_fontes_reutiliza_mesma_instancia(self):
        f1 = mod_fontes.carregar_fonte_sans(14, bold=True, italic=False)
        f2 = mod_fontes.carregar_fonte_sans(14, bold=True, italic=False)
        m1 = mod_fontes.carregar_fonte_mono(12, bold=True)
        m2 = mod_fontes.carregar_fonte_mono(12, bold=True)
        self.assertIs(f1, f2)
        self.assertIs(m1, m2)

    def test_hud_e_menu_conquistas_sem_fallback_para_default_em_win11_simulado(self):
        """HUD e MenuConquistas devem usar fontes embutidas sem emitir UserWarning de SysFont."""
        f_default = pygame.font.Font(None, 16)
        with mock.patch("pygame.font.match_font", return_value=None), \
             warnings.catch_warnings(record=True) as avisos:
            warnings.simplefilter("always")
            hud = HUD()
            f_hud_sans = hud._obter_fonte_nativa("sans", 16, bold=True, scale=1.0)
            f_hud_mono = hud._obter_fonte_nativa("mono", 16, bold=True, scale=1.0)

            cfg = GerenciadorConfiguracoes()
            menu = MenuConquistas(cfg)
            f_mc_sans = menu._fonte("sans", 16, bold=True)
            f_mc_mono = menu._fonte("mono", 16, bold=True)

        self.assertGreater(f_hud_sans.get_height(), f_default.get_height() + 4)
        self.assertGreater(f_hud_mono.get_height(), f_default.get_height() + 6)
        self.assertGreater(f_mc_sans.get_height(), f_default.get_height() + 4)
        self.assertGreater(f_mc_mono.get_height(), f_default.get_height() + 6)
        self.assertEqual([w for w in avisos if issubclass(w.category, UserWarning)], [])


if __name__ == "__main__":
    unittest.main()
