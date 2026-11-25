import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_conquistas import SistemaConquistas
from src.ui.banner_dicas import DICAS_JOGO
from src.ui.hud import HUD, formatar_recompensas_conquista
from src.ui.menu_configs import MenuConfigs
from src.ui.menu_conquistas import MenuConquistas
from src.ui.menu_debug import MenuDebug
from src.utils.pixel_art_sprites import obter_sprite_arma


class _MockMousePPlay:
    def __init__(self, pos=(0, 0), down=False):
        self._pos = pos
        self._down = down

    def get_position(self):
        return self._pos

    def button_down(self, btn):
        return btn == 1 and self._down


class TestPlaytestFixesUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.font.init()

    def setUp(self):
        self.screen = pygame.Surface((1280, 720))

    def test_01_pipe_wrench_and_shock_baton_sprites_and_pngs(self):
        s_melee = obter_sprite_arma("arma_melee", 36, 36)
        s_baton = obter_sprite_arma("bastao_choque", 36, 36)
        self.assertEqual(s_melee.get_size(), (36, 36))
        self.assertEqual(s_baton.get_size(), (36, 36))
        self.assertNotEqual(
            pygame.image.tobytes(s_melee, "RGBA"),
            pygame.image.tobytes(s_baton, "RGBA"),
        )
        self.assertTrue(os.path.isfile("assets/sprites/armas/arma_melee.png"))
        self.assertTrue(os.path.isfile("assets/sprites/armas/arma_bastao_choque.png"))
        png_melee = pygame.image.load("assets/sprites/armas/arma_melee.png")
        png_baton = pygame.image.load("assets/sprites/armas/arma_bastao_choque.png")
        self.assertNotEqual(
            pygame.image.tobytes(png_melee, "RGBA"),
            pygame.image.tobytes(png_baton, "RGBA"),
        )

    def test_02_hud_pinned_achievements_dynamic_milestone_and_zero_font_alloc(self):
        hud = HUD()
        resumo_m1 = [
            {
                "id": "mestre_chave_inglesa",
                "nome": "Mestre da Chave Inglesa",
                "atual": 5,
                "meta": 15,
                "progresso": 5 / 15,
                "concluida": False,
            }
        ]
        nome1, recomp1, acao1 = hud._resolver_detalhes_pin(resumo_m1[0])
        self.assertEqual(nome1, "Mestre da Chave Inglesa")
        self.assertIn("Dash", recomp1)
        self.assertIn("SMG Compacta", recomp1)
        self.assertTrue(len(acao1) > 5)

        # Quando milestone 1 (15) é concluído, meta avança para 50 -> recompensa muda dinamicamente!
        resumo_m2 = [
            {
                "id": "mestre_chave_inglesa",
                "nome": "Mestre da Chave Inglesa",
                "atual": 16,
                "meta": 50,
                "progresso": 16 / 50,
                "concluida": False,
            }
        ]
        _, recomp2, _ = hud._resolver_detalhes_pin(resumo_m2[0])
        self.assertIn("Troféu", recomp2)

        resumo_oc = {
            "id": "primeiro_overclock_sujo",
            "nome": "Primeiro Overclock Sujo",
            "atual": 0,
            "meta": 1,
            "progresso": 0.0,
            "concluida": False,
        }
        _, recomp_oc, _ = hud._resolver_detalhes_pin(resumo_oc)
        self.assertIn("Gatilho Duplo", recomp_oc)

        with patch("pygame.font.SysFont", side_effect=AssertionError("SysFont não deve ser chamado por frame!")):
            hud.desenhar_pins_conquistas(self.screen, resumo_m1, visivel=True)
            hud.desenhar_pins_conquistas(self.screen, resumo_m2, visivel=True)

    def test_03_menu_conquistas_mouse_clicks_and_rewards(self):
        cfg = GerenciadorConfiguracoes()
        sys_conq = cfg.sistema_conquistas
        sys_conq.recompensas["modificador_run"].add("gatilho_duplo")
        menu = MenuConquistas(cfg, sys_conq, em_jogo=False)
        menu.abrir(aba=0)
        menu.cooldown_input = 0.0
        menu.draw(self.screen)

        # Clicar na aba FIRMWARE usando API PPlay (button_down + get_position)
        _aba0, aba1, btn_fechar = menu._obter_rects_topo()
        menu.update(0.016, mouse=_MockMousePPlay(aba1.center, down=True))
        self.assertEqual(menu.aba_atual, 1)

        # Voltar para aba CONQUISTAS
        menu.update(0.016, mouse=_MockMousePPlay(_aba0.center, down=True))
        self.assertEqual(menu.aba_atual, 0)

        # Clicar no botão FIXAR do primeiro card
        btn_pin = pygame.Rect(menu.offset_x + menu.largura_modal - 134, menu.offset_y + 134 + 28, 96, 28)
        pins_antes = len(sys_conq.fixadas)
        menu.update(0.016, mouse=_MockMousePPlay(btn_pin.center, down=True))
        self.assertNotEqual(len(sys_conq.fixadas), pins_antes)

        # Clicar em Fechar
        menu.update(0.016, mouse=_MockMousePPlay(btn_fechar.center, down=True))
        self.assertFalse(menu.ativo)

        # Recompensa formatada legível
        txt = formatar_recompensas_conquista([("habilidade", "dash"), ("arma", "smg_compacta")])
        self.assertIn("Dash", txt)
        self.assertIn("SMG Compacta", txt)

    def test_04_menu_configs_mouse_clicks_and_visibility(self):
        cfg = GerenciadorConfiguracoes()
        menu = MenuConfigs(cfg, em_jogo=False)
        menu.abrir()
        menu.cooldown_input = 0.0
        menu.draw(self.screen)

        aba0, aba1, btn_fechar, _ = menu._obter_rects_barra_topo()
        menu.update(0.016, mouse=_MockMousePPlay(aba1.center, down=True))
        self.assertEqual(menu.aba_atual, 1)

        menu.update(0.016, mouse=_MockMousePPlay(aba0.center, down=True))
        self.assertEqual(menu.aba_atual, 0)

        menu.update(0.016, mouse=_MockMousePPlay(btn_fechar.center, down=True))
        self.assertFalse(menu.ativo)

    def test_05_menu_debug_v2_options(self):
        cfg = GerenciadorConfiguracoes()
        cena = SimpleNamespace(
            config_sistema=cfg,
            sistema_conquistas=cfg.sistema_conquistas,
            jogador=SimpleNamespace(x=100.0, y=100.0, armas=[None, None], slot1_id="chave_manutencao", slot2_id="pistola"),
            inimigos=[],
        )
        dbg = MenuDebug(cena_gameplay=cena)
        armas_ids = [c for _, c in dbg.opcoes_armas]
        for expected in ("BastaoChoque", "SMGCompacta", "RifleArco", "LancaChamas"):
            self.assertIn(expected, armas_ids)

        inim_ids = [t for _, t in dbg.opcoes_inimigos]
        self.assertIn("impressora", inim_ids)
        self.assertIn("ninja", inim_ids)

        # Destravar todas as 29 configs
        dbg.indice_foco = 11
        dbg._executar_acao_selecionada()
        self.assertTrue(all(cfg.is_desbloqueada(cid) for cid in CONFIGURACOES_GAMEPLAY))
        self.assertEqual(len(CONFIGURACOES_GAMEPLAY), 29)

        # Destravar todas conquistas & firmware
        dbg.indice_foco = 17
        dbg._executar_acao_selecionada()
        self.assertEqual(cfg.sistema_conquistas.slots_firmware_max, 3)
        self.assertTrue(cfg.sistema_conquistas.possui_recompensa("arma", "bastao_choque"))

    def test_06_banner_dicas_and_tutorial_and_first_time_popup(self):
        junto = " ".join(DICAS_JOGO).lower()
        self.assertNotIn("50 parries", junto)
        self.assertNotIn("23 configs", junto)
        self.assertIn("15 parries", junto)
        self.assertIn("29 configurações", junto)

        from src.cenas.tutorial import TutorialScene
        tut = TutorialScene.__new__(TutorialScene)
        tut.tempo_acumulado = 0.0
        tut.pagina_atual = 0
        tut.total_paginas = 4
        tut.banner_dicas = None
        tut.janela = SimpleNamespace(screen=self.screen)
        for p in range(4):
            tut.pagina_atual = p
            tut.draw()

        from src.cenas.menu_principal import MenuPrincipalScene
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "save.json")
            with patch("src.cenas.menu_principal.SAVE_FILE_PATH", save_path):
                cena = MenuPrincipalScene.__new__(MenuPrincipalScene)
                cena.gerenciador_config = GerenciadorConfiguracoes()
                cena.mostrar_popup_tutorial = not bool(getattr(cena.gerenciador_config, "tutorial_visto", False))
                self.assertTrue(cena.mostrar_popup_tutorial)
                cena._confirmar_popup_tutorial(False)
                self.assertFalse(cena.mostrar_popup_tutorial)
                self.assertTrue(getattr(cena.gerenciador_config, "tutorial_visto", False))


if __name__ == "__main__":
    unittest.main()
