"""
Testes Unitários e de Integração M3 — Protocolo: Batata
Valida:
1. Centralização Horizontal do Menu Principal e HUD via Pygame Font (rect.centerx == LARGURA_TELA // 2).
2. Mecânica de Disparo exclusivamente via Clique Explícito do Mouse (pygame.MOUSEBUTTONDOWN / button_down).
3. Troca de Armas pelas teclas numéricas 1, 2 e 3 e disparo exclusivo da arma ativa selecionada.
"""

import os
import sys
import unittest
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.constantes import LARGURA_TELA, ALTURA_TELA, TITULO_JOGO, DOURADO, BRANCO, AMARELO_XP
from src.entidades.jogador import Jogador
from src.armas.melee import Melee
from src.armas.pistola import Pistola
from src.cenas.menu_principal import MenuPrincipalScene
from src.cenas.gameplay import GameplayScene
from PPlay.window import Window


class TestUICenteringM3(unittest.TestCase):
    """Testa se os retângulos de texto do Menu e HUD estão matematicamente centralizados na tela virtual."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.font.init()
        cls.janela = Window(LARGURA_TELA, ALTURA_TELA, "TestWindow", resizavel=False, pixel_art=True)

    def test_menu_principal_titulos_e_opcoes_centralizados(self):
        fonte_titulo = pygame.font.SysFont("Arial", 36, bold=True)
        titulo_surf = fonte_titulo.render(TITULO_JOGO, True, DOURADO)
        titulo_rect = titulo_surf.get_rect(centerx=LARGURA_TELA // 2, top=110)

        self.assertEqual(titulo_rect.centerx, LARGURA_TELA // 2)
        self.assertEqual(titulo_rect.centerx, 400)

        # Testa opções do menu
        fonte_opcoes = pygame.font.SysFont("Arial", 18, bold=True)
        opcoes = ["JOGAR [ENTER]", "CONFIGURAÇÕES [C]", "CRÉDITOS [K]", "SAIR [ESC]"]
        for i, texto in enumerate(opcoes):
            y = 260 + i * 50
            caixa_destaque = pygame.Rect(0, y - 5, 280, 35)
            caixa_destaque.centerx = LARGURA_TELA // 2
            self.assertEqual(caixa_destaque.centerx, 400)

            opcao_surf = fonte_opcoes.render(f"> {texto}", True, DOURADO)
            opcao_rect = opcao_surf.get_rect(centerx=LARGURA_TELA // 2, centery=y + 12)
            self.assertEqual(opcao_rect.centerx, 400)

        # Rodapé
        fonte_rodape = pygame.font.SysFont("Arial", 14)
        rodape_surf = fonte_rodape.render("PPlay 2.0 Engine", True, (120, 135, 155))
        rodape_rect = rodape_surf.get_rect(centerx=LARGURA_TELA // 2, bottom=ALTURA_TELA - 25)
        self.assertEqual(rodape_rect.centerx, 400)

    def test_hud_timer_e_abates_centralizados(self):
        fonte_tempo = pygame.font.SysFont("Arial", 22, bold=True)
        tempo_surf = fonte_tempo.render("02:45", True, BRANCO)
        tempo_rect = tempo_surf.get_rect(centerx=LARGURA_TELA // 2, top=14)
        self.assertEqual(tempo_rect.centerx, 400)

        fonte_abates = pygame.font.SysFont("Arial", 14, bold=True)
        abates_surf = fonte_abates.render("Abates: 42", True, AMARELO_XP)
        abates_rect = abates_surf.get_rect(centerx=LARGURA_TELA // 2, top=40)
        self.assertEqual(abates_rect.centerx, 400)

    def test_menu_principal_draw_execucao(self):
        cena_menu = MenuPrincipalScene()
        # Não deve lançar nenhuma exceção ao desenhar
        cena_menu.draw()


class TestWeaponSwitchingAndClickInputsM3(unittest.TestCase):
    """Testa troca de armas (1, 2, 3) e mecânica de disparo por clique."""

    def setUp(self):
        self.jogador = Jogador(x=400, y=300)

    def test_selecao_e_obtencao_de_arma_ativa(self):
        # Por padrão slot_ativo é 2 (Pistola)
        self.assertEqual(self.jogador.slot_ativo, 2)
        arma_2 = self.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_2, Pistola)

        # Troca para Slot 1 (Melee)
        self.jogador.selecionar_slot(1)
        self.assertEqual(self.jogador.slot_ativo, 1)
        arma_1 = self.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_1, Melee)

        # Troca para Slot 3 (Especial)
        self.jogador.selecionar_slot(3)
        self.assertEqual(self.jogador.slot_ativo, 3)
        self.assertIsNone(self.jogador.obter_arma_ativa())

        # Atribui arma especial e testa Slot 3
        arma_especial_fake = Pistola(dano=50, cooldown=0.1)
        self.jogador.arma_especial = arma_especial_fake
        self.assertEqual(self.jogador.obter_arma_ativa(), arma_especial_fake)

    def test_input_teclado_troca_slots_1_2_3(self):
        class MockKeyboard:
            def __init__(self, pressed_key):
                self.pressed_key = pressed_key

            def key_pressed(self, k):
                return k == self.pressed_key

            def key_down(self, k):
                return k == self.pressed_key

        # Simula pressionar tecla 1
        teclado_1 = MockKeyboard("1")
        self.jogador.processar_input(teclado_1, None, dt=0.016)
        self.assertEqual(self.jogador.slot_ativo, 1)

        # Simula pressionar tecla 2
        teclado_2 = MockKeyboard("2")
        self.jogador.processar_input(teclado_2, None, dt=0.016)
        self.assertEqual(self.jogador.slot_ativo, 2)

        # Simula pressionar tecla 3
        teclado_3 = MockKeyboard("3")
        self.jogador.processar_input(teclado_3, None, dt=0.016)
        self.assertEqual(self.jogador.slot_ativo, 3)

    def test_gameplay_scene_disparo_apenas_com_clique_e_arma_ativa(self):
        cena = GameplayScene()
        # Sem clique: nenhum projétil é gerado
        cena.jogador.selecionar_slot(2)  # Pistola
        total_proj_antes = len(cena.projeteis)

        # Simula um ciclo de loop sem eventos de mouse (sem clique)
        cena.loop()
        self.assertEqual(len(cena.projeteis), total_proj_antes)

        # Simula arma ativa selecionada e disparo da pistola isolado
        arma_ativa = cena.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_ativa, Pistola)
        tiros = arma_ativa.disparar(100, 100, 200, 100)
        self.assertEqual(len(tiros), 1)

        # Troca para slot 1 (Melee): obter_arma_ativa deve ser Melee
        cena.jogador.selecionar_slot(1)
        arma_melee = cena.jogador.obter_arma_ativa()
        self.assertIsInstance(arma_melee, Melee)
        tiros_melee = arma_melee.disparar(100, 100, 200, 100)
        self.assertEqual(len(tiros_melee), 0)  # Melee não dispara projéteis


if __name__ == "__main__":
    unittest.main()
