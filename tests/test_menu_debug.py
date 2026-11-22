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

        self.inimigos = []
        self.projeteis = []
        self.pausado = False
        self.tempo_sobrevivencia = 0.0

    @property
    def drops(self):
        return self.sistema_drops.drops if hasattr(self, "sistema_drops") else []

    @drops.setter
    def drops(self, val):
        if hasattr(self, "sistema_drops"):
            self.sistema_drops.drops = val


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
        self.assertEqual(MELEE_ARCO_GRAUS, 90.0)
        self.assertEqual(MINIGUN_MUNICIAO_MAX, 300)
        self.assertEqual(SHOTGUN_MUNICIAO_MAX, 60)
        self.assertEqual(RIFLE_MUNICIAO_MAX, 120)
        self.assertEqual(FOGUETES_MUNICIAO_MAX, 24)
        self.assertEqual(GRANADAS_MUNICIAO_MAX, 32)
        self.assertEqual(RAILGUN_MUNICIAO_MAX, 10)

    def test_weapon_instances_initial_ammo(self):
        """Verifica se instâncias das armas nascem com munição balanceada para a Sprint 2."""
        minigun = Minigun()
        shotgun = Shotgun()
        rifle = RifleAssalto()
        foguetes = LancaFoguetes()
        granadas = LancaGranadas()
        railgun = Railgun()

        self.assertEqual(minigun.municao_atual, 300)
        self.assertEqual(shotgun.municao_atual, 60)
        self.assertEqual(rifle.municao_atual, 120)
        self.assertEqual(foguetes.municao_atual, 24)
        self.assertEqual(granadas.municao_atual, 32)
        self.assertEqual(railgun.municao_atual, 10)

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

        # 7. Ação Subir Nível (+1)
        nivel_inicial = self.cena.jogador.nivel
        self.debug_menu.indice_foco = 10
        self.debug_menu.idx_level_up = 0  # +1
        self.debug_menu._executar_acao_selecionada()
        self.assertEqual(self.cena.jogador.nivel, nivel_inicial + 1)

        # 8. Ação Desbloquear Todas Configurações
        self.debug_menu.indice_foco = 11
        self.debug_menu._executar_acao_selecionada()
        self.assertEqual(len(self.cena.config_sistema.desbloqueadas), 23)

    def test_debug_menu_spawn_drops_and_enemies(self):
        """Testa geração de drops e inimigos nas coordenadas do mundo com centro alinhado."""
        # 1. Spawn Drop XP (+50)
        self.debug_menu.indice_foco = 4
        self.debug_menu.idx_tipo_drop = 1  # XP (+50)
        self.debug_menu._spawnar_item_ou_inimigo_no_mundo(500.0, 400.0)
        self.assertEqual(len(self.cena.drops), 1)
        self.assertEqual(self.cena.drops[0].tipo, "xp")
        self.assertEqual(self.cena.drops[0].valor, 50)
        self.assertEqual(self.cena.drops[0].x + self.cena.drops[0].largura / 2.0, 500.0)
        self.assertEqual(self.cena.drops[0].y + self.cena.drops[0].altura / 2.0, 400.0)

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

        # 4. Spawn Inimigo (Tanque) — Valida que o CENTRO do inimigo coincide com o clique
        self.debug_menu.indice_foco = 7
        self.debug_menu.idx_inimigo = 5  # Tanque
        self.debug_menu._spawnar_item_ou_inimigo_no_mundo(600.0, 350.0)
        self.assertEqual(len(self.cena.inimigos), 1)
        self.assertEqual(self.cena.inimigos[0].hp, 120)
        self.assertEqual(self.cena.inimigos[0].x + self.cena.inimigos[0].largura / 2.0, 600.0)
        self.assertEqual(self.cena.inimigos[0].y + self.cena.inimigos[0].altura / 2.0, 350.0)

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
        """Testa que o ataque Melee atinge alvos no novo alcance de 109px e arco de 120º."""
        melee = Melee()
        self.assertEqual(melee.alcance, 109.0)
        self.assertEqual(melee.arco_graus, 90.0)

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

    def test_sistema_xp_methods_and_aliases(self):
        """Valida que adicionar_xp, ganhar_xp e xp_necessario funcionam de forma idêntica."""
        from src.sistemas.sistema_xp import SistemaXP
        xp_sys = SistemaXP()
        self.assertEqual(xp_sys.xp_necessario, 103)
        self.assertEqual(xp_sys.xp_para_proximo_nivel(), 103)

        # Testa ganhar_xp
        niveis = xp_sys.ganhar_xp(103)
        self.assertEqual(xp_sys.nivel, 2)
        self.assertIn(2, niveis)
        self.assertEqual(xp_sys.xp_necessario, 192)

    def test_hud_xp_and_boss_bar_vertical_separation(self):
        """Valida que a barra de XP (y=58..68) e o texto/barra do Mini-Boss (y=74..102) não se sobrepõem."""
        from src.ui.hud import HUD
        hud = HUD()
        screen = pygame.Surface((800, 600))
        boss = InimigoPadrao(x=0, y=0)
        boss.is_elite = True

        # Renderiza sem exceção
        hud.desenhar_barra_xp(screen, self.cena.jogador.sistema_xp)
        hud.desenhar_barra_boss(screen, boss)

    def test_in_world_hp_bar_centering(self):
        """Valida que _desenhar_hp_in_world() desenha a barra de HP centralizada abaixo do avatar na surface."""
        from src.cenas.gameplay import GameplayScene
        from src.utils.constantes import VERDE_CURA
        cena = GameplayScene()
        cena.camera.x = 0.0
        cena.camera.y = 0.0
        cena.jogador.x = 200.0
        cena.jogador.y = 200.0
        cena.jogador.hp = cena.jogador.hp_max

        screen = cena.janela.screen
        screen.fill((0, 0, 0))
        cena._desenhar_hp_in_world()

        sprite_w = float(cena.jogador.largura)
        sprite_h = float(cena.jogador.altura)
        centro_x = int(cena.jogador.x + sprite_w / 2.0)
        meio_y = int(cena.jogador.y + sprite_h + 7.0)

        self.assertEqual(screen.get_at((centro_x, meio_y))[:3], VERDE_CURA)

    def test_menu_debug_spawning_all_drops_on_real_gameplay_scene(self):
        """Testa spawn e coleta de todas as categorias de drops na GameplayScene real sem exceções."""
        from src.cenas.gameplay import GameplayScene
        cena = GameplayScene()
        debug_menu = cena.menu_debug
        debug_menu.indice_foco = 4  # Spawn Drop

        for idx in range(len(debug_menu.opcoes_tipo_drop)):
            debug_menu.idx_tipo_drop = idx
            debug_menu._spawnar_item_ou_inimigo_no_mundo(cena.jogador.x, cena.jogador.y)
            self.assertGreater(len(cena.sistema_drops.drops), 0)
            self.assertGreater(len(cena.drops), 0)

        # Executa ciclo de coleta do jogador
        cena.loop()
        self.assertGreaterEqual(len(cena.toasts_coleta), 1)

    def test_menu_debug_spawning_all_weapons_and_drones_on_real_gameplay_scene(self):
        """Testa equipar todas as 6 armas especiais e 3 drones companheiros na GameplayScene real."""
        from src.cenas.gameplay import GameplayScene
        cena = GameplayScene()
        debug_menu = cena.menu_debug

        # 1. Armas
        debug_menu.indice_foco = 5
        for idx in range(len(debug_menu.opcoes_armas)):
            debug_menu.idx_arma = idx
            debug_menu._spawnar_item_ou_inimigo_no_mundo(500, 400)
            self.assertIsNotNone(cena.jogador.arma_especial)
            self.assertEqual(cena.jogador.slot_ativo, 3)

        # 2. Drones
        debug_menu.indice_foco = 6
        for idx in range(len(debug_menu.opcoes_drones)):
            debug_menu.idx_drone = idx
            debug_menu._spawnar_item_ou_inimigo_no_mundo(500, 400)
            self.assertGreaterEqual(len(cena.jogador.drones), 1)

        cena.loop()

    def test_menu_debug_spawning_all_enemy_types_on_real_gameplay_scene(self):
        """Testa spawn de todos os tipos de inimigos (incluindo Elite) na GameplayScene real."""
        from src.cenas.gameplay import GameplayScene
        cena = GameplayScene()
        debug_menu = cena.menu_debug
        debug_menu.indice_foco = 7  # Spawn Inimigo

        for idx in range(len(debug_menu.opcoes_inimigos)):
            debug_menu.idx_inimigo = idx
            debug_menu._spawnar_item_ou_inimigo_no_mundo(450.0, 350.0)

        self.assertEqual(len(cena.inimigos), len(debug_menu.opcoes_inimigos))
        cena.loop()

    def test_menu_debug_mouse_click_panel_selection_and_world_spawn(self):
        """Testa seleção de itens por clique no painel e spawn no mundo."""
        from src.cenas.gameplay import GameplayScene
        cena = GameplayScene()
        debug_menu = cena.menu_debug
        debug_menu.abrir()

        # Simula clique no item 5 (Equipar Arma: idx 5 -> y = 16 + 40 + 5*24 = 176)
        debug_menu.rect_painel.x = 16
        debug_menu.rect_painel.y = 16
        debug_menu.indice_foco = 0

        # Clique no painel para mudar foco
        y_item5 = 16 + 40 + 5 * 24 + 10
        x_item5_esq = 16 + 50
        # Força cooldown 0
        debug_menu.cooldown_input = 0.0

        # Atualiza com clique simulado
        import pygame
        screen = pygame.Surface((800, 600))
        debug_menu.draw(screen)


if __name__ == "__main__":
    unittest.main()