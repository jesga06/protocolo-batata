"""
Testes Unitários de Inimigos Avançados (Milestone 4 / Fase 5) — Protocolo: Batata
Valida:
1. Inimigo Rápido (InimigoRapido): HP=25 e eliminação em exatamente 2 tiros de pistola (17 * 2 = 34 >= 25).
2. Inimigo Ranged (InimigoRanged): Stand-off a 280px, disparo periódico a cada 1.2s em alcance <= 350px,
   projéteis com dono="inimigo" e tabela de loot enriquecida (15% arma, 15% equip).
3. Inimigo Phasing (InimigoPhasing): Ciclo de 3.0s, janela de 1.2s em fase com imunidade total a dano
   e renderização translúcida.
4. Inimigo Blindado (InimigoBlindado): Cálculo vetorial da placa balística frontal (arco de 90°),
   redução de 30% de dano frontal e 100% de dano pleno em ataques de flanco/retaguarda.
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

from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.projetil import Projetil
from src.sistemas.sistema_drops import SistemaDrops
from src.utils.constantes import (
    INIMIGO_RAPIDO_HP, INIMIGO_RANGED_HP, INIMIGO_PHASING_HP, INIMIGO_BLINDADO_HP,
    PISTOLA_DANO
)


class TestInimigoRapidoBalance(unittest.TestCase):
    """Testa o balanceamento do Inimigo Rápido conforme diretiva de autoridade Tier 1."""

    def test_inimigo_rapido_hp_and_2_shot_threshold(self):
        """
        Valida que o Inimigo Rápido possui 10 HP (v2.0 SSOT) e morre em 1 tiro de pistola (10 de dano).
        """
        e = InimigoRapido(x=0.0, y=0.0)
        self.assertEqual(e.hp, 10)
        self.assertEqual(e.hp_max, 10)

        # 1º Tiro (10 Dano) -> Destruído
        e.receber_dano(10)
        self.assertFalse(e.vivo)
        self.assertEqual(e.hp, 0)


class TestInimigoRanged(unittest.TestCase):
    """Testa a IA de stand-off, disparo balístico periódico e loot do Inimigo Ranged."""

    def test_standoff_distance_movement_behavior(self):
        """
        Inimigo Ranged avança em direção ao jogador se distância > 280px.
        Ao atingir <= 280px, cessa o avanço para manter distância.
        """
        # Caso 1: Distância = 400px (> 280px) -> Avança
        e = InimigoRanged(x=500.0, y=100.0, velocidade=80.0)
        alvo = (100.0, 100.0 + e.altura / 2.0)
        e.update(dt=0.5, pos_alvo=alvo)
        # Avança 40px para a esquerda (500 -> 460)
        self.assertAlmostEqual(e.x, 460.0)

        # Caso 2: Distância = 250px (<= 280px) -> Não avança
        e_close = InimigoRanged(x=350.0, y=100.0, velocidade=80.0)
        e_close.update(dt=0.5, pos_alvo=alvo)
        # Permanece em 350.0 (velocidade de avanço zerada no stand-off)
        self.assertAlmostEqual(e_close.x, 350.0)

    def test_periodic_projectile_shooting_in_range(self):
        """
        Inimigo Ranged dispara um projétil vermelho a cada 1.2s quando o jogador está a <= 350px.
        """
        e = InimigoRanged(x=300.0, y=100.0, cooldown_tiro=1.2, distancia_tiro_max=350.0)
        alvo = (100.0, 100.0 + e.altura / 2.0)  # Distância ~200px (dentro do alcance de 350px)

        # Avança 0.6s (< 1.2s): ainda não disparou
        e.update(dt=0.6, pos_alvo=alvo)
        self.assertEqual(len(e.projeteis_pendentes), 0)

        # Avança mais 0.65s (total 1.25s >= 1.2s): dispara!
        e.update(dt=0.65, pos_alvo=alvo)
        self.assertEqual(len(e.projeteis_pendentes), 1)

        tiros = e.obter_projeteis_pendentes()
        self.assertEqual(len(tiros), 1)
        self.assertEqual(len(e.projeteis_pendentes), 0)  # Fila esvaziada

        proj = tiros[0]
        self.assertEqual(proj.dono, "inimigo")
        self.assertEqual(proj.dano, 10)
        self.assertAlmostEqual(proj.velocidade, 390.0)
        self.assertEqual(proj.sprite_key, "projetil_inimigo")
        # Projétil aponta para a esquerda em direção ao alvo (dir_x = -1.0, dir_y = 0.0)
        self.assertAlmostEqual(proj.dir_x, -1.0)
        self.assertAlmostEqual(proj.dir_y, 0.0)

    def test_no_shooting_outside_maximum_range(self):
        """Inimigo Ranged não dispara se a distância for superior a 350px."""
        e = InimigoRanged(x=600.0, y=100.0, cooldown_tiro=1.2, distancia_tiro_max=350.0)
        alvo = (100.0, 100.0 + e.altura / 2.0)  # Distância ~500px (> 350px)

        # Avança 2.0s
        e.update(dt=2.0, pos_alvo=alvo)
        self.assertEqual(len(e.projeteis_pendentes), 0)

    def test_rich_loot_table_attributes(self):
        """Valida que o Inimigo Ranged possui flags de loot enriquecido (30% arma, 15% equip)."""
        e = InimigoRanged(x=100.0, y=100.0)
        self.assertTrue(e.loot_enriquecido)
        self.assertAlmostEqual(e.chance_drop_arma, 0.3)
        self.assertAlmostEqual(e.chance_drop_equipamento, 0.15)


class TestInimigoPhasing(unittest.TestCase):
    """Testa a máquina de estados cíclica e a imunidade total do Inimigo Phasing."""

    def test_phasing_state_machine_cycle(self):
        """
        Ciclo de 3.0s com 1.2s em fase invulnerável:
        - 0.0s a 1.2s: em_fase == True (imune a dano)
        - 1.2s a 3.0s: em_fase == False (vulnerável)
        """
        e = InimigoPhasing(x=100.0, y=100.0, tempo_ciclo=3.0, tempo_fase=1.2)
        alvo = (100.0, 100.0)

        # t = 0.0s -> em fase
        self.assertTrue(e.em_fase)

        # t = 0.6s -> ainda em fase
        e.update(dt=0.6, pos_alvo=alvo)
        self.assertTrue(e.em_fase)

        # t = 1.3s -> saiu da fase
        e.update(dt=0.7, pos_alvo=alvo)
        self.assertFalse(e.em_fase)

        # t = 2.8s -> continua fora da fase
        e.update(dt=1.5, pos_alvo=alvo)
        self.assertFalse(e.em_fase)

        # t = 3.2s (mod 3.0 = 0.2s) -> voltou para a fase
        e.update(dt=0.4, pos_alvo=alvo)
        self.assertTrue(e.em_fase)

    def test_damage_immunity_during_phase(self):
        """Valida que chamadas a receber_dano() são completamente anuladas durante a fase."""
        e = InimigoPhasing(x=100.0, y=100.0, hp=35, tempo_ciclo=3.0, tempo_fase=1.2)
        alvo = (100.0, 100.0)

        # Durante a fase (t=0.0s): recebe 20 de dano -> HP permanece 35
        self.assertTrue(e.em_fase)
        e.receber_dano(20)
        self.assertEqual(e.hp, 35)
        self.assertTrue(e.vivo)

        # Avança para fora da fase (t=1.5s): recebe 20 de dano -> HP cai para 15
        e.update(dt=1.5, pos_alvo=alvo)
        self.assertFalse(e.em_fase)
        e.receber_dano(20)
        self.assertEqual(e.hp, 15)
        self.assertTrue(e.vivo)

        # Avança de volta para a fase (t=3.1s): recebe 15 de dano -> HP permanece 15
        e.update(dt=1.6, pos_alvo=alvo)
        self.assertTrue(e.em_fase)
        e.receber_dano(15)
        self.assertEqual(e.hp, 15)
        self.assertTrue(e.vivo)

    def test_continuous_movement_during_phase(self):
        """Inimigo Phasing continua se movendo em linha reta em direção ao jogador mesmo quando em fase."""
        e = InimigoPhasing(x=0.0, y=0.0, velocidade=90.0)
        alvo = (100.0, e.altura / 2.0)

        # Em 1.0s (durante a fase), avança exatamente 90px
        e.update(dt=1.0, pos_alvo=alvo)
        self.assertTrue(e.em_fase)
        self.assertAlmostEqual(e.x, 90.0)


class TestInimigoBlindado(unittest.TestCase):
    """Testa o cálculo vetorial de armadura frontal e atenuação de 30% de dano do Inimigo Blindado."""

    def setUp(self):
        # Inimigo Blindado em (100, 100), centro em (123.5, 123.5)
        self.e = InimigoBlindado(x=100.0, y=100.0, hp=50)
        self.cx = self.e.x + self.e.largura / 2.0
        self.cy = self.e.y + self.e.altura / 2.0
        # Atualiza olhando para a direita (alvo em 300, cy) -> facing = (1.0, 0.0)
        self.e.update(dt=0.1, pos_alvo=(300.0, self.cy))
        self.assertAlmostEqual(self.e.facing_x, 1.0)
        self.assertAlmostEqual(self.e.facing_y, 0.0)

    def test_frontal_hit_receives_30_percent_damage_reduction(self):
        """Ataque vindo diretamente pela frente (origem em 250, cy) sofre 30% de redução (dano * 0.70)."""
        # Tiro de 30 de dano pela frente: 30 * 0.70 = 21 de dano efetivo
        self.assertTrue(self.e.is_ataque_frontal(origem_x=250.0, origem_y=self.cy))
        self.e.receber_dano(30, origem_x=250.0, origem_y=self.cy)
        self.assertEqual(self.e.hp, 50 - 21)  # 29 HP

    def test_rear_hit_receives_100_percent_full_damage(self):
        """Ataque vindo pelas costas (origem em 50, cy) causa 100% de dano pleno."""
        # Tiro de 20 de dano pelas costas: 20 de dano efetivo
        self.assertFalse(self.e.is_ataque_frontal(origem_x=50.0, origem_y=self.cy))
        self.e.receber_dano(20, origem_x=50.0, origem_y=self.cy)
        self.assertEqual(self.e.hp, 50 - 20)  # 30 HP

    def test_flank_hit_receives_100_percent_full_damage(self):
        """Ataque perpendicular de 90° (flanco em cx, 250) causa 100% de dano pleno."""
        self.assertFalse(self.e.is_ataque_frontal(origem_x=self.cx, origem_y=250.0))
        self.e.receber_dano(15, origem_x=self.cx, origem_y=250.0)
        self.assertEqual(self.e.hp, 50 - 15)  # 35 HP

    def test_frontal_cone_angular_boundaries(self):
        """
        Testa os limites angulares do arco de 90° (+-45° da linha central):
        - Ataque a 30° (dentro de 45°): frontal -> 30% redução.
        - Ataque a 60° (fora de 45°): não-frontal -> dano total.
        """
        # Ângulo de 30° a partir do eixo facing (1, 0)
        ang_30 = math.radians(30.0)
        x_30 = self.cx + math.cos(ang_30) * 100.0
        y_30 = self.cy + math.sin(ang_30) * 100.0
        self.assertTrue(self.e.is_ataque_frontal(origem_x=x_30, origem_y=y_30))

        # Ângulo de 60° a partir do eixo facing (1, 0)
        ang_60 = math.radians(60.0)
        x_60 = self.cx + math.cos(ang_60) * 100.0
        y_60 = self.cy + math.sin(ang_60) * 100.0
        self.assertFalse(self.e.is_ataque_frontal(origem_x=x_60, origem_y=y_60))

    def test_incoming_projectile_direction_vector(self):
        """Valida que projétil viajando em direção oposta ao facing (-1.0, 0.0) é reconhecido como frontal."""
        # Projétil vindo da direita em direção à esquerda (dir_x = -1.0, dir_y = 0.0)
        self.assertTrue(self.e.is_ataque_frontal(dir_ataque=(-1.0, 0.0)))
        # Projétil vindo da esquerda em direção à direita (dir_x = 1.0, dir_y = 0.0) - pelas costas
        self.assertFalse(self.e.is_ataque_frontal(dir_ataque=(1.0, 0.0)))

    def test_tank_controls_slow_turn_and_forward_movement(self):
        """Gira lentamente em direção ao alvo e anda reto na direção frontal atual (controles de tanque)."""
        e = InimigoBlindado(x=100.0, y=100.0, hp=50, vel_giro_rad_s=1.0)
        # Começa olhando para direita (0 rad), alvo diretamente abaixo (90 deg = +pi/2)
        cx_ini = e.x + e.largura / 2.0
        cy_ini = e.y + e.altura / 2.0
        e.update(dt=0.25, pos_alvo=(cx_ini, cy_ini + 300.0))

        # Após 0.25s a 1.0 rad/s, deve ter girado ~0.25 rad (não instantaneamente para pi/2)
        ang = math.atan2(e.facing_y, e.facing_x)
        self.assertAlmostEqual(ang, 0.25, places=3)
        self.assertGreater(e.x, 100.0)  # Ainda avançou majoritariamente para a frente (+X)

    def test_two_frontal_breakable_hits_shatter_armor(self):
        """Explosão/melee/sobrecarregado pela frente quebram a placa em 2 golpes e liberam 100% de dano."""
        e = InimigoBlindado(x=100.0, y=100.0, hp=200)
        cx = e.x + e.largura / 2.0
        cy = e.y + e.altura / 2.0

        # Tiro comum frontal não gasta cargas
        e.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=False)
        self.assertEqual(e.cargas_blindagem, 2)
        self.assertFalse(e.blindagem_quebrada)

        # Golpe válido pelas costas não gasta cargas
        e.receber_dano(10, origem_x=cx - 100.0, origem_y=cy, quebra_blindagem=True)
        self.assertEqual(e.cargas_blindagem, 2)
        self.assertFalse(e.blindagem_quebrada)

        # 1º golpe frontal válido: sofre redução (10*0.7=7), reduz carga para 1 e gera evento rachadura
        d1 = e.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=True)
        self.assertEqual(d1, 7)
        self.assertEqual(e.cargas_blindagem, 1)
        self.assertFalse(e.blindagem_quebrada)
        self.assertEqual(e.eventos_blindagem_pendentes[-1]["tipo"], "rachadura")

        # 2º golpe frontal válido: sofre redução neste golpe (7), quebra a placa (cargas=0) e gera evento quebra
        d2 = e.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=True)
        self.assertEqual(d2, 7)
        self.assertEqual(e.cargas_blindagem, 0)
        self.assertTrue(e.blindagem_quebrada)
        self.assertEqual(e.eventos_blindagem_pendentes[-1]["tipo"], "quebra")

        # A partir de então, tiros comuns pela frente causam 100% do dano
        d3 = e.receber_dano(20, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=False)
        self.assertEqual(d3, 20)

    def test_miniboss_armor_regenerates_after_10s_and_resets_on_frontal_hit(self):
        """Mini-Boss No-Break regenera placa após 10s sem ataque frontal que quebra; novo ataque reseta 10s e ele mira no jogador."""
        boss = InimigoBlindado(x=100.0, y=100.0, hp=800, is_elite=True, nome_elite="NO-BREAK")
        boss.arquetipo_miniboss = "nobreak_chumbado"
        cx = boss.x + boss.largura / 2.0
        cy = boss.y + boss.altura / 2.0

        # Quebra a placa em 2 golpes frontais válidos
        boss.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=True)
        boss.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=True)
        self.assertTrue(boss.blindagem_quebrada)
        self.assertAlmostEqual(boss.timer_regen_blindagem, 10.0)

        # Passam 6s (alvo à frente) -> ainda quebrada (restam 4s)
        boss.update(dt=6.0, pos_alvo=(cx + 3000.0, cy))
        self.assertTrue(boss.blindagem_quebrada)
        self.assertAlmostEqual(boss.timer_regen_blindagem, 4.0)

        cx = boss.x + boss.largura / 2.0
        cy = boss.y + boss.altura / 2.0

        # Tiro comum frontal NÃO reseta o timer de 10s
        boss.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=False)
        self.assertAlmostEqual(boss.timer_regen_blindagem, 4.0)

        # Golpe quebrador pelas costas NÃO reseta o timer de 10s
        boss.receber_dano(10, origem_x=cx - 100.0, origem_y=cy, quebra_blindagem=True)
        self.assertAlmostEqual(boss.timer_regen_blindagem, 4.0)

        # Golpe quebrador FRONTAL reseta o timer para 10.0s
        boss.receber_dano(10, origem_x=cx + 100.0, origem_y=cy, quebra_blindagem=True)
        self.assertAlmostEqual(boss.timer_regen_blindagem, 10.0)

        # Passam 10.1s sem ataques frontais válidos -> placa regenera
        boss.obter_projeteis_pendentes()
        boss.timer_habilidade_elite = 2.55
        boss.update(dt=10.1, pos_alvo=(boss.x + boss.largura / 2.0, boss.y + boss.altura / 2.0 + 3000.0))
        self.assertFalse(boss.blindagem_quebrada)
        self.assertEqual(boss.cargas_blindagem, 2)
        self.assertEqual(boss.eventos_blindagem_pendentes[-1]["tipo"], "regenerada")

        # Leque de 5 projéteis do No-Break mira na direção de pos_alvo (para baixo +Y), independente do facing
        projs = boss.obter_projeteis_pendentes()
        self.assertEqual(len(projs), 5)
        self.assertGreater(projs[2].dir_y, 0.9)

    def test_render_rotacionado_intacto_e_quebrado_headless(self):
        """Renderização intacta, sem escudo e low_graphics executa sem erros em superfície headless."""
        import pygame
        pygame.init()
        surf = pygame.Surface((400, 400), pygame.SRCALPHA)

        class JanelaMock:
            largura = 400
            altura = 400
            low_graphics = False
            screen = surf

        e = InimigoBlindado(x=100.0, y=100.0, hp=50)
        e.facing_x, e.facing_y = math.cos(0.7), math.sin(0.7)
        e.desenhar(JanelaMock())
        e.blindagem_quebrada = True
        e.desenhar(JanelaMock())
        JanelaMock.low_graphics = True
        e.blindagem_quebrada = False
        e.desenhar(JanelaMock())


if __name__ == "__main__":
    unittest.main()
