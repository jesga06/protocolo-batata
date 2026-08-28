"""
Adversarial Stress Test Suite — Protocolo: Batata
EMPIRICAL CHALLENGER VERIFICATION (teamwork_preview_challenger_1)

Tests:
1. Melee 45° Cone Boundary Conditions & Precision:
   - 22.4° (hit) vs 22.6° (miss)
   - Angle wrap-around across [-pi, +pi] boundary (-179° vs +179° -> 2° -> hit)
   - Radial reach at 83.9px (hit) vs 84.1px (miss)
   - 10 enemies inside cone: all 10 receive 10 dmg, exactly 2 closest receive 360 px/s knockback.
2. XP & Drop Boundary Cases:
   - Awarding 500 XP from level 1 sequentially levels up (L1->L12, 60 leftover, 500 total).
   - Drop lifetime at 9.9s (active) vs 10.05s (expired).
   - Scavenger grace period at 0.9s (ineligible) vs 1.05s (eligible).
3. Configuration Multipliers Stress Testing:
   - All 20 gameplay configurations enabled simultaneously at extreme values (no NaN, no overflow, exact math products).
   - Locked configurations strictly apply neutral baseline (no active buffs).
"""

import math
import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"

from src.armas.melee import Melee
from src.entidades.drop import ItemDrop
from src.sistemas.sistema_drops import SistemaDrops
from src.sistemas.sistema_xp import SistemaXP
from src.sistemas.sistema_scavenger import SistemaScavenger
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY, TODAS_CONFIGURACOES
from src.sistemas.config_efeitos import calcular_modificadores, ModificadoresGameplay
from src.sistemas.config_sistema import GerenciadorConfiguracoes


class MockEnemy:
    """Mock enemy for testing hitboxes, health, and knockback."""
    def __init__(self, x: float, y: float, hp: int = 50, largura: int = 28, altura: int = 28):
        self.x = float(x)
        self.y = float(y)
        self.largura = largura
        self.altura = altura
        self.hp = hp
        self.vivo = True
        self.knockback_aplicado = False
        self.kb_dir_x = 0.0
        self.kb_dir_y = 0.0
        self.kb_forca = 0.0

    def receber_dano(self, quantidade: int):
        self.hp -= quantidade
        if self.hp <= 0:
            self.vivo = False

    def aplicar_knockback(self, dir_x: float, dir_y: float, forca: float):
        self.knockback_aplicado = True
        self.kb_dir_x = dir_x
        self.kb_dir_y = dir_y
        self.kb_forca = forca


class TestChallengerR1MeleeCone(unittest.TestCase):
    """Stress testing R1: Melee 45° cone directional combat."""

    def setUp(self):
        self.melee = Melee(dano=10, alcance=84.0, knockback_forca=360.0, max_alvos_knockback=2, arco_graus=45.0)

    def test_cone_angle_boundary_22_4_vs_22_6(self):
        """
        45° cone has half-angle of 22.5°.
        An enemy at 22.4° must be HIT.
        An enemy at 22.6° must be MISSED.
        """
        origem_x, origem_y = 100.0, 100.0
        dist = 50.0  # Well within 84px reach
        mira_ang = 0.0  # Aiming along +X axis (0 degrees)

        # 1. Target at 22.4 degrees
        ang_hit = math.radians(22.4)
        target_hit = MockEnemy(
            x=origem_x + dist * math.cos(ang_hit) - 14.0,
            y=origem_y + dist * math.sin(ang_hit) - 14.0
        )

        # 2. Target at 22.6 degrees
        ang_miss = math.radians(22.6)
        target_miss = MockEnemy(
            x=origem_x + dist * math.cos(ang_miss) - 14.0,
            y=origem_y + dist * math.sin(ang_miss) - 14.0
        )

        atingidos = self.melee.executar_ataque(
            origem_x=origem_x,
            origem_y=origem_y,
            lista_inimigos=[target_hit, target_miss],
            angulo_mira=mira_ang
        )

        self.assertIn(target_hit, atingidos, "Enemy at 22.4° (inside 22.5° half-arc) must be HIT")
        self.assertNotIn(target_miss, atingidos, "Enemy at 22.6° (outside 22.5° half-arc) must be MISSED")
        self.assertEqual(target_hit.hp, 40)
        self.assertEqual(target_miss.hp, 50)

    def test_cone_angle_wraparound_minus_179_plus_179(self):
        """
        Aim at -179° (-3.124 rad) and enemy at +179° (+3.124 rad).
        Angular delta across the [-pi, +pi] branch cut is exactly 2.0° <= 22.5°.
        The attack MUST hit.
        """
        origem_x, origem_y = 200.0, 200.0
        dist = 60.0
        ang_mira = math.radians(-179.0)
        ang_enemy = math.radians(179.0)

        enemy = MockEnemy(
            x=origem_x + dist * math.cos(ang_enemy) - 14.0,
            y=origem_y + dist * math.sin(ang_enemy) - 14.0
        )

        atingidos = self.melee.executar_ataque(
            origem_x=origem_x,
            origem_y=origem_y,
            lista_inimigos=[enemy],
            angulo_mira=ang_mira
        )

        self.assertEqual(len(atingidos), 1, "Wraparound across +/-180° boundary must be detected as 2° delta")
        self.assertIn(enemy, atingidos)
        self.assertEqual(enemy.hp, 40)
        self.assertTrue(enemy.knockback_aplicado)
        self.assertEqual(enemy.kb_forca, 360.0)

    def test_radial_reach_83_9_vs_84_1(self):
        """
        Radial reach is exactly 84.0px.
        Enemy centered at 83.9px must be HIT.
        Enemy centered at 84.1px must be MISSED.
        """
        origem_x, origem_y = 100.0, 100.0
        ang_mira = 0.0

        # Enemy at 83.9px
        e_hit = MockEnemy(x=origem_x + 83.9 - 14.0, y=origem_y - 14.0)
        # Enemy at 84.1px
        e_miss = MockEnemy(x=origem_x + 84.1 - 14.0, y=origem_y - 14.0)

        atingidos = self.melee.executar_ataque(
            origem_x=origem_x,
            origem_y=origem_y,
            lista_inimigos=[e_hit, e_miss],
            angulo_mira=ang_mira
        )

        self.assertIn(e_hit, atingidos, "Enemy at 83.9px <= 84.0px reach must be HIT")
        self.assertNotIn(e_miss, atingidos, "Enemy at 84.1px > 84.0px reach must be MISSED")
        self.assertEqual(e_hit.hp, 40)
        self.assertEqual(e_miss.hp, 50)

    def test_10_enemies_in_cone_damage_and_knockback_limit(self):
        """
        When 10 enemies are inside the 45° cone:
        - ALL 10 must receive 10 damage.
        - ONLY the 2 closest enemies receive 360.0 px/s knockback.
        - The remaining 8 enemies do NOT receive knockback.
        """
        origem_x, origem_y = 0.0, 0.0
        ang_mira = 0.0

        enemies = []
        for i in range(10):
            # Place at distances: 20px, 25px, 30px, ..., 65px (all within 84px)
            d = 20.0 + i * 5.0
            e = MockEnemy(x=d - 14.0, y=0.0 - 14.0, hp=50)
            enemies.append(e)

        atingidos = self.melee.executar_ataque(
            origem_x=origem_x,
            origem_y=origem_y,
            lista_inimigos=enemies,
            angulo_mira=ang_mira
        )

        self.assertEqual(len(atingidos), 10, "All 10 enemies in cone must be hit")

        # Check all 10 took 10 damage
        for idx, e in enumerate(enemies):
            self.assertEqual(e.hp, 40, f"Enemy #{idx} must have 40 HP remaining")

        # Check knockback on 2 closest
        self.assertTrue(enemies[0].knockback_aplicado, "Closest enemy #0 must receive knockback")
        self.assertEqual(enemies[0].kb_forca, 360.0)
        self.assertTrue(enemies[1].knockback_aplicado, "2nd closest enemy #1 must receive knockback")
        self.assertEqual(enemies[1].kb_forca, 360.0)

        # Check other 8 did NOT receive knockback
        for idx in range(2, 10):
            self.assertFalse(
                enemies[idx].knockback_aplicado,
                f"Enemy #{idx} (rank {idx+1}) must NOT receive knockback when max_alvos=2"
            )


class TestChallengerR2DropsXP(unittest.TestCase):
    """Stress testing R2: Drops, Lifetimes & XP Leveling."""

    def test_award_500_xp_in_one_go_multi_level_progression(self):
        """
        Awarding 500 XP from level 1:
        Level 1: 15 XP -> remaining 485 XP (L2)
        Level 2: 20 XP -> remaining 465 XP (L3)
        Level 3: 25 XP -> remaining 440 XP (L4)
        Level 4: 30 XP -> remaining 410 XP (L5)
        Level 5: 35 XP -> remaining 375 XP (L6)
        Level 6: 40 XP -> remaining 335 XP (L7)
        Level 7: 45 XP -> remaining 290 XP (L8)
        Level 8: 50 XP -> remaining 240 XP (L9)
        Level 9: 55 XP -> remaining 185 XP (L10)
        Level 10: 60 XP -> remaining 125 XP (L11)
        Level 11: 65 XP -> remaining 60 XP (L12)
        Level 12: requires 10 + 5*12 = 70 XP. 60 < 70, so stays at Level 12 with 60 leftover XP.
        Total sum of L1..L11 = 440 XP. 440 + 60 = 500 XP total.
        """
        sistema = SistemaXP(nivel_inicial=1, nivel_maximo=20)
        callback_history = []
        sistema.registrar_callback_level_up(lambda lvl: callback_history.append(lvl))

        niveis_ganhos = sistema.adicionar_xp(500)

        expected_levels = list(range(2, 13))  # [2, 3, ..., 12]
        self.assertEqual(niveis_ganhos, expected_levels)
        self.assertEqual(callback_history, expected_levels)
        self.assertEqual(sistema.nivel, 12, "Player should be level 12 after 500 XP")
        self.assertEqual(sistema.xp_atual, 60, "Residual XP must be exactly 60 without loss")
        self.assertEqual(sistema.xp_total, 500, "Total XP must be exactly 500")
        self.assertEqual(sistema.xp_para_proximo_nivel(12), 70)
        self.assertAlmostEqual(sistema.progresso_normalizado(), 60.0 / 70.0, places=5)

    def test_drop_lifetime_9_9s_vs_10_05s(self):
        """
        Drop has 10.0s lifetime.
        At 9.9s elapsed: active = True, tempo_restante = 0.1s.
        At 10.05s elapsed: active = False.
        """
        drop1 = ItemDrop(x=50, y=50, tipo="xp", valor=10, tempo_vida=10.0)
        drop1.update(9.9)
        self.assertTrue(drop1.ativo, "Drop at 9.9s must remain active")
        self.assertAlmostEqual(drop1.tempo_restante, 0.1, places=5)

        drop2 = ItemDrop(x=50, y=50, tipo="xp", valor=10, tempo_vida=10.0)
        drop2.update(10.05)
        self.assertFalse(drop2.ativo, "Drop at 10.05s must expire (ativo=False)")
        self.assertEqual(drop2.tempo_restante, 0.0)

    def test_scavenger_grace_period_0_9s_vs_1_05s(self):
        """
        Scavenger grace period is 1.0s.
        At 0.9s: drop is NOT eligible for scavenger capture.
        At 1.05s: drop IS eligible for scavenger capture.
        """
        drop = ItemDrop(x=100, y=100, tipo="cura", valor=25, tempo_vida=10.0, tempo_scavenger=1.0)
        drop.update(0.9)
        self.assertFalse(drop.elegivel_scavenger(), "At 0.9s, drop must NOT be eligible for scavenger")

        drop.update(0.15)  # Total 1.05s
        self.assertTrue(drop.elegivel_scavenger(), "At 1.05s, drop MUST be eligible for scavenger")


class TestChallengerR3ConfigurationMultipliers(unittest.TestCase):
    """Stress testing R3: Configuration Multipliers & Locked Isolation."""

    def test_all_20_gameplay_configs_simultaneously_extreme_values(self):
        """
        Activate all 20 gameplay configurations at their maximum multiplier settings.
        Verify:
        - Math does not overflow, NaN, or crash.
        - Calculated multipliers match exact theoretical products.
        """
        # Unlock all 20 configs
        unlocked = set(CONFIGURACOES_GAMEPLAY.keys())
        self.assertEqual(len(unlocked), 20, "There must be exactly 20 unlockable gameplay configs")

        # Pick extreme values for each
        extreme_actives = {
            "fps_cap": "15",                 # dano_inimigos_mult=0.7225, vel_inimigos_mult=0.81
            "graficos_qualidade": "baixa",   # hp_inimigos_mult=0.80
            "resolucao": "25%",              # drop_chance_bonus=0.50
            "vsync": "desligado",            # vel_jogador_mult=1.10
            "screen_shake": "ligado",        # dano_explosivos_mult=1.20
            "motion_blur": "ligado",         # vel_jogador_mult=1.15
            "hud": "desligado",              # xp_ganho_mult=1.25
            "damage_numbers": "ligado",      # critico_chance=0.15, critico_mult=2.0
            "zoom": "150%",                  # dano_armas_mult=1.20
            "movimento_mouse": "ligado",     # drop_chance_mult=1.40
            "keybinds": "pesadelo",          # dano_armas_mult=1.30
            "suavizacao_camera": "desligado",# vel_jogador_mult=1.08
            "auto_fire": "desligado",        # dano_armas_mult=1.15
            "inimigos_ranged": "ligado",     # loot_enriquecido=True
            "coleta_inimiga": "ligado",      # drops_valor_mult=2.0
            "velocidade_inimigos": "+50%",   # vel_inimigos_mult=1.50, xp_ganho_mult=1.40
            "vida_inimigos": "+100%",        # hp_inimigos_mult=2.00, drop_chance_bonus=0.40
            "iluminacao": "ligado",          # dano_fora_visao_mult=0.50
            "cores_invertidas": "ligado",    # dano_armas_mult=1.20
            "fogo_amigo": "ligado",          # dano_armas_mult=1.25, auto_dano=True
        }

        mods = calcular_modificadores(configs_desbloqueadas=unlocked, configs_ativas=extreme_actives)

        # Verify no NaN or Inf
        for field_name, val in mods.__dict__.items():
            if isinstance(val, float):
                self.assertFalse(math.isnan(val), f"Field {field_name} must not be NaN")
                self.assertFalse(math.isinf(val), f"Field {field_name} must not be Inf")

        # 1. Weapon Damage: 1.20 * 1.30 * 1.15 * 1.20 * 1.25 = 2.691
        expected_dano_armas = 1.20 * 1.30 * 1.15 * 1.20 * 1.25
        self.assertAlmostEqual(mods.dano_armas_mult, expected_dano_armas, places=5)
        self.assertAlmostEqual(mods.dano_armas_mult, 2.691, places=5)

        # 2. Player Speed: 1.10 * 1.15 * 1.08 = 1.3662
        expected_vel_jogador = 1.10 * 1.15 * 1.08
        self.assertAlmostEqual(mods.vel_jogador_mult, expected_vel_jogador, places=5)
        self.assertAlmostEqual(mods.vel_jogador_mult, 1.3662, places=5)

        # 3. XP Gain: 1.25 * 1.40 = 1.75
        expected_xp = 1.25 * 1.40
        self.assertAlmostEqual(mods.xp_ganho_mult, expected_xp, places=5)
        self.assertAlmostEqual(mods.xp_ganho_mult, 1.75, places=5)

        # 4. Drop Chance Bonus: 0.50 + 0.40 = 0.90
        self.assertAlmostEqual(mods.drop_chance_bonus, 0.90, places=5)

        # 5. Drop Chance Mult: 1.40
        self.assertAlmostEqual(mods.drop_chance_mult, 1.40, places=5)

        # 6. Drops Value Mult: 2.0
        self.assertAlmostEqual(mods.drops_valor_mult, 2.0, places=5)

        # 7. Enemy HP: 0.80 * 2.00 = 1.60
        self.assertAlmostEqual(mods.hp_inimigos_mult, 1.60, places=5)

        # 8. Enemy Speed: 0.81 * 1.50 = 1.215
        self.assertAlmostEqual(mods.vel_inimigos_mult, 1.215, places=5)

        # 9. Enemy Damage: 0.7225
        self.assertAlmostEqual(mods.dano_inimigos_mult, 0.7225, places=5)

        # 10. Damage Outside Vision: 0.50
        self.assertAlmostEqual(mods.dano_fora_visao_mult, 0.50, places=5)

        # 11. Explosives Damage: 1.20
        self.assertAlmostEqual(mods.dano_explosivos_mult, 1.20, places=5)

        # 12. Critical Strike: chance 0.15, mult 2.0
        self.assertAlmostEqual(mods.critico_chance, 0.15, places=5)
        self.assertAlmostEqual(mods.critico_mult, 2.0, places=5)

        # 13. Booleans
        self.assertTrue(mods.auto_dano)
        self.assertTrue(mods.loot_enriquecido)

    def test_locked_configurations_strictly_isolated(self):
        """
        When all configurations are LOCKED (configs_desbloqueadas = set()),
        even if configs_ativas contains extreme buff values,
        the system MUST return the 100% neutral baseline (no buffs applied).
        """
        extreme_actives = {
            "fps_cap": "15",
            "graficos_qualidade": "baixa",
            "resolucao": "25%",
            "vsync": "desligado",
            "screen_shake": "ligado",
            "motion_blur": "ligado",
            "hud": "desligado",
            "damage_numbers": "ligado",
            "zoom": "150%",
            "movimento_mouse": "ligado",
            "keybinds": "pesadelo",
            "suavizacao_camera": "desligado",
            "auto_fire": "desligado",
            "inimigos_ranged": "ligado",
            "coleta_inimiga": "ligado",
            "velocidade_inimigos": "+50%",
            "vida_inimigos": "+100%",
            "iluminacao": "ligado",
            "cores_invertidas": "ligado",
            "fogo_amigo": "ligado",
        }

        # Calculate with EMPTY unlocked set
        mods = calcular_modificadores(configs_desbloqueadas=set(), configs_ativas=extreme_actives)

        # Strict Neutral Baseline Check
        self.assertEqual(mods.dano_armas_mult, 1.0)
        self.assertEqual(mods.dano_explosivos_mult, 1.0)
        self.assertEqual(mods.vel_jogador_mult, 1.0)
        self.assertEqual(mods.xp_ganho_mult, 1.0)
        self.assertEqual(mods.drop_chance_bonus, 0.0)
        self.assertEqual(mods.drop_chance_mult, 1.0)
        self.assertEqual(mods.drops_valor_mult, 1.0)
        self.assertEqual(mods.hp_inimigos_mult, 1.0)
        self.assertEqual(mods.vel_inimigos_mult, 1.0)
        self.assertEqual(mods.dano_inimigos_mult, 1.0)
        self.assertEqual(mods.dano_fora_visao_mult, 1.0)
        self.assertEqual(mods.hitbox_projeteis_mult, 1.0)
        self.assertEqual(mods.critico_chance, 0.0)
        self.assertEqual(mods.critico_mult, 1.0)
        self.assertFalse(mods.auto_dano)
        self.assertFalse(mods.loot_enriquecido)

    def test_single_unlock_applies_only_its_own_modifiers(self):
        """
        Unlocking ONLY 'hud' and setting it to 'desligado' should ONLY modify xp_ganho_mult (1.25x),
        leaving all other 19 multipliers at strict baseline.
        """
        mods = calcular_modificadores(
            configs_desbloqueadas={"hud"},
            configs_ativas={"hud": "desligado", "fogo_amigo": "ligado", "keybinds": "pesadelo"}
        )

        self.assertEqual(mods.xp_ganho_mult, 1.25)
        self.assertEqual(mods.dano_armas_mult, 1.0, "Locked 'keybinds' and 'fogo_amigo' must not apply")
        self.assertFalse(mods.auto_dano)
        self.assertEqual(mods.vel_jogador_mult, 1.0)


if __name__ == "__main__":
    unittest.main()
