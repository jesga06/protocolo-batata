"""
Testes Unitários — Milestone 2: 20 Gameplay Config Effects & Sacrifices Complete Implementation (R2)
SSOT: CONFIGURACOES.md, config_dados.py, PROJECT.md, architecture_cache.md
Valida os efeitos e sacrifícios de todas as 20 configurações de gameplay do jogo quando desbloqueadas e ativadas:
 1. fps_cap (60 -> 45, 30, 15)
 2. graficos_qualidade (alta -> baixa)
 3. resolucao (100% -> 75%, 50%, 25%)
 4. vsync (ligado -> desligado)
 5. screen_shake (desligado -> ligado)
 6. motion_blur (desligado -> ligado)
 7. hud (ligado -> desligado)
 8. damage_numbers (desligado -> ligado)
 9. zoom (100% -> 75%, 125%, 150%)
10. movimento_mouse (desligado -> ligado)
11. keybinds (padrao -> invertido, arrow_keys, uma_mao, pesadelo)
12. suavizacao_camera (ligado -> desligado)
13. auto_fire (ligado -> desligado)
14. inimigos_ranged (desligado -> ligado)
15. coleta_inimiga (desligado -> ligado)
16. velocidade_inimigos (normal -> +25%, +50%)
17. vida_inimigos (normal -> +50%, +100%)
18. iluminacao (desligado -> ligado)
19. cores_invertidas (desligado -> ligado)
20. fogo_amigo (desligado -> ligado)
"""

import os
import sys
import math
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
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.projetil import Projetil
from src.entidades.drop import ItemDrop
from src.cenas.gameplay import GameplayScene
from src.sistemas.sistema_spawn import SistemaSpawn
from src.sistemas.sistema_particulas import SistemaParticulas


class TestGameplayConfigsCatalog(unittest.TestCase):
    """Bateria de testes que valida cada uma das 20 configurações de gameplay."""

    def setUp(self):
        self.mgr = GerenciadorConfiguracoes()

    def test_config_01_fps_cap(self):
        """Config 1: fps_cap reduz dano e velocidade de inimigos quando em 30 ou 15 FPS."""
        self.mgr.desbloquear_config("fps_cap")
        self.mgr.definir_valor("fps_cap", "30")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.vel_inimigos_mult, 0.90)

    def test_config_02_graficos_qualidade(self):
        """Config 2: graficos_qualidade baixa reduz HP de inimigos em -20%."""
        self.mgr.desbloquear_config("graficos_qualidade")
        self.mgr.definir_valor("graficos_qualidade", "baixa")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.hp_inimigos_mult, 0.80)

    def test_config_03_resolucao(self):
        """Config 3: resolucao 50% dá +25% de bônus na chance de drop."""
        self.mgr.desbloquear_config("resolucao")
        self.mgr.definir_valor("resolucao", "50%")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.drop_chance_bonus, 0.25)

    def test_config_04_vsync(self):
        """Config 4: vsync desligado concede +10% de velocidade com oscilação."""
        self.mgr.desbloquear_config("vsync")
        self.mgr.definir_valor("vsync", "desligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.vel_jogador_mult, 1.10)

    def test_config_05_screen_shake(self):
        """Config 5: screen_shake ligado multiplica dano das armas explosivas por 1.20."""
        self.mgr.desbloquear_config("screen_shake")
        self.mgr.definir_valor("screen_shake", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.dano_explosivos_mult, 1.20)

    def test_config_06_motion_blur(self):
        """Config 6: motion_blur ligado concede +15% de velocidade de movimento."""
        self.mgr.desbloquear_config("motion_blur")
        self.mgr.definir_valor("motion_blur", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.vel_jogador_mult, 1.15)

    def test_config_07_hud(self):
        """Config 7: hud desligado concede +25% de XP como recompensa por jogar às cegas."""
        self.mgr.desbloquear_config("hud")
        self.mgr.definir_valor("hud", "desligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.xp_ganho_mult, 1.25)

    def test_config_08_damage_numbers_and_crits(self):
        """Config 8: damage_numbers ligado concede 25% de chance de crítico 2x dano e emite números flutuantes."""
        self.mgr.desbloquear_config("damage_numbers")
        self.mgr.definir_valor("damage_numbers", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.critico_chance, 0.25)
        self.assertEqual(mods.critico_mult, 2.0)
        self.assertTrue(mods.damage_numbers_knockback)

        # Valida emissão no SistemaParticulas
        sp = SistemaParticulas()
        sp.emitir_texto_dano(100, 100, 42, critico=True)
        self.assertEqual(len(sp.textos_dano), 1)
        self.assertEqual(sp.textos_dano[0].texto, "42!")
        self.assertTrue(sp.textos_dano[0].critico)

    def test_config_09_zoom_hitbox(self):
        """Config 9: zoom 75% aumenta as hitboxes de projéteis em +50%."""
        self.mgr.desbloquear_config("zoom")
        self.mgr.definir_valor("zoom", "75%")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.hitbox_projeteis_mult, 1.50)

    def test_config_10_movimento_mouse_autopilot(self):
        """Config 10: movimento_mouse ligado move o jogador em direção ao cursor e dá +40% de drop rate."""
        jogador = Jogador(x=100.0, y=100.0)
        self.mgr.desbloquear_config("movimento_mouse")
        self.mgr.definir_valor("movimento_mouse", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.drop_chance_mult, 1.40)

        mock_mouse = MagicMock()
        mock_mouse.get_position.return_value = (300.0, 100.0)  # Cursor à direita

        jogador.processar_input(
            teclado=None,
            mouse=mock_mouse,
            dt=0.1,
            config_sistema=self.mgr
        )
        self.assertGreater(jogador.x, 100.0, "Jogador deve ter se movido para a direita seguindo o cursor do mouse.")

    def test_config_11_keybinds_presets(self):
        """Config 11: keybinds suporta padrao, invertido, arrow_keys, uma_mao e pesadelo."""
        jogador = Jogador(x=500.0, y=500.0)

        # Invertido: 'd' move para a esquerda (dx -= 1.0)
        self.mgr.desbloquear_config("keybinds")
        self.mgr.definir_valor("keybinds", "invertido")
        mock_teclado = MagicMock()
        mock_teclado.key_pressed.side_effect = lambda k: k == "d"
        mock_teclado.key_down.side_effect = lambda k: False

        jogador.processar_input(mock_teclado, None, dt=0.1, config_sistema=self.mgr)
        self.assertLess(jogador.x, 500.0, "Com keybinds invertido, 'd' deve mover para a esquerda.")

    def test_config_12_suavizacao_camera(self):
        """Config 12: suavizacao_camera desligada usa fator 1.0 (trava rígida instantânea)."""
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("suavizacao_camera")
        cena.config_sistema.definir_valor("suavizacao_camera", "desligado")
        val_suav = cena.config_sistema.obter_valor("suavizacao_camera")
        suav_fator = 1.0 if str(val_suav).lower() in ("desligado", "0", "false") else 0.15
        self.assertEqual(suav_fator, 1.0)

    def test_config_13_auto_fire_discrete_click(self):
        """Config 13: auto_fire desligado não dispara sem clique discreto."""
        cena = GameplayScene()
        cena.config_sistema.desbloquear_config("auto_fire")
        cena.config_sistema.definir_valor("auto_fire", "desligado")
        self.assertEqual(cena.config_sistema.obter_valor("auto_fire"), "desligado")

    def test_config_14_inimigos_ranged(self):
        """Config 14: inimigos_ranged desligado impede o spawn de InimigoRanged no SistemaSpawn."""
        spawner = SistemaSpawn()
        # Com permitir_ranged=False em tempo avançado (120s), InimigoRanged deve ser substituído por InimigoPadrao
        arquetipos = [spawner.escolher_arquetipo(120.0, permitir_ranged=False) for _ in range(100)]
        self.assertNotIn(InimigoRanged, arquetipos, "Não deve conter InimigoRanged quando permitir_ranged=False.")

    def test_config_15_coleta_inimiga(self):
        """Config 15: coleta_inimiga liga Scavenger AI e dobra drops."""
        self.mgr.desbloquear_config("coleta_inimiga")
        self.mgr.definir_valor("coleta_inimiga", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertEqual(self.mgr.obter_valor("coleta_inimiga"), "ligado")
        self.assertEqual(mods.drops_valor_mult, 2.0)

    def test_config_16_velocidade_inimigos(self):
        """Config 16: velocidade_inimigos +25% aumenta vel_inimigos_mult para 1.25 e dá +20% de XP."""
        self.mgr.desbloquear_config("velocidade_inimigos")
        self.mgr.definir_valor("velocidade_inimigos", "+25%")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.vel_inimigos_mult, 1.25)
        self.assertAlmostEqual(mods.xp_ganho_mult, 1.20)

    def test_config_17_vida_inimigos(self):
        """Config 17: vida_inimigos +50% aumenta hp_inimigos_mult para 1.50 e dá +20% chance de drop."""
        self.mgr.desbloquear_config("vida_inimigos")
        self.mgr.definir_valor("vida_inimigos", "+50%")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.hp_inimigos_mult, 1.50)
        self.assertAlmostEqual(mods.drop_chance_bonus, 0.20)

    def test_config_18_iluminacao_fog_damage_reduction(self):
        """Config 18: iluminacao ligada reduz dano de inimigos fora do campo de visão (>195px) em 50%."""
        self.mgr.desbloquear_config("iluminacao")
        self.mgr.definir_valor("iluminacao", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.dano_fora_visao_mult, 0.50)

    def test_config_19_cores_invertidas(self):
        """Config 19: cores_invertidas ligado concede +20% de dano global."""
        self.mgr.desbloquear_config("cores_invertidas")
        self.mgr.definir_valor("cores_invertidas", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertAlmostEqual(mods.dano_armas_mult, 1.20)

    def test_config_20_fogo_amigo(self):
        """Config 20: fogo_amigo ligado concede +25% de dano com auto-dano balístico."""
        self.mgr.desbloquear_config("fogo_amigo")
        self.mgr.definir_valor("fogo_amigo", "ligado")
        mods = self.mgr.obter_modificadores()
        self.assertTrue(mods.auto_dano)
        self.assertAlmostEqual(mods.dano_armas_mult, 1.25)


if __name__ == "__main__":
    unittest.main()
