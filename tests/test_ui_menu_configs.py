"""
Testes Unitários do Menu de Configurações (Phase 4 UI / R2) — Protocolo: Batata
SSOT: CONFIGURACOES.md, s5.md
Valida:
- Abertura e fechamento via botão de engrenagem, tecla ESC e tecla C.
- Navegação entre Aba 1 (Gameplay) e Aba 2 (Sistema & Acessibilidade).
- Imutabilidade de configurações travadas / bloqueadas.
- Alteração dinâmica e recálculo de modificadores em tempo real para configurações desbloqueadas.
- Ajuste de sliders de volume (Master, Música, SFX), Filtro Daltônico (S4) e Escala Global (S5).
- Persistência e carregamento de estado em save.json.
- Integração com GameplayScene e MenuPrincipalScene.
"""

import os
import sys
import json
import unittest
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.menu_configs import MenuConfigs
from src.cenas.gameplay import GameplayScene
from src.cenas.menu_principal import MenuPrincipalScene


class TestMenuConfigsLogicAndNavigation(unittest.TestCase):
    """Testa a máquina de estados, navegação de abas e regras de bloqueio do MenuConfigs."""

    def setUp(self):
        self.gerenciador = GerenciadorConfiguracoes()
        self.menu = MenuConfigs(self.gerenciador, em_jogo=True)

    def test_initial_state_closed(self):
        """O menu deve iniciar fechado com a aba 0 (Gameplay) como padrão."""
        self.assertFalse(self.menu.ativo)
        self.assertEqual(self.menu.aba_atual, 0)

    def test_open_close_cycle(self):
        """Abertura e fechamento devem alterar o estado booleano corretamente."""
        self.menu.abrir()
        self.assertTrue(self.menu.ativo)
        self.menu.fechar()
        self.assertFalse(self.menu.ativo)

    def test_tab_switching(self):
        """Alternância entre abas de Gameplay (0) e Sistema (1)."""
        self.menu.abrir()
        self.menu.alternar_aba(1)
        self.assertEqual(self.menu.aba_atual, 1)

        self.menu.alternar_aba(0)
        self.assertEqual(self.menu.aba_atual, 0)

    def test_locked_configs_reject_modification(self):
        """Configurações travadas não devem permitir alteração de valor ou ciclo de opções."""
        # fps_cap inicia bloqueada
        self.assertFalse(self.gerenciador.is_desbloqueada("fps_cap"))
        self.assertEqual(self.gerenciador.obter_valor("fps_cap"), "60")

        # Tentativa de alterar pelo menu deve retornar False e manter o padrão neutro 60 FPS
        sucesso_alt = self.menu.alterar_valor_gameplay("fps_cap", "15")
        self.assertFalse(sucesso_alt)
        self.assertEqual(self.gerenciador.obter_valor("fps_cap"), "60")

        sucesso_ciclo = self.menu.ciclar_opcao_gameplay("fps_cap", 1)
        self.assertFalse(sucesso_ciclo)
        self.assertEqual(self.gerenciador.obter_valor("fps_cap"), "60")

    def test_unlocked_configs_modify_and_apply_in_real_time(self):
        """Configurações desbloqueadas devem ser alteradas livremente e impactar os modificadores."""
        self.gerenciador.desbloquear_config("fps_cap")
        self.assertTrue(self.gerenciador.is_desbloqueada("fps_cap"))

        # Altera valor para 15 FPS
        self.assertTrue(self.menu.alterar_valor_gameplay("fps_cap", "15"))
        self.assertEqual(self.gerenciador.obter_valor("fps_cap"), "15")

        mods = self.gerenciador.obter_modificadores()
        self.assertAlmostEqual(mods.dano_inimigos_mult, 0.7225)
        self.assertAlmostEqual(mods.vel_inimigos_mult, 0.81)

        # Cicla opção para a próxima (deve voltar para 60)
        self.menu.ciclar_opcao_gameplay("fps_cap", 1)
        self.assertEqual(self.gerenciador.obter_valor("fps_cap"), "60")

    def test_system_settings_sliders_and_selectors(self):
        """Valida ajustes na aba de sistema (3 sliders de áudio: master, música e SFX)."""
        # Volume Master
        self.menu.definir_volume_sistema("volume_master", 75)
        self.assertEqual(self.gerenciador.obter_valor("volume_master"), 75)

        # Volume Música
        self.menu.definir_volume_sistema("volume_musica", 40)
        self.assertEqual(self.gerenciador.obter_valor("volume_musica"), 40)

        # Volume SFX
        self.menu.definir_volume_sistema("volume_sfx", 90)
        self.assertEqual(self.gerenciador.obter_valor("volume_sfx"), 90)

        # Stubs S4/S5 removidos devem ser rejeitados
        self.assertFalse(self.gerenciador.definir_valor("filtro_daltonico", "protanopia"))
        self.assertIsNone(self.gerenciador.obter_valor("filtro_daltonico"))
        self.assertFalse(self.gerenciador.definir_valor("escala_global", "150%"))
        self.assertIsNone(self.gerenciador.obter_valor("escala_global"))


class TestMenuConfigsIntegrationAndPersistence(unittest.TestCase):
    """Testa a integração em GameplayScene, MenuPrincipalScene e persistência em disco."""

    def test_gameplay_scene_menu_integration(self):
        """Valida que GameplayScene inicializa o menu, abre com 'C'/ESC e pausa o jogo."""
        cena = GameplayScene()
        self.assertFalse(cena.menu_configs.ativo)
        self.assertFalse(cena.pausado)

        # Teclado mock com tecla 'c'
        mock_teclado = MagicMock()
        mock_teclado.key_down.side_effect = lambda k: k in ("c", "C")
        mock_teclado.key_pressed.side_effect = lambda k: False
        cena.teclado = mock_teclado

        cena.loop()
        self.assertTrue(cena.menu_configs.ativo, "Tecla 'C' deve abrir o Menu de Configurações")
        self.assertTrue(cena.pausado, "Jogo deve pausar com Menu de Configurações aberto")

    def test_menu_principal_scene_integration(self):
        """Valida que MenuPrincipalScene suporta abrir o Menu de Configurações."""
        menu_scene = MenuPrincipalScene()
        self.assertFalse(menu_scene.menu_configs.ativo)

        # Simula seleção de Configurações (opção índice 1) com ENTER
        mock_teclado = MagicMock()
        mock_teclado.key_down.side_effect = lambda k: k == "ENTER"
        mock_teclado.key_pressed.side_effect = lambda k: False
        menu_scene.teclado = mock_teclado
        menu_scene.opcao_selecionada = 1

        menu_scene.loop()
        self.assertTrue(menu_scene.menu_configs.ativo, "Opção Configurações deve abrir o MenuConfigs")

    def test_persistence_save_and_load(self):
        """Verifica serialização e restauração do arquivo de save."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            manager1 = GerenciadorConfiguracoes()
            manager1.desbloquear_config("vsync")
            manager1.definir_valor("vsync", "desligado")
            manager1.definir_valor("volume_master", 65)

            # Salva
            manager1.salvar_arquivo(tmp_path)
            self.assertTrue(os.path.isfile(tmp_path))

            # Carrega em novo gerenciador
            manager2 = GerenciadorConfiguracoes()
            manager2.carregar_arquivo(tmp_path)

            self.assertTrue(manager2.is_desbloqueada("vsync"))
            self.assertEqual(manager2.obter_valor("vsync"), "desligado")
            self.assertEqual(manager2.obter_valor("volume_master"), 65)
        finally:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)

    def test_draw_surface_rendering_headless(self):
        """Verifica renderização visual em ambas as abas sem falhas."""
        screen = pygame.Surface((800, 600))
        gerenciador = GerenciadorConfiguracoes()
        menu = MenuConfigs(gerenciador, em_jogo=True)
        menu.abrir()

        # Desenha Aba 0
        menu.alternar_aba(0)
        menu.draw(screen)

        # Desenha Aba 1
        menu.alternar_aba(1)
        menu.draw(screen)


if __name__ == "__main__":
    unittest.main()
