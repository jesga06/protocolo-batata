"""
Testes para BannerDica, Card de Parry no HUD (canto superior direito) e XP até Nível 5.
"""

import os
import sys
import unittest
import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.sistemas.sistema_xp import SistemaXP
from src.ui.banner_dicas import BannerDica, DICAS_JOGO
from src.ui.hud import HUD


class _JogadorStub:
    def __init__(self, dash_desbloqueado: bool = False):
        self.dash_desbloqueado = dash_desbloqueado
        self.hp = 150
        self.hp_max = 150
        self.escudo_sobrevida = 0


class TestDicasEParryHUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

    def test_xp_total_ate_nivel_5_reduzido_25_porcento(self):
        total_xp = sum(SistemaXP.calcular_xp_para_nivel(lvl) for lvl in range(1, 5))
        self.assertEqual(total_xp, 545)
        xp_sys = SistemaXP(nivel_inicial=1, nivel_maximo=12)
        niveis = xp_sys.adicionar_xp(545)
        self.assertEqual(niveis, [2, 3, 4, 5])
        self.assertEqual(xp_sys.nivel, 5)

    def test_miniboss_abate_coleta_xp_automaticamente(self):
        from src.cenas.gameplay import GameplayScene
        from src.entidades.inimigo_padrao import InimigoPadrao

        cena = GameplayScene()
        xp_antes = cena.jogador.sistema_xp.xp_total
        elite = InimigoPadrao(200, 200, is_elite=True, nome_elite="MINI-BOSS TESTE")
        cena._registrar_abate_inimigo(elite)

        self.assertEqual(cena.jogador.sistema_xp.xp_total - xp_antes, 75)
        xp_no_chao = [d for d in cena.sistema_drops.drops if d.tipo == "xp"]
        self.assertEqual(len(xp_no_chao), 0)

    def test_banner_dica_rotacao_e_desenho(self):
        banner = BannerDica(intervalo_rotacao=8.0, indice_inicial=0)
        self.assertEqual(banner.texto_atual, DICAS_JOGO[0])
        banner.atualizar(8.0)
        self.assertEqual(banner.texto_atual, DICAS_JOGO[1])

        surf = pygame.Surface((1280, 720))
        banner.desenhar(surf, pygame.Rect(100, 600, 700, 56), scale=1.0)

    def test_hud_card_parry_renderiza_apenas_quando_dash_bloqueado(self):
        hud = HUD()
        surf_bloqueado = pygame.Surface((1280, 720))
        surf_bloqueado.fill((0, 0, 0))
        hud.desenhar_card_parry(surf_bloqueado, _JogadorStub(False), parries_total=42, visivel=True)

        surf_desbloqueado = pygame.Surface((1280, 720))
        surf_desbloqueado.fill((0, 0, 0))
        hud.desenhar_card_parry(surf_desbloqueado, _JogadorStub(True), parries_total=100, visivel=True)

        # Canto superior direito deve ter pixels desenhados quando bloqueado e permanecer preto quando desbloqueado
        regiao_dir_bloq = pygame.transform.average_color(surf_bloqueado, pygame.Rect(950, 60, 320, 80))
        regiao_dir_desbloq = pygame.transform.average_color(surf_desbloqueado, pygame.Rect(950, 60, 320, 80))
        self.assertGreater(sum(regiao_dir_bloq[:3]), 0)
        self.assertEqual(regiao_dir_desbloq[:3], (0, 0, 0))

    def test_in_world_dash_e_municao_abaixo_do_hp(self):
        from src.cenas.gameplay import GameplayScene

        cena = GameplayScene()
        surf = pygame.Surface((1280, 720))
        cena.janela.screen = surf
        cena.camera.x = 0
        cena.camera.y = 0
        cena.jogador.x = 100
        cena.jogador.y = 100

        base_y = int(cena.jogador.y + cena.jogador.altura + 5.0)
        cx = int(cena.jogador.x + cena.jogador.largura / 2.0)

        # Dash bloqueado: apenas 1 barra extra (munição) em base_y + 7; linha 2 (base_y + 12) vazia
        cena.jogador.dash_desbloqueado = False
        surf.fill((0, 0, 0))
        cena._desenhar_hp_in_world()
        self.assertNotEqual(surf.get_at((cx, base_y + 8))[:3], (0, 0, 0))
        self.assertEqual(surf.get_at((cx, base_y + 13))[:3], (0, 0, 0))

        # Dash desbloqueado: barra do dash em base_y + 7 (ciano) e barra de munição em base_y + 12
        cena.jogador.dash_desbloqueado = True
        cena.jogador.dash_cooldown_restante = 0.0
        surf.fill((0, 0, 0))
        cena._desenhar_hp_in_world()
        self.assertEqual(surf.get_at((cx, base_y + 8))[:3], (34, 211, 238))
        self.assertNotEqual(surf.get_at((cx, base_y + 13))[:3], (0, 0, 0))

    def test_modal_level_up_permite_escolher_duas_configs(self):
        from src.sistemas.config_sistema import GerenciadorConfiguracoes
        from src.ui.modal_level_up import ModalLevelUp

        cfg = GerenciadorConfiguracoes()
        modal = ModalLevelUp(cfg, jogador=None, cena=None)
        modal.abrir(nivel=5)
        self.assertTrue(modal.ativo)
        self.assertEqual(modal.escolhas_restantes, 2)

        # Primeira escolha mantém o modal aberto e impede repetir o mesmo card
        self.assertTrue(modal.selecionar_card(0))
        self.assertTrue(modal.ativo)
        self.assertEqual(modal.escolhas_restantes, 1)
        self.assertFalse(modal.selecionar_card(0))

        # Segunda escolha desbloqueia a 2ª config e fecha o modal
        self.assertTrue(modal.selecionar_card(1))
        self.assertFalse(modal.ativo)
        self.assertEqual(len(cfg.desbloqueadas), 2)

    def test_ninja_projetil_50_maior_roxo_e_25_mais_lento(self):
        from src.entidades.inimigo_ninja import InimigoNinja
        from src.entidades.projetil import Projetil

        ninja = InimigoNinja(100, 100)
        self.assertAlmostEqual(ninja.vel_projetil, 380.0)

        ninja.timer_tiro = ninja.cooldown_tiro
        ninja.update(0.016, (250, 100))
        projs = ninja.obter_projeteis_pendentes()
        self.assertEqual(len(projs), 1)
        self.assertEqual((projs[0].largura, projs[0].altura), (20, 20))
        self.assertEqual(projs[0].cor, (168, 85, 247))
        self.assertAlmostEqual(projs[0].velocidade, 380.0)

        p_duelo = ninja._emitir_projetil_duelo(2, (250, 100))
        self.assertEqual((p_duelo.largura, p_duelo.altura), (20, 20))
        self.assertEqual(p_duelo.cor, (168, 85, 247))
        self.assertAlmostEqual(p_duelo.velocidade, 470.0)

        p_jog = Projetil(100, 100, 1.0, 0.0, 400.0, 10, dono="jogador", largura=12, altura=12)
        ref = ninja.aparar_projetil_jogador(p_jog, (250, 100))
        self.assertIsNotNone(ref)
        self.assertEqual((ref.largura, ref.altura), (20, 20))
        self.assertEqual(ref.cor, (168, 85, 247))
        self.assertAlmostEqual(ref.velocidade, 380.0)


if __name__ == "__main__":
    unittest.main()
