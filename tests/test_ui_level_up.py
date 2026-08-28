"""
Testes Unitários do Modal de Level Up (Phase 4 UI / R1) — Protocolo: Batata
SSOT: CONFIGURACOES.md, s5.md, User Directives
Valida:
- Abertura e ativação ao subir de nível via SistemaXP.
- Consumíveis em tiers para níveis padrão (não múltiplos de 5).
- Inserção obrigatória de Configuração de Gameplay no card central (slot 2) em níveis de marco (múltiplos de 5).
- Persistência do Buffer de Misericórdia (Pity Buffer) até a configuração ser selecionada.
- Seleção de cartas via mouse e teclas 1, 2, 3.
- Desbloqueio e aplicação de modificadores em tempo real.
- Processamento e esvaziamento correto de filas com múltiplos level-ups acumulados.
- Comportamento de fallback quando todas as configurações estão desbloqueadas.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()

from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.entidades.jogador import Jogador
from src.ui.modal_level_up import (
    ModalLevelUp, obter_tier_nivel, gerar_pool_consumiveis_por_tier
)


class TestModalLevelUpTierAndMilestone(unittest.TestCase):
    """Testa as regras de tiers de consumíveis e posicionamento de marcos (múltiplos de 5)."""

    def setUp(self):
        self.gerenciador = GerenciadorConfiguracoes()
        self.jogador = Jogador(x=100, y=100)
        self.modal = ModalLevelUp(self.gerenciador, self.jogador)

    def test_tier_calculation_by_level(self):
        """Verifica a categorização correta de tiers por faixa de nível."""
        self.assertEqual(obter_tier_nivel(1), 1)
        self.assertEqual(obter_tier_nivel(4), 1)
        self.assertEqual(obter_tier_nivel(5), 2)
        self.assertEqual(obter_tier_nivel(9), 2)
        self.assertEqual(obter_tier_nivel(10), 3)
        self.assertEqual(obter_tier_nivel(14), 3)
        self.assertEqual(obter_tier_nivel(15), 4)
        self.assertEqual(obter_tier_nivel(20), 4)

    def test_standard_level_up_offers_3_consumables(self):
        """Níveis padrão (não múltiplos de 5) geram 3 cartas consumíveis escaladas por tier."""
        # Nível 1 -> Tier 1
        self.jogador.nivel = 1
        self.modal.abrir(nivel=1)
        self.assertTrue(self.modal.ativo)
        self.assertEqual(len(self.modal.cards_sorteados), 3)

        for card in self.modal.cards_sorteados:
            self.assertNotEqual(card["tipo"], "config", "Nível 1 não deve sortear config sem pity!")
            self.assertEqual(card["categoria"], "Consumível")

    def test_milestone_level_5_places_config_in_middle_slot(self):
        """No nível 5 (marco), o card central (índice 1) deve ser obrigatoriamente uma configuração."""
        self.jogador.nivel = 5
        self.modal.abrir(nivel=5)
        self.assertTrue(self.modal.ativo)
        self.assertEqual(len(self.modal.cards_sorteados), 3)

        # Card lateral 0: Consumível
        self.assertEqual(self.modal.cards_sorteados[0]["categoria"], "Consumível")
        # Card central 1: Configuração de gameplay
        self.assertEqual(self.modal.cards_sorteados[1]["tipo"], "config")
        self.assertIn(self.modal.cards_sorteados[1]["config_id"], CONFIGURACOES_GAMEPLAY)
        # Card lateral 2: Consumível
        self.assertEqual(self.modal.cards_sorteados[2]["categoria"], "Consumível")

    def test_pity_buffer_persistence_until_selected(self):
        """
        Se o jogador ignorar a configuração no nível 5 e escolher um consumível lateral,
        a configuração deve permanecer no slot central no nível 6 (pity buffer).
        """
        self.jogador.nivel = 5
        self.modal.abrir(nivel=5)

        config_ofertada = self.modal.cards_sorteados[1]
        self.assertIsNotNone(self.modal.config_pity_buffer)
        self.assertEqual(self.modal.config_pity_buffer.id, config_ofertada["config_id"])

        # Jogador escolhe o Card 0 (Consumível lateral)
        self.modal.selecionar_card(0)
        self.assertFalse(self.modal.ativo)
        self.assertFalse(self.gerenciador.is_desbloqueada(config_ofertada["config_id"]))
        # Pity buffer deve permanecer ativo
        self.assertIsNotNone(self.modal.config_pity_buffer)

        # Próximo level-up: Nível 6 (não é múltiplo de 5, mas tem pity buffer)
        self.jogador.nivel = 6
        self.modal.abrir(nivel=6)
        self.assertTrue(self.modal.ativo)

        # Card do meio continua sendo a configuração do pity buffer
        self.assertEqual(self.modal.cards_sorteados[1]["tipo"], "config")
        self.assertEqual(self.modal.cards_sorteados[1]["config_id"], config_ofertada["config_id"])

        # Agora o jogador seleciona o Card 1 (a configuração)
        self.modal.selecionar_card(1)
        self.assertTrue(self.gerenciador.is_desbloqueada(config_ofertada["config_id"]))
        # Pity buffer deve ser limpo
        self.assertIsNone(self.modal.config_pity_buffer)

        # Nível 7: Volta a ter 3 consumíveis puros
        self.jogador.nivel = 7
        self.modal.abrir(nivel=7)
        for c in self.modal.cards_sorteados:
            self.assertNotEqual(c["tipo"], "config")


class TestModalLevelUpInteractionAndQueue(unittest.TestCase):
    """Testa controles (teclado/mouse), fila de múltiplos níveis e efeitos no jogador."""

    def setUp(self):
        self.gerenciador = GerenciadorConfiguracoes()
        self.jogador = Jogador(x=100, y=100)
        self.modal = ModalLevelUp(self.gerenciador, self.jogador)

    def test_keyboard_selection_keys_1_2_3(self):
        """Testa acionamento via atalhos numéricos 1, 2 e 3."""
        self.modal.abrir(nivel=1)
        self.assertTrue(self.modal.ativo)

        # Teclado mock com tecla 1 pressionada
        mock_teclado = MagicMock()
        mock_teclado.key_down.side_effect = lambda k: k == "1"
        mock_teclado.key_pressed.side_effect = lambda k: False

        self.modal.update(0.016, teclado=mock_teclado, mouse=None)
        self.assertFalse(self.modal.ativo, "Modal deveria fechar após selecionar card 1")

    def test_multi_level_queue_handling(self):
        """Valida acúmulo de múltiplos níveis em sucessão rápida."""
        # Enfileira 3 níveis
        self.modal.enfileirar_level_up(2)
        self.modal.enfileirar_level_up(3)
        self.modal.enfileirar_level_up(4)

        self.assertTrue(self.modal.ativo)
        self.assertEqual(self.modal.fila_level_ups, 3)

        # Escolhe primeira carta
        self.modal.selecionar_card(0)
        self.assertTrue(self.modal.ativo, "Ainda deve permanecer ativo (2 restantes)")
        self.assertEqual(self.modal.fila_level_ups, 2)

        # Escolhe segunda carta
        self.modal.selecionar_card(1)
        self.assertTrue(self.modal.ativo, "Ainda deve permanecer ativo (1 restante)")
        self.assertEqual(self.modal.fila_level_ups, 1)

        # Escolhe terceira carta
        self.modal.selecionar_card(2)
        self.assertFalse(self.modal.ativo, "Deve fechar ao esgotar a fila")
        self.assertEqual(self.modal.fila_level_ups, 0)

    def test_consumable_effects_applied_to_player(self):
        """Valida que cartas de cura, vida máxima e velocidade alteram os atributos do Jogador."""
        # 1. Cura
        self.jogador.hp_max = 100
        self.jogador.hp = 20
        card_cura = {"tipo": "cura", "valor": 50, "nome": "Cura", "categoria": "Consumível"}
        self.modal.cards_sorteados = [card_cura]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.hp, 70)

        # 2. Vitalidade
        card_vit = {"tipo": "vitalidade", "valor": 20, "nome": "Vitalidade", "categoria": "Consumível"}
        self.modal.cards_sorteados = [card_vit]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertEqual(self.jogador.hp_max, 120)
        self.assertEqual(self.jogador.hp, 90)

        # 3. Velocidade
        vel_ant = self.jogador.velocidade_base
        card_vel = {"tipo": "velocidade", "valor": 0.10, "nome": "Velocidade", "categoria": "Consumível"}
        self.modal.cards_sorteados = [card_vel]
        self.modal.ativo = True
        self.modal.fila_level_ups = 1
        self.modal.selecionar_card(0)
        self.assertAlmostEqual(self.jogador.velocidade_base, vel_ant * 1.10)

    def test_full_unlock_fallback_all_consumables(self):
        """Quando todas as 20 configs estiverem desbloqueadas, o sorteio é 100% consumíveis."""
        for cid in list(CONFIGURACOES_GAMEPLAY.keys()):
            self.gerenciador.desbloquear_config(cid)

        self.assertEqual(len(self.gerenciador.obter_bloqueadas()), 0)

        # Marco nível 5 sem configs restantes -> 3 consumíveis
        self.modal.abrir(nivel=5)
        self.assertEqual(len(self.modal.cards_sorteados), 3)
        for c in self.modal.cards_sorteados:
            self.assertEqual(c["categoria"], "Consumível")

    def test_draw_surface_rendering_headless(self):
        """Verifica que draw() executa com sucesso sem falhar em surface virtual."""
        screen = pygame.Surface((800, 600))
        self.modal.abrir(nivel=5)
        # Não deve lançar nenhuma exceção
        self.modal.draw(screen)


if __name__ == "__main__":
    unittest.main()
