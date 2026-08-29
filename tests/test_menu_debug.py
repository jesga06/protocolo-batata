"""
Testes Unitários do Menu de Debug e Balanceamento de Armas/Melee — Protocolo: Batata
Valida o console de desenvolvedor (F1/~), navegação por teclado, toggles de depuração,
spawn de entidades, cura/dano, level up, destravar configs, detonação do lança-foguetes
e alcance expandido do ataque melee.
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

from src.utils.constantes import (
    MELEE_ALCANCE, MELEE_ARCO_GRAUS,
    MINIGUN_MUNICIAO_MAX, SHOTGUN_MUNICIAO_MAX, RIFLE_MUNICIAO_MAX,
    FOGUETES_MUNICIAO_MAX, GRANADAS_MUNICIAO_MAX, RAILGUN_MUNICIAO_MAX
)
from src.entidades.jogador import Jogador
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.projetil import Projetil
from src.armas import (
    Melee, Pistola, Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun
)
from src.ui.menu_debug import MenuDebug


class MockGameplayCena:
    """Mock da cena de gameplay para testes isolados de MenuDebug."""
    def __init__(self):
        from src.sistemas.config_sistema import GerenciadorConfiguracoes
        from src.sistemas.sistema_drops import SistemaDrops
        from src.sistemas.sistema_spawn import SistemaSpawn
        from src.sistemas.sistema_particulas import SistemaParticulas
        from src.ui.modal_level_up import ModalLevelUp
        from src.ui.menu_configs import MenuConfigs
        from PPlay.camera import Camera

        self.jogador = Jogador(x=400.0, y=300.0)
        self.camera = Camera(800, 600)
        self.config_sistema = GerenciadorConfiguracoes()
        self.modal_level_up = ModalLevelUp(self.config_sistema, self.jogador, cena=self)
        self.menu_configs = MenuConfigs(self.config_sistema, em_jogo=True, cena=self)
        self.sistema_drops = SistemaDrops()
        self.spawner = SistemaSpawn(max_ativos=400)
        self.sistema_particulas = SistemaParticulas()

        self.drops = []
        self.inimigos = []
        self.projeteis = []
        self.pausado = False
        self.tempo_sobrevivencia = 0.0


class TestMenuDebugAndWeapons(unittest.TestCase):
    """Testa o comportamento completo do MenuDebug e novas mecânicas de combate."""

    def setUp(self):
        if not pygame.get_init():
            pygame.init()
        self.cena = MockGameplayCena()
        self.debug_menu = MenuDebug(cena_gameplay=self.cena)

    def test_rebalance_constants_values(self):
        """Verifica se as constantes de combate e munição foram atualizadas corretamente."""
        self.assertEqual(MELEE_ALCANCE, 109.0)
        self.assertEqual(MELEE_ARCO_GRAUS, 60.0)
        self.assertEqual(MINIGUN_MUNICIAO_MAX, 225)
        self.assertEqual(SHOTGUN_MUNICIAO_MAX, 45)
        self.assertEqual(RIFLE_MUNICIAO_MAX, 90)
        self.assertEqual(FOGUETES_MUNICIAO_MAX, 18)
        self.assertEqual(GRANADAS_MUNICIAO_MAX, 24)
        self.assertEqual(RAILGUN_MUNICIAO_MAX, 22)

    def test_weapon_instances_initial_ammo(self):
        """Verifica se instâncias das armas nascem com +50% de munição."""
        minigun = Minigun()
        shotgun = Shotgun()
        rifle = RifleAssalto()
        foguetes = LancaFoguetes()
        granadas = LancaGranadas()
        railgun = Railgun()

        self.assertEqual(minigun.municao_atual, 225)
        self.assertEqual(shotgun.municao_atual, 45)
        self.assertEqual(rifle.municao_atual, 90)
        self.assertEqual(foguetes.municao_atual, 18)
        self.assertEqual(granadas.municao_atual, 24)
        self.assertEqual(railgun.municao_atual, 22)

    def test_debug_menu_toggle_open_close(self):
        """Valida abertura, fechamento e controle de pausa da partida."""
        self.assertFalse(self.debug_menu.ativo)
        self.assertFalse(self.cena.pausado)

        self.debug_menu.abrir()
        self.assertTrue(self.debug_menu.ativo)
        self.assertTrue(self.cena.pausado)

        self.debug_menu.fechar()
        self.assertFalse(self.debug_menu.ativo)
        self.assertFalse(self.cena.pausado)

    def test_debug_menu_toggles_and_actions(self):
        """Testa alteração de toggles e execução de ações do console."""
        # 1. Toggle Natural Spawning
        self.debug_menu.indice_foco = 0
        self.assertTrue(self.debug_menu.spawn_natural_ativo)
        self.debug_menu._executar_acao_selecionada()
        self.assertFalse(self.debug_menu.spawn_natural_ativo)

        # 2. Toggle Congelar Timer
        self.debug_menu.indice_foco = 1
        self.assertFalse(self.debug_menu.timer_congelado)
        self.debug_menu._executar_acao_selecionada()
        self.assertTrue(self.debug_menu.timer_congelado)

        # 3. Toggle Munição Infinita
        self.debug_menu.indice_foco = 2
        self.assertFalse(self.debug_menu.municao_infinita)
        self.debug_menu._executar_acao_selecionada()
        self.assertTrue(self.debug_menu.municao_infinita)

        # 4. Toggle Modo Deus
        self.debug_menu.indice_foco = 3
        self.assertFalse(self.debug_menu.modo_deus)
        self.debug_menu._executar_acao_selecionada()
        self.assertTrue(self.debug_menu.modo_deus)

        # 5. Ação Curar Vida Completa
        self.cena.jogador.hp = 10
        self.debug_menu.indice_foco = 8
        self.debug_menu._executar_acao_selecionada()
        self.assertEqual(self.cena.jogador.hp, self.cena.jogador.hp_max)

        # 6. Ação Tomar Dano (1/8 HP)
        dano_esperado = max(1, self.cena.jogador.hp_max // 8)
        self.debug_menu.indice_foco = 9
        self.debug_menu._executar_acao_selecionada()
        self.assertEqual(self.cena.jogador.hp, self.cena.jogador.hp_max - dano_esperado)

        # 7. Ação Desbloquear Todas Configurações
        self.debug_menu.indice_foco = 11
        self.debug_menu._executar_acao_selecionada()
        self.assertEqual(len(self.cena.config_sistema.desbloqueadas), 20)

    def test_debug_menu_spawn_drops_and_enemies(self):
        """Testa geração de drops e inimigos nas coordenadas do mundo."""
        # 1. Spawn Drop XP (+50)
        self.debug_menu.indice_foco = 4
        self.debug_menu.idx_tipo_drop = 1  # XP (+50)
        self.debug_menu._spawnar_item_ou_inimigo_no_mundo(500.0, 400.0)
        self.assertEqual(len(self.cena.drops), 1)
        self.assertEqual(self.cena.drops[0].tipo, "xp")
        self.assertEqual(self.cena.drops[0].valor, 50)

        # 2. Spawn Arma Específica (Minigun)
        self.debug_menu.indice_foco = 5
        self.debug_menu.idx_arma = 0  # Minigun
        self.debug_menu._spawnar_item_ou_inimigo_no_mundo(500.0, 400.0)
        self.assertIsNotNone(self.cena.jogador.arma_especial)
        self.assertEqual(self.cena.jogador.arma_especial.nome, "Minigun")
        self.assertEqual(self.cena.jogador.slot_ativo, 3)

        # 3. Spawn Drone Específico (Drone Cura)
        self.debug_menu.indice_foco = 6
        self.debug_menu.idx_drone = 0  # Drone Cura
        self.debug_menu._spawnar_item_ou_inimigo_no_mundo(500.0, 400.0)
        self.assertTrue(len(self.cena.jogador.drones) >= 1)
        self.assertEqual(self.cena.jogador.drones[0].nome, "Drone de Cura")

        # 4. Spawn Inimigo (Tanque)
        self.debug_menu.indice_foco = 7
        self.debug_menu.idx_inimigo = 5  # Tanque
        self.debug_menu._spawnar_item_ou_inimigo_no_mundo(600.0, 350.0)
        self.assertEqual(len(self.cena.inimigos), 1)
        self.assertEqual(self.cena.inimigos[0].hp, 120)

    def test_rocket_launcher_direct_hit_bonus_and_aoe(self):
        """Testa que o foguete aplica 2x dano no impacto direto e 1x dano aos demais na área."""
        foguete = Projetil(
            x=100.0, y=100.0, dir_x=1.0, dir_y=0.0,
            dano=45, explosivo=True, raio_explosao=80.0
        )
        inimigo_direto = InimigoPadrao(x=100.0, y=100.0)  # HP 40
        inimigo_direto.hp = 120
        inimigo_vizinho = InimigoPadrao(x=140.0, y=100.0)  # HP 40 (dentro de 40px)
        inimigo_distante = InimigoPadrao(x=300.0, y=100.0)  # HP 40 (fora de 80px)

        inimigos = [inimigo_direto, inimigo_vizinho, inimigo_distante]

        afetados = foguete.explodir(inimigos, alvo_direto=inimigo_direto)

        # Alvo direto tomou 2x dano (45 * 2 = 90) -> 120 - 90 = 30 HP
        self.assertEqual(inimigo_direto.hp, 30)

        # Alvo vizinho no raio tomou 1x dano (45) -> 40 - 45 = -5 HP (derrotado)
        self.assertLessEqual(inimigo_vizinho.hp, 0)
        self.assertFalse(inimigo_vizinho.vivo)

        # Alvo distante fora do raio de 80px não sofreu dano -> 40 HP
        self.assertEqual(inimigo_distante.hp, 40)
        self.assertIn(inimigo_direto, afetados)
        self.assertIn(inimigo_vizinho, afetados)
        self.assertNotIn(inimigo_distante, afetados)

    def test_melee_increased_reach_and_cone_arc(self):
        """Testa que o ataque Melee atinge alvos no novo alcance de 109px e arco de 60º."""
        melee = Melee()
        self.assertEqual(melee.alcance, 109.0)
        self.assertEqual(melee.arco_graus, 60.0)

        # Inimigo com centro em (494, 300) a 94px do jogador (dentro de 109px, mas além do alcance antigo de 84px)
        inimigo_alcance_novo = InimigoPadrao(x=480.0, y=286.0)
        inimigos = [inimigo_alcance_novo]

        afetados = melee.executar_ataque(
            origem_x=400.0, origem_y=300.0,
            lista_inimigos=inimigos,
            mira_x=550.0, mira_y=300.0,
            angulo_mira=0.0
        )
        self.assertIn(inimigo_alcance_novo, afetados)
        self.assertEqual(inimigo_alcance_novo.hp, 30)  # 40 - 10 = 30 HP


if __name__ == "__main__":
    unittest.main()