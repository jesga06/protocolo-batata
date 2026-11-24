import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_combo import SistemaCombo
from src.ui.hud import HUD
from src.ui.menu_configs import MenuConfigs
from src.ui.menu_conquistas import MenuConquistas
from src.utils.pixel_art_sprites import gerar_assets_v2, obter_icone_config, obter_sprite_arma


class TestUIRenderV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.init()
        pygame.font.init()

    def setUp(self):
        self.screen = pygame.Surface((1280, 720))

    def test_01_pixel_art_sprites_and_8_pngs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gerados = gerar_assets_v2(tmpdir)
            self.assertEqual(len(gerados), 8)
            for caminho in gerados:
                self.assertTrue(os.path.isfile(caminho), f"PNG ausente: {caminho}")
                self.assertGreater(os.path.getsize(caminho), 0)
                if "icon_" in caminho:
                    surf = pygame.image.load(caminho)
                    self.assertEqual(surf.get_size(), (32, 32))

        for arma_id in ("chave_manutencao", "bastao_choque", "smg_compacta", "rifle_arco", "lanca_chamas"):
            surf = obter_sprite_arma(arma_id, 24, 16)
            self.assertEqual(surf.get_size(), (24, 16))
        for cid in ("dash_protocolo", "dash_rastro", "garbage_collector", "latencia_ping", "modo_wireframe"):
            surf = obter_icone_config(cid, 32)
            self.assertEqual(surf.get_size(), (32, 32))

    def test_02_hud_pins_combo_calor_e_ocultacao(self):
        hud = HUD()
        resumo = [
            {"id": "mestre_chave_inglesa", "nome": "Mestre Chave", "atual": 5, "meta": 15, "progresso": 0.33, "concluida": False},
            {"id": "depurador_escritorio", "nome": "Depurador", "atual": 100, "meta": 100, "progresso": 1.0, "concluida": True},
        ]
        # Renderiza visível e oculto sem exceções
        hud.desenhar_pins_conquistas(self.screen, resumo, visivel=True)
        hud.desenhar_pins_conquistas(self.screen, resumo, visivel=False)

        combo = SistemaCombo()
        combo.definir_modo_estilo(True)
        for i in range(1, 15):
            combo.registrar_parry(i)
        self.assertEqual(combo.rank, "S")
        hud.desenhar_indicador_combo(self.screen, combo, visivel=True)
        hud.desenhar_indicador_combo(self.screen, combo, visivel=False)

        arma_smg = SimpleNamespace(usa_calor=True, calor_atual=80.0, superaquecida=False, em_zona_ideal=True)
        hud.desenhar_barra_calor_in_world(self.screen, 100, 100, 34, arma_smg)

        efeito_gc = SimpleNamespace(disparos_travados=False, ram_progresso=0.65)
        hud.desenhar_barra_ram_gc(self.screen, efeito_gc, visivel=True)

    def test_03_menu_conquistas_firmware_editavel_vs_somente_leitura(self):
        cfg = GerenciadorConfiguracoes()
        sc = cfg.sistema_conquistas
        # Desbloqueia 1 chip para teste
        sc.recompensas["modificador_run"].add("gatilho_duplo")

        with patch.object(cfg, "salvar_arquivo", return_value=True) as mock_save:
            menu_fora = MenuConquistas(cfg, sc, em_jogo=False)
            menu_fora.abrir(aba=1)
            self.assertTrue(menu_fora.tentar_alternar_firmware("gatilho_duplo"))
            self.assertIn("gatilho_duplo", sc.modificadores_equipados)
            self.assertGreaterEqual(mock_save.call_count, 1)

            menu_pausa = MenuConquistas(cfg, sc, em_jogo=True)
            menu_pausa.abrir(aba=1)
            self.assertFalse(menu_pausa.tentar_alternar_firmware("gatilho_duplo"))
            # Continua equipado (somente leitura na pausa)
            self.assertIn("gatilho_duplo", sc.modificadores_equipados)

        # Pins 0..3
        self.assertTrue(menu_fora.tentar_alternar_fixada("depurador_escritorio"))
        self.assertIn("depurador_escritorio", sc.fixadas)

    def test_04_menu_configs_28_e_conflitos(self):
        self.assertEqual(len(CONFIGURACOES_GAMEPLAY), 28)
        cfg = GerenciadorConfiguracoes()
        cfg.desbloquear_config("dash_protocolo", via_conquista=True)
        cfg.desbloquear_config("dash_rastro", via_conquista=True)
        menu = MenuConfigs(cfg, em_jogo=False)
        menu.abrir()
        menu.draw(self.screen)

        # Força conflito mútuo via alterar_valor_gameplay (se configurado) ou verifica chamada
        with patch.object(cfg, "definir_valor_com_conflitos", return_value=(True, [("dash_rastro", "padrao")])) as mock_def:
            ok = menu.alterar_valor_gameplay("dash_protocolo", "teleporte_buffer")
            self.assertTrue(ok)
            mock_def.assert_called_once_with("dash_protocolo", "teleporte_buffer")
            self.assertGreater(menu._toast_conflito_timer, 0.0)
            self.assertIn("CONFLITO", menu._toast_conflito)

    def test_05_menu_principal_loadout_e_anti_alocacao_fonte(self):
        from src.cenas.menu_principal import MenuPrincipalScene
        from src.cenas.gameplay_render import GameplayRenderMixin

        # MenuPrincipalScene pode precisar de janela dummy
        class _DummyMixin(GameplayRenderMixin):
            pass

        dummy = _DummyMixin()
        r_cont, r_menu = dummy._obter_rects_overlay_pausa()
        self.assertIsInstance(r_cont, pygame.Rect)
        self.assertIsInstance(r_menu, pygame.Rect)
        r_conq = dummy._obter_rect_btn_conquistas_pausa()
        self.assertIsInstance(r_conq, pygame.Rect)

        cfg = GerenciadorConfiguracoes()
        sc = cfg.sistema_conquistas
        # Sem 15 parries, SMG bloqueada
        self.assertFalse(sc.possui_recompensa("arma", "smg_compacta"))

        # Testa anti-alocação de fonte em HUD e MenuConquistas durante draw()
        hud = HUD()
        menu_conq = MenuConquistas(cfg, sc, em_jogo=False)
        menu_conq.abrir(aba=0)
        combo = SistemaCombo()
        combo.registrar_parry(1)
        resumo = sc.obter_resumo_fixadas()

        # Primeira passagem aquece caches
        hud.desenhar_pins_conquistas(self.screen, resumo, visivel=True)
        hud.desenhar_indicador_combo(self.screen, combo, visivel=True)
        menu_conq.draw(self.screen)

        with patch("pygame.font.Font", side_effect=AssertionError("Font alocada em draw()!")), \
             patch("pygame.font.SysFont", side_effect=AssertionError("SysFont alocada em draw()!")):
            hud.desenhar_pins_conquistas(self.screen, resumo, visivel=True)
            hud.desenhar_indicador_combo(self.screen, combo, visivel=True)
            menu_conq.draw(self.screen)

        # Valida troca de loadout no MenuPrincipalScene
        with patch.object(MenuPrincipalScene, "__init__", lambda s: None):
            cena = MenuPrincipalScene()
            cena.gerenciador_config = cfg
            with patch.object(cfg, "salvar_arquivo", return_value=True):
                self.assertFalse(cena.alternar_loadout_slot2())
                sc.registrar_evento("parry", 15)
                self.assertTrue(sc.possui_recompensa("arma", "smg_compacta"))
                self.assertTrue(cena.alternar_loadout_slot2())
                self.assertEqual(cfg.loadout["slot2"], "smg_compacta")


if __name__ == "__main__":
    unittest.main()
