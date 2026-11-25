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

from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.sistemas.sistema_xp import SistemaXP
from src.ui.banner_dicas import (
    BANCO_DICAS,
    BannerDica,
    CONDICOES_DICAS,
    CONDICOES_PARAMETRIZADAS,
    DICAS_JOGO,
    avaliar_condicao,
    dica,
    dica_elegivel,
    obter_dicas_elegiveis,
    validar_condicao_spec,
)
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

    def test_dicas_condicionais_save_zerado_vs_desbloqueios(self):
        cfg = GerenciadorConfiguracoes()
        pool_zerado = " ".join(obter_dicas_elegiveis(cfg)).lower()
        self.assertIn("15 parries", pool_zerado)
        self.assertNotIn("smg compacta", pool_zerado)
        self.assertNotIn("zona ideal de calor", pool_zerado)
        self.assertNotIn("firmware", pool_zerado)
        self.assertNotIn("auto-fire", pool_zerado)
        self.assertNotIn("bastão de choque", pool_zerado)
        self.assertNotIn("mira oculta", pool_zerado)
        self.assertNotIn("postura riposte", pool_zerado)
        self.assertNotIn("29 configurações", pool_zerado)
        self.assertNotIn("just-dodge", pool_zerado)
        self.assertNotIn("combo", " ".join(DICAS_JOGO).lower())

        # Desbloquear Dash + SMG + 2 configs
        cfg.sistema_conquistas.recompensas["habilidade"].add("dash")
        cfg.sistema_conquistas.recompensas["arma"].add("smg_compacta")
        cfg.desbloqueadas.add("auto_fire")
        cfg.desbloqueadas.add("mira_oculta")
        pool_dash = " ".join(obter_dicas_elegiveis(cfg)).lower()
        self.assertNotIn("acumule 15 parries", pool_dash)
        self.assertIn("smg compacta", pool_dash)
        self.assertIn("just-dodge", pool_dash)
        self.assertIn("auto-fire", pool_dash)
        self.assertIn("mira oculta", pool_dash)
        self.assertIn("loadout", pool_dash)
        self.assertIn("primeiro chip de firmware", pool_dash)
        self.assertNotIn("2/4/6", pool_dash)

        # Desbloquear primeiro Chip de Firmware + Bastao + Postura Riposte
        cfg.sistema_conquistas.recompensas["modificador_run"].add("gatilho_duplo")
        cfg.sistema_conquistas.recompensas["arma"].add("bastao_choque")
        cfg.sistema_conquistas.recompensas["opcao_config"].add("precisao_parry:postura_riposte")
        pool_fw = " ".join(obter_dicas_elegiveis(cfg)).lower()
        self.assertIn("2/4/6", pool_fw)
        self.assertIn("bastão de choque", pool_fw)
        self.assertIn("ripostar", pool_fw)

        # Reset save volta instantaneamente ao pool inicial seguro
        banner = BannerDica(gerenciador_config=cfg, indice_inicial=0)
        banner.indice_atual = max(0, len(obter_dicas_elegiveis(cfg)) - 1)
        cfg._resetar_para_v2_limpo()
        self.assertNotIn("firmware", banner.texto_atual.lower())

        # Registro exposto de condicoes + avaliacao parametrizada + validacao
        self.assertGreaterEqual(len(CONDICOES_DICAS), 30)
        self.assertGreaterEqual(len(CONDICOES_PARAMETRIZADAS), 15)
        self.assertGreater(len(BANCO_DICAS), 15)
        cfg.sistema_conquistas.recompensas["arma"].add("rifle_arco")
        self.assertTrue(avaliar_condicao(("arma", "rifle_arco"), cfg))
        self.assertFalse(avaliar_condicao(("min_configs_ativas", 2), cfg))
        with self.assertRaises(ValueError):
            validar_condicao_spec("condicao_inexistente_xyz")

    def test_dica_expressao_legivel_e_validacao(self):
        cfg = GerenciadorConfiguracoes()
        cfg.sistema_conquistas.recompensas["arma"].add("rifle_arco")
        cfg.estatisticas["parries_total"] = 20

        self.assertTrue(avaliar_condicao("arma('rifle_arco') and parries >= 15", cfg))
        self.assertTrue(avaliar_condicao("arma:rifle_arco and not dash_desbloqueado", cfg))
        self.assertFalse(avaliar_condicao("arma('smg_compacta') or dash_desbloqueado", cfg))

        item = dica("Teste", quando="arma('rifle_arco') and parries >= 15", exceto="dash_desbloqueado")
        self.assertTrue(dica_elegivel(item, cfg))
        cfg.sistema_conquistas.recompensas["habilidade"].add("dash")
        self.assertFalse(dica_elegivel(item, cfg))

        for invalida in ("arma('x') and condicao_falsa_xyz", "desconhecida('x')", "parries == 10", "a + b"):
            with self.assertRaises(ValueError):
                validar_condicao_spec(invalida)

    def test_in_world_dash_e_municao_abaixo_do_hp(self):
        from src.cenas.gameplay import GameplayScene
        from src.armas.minigun import Minigun

        cena = GameplayScene()
        surf = pygame.Surface((1280, 720))
        cena.janela.screen = surf
        cena.camera.x = 0
        cena.camera.y = 0
        cena.jogador.x = 100
        cena.jogador.y = 100

        base_y = int(cena.jogador.y + cena.jogador.altura + 5.0)
        cx = int(cena.jogador.x + cena.jogador.largura / 2.0)

        # Pistola (munição infinita) sem Dash bloqueado: SEM barra amarela estática abaixo do HP
        cena.jogador.dash_desbloqueado = False
        surf.fill((0, 0, 0))
        cena._desenhar_hp_in_world()
        self.assertEqual(surf.get_at((cx, base_y + 8))[:3], (0, 0, 0))
        self.assertEqual(surf.get_at((cx, base_y + 13))[:3], (0, 0, 0))

        # Arma finita (Slot 3): barra de munição em base_y + 7; linha 2 (base_y + 12) vazia sem Dash
        cena.jogador.equipar_arma_especial(Minigun())
        cena.jogador.selecionar_slot(3)
        surf.fill((0, 0, 0))
        cena._desenhar_hp_in_world()
        self.assertNotEqual(surf.get_at((cx, base_y + 8))[:3], (0, 0, 0))
        self.assertEqual(surf.get_at((cx, base_y + 13))[:3], (0, 0, 0))

        # Dash desbloqueado + arma finita: barra do dash em base_y + 7 (ciano) e barra de munição em base_y + 12
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
