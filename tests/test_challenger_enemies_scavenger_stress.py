"""
Testes Adversariais e de Stress: Inimigos Avançados e Mecânicas Scavenger (Fase 5) — Protocolo: Batata
Challenger 2 Suite de Verificação Empírica

Valida rigorosamente:
1. InimigoRanged Stand-off & Firing Boundaries:
   - Distância a 279px (velocidade zerada no stand-off) vs 281px (avança em direção ao jogador).
   - Acúmulo de dt no timer de disparo (1.19s sem tiro vs 1.21s com disparo).
   - Parâmetros do projétil balístico (dono='inimigo', dano=10, vel=260.0, tempo_vida=3.5, sprite).
   - Limite máximo de alcance de disparo (349px dispara vs 351px não dispara).
2. InimigoPhasing Intangibility Cycle:
   - Ciclo exato de 3.0s (1.2s em fase invulnerável):
     * t = 0.00s (em fase / imune)
     * t = 1.19s (em fase / imune)
     * t = 1.21s (vulnerável / dano aplicado)
     * t = 2.99s (vulnerável / dano aplicado)
     * t = 3.01s (em fase / imune)
   - Movimento contínuo e inalterado durante a fase.
3. InimigoBlindado Frontal Armor Angle Boundaries:
   - Limites angulares do arco de 90° (+-45° da direção de visão):
     * theta = 0° (frontal, 30% redução)
     * theta = 44° e -44° (frontal, 30% redução)
     * theta = 46° e -46° (flanco, 100% dano total)
     * theta = 180° (retaguarda, 100% dano total)
   - Modos de cálculo: via coordenadas de origem (origem_x, origem_y) e vetor de ataque (dir_ataque).
4. Fast Enemy 2-Shot Calibration:
   - InimigoRapido com HP = 25 (e baseline) calibrado para eliminação em exatamente 2 tiros de pistola (17 dano cada).
5. Scavenger AI & Drop Stacking Edge Cases:
   - Drop com idade 0.99s (sem seleção) vs 1.01s (elegível e selecionado).
   - Pool de candidatos com 3 inimigos (nenhum selecionado / 3 mais próximos excluídos) vs 4 inimigos (1 selecionado).
   - Exclusão de inimigos fora do raio máximo (>600px).
   - Consumo de drop pelo Scavenger sem recompensas ao jogador.
   - Coleta de drops pelo jogador sob Config 15 (multiplicador 2.0x exato para XP, Cura, Munição e Drones).
"""

import os
import sys
import math
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.drop import ItemDrop
from src.entidades.jogador import Jogador
from src.entidades.projetil import Projetil
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.sistema_drops import SistemaDrops
from src.armas.minigun import Minigun
from src.armas.shotgun import Shotgun
from src.armas.rifle_assalto import RifleAssalto
from src.armas.lanca_foguetes import LancaFoguetes
from src.armas.lanca_granadas import LancaGranadas
from src.equipamentos.drone_cura import DroneCura
from src.equipamentos.drone_combate import DroneCombate
from src.equipamentos.drone_suporte import DroneSuporte
from src.utils.constantes import (
    INIMIGO_RANGED_HP, INIMIGO_RANGED_DISTANCIA_TIRO,
    INIMIGO_PHASING_HP, INIMIGO_PHASING_CICLO,
    INIMIGO_BLINDADO_HP, INIMIGO_RAPIDO_HP
)


class TestChallengerInimigoRangedStandoffAndFiringBoundaries(unittest.TestCase):
    """Bateria de testes de limites físicos e temporais do Inimigo Ranged."""

    def test_standoff_distance_exact_boundary_279_vs_281(self):
        """
        Verifica o limiar exato do stand-off (280px):
        - dist = 281.0px (> 280.0px): o inimigo avança em direção ao alvo.
        - dist = 280.0px (== 280.0px): o avanço direto é interrompido.
        - dist = 279.0px (< 280.0px): a velocidade de aproximação é zerada.
        """
        # Caso 1: dist = 281.0px (alvo em x=281.0, y=0.0; inimigo em x=0.0, y=0.0)
        e_281 = InimigoRanged(x=0.0, y=0.0, velocidade=100.0, distancia_standoff=280.0)
        e_281.update(dt=0.1, pos_alvo=(281.0, 0.0))
        # Deve ter avançado 100 * 0.1 = 10.0px no eixo X
        self.assertAlmostEqual(e_281.x, 10.0, places=3)

        # Caso 2: dist = 280.0px (limite exato)
        e_280 = InimigoRanged(x=0.0, y=0.0, velocidade=100.0, distancia_standoff=280.0)
        e_280.update(dt=0.1, pos_alvo=(280.0, 0.0))
        self.assertAlmostEqual(e_280.x, 0.0, places=3)

        # Caso 3: dist = 279.0px (dentro do stand-off)
        e_279 = InimigoRanged(x=0.0, y=0.0, velocidade=100.0, distancia_standoff=280.0)
        e_279.update(dt=0.1, pos_alvo=(279.0, 0.0))
        self.assertAlmostEqual(e_279.x, 0.0, places=3)

    def test_standoff_distance_negative_direction_boundary(self):
        """Verifica o stand-off quando o jogador está à esquerda do inimigo (-X)."""
        # Inimigo em x=500.0, alvo em x=219.0 (dist = 281.0px) -> deve mover para a esquerda
        e_left_move = InimigoRanged(x=500.0, y=0.0, velocidade=100.0, distancia_standoff=280.0)
        e_left_move.update(dt=0.1, pos_alvo=(219.0, 0.0))
        self.assertAlmostEqual(e_left_move.x, 490.0, places=3)

        # Inimigo em x=500.0, alvo em x=221.0 (dist = 279.0px) -> não deve mover
        e_left_stop = InimigoRanged(x=500.0, y=0.0, velocidade=100.0, distancia_standoff=280.0)
        e_left_stop.update(dt=0.1, pos_alvo=(221.0, 0.0))
        self.assertAlmostEqual(e_left_stop.x, 500.0, places=3)

    def test_firing_cooldown_dt_accumulation_boundaries(self):
        """
        Verifica o temporizador de disparo balístico periódico (cooldown 1.2s):
        - dt acumulado = 1.19s (< 1.20s): nenhum projétil gerado.
        - dt acumulado adicional de 0.02s (total 1.21s >= 1.20s): exatamente 1 projétil disparado.
        - Fila limpa e timer resetado.
        """
        e = InimigoRanged(x=200.0, y=100.0, cooldown_tiro=1.2, distancia_tiro_max=350.0)
        alvo = (100.0, 100.0)  # Distância ~100px (<= 350px)

        # Atualizações parciais acumulando 1.19s
        e.update(dt=0.50, pos_alvo=alvo)
        e.update(dt=0.50, pos_alvo=alvo)
        e.update(dt=0.19, pos_alvo=alvo)
        self.assertEqual(len(e.projeteis_pendentes), 0)
        self.assertAlmostEqual(e.timer_tiro, 1.19, places=4)

        # Avança mais 0.02s -> total 1.21s >= 1.2s -> Dispara!
        e.update(dt=0.02, pos_alvo=alvo)
        self.assertEqual(len(e.projeteis_pendentes), 1)
        self.assertAlmostEqual(e.timer_tiro, 0.0, places=4)

        # Extrai os projéteis e valida esvaziamento da fila
        disparos = e.obter_projeteis_pendentes()
        self.assertEqual(len(disparos), 1)
        self.assertEqual(len(e.projeteis_pendentes), 0)

        # Valida atributos do projétil balístico
        proj = disparos[0]
        self.assertEqual(proj.dono, "inimigo")
        self.assertEqual(proj.dano, 10)
        self.assertAlmostEqual(proj.velocidade, 260.0, places=2)
        self.assertAlmostEqual(proj.tempo_vida, 3.5, places=2)
        self.assertEqual(proj.sprite_key, "projetil_inimigo")
        self.assertAlmostEqual(proj.dir_x, -1.0, places=3)
        self.assertAlmostEqual(proj.dir_y, 0.0, places=3)

    def test_firing_distance_max_boundary_349_vs_351(self):
        """
        Verifica o limite de alcance máximo de disparo (350px):
        - dist = 349px (<= 350px): dispara normalmente ao expirar cooldown.
        - dist = 351px (> 350px): não dispara mesmo com cooldown expirado.
        """
        # Inimigo em x=0, y=0. Alvo em x=349, y=0 (dist = 349px)
        e_in_range = InimigoRanged(x=0.0, y=0.0, cooldown_tiro=1.2, distancia_tiro_max=350.0)
        e_in_range.update(dt=1.25, pos_alvo=(349.0, 0.0))
        self.assertEqual(len(e_in_range.projeteis_pendentes), 1)

        # Inimigo em x=0, y=0. Alvo em x=351, y=0 (dist = 351px)
        e_out_range = InimigoRanged(x=0.0, y=0.0, cooldown_tiro=1.2, distancia_tiro_max=350.0)
        e_out_range.update(dt=1.25, pos_alvo=(351.0, 0.0))
        self.assertEqual(len(e_out_range.projeteis_pendentes), 0)


class TestChallengerInimigoPhasingIntangibilityCycle(unittest.TestCase):
    """Bateria de testes de ciclo temporal e imunidade a dano do Inimigo Phasing."""

    def test_phasing_cycle_exact_timing_and_damage_immunity(self):
        """
        Valida o ciclo de alternância de fase e a anulação de dano:
        - t = 0.00s: em_fase == True (imune a dano)
        - t = 1.19s: em_fase == True (imune a dano)
        - t = 1.21s: em_fase == False (vulnerável a dano)
        - t = 2.99s: em_fase == False (vulnerável a dano)
        - t = 3.01s: em_fase == True (imune a dano / ciclo reiniciado)
        """
        e = InimigoPhasing(x=100.0, y=100.0, hp=35, tempo_ciclo=3.0, tempo_fase=1.2)
        alvo = (100.0, 100.0)

        # 1. Teste em t = 0.00s (inicial) -> Imune
        self.assertTrue(e.em_fase)
        e.receber_dano(20)
        self.assertEqual(e.hp, 35)  # Dano totalmente anulado

        # 2. Teste em t = 1.19s -> Imune
        e.update(dt=1.19, pos_alvo=alvo)
        self.assertTrue(e.em_fase)
        e.receber_dano(20)
        self.assertEqual(e.hp, 35)  # Dano totalmente anulado

        # 3. Teste em t = 1.21s (avanço de 0.02s) -> Vulnerável
        e.update(dt=0.02, pos_alvo=alvo)
        self.assertFalse(e.em_fase)
        e.receber_dano(10)
        self.assertEqual(e.hp, 25)  # Dano aplicado com sucesso

        # 4. Teste em t = 2.99s (avanço de 1.78s) -> Vulnerável
        e.update(dt=1.78, pos_alvo=alvo)
        self.assertFalse(e.em_fase)
        e.receber_dano(5)
        self.assertEqual(e.hp, 20)  # Dano aplicado com sucesso

        # 5. Teste em t = 3.01s (avanço de 0.02s, mod 3.0 = 0.01s) -> Imune novamente
        e.update(dt=0.02, pos_alvo=alvo)
        self.assertTrue(e.em_fase)
        e.receber_dano(15)
        self.assertEqual(e.hp, 20)  # Dano totalmente anulado

    def test_phasing_multi_cycle_wraparound_robustness(self):
        """Valida a precisão da máquina de estados após 5 ciclos completos (15 segundos)."""
        e = InimigoPhasing(x=0.0, y=0.0, hp=50, tempo_ciclo=3.0, tempo_fase=1.2)
        alvo = (0.0, 0.0)

        # Avança 15.0s (5 ciclos exatos)
        for _ in range(150):
            e.update(dt=0.1, pos_alvo=alvo)

        # Em t=15.0s (mod 3.0 = 0.0s), deve estar em fase
        self.assertTrue(e.em_fase)
        e.receber_dano(30)
        self.assertEqual(e.hp, 50)

        # Avança mais 1.5s -> t=16.5s (mod 3.0 = 1.5s >= 1.2s), deve estar fora de fase
        e.update(dt=1.5, pos_alvo=alvo)
        self.assertFalse(e.em_fase)
        e.receber_dano(10)
        self.assertEqual(e.hp, 40)

    def test_phasing_movement_uninterrupted_in_and_out_of_phase(self):
        """Garante que a perseguição beeline do inimigo ocorre sem interrupção tanto em fase quanto fora dela."""
        e = InimigoPhasing(x=0.0, y=0.0, velocidade=100.0, tempo_ciclo=3.0, tempo_fase=1.2)
        alvo = (500.0, 0.0)

        # 1.0s em fase: avança 100px
        e.update(dt=1.0, pos_alvo=alvo)
        self.assertTrue(e.em_fase)
        self.assertAlmostEqual(e.x, 100.0, places=2)

        # 1.0s fora de fase: avança mais 100px (total 200px)
        e.update(dt=1.0, pos_alvo=alvo)
        self.assertFalse(e.em_fase)
        self.assertAlmostEqual(e.x, 200.0, places=2)


class TestChallengerInimigoBlindadoFrontalArmor(unittest.TestCase):
    """Bateria de testes geométricos e angulares da armadura frontal do Inimigo Blindado."""

    def setUp(self):
        # Inimigo Blindado em (100, 100)
        self.e = InimigoBlindado(x=100.0, y=100.0, hp=100, reducao_frontal=0.30, arco_frontal_graus=90.0)
        self.cx = self.e.x + self.e.largura / 2.0
        self.cy = self.e.y + self.e.altura / 2.0
        # Orientado olhando para a direita (facing_x = 1.0, facing_y = 0.0)
        self.e.facing_x = 1.0
        self.e.facing_y = 0.0

    def test_frontal_armor_angle_exact_boundaries_origem(self):
        """
        Testa o arco de 90° (+-45°) usando pontos de origem do ataque:
        - theta = 0° (frontal): 30% redução (100 dano -> 70 efetivo)
        - theta = 44° (frontal): 30% redução (100 dano -> 70 efetivo)
        - theta = -44° (frontal): 30% redução (100 dano -> 70 efetivo)
        - theta = 46° (flanco): 100% dano total (100 dano -> 100 efetivo)
        - theta = -46° (flanco): 100% dano total (100 dano -> 100 efetivo)
        - theta = 180° (costas): 100% dano total (100 dano -> 100 efetivo)
        """
        raio = 100.0

        # 1. theta = 0° (frontal)
        x_0 = self.cx + math.cos(math.radians(0.0)) * raio
        y_0 = self.cy + math.sin(math.radians(0.0)) * raio
        self.assertTrue(self.e.is_ataque_frontal(origem_x=x_0, origem_y=y_0))

        # 2. theta = 44° (dentro de 45° -> frontal)
        x_44 = self.cx + math.cos(math.radians(44.0)) * raio
        y_44 = self.cy + math.sin(math.radians(44.0)) * raio
        self.assertTrue(self.e.is_ataque_frontal(origem_x=x_44, origem_y=y_44))

        # 3. theta = -44° (dentro de -45° -> frontal)
        x_m44 = self.cx + math.cos(math.radians(-44.0)) * raio
        y_m44 = self.cy + math.sin(math.radians(-44.0)) * raio
        self.assertTrue(self.e.is_ataque_frontal(origem_x=x_m44, origem_y=y_m44))

        # 4. theta = 46° (fora de 45° -> flanco)
        x_46 = self.cx + math.cos(math.radians(46.0)) * raio
        y_46 = self.cy + math.sin(math.radians(46.0)) * raio
        self.assertFalse(self.e.is_ataque_frontal(origem_x=x_46, origem_y=y_46))

        # 5. theta = -46° (fora de -45° -> flanco)
        x_m46 = self.cx + math.cos(math.radians(-46.0)) * raio
        y_m46 = self.cy + math.sin(math.radians(-46.0)) * raio
        self.assertFalse(self.e.is_ataque_frontal(origem_x=x_m46, origem_y=y_m46))

        # 6. theta = 180° (retaguarda)
        x_180 = self.cx + math.cos(math.radians(180.0)) * raio
        y_180 = self.cy + math.sin(math.radians(180.0)) * raio
        self.assertFalse(self.e.is_ataque_frontal(origem_x=x_180, origem_y=y_180))

    def test_frontal_damage_reduction_math_exactness(self):
        """Verifica a aplicação de 30% de redução numérica exata de dano."""
        # Dano 100 frontal: 100 * 0.70 = 70 efetivo
        e1 = InimigoBlindado(x=100.0, y=100.0, hp=100)
        e1.facing_x = 1.0
        e1.facing_y = 0.0
        e1.receber_dano(100, origem_x=self.cx + 50.0, origem_y=self.cy + 1.0)
        self.assertEqual(e1.hp, 30)

        # Dano 100 pelas costas: 100 efetivo -> morte
        e2 = InimigoBlindado(x=100.0, y=100.0, hp=100)
        e2.facing_x = 1.0
        e2.facing_y = 0.0
        e2.receber_dano(100, origem_x=self.cx - 50.0, origem_y=self.cy + 1.0)
        self.assertEqual(e2.hp, 0)
        self.assertFalse(e2.vivo)

    def test_incoming_projectile_direction_vector_modes(self):
        """Testa a atenuação de dano quando o ataque é fornecido via dir_ataque do projétil."""
        # Projétil vindo de frente (voando em (-1, 0)) -> frontal
        self.assertTrue(self.e.is_ataque_frontal(dir_ataque=(-1.0, 0.0)))

        # Projétil a 44° (-cos(44°), -sin(44°)) -> frontal
        ang_44 = math.radians(44.0)
        self.assertTrue(self.e.is_ataque_frontal(dir_ataque=(-math.cos(ang_44), -math.sin(ang_44))))

        # Projétil a 46° (-cos(46°), -sin(46°)) -> flanco
        ang_46 = math.radians(46.0)
        self.assertFalse(self.e.is_ataque_frontal(dir_ataque=(-math.cos(ang_46), -math.sin(ang_46))))

        # Projétil vindo de trás (voando em (1, 0)) -> costas
        self.assertFalse(self.e.is_ataque_frontal(dir_ataque=(1.0, 0.0)))


class TestChallengerFastEnemyTwoShotCalibration(unittest.TestCase):
    """Bateria de testes de calibração de combate do Inimigo Rápido (2 tiros de pistola de 17 dano)."""

    def test_fast_enemy_two_shot_calibration_25hp(self):
        """
        Valida que o Inimigo Rápido com 25 HP é eliminado em exatamente 2 disparos de pistola (17 dano cada):
        - Disparo 1 (17 dano): HP cai para 8 (vivo == True).
        - Disparo 2 (17 dano): HP cai para -9 <= 0 (vivo == False).
        """
        e = InimigoRapido(x=0.0, y=0.0, hp=25)
        self.assertEqual(e.hp, 25)

        # 1º Tiro (17 de Dano)
        e.receber_dano(17)
        self.assertEqual(e.hp, 8)
        self.assertTrue(e.vivo)

        # 2º Tiro (17 de Dano) -> Eliminação
        e.receber_dano(17)
        self.assertLessEqual(e.hp, 0)
        self.assertFalse(e.vivo)

    def test_fast_enemy_damage_boundary_thresholds(self):
        """Valida que valores abaixo do limiar de 25 não eliminam em 2 tiros de 12 dano (total 24)."""
        e = InimigoRapido(x=0.0, y=0.0, hp=25)

        # 2 tiros de 12 dano = 24 dano -> Sobrevive com 1 HP
        e.receber_dano(12)
        e.receber_dano(12)
        self.assertEqual(e.hp, 1)
        self.assertTrue(e.vivo)

        # 1 tiro adicional de 1 dano -> Eliminação
        e.receber_dano(1)
        self.assertEqual(e.hp, 0)
        self.assertFalse(e.vivo)


class TestChallengerScavengerAndDropStackingStress(unittest.TestCase):
    """Bateria de testes de stress do Sistema Scavenger e Multiplicadores da Config 15."""

    def setUp(self):
        self.scavenger_sys = SistemaScavenger(dist_maxima=600.0)
        self.sistema_drops = SistemaDrops()

    def test_drop_age_scavenger_selection_boundaries_099_vs_101(self):
        """
        Verifica o período de carência do drop para seleção de scavenger (10.0s):
        - Drop com idade 9.99s: não elegível, nenhum scavenger selecionado.
        - Drop com idade 10.01s: elegível, scavenger selecionado entre candidatos válidos.
        """
        drop = ItemDrop(x=200.0, y=200.0, tipo="xp", valor=10, tempo_scavenger=10.0)
        drop.tempo_decorrido = 9.99

        # 4 inimigos válidos
        e1 = InimigoPadrao(x=210.0, y=200.0)
        e2 = InimigoPadrao(x=220.0, y=200.0)
        e3 = InimigoPadrao(x=230.0, y=200.0)
        e4 = InimigoPadrao(x=300.0, y=200.0)
        todos = [e1, e2, e3, e4]

        # 1. Com 9.99s, nenhum scavenger é selecionado
        self.assertFalse(drop.elegivel_scavenger())
        self.assertIsNone(self.scavenger_sys.selecionar_scavenger(todos, [drop]))

        # 2. Com 10.01s, drop torna-se elegível e e4 é selecionado (os 3 mais próximos e1, e2, e3 são excluídos)
        drop.tempo_decorrido = 10.01
        self.assertTrue(drop.elegivel_scavenger())
        escolhido = self.scavenger_sys.selecionar_scavenger(todos, [drop])
        self.assertEqual(escolhido, e4)
        self.assertEqual(self.scavenger_sys.scavenger_atual, e4)

    def test_scavenger_candidate_pool_exclusion_rule_3_vs_4_enemies(self):
        """
        Verifica a regra de exclusão dos 3 inimigos mais próximos:
        - Com exatamente 3 inimigos na tela: nenhum pode ser scavenger (pool restante = 0).
        - Com 4 inimigos na tela: exatamente o 4º mais distante é selecionado.
        """
        drop = ItemDrop(x=100.0, y=100.0, tipo="xp", valor=10, tempo_scavenger=10.0)
        drop.tempo_decorrido = 10.5

        e1 = InimigoPadrao(x=120.0, y=100.0)  # dist 20px
        e2 = InimigoPadrao(x=140.0, y=100.0)  # dist 40px
        e3 = InimigoPadrao(x=160.0, y=100.0)  # dist 60px
        pool_3 = [e1, e2, e3]

        # Pool de 3 inimigos -> Nenhum selecionado
        self.assertIsNone(self.scavenger_sys.selecionar_scavenger(pool_3, [drop]))

        # Adiciona o 4º inimigo
        e4 = InimigoPadrao(x=250.0, y=100.0)  # dist 150px
        pool_4 = [e1, e2, e3, e4]

        # Pool de 4 inimigos -> e4 selecionado
        escolhido = self.scavenger_sys.selecionar_scavenger(pool_4, [drop])
        self.assertEqual(escolhido, e4)

    def test_scavenger_distance_cutoff_above_600px(self):
        """Inimigos a mais de 600px de distância do drop são descartados da seleção."""
        drop = ItemDrop(x=0.0, y=0.0, tipo="xp", valor=10, tempo_scavenger=10.0)
        drop.tempo_decorrido = 10.5

        e1 = InimigoPadrao(x=50.0, y=0.0)
        e2 = InimigoPadrao(x=100.0, y=0.0)
        e3 = InimigoPadrao(x=150.0, y=0.0)
        # 4º inimigo além de 600px (x=650.0)
        e4_too_far = InimigoPadrao(x=650.0, y=0.0)

        todos = [e1, e2, e3, e4_too_far]
        # Como e4 está >600px, o número de candidatos válidos <= 600px é apenas 3 -> nenhum selecionado
        self.assertIsNone(self.scavenger_sys.selecionar_scavenger(todos, [drop]))

    def test_scavenger_eats_drop_no_player_reward(self):
        """Quando o Scavenger alcança o drop, o item é destruído sem conceder recompensas ao jogador."""
        drop = ItemDrop(x=200.0, y=200.0, tipo="cura", valor=35, tempo_scavenger=10.0)
        drop.tempo_decorrido = 10.5

        jogador = Jogador(x=50.0, y=50.0, hp_max=150)
        jogador.hp = 50

        # Inimigo Scavenger posicionado exatamente sobre o drop
        e1 = InimigoPadrao(x=210.0, y=200.0)
        e2 = InimigoPadrao(x=220.0, y=200.0)
        e3 = InimigoPadrao(x=230.0, y=200.0)
        scav = InimigoPadrao(x=200.0, y=200.0)
        todos = [e1, e2, e3, scav]

        self.scavenger_sys.scavenger_atual = scav
        self.scavenger_sys.drop_alvo = drop

        # Update processa a colisão do scavenger com o drop
        self.scavenger_sys.update(dt=0.01, lista_inimigos=todos, lista_drops=[drop])

        # Drop consumido
        self.assertFalse(drop.ativo)
        self.assertTrue(drop.coletado)
        # Jogador não recebeu cura (HP permanece 50)
        self.assertEqual(jogador.hp, 50)

    def test_player_collection_config_15_exact_2x_multipliers_stress(self):
        """
        Sob a Config 15 (mult_valor_drop = 2.0):
        - XP Gem (10) -> 20 XP
        - Cura (35) -> 70 HP
        - Arma Especial (Minigun 150) -> 300 Munição
        - Drone (30s) -> 60s Duração
        """
        jogador = Jogador(x=100.0, y=100.0, hp_max=200)
        jogador.hp = 30
        jogador.xp = 0

        # 1. Gema de XP
        drop_xp = ItemDrop(x=102.0, y=102.0, tipo="xp", valor=10)
        self.sistema_drops.drops = [drop_xp]
        eventos = self.sistema_drops.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["valor"], 20)
        self.assertEqual(jogador.xp, 20)

        # 2. Caixa de Cura
        drop_cura = ItemDrop(x=102.0, y=102.0, tipo="cura", valor=35)
        self.sistema_drops.drops = [drop_cura]
        eventos_cura = self.sistema_drops.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos_cura), 1)
        self.assertEqual(eventos_cura[0]["valor"], 70)
        self.assertEqual(jogador.hp, 30 + 70)  # 100 HP

        # 3. Caixa de Arma Especial
        drop_arma = ItemDrop(x=102.0, y=102.0, tipo="arma", valor=1)
        self.sistema_drops.drops = [drop_arma]
        eventos_arma = self.sistema_drops.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos_arma), 1)
        self.assertIsNotNone(jogador.arma_especial)
        # A munição deve ser o dobro da munição máxima padrão
        classe_arma = type(jogador.arma_especial)
        arma_padrao = classe_arma()
        self.assertEqual(jogador.arma_especial.municao_max, arma_padrao.municao_max * 2)
        self.assertEqual(jogador.arma_especial.municao_atual, arma_padrao.municao_max * 2)

        # 4. Caixa de Equipamento / Drone
        drop_equip = ItemDrop(x=102.0, y=102.0, tipo="equipamento", valor=1)
        self.sistema_drops.drops = [drop_equip]
        eventos_equip = self.sistema_drops.coletar_jogador(jogador, mult_valor_drop=2.0)
        self.assertEqual(len(eventos_equip), 1)
        self.assertIsNotNone(jogador.drone)
        self.assertAlmostEqual(jogador.drone.tempo_vida, 60.0, places=2)
        self.assertAlmostEqual(jogador.drone.tempo_restante, 60.0, places=2)


if __name__ == "__main__":
    unittest.main()
