"""
Adversarial Challenge Test Harness — Challenger 1 (Milestone 2)
Author: teamwork_preview_challenger
Mission: Adversarially stress-test Player, Movement Normalization, Starter Weapons,
         and Projectile Collision mechanics in Protocolo: Batata.

Test Suites:
1. TestDiagonalVelocityAndMovementCombinations:
   - W+D, S+A, W+A, S+D, Arrow keys, Single axes, Opposing keys, Mixed keys.
   - Rigorous mathematical assertion: ||v|| = 200.0 +- 0.01 in all diagonal movements.
2. TestArenaBoundaryClamping:
   - 4 edges (Top, Bottom, Left, Right) and 4 corners (Top-Left, Top-Right, Bottom-Left, Bottom-Right).
   - Bounds: [0, ARENA_W - 32] and [0, ARENA_H - 32].
   - Hyper-speed / quantum tunneling resistance (large dt).
   - Out-of-bounds spawn snapping.
3. TestWeaponFireRatesAndTrajectories:
   - Rapid clicking vs Continuous holding fire-rate equivalence.
   - Cooldown timer precision and countdown behavior.
   - Trajectories toward arbitrary mouse coordinates (360 deg, negative coordinates, float, zero distance).
4. TestProjectileEnemyCollisions:
   - Damage calculation and HP subtraction.
   - Immediate bullet deactivation/destruction upon impact (no ghost piercing).
   - Overlapping enemies test (single bullet hits at most 1 enemy).
   - Multi-bullet destruction, overkill handling, kill & score tracking.
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

from src.entidades.jogador import Jogador
from src.entidades.projetil import Projetil
from src.entidades.inimigo_padrao import InimigoPadrao
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.cenas.gameplay import GameplayScene
from src.utils.constantes import (
    JOGADOR_VELOCIDADE_PADRAO, JOGADOR_LARGURA, JOGADOR_ALTURA,
    LARGURA_ARENA, ALTURA_ARENA, PISTOLA_DANO, PISTOLA_COOLDOWN,
    INIMIGO_PADRAO_HP
)


class MockKeyboard:
    """Mock teclado determinístico com suporte a case-insensitivity e múltiplas teclas."""
    def __init__(self, pressed_keys=None):
        self.pressed_keys = set(k.lower() for k in (pressed_keys or []))

    def key_pressed(self, key):
        return key.lower() in self.pressed_keys

    def set_keys(self, keys):
        self.pressed_keys = set(k.lower() for k in keys)


class MockMouse:
    """Mock mouse com coordenadas e botões virtuais."""
    def __init__(self, pos=(400, 300), pressed=False, down=False):
        self.pos = pos
        self.pressed = pressed
        self.down = down

    def get_position(self):
        return self.pos

    def button_pressed(self, btn):
        return self.pressed

    def button_down(self, btn):
        return self.down


class TestDiagonalVelocityAndMovementCombinations(unittest.TestCase):
    """
    Stress-tests player velocity vectors under all keyboard combinations.
    Requirement 1: Assert ||v|| = 200.0 +- 0.01 in all diagonal cases.
    """

    def setUp(self):
        self.arena = (1600.0, 1200.0)

    def _calculate_velocity(self, keys, dt=0.1):
        """Helper to process input and measure resulting velocity vector."""
        j = Jogador(x=800.0, y=600.0, velocidade=200.0)
        teclado = MockKeyboard(keys)
        mouse = MockMouse((800, 600))
        j.processar_input(teclado, mouse, dt=dt, limite_arena=self.arena)

        vx = (j.x - 800.0) / dt
        vy = (j.y - 600.0) / dt
        magnitude = math.sqrt(vx * vx + vy * vy)
        return vx, vy, magnitude

    def test_single_axis_movement(self):
        """Single cardinal keys must yield exact magnitude = 200.0."""
        cardinals = [
            (["d"], 200.0, 0.0),
            (["a"], -200.0, 0.0),
            (["w"], 0.0, -200.0),
            (["s"], 0.0, 200.0),
            (["right"], 200.0, 0.0),
            (["left"], -200.0, 0.0),
            (["up"], 0.0, -200.0),
            (["down"], 0.0, 200.0),
        ]
        for keys, expected_vx, expected_vy in cardinals:
            with self.subTest(keys=keys):
                vx, vy, mag = self._calculate_velocity(keys)
                self.assertAlmostEqual(vx, expected_vx, places=4)
                self.assertAlmostEqual(vy, expected_vy, places=4)
                self.assertAlmostEqual(mag, 200.0, places=4)

    def test_all_diagonal_combinations_magnitude_exact_200(self):
        """
        Adversarially tests all 4 diagonal quadrants:
        - W+D (Up-Right)
        - W+A (Up-Left)
        - S+D (Down-Right)
        - S+A (Down-Left)
        - Arrow key diagonals
        - Mixed WASD and Arrow combinations
        Asserts ||v|| = 200.0 +- 0.01.
        """
        diagonal_combos = [
            ["w", "d"],
            ["w", "a"],
            ["s", "d"],
            ["s", "a"],
            ["up", "right"],
            ["up", "left"],
            ["down", "right"],
            ["down", "left"],
            ["w", "right"],
            ["w", "left"],
            ["s", "right"],
            ["s", "left"],
            ["up", "d"],
            ["up", "a"],
            ["down", "d"],
            ["down", "a"],
            # Uppercase variants
            ["W", "D"],
            ["S", "A"],
            ["UP", "RIGHT"],
            ["DOWN", "LEFT"],
        ]

        for keys in diagonal_combos:
            with self.subTest(keys=keys):
                vx, vy, mag = self._calculate_velocity(keys)
                # Absolute tolerance 0.01
                self.assertTrue(
                    abs(mag - 200.0) <= 0.01,
                    f"Diagonal velocity magnitude {mag} violated ||v|| = 200 +- 0.01 for keys {keys} (vx={vx}, vy={vy})"
                )

    def test_opposing_keys_cancellation(self):
        """Opposing keys (W+S, A+D, etc.) must perfectly cancel out with zero net movement."""
        cancellations = [
            ["w", "s"],
            ["a", "d"],
            ["up", "down"],
            ["left", "right"],
            ["w", "s", "a", "d"],
            ["w", "s", "d"],  # Net right only
            ["a", "d", "w"],  # Net up only
            ["w", "down"],
            ["left", "d"],
        ]
        for keys in cancellations:
            with self.subTest(keys=keys):
                vx, vy, mag = self._calculate_velocity(keys)
                if set(keys) in [{"w", "s"}, {"a", "d"}, {"up", "down"}, {"left", "right"}, {"w", "s", "a", "d"}, {"w", "down"}, {"left", "d"}]:
                    self.assertAlmostEqual(mag, 0.0, places=4, msg=f"Opposing keys {keys} failed to cancel out!")
                elif set(keys) == {"w", "s", "d"}:
                    self.assertAlmostEqual(vx, 200.0, places=4)
                    self.assertAlmostEqual(vy, 0.0, places=4)
                    self.assertAlmostEqual(mag, 200.0, places=4)
                elif set(keys) == {"a", "d", "w"}:
                    self.assertAlmostEqual(vx, 0.0, places=4)
                    self.assertAlmostEqual(vy, -200.0, places=4)
                    self.assertAlmostEqual(mag, 200.0, places=4)

    def test_redundant_key_stacking(self):
        """Pressing both 'd' and 'right' simultaneously must NOT double the speed (vx must remain 200.0, not 400.0)."""
        redundant_combos = [
            (["d", "right"], 200.0, 0.0),
            (["a", "left"], -200.0, 0.0),
            (["w", "up"], 0.0, -200.0),
            (["s", "down"], 0.0, 200.0),
            (["w", "up", "d", "right"], 200.0 * 0.70710678118, -200.0 * 0.70710678118),
        ]
        for keys, exp_vx, exp_vy in redundant_combos:
            with self.subTest(keys=keys):
                vx, vy, mag = self._calculate_velocity(keys)
                self.assertAlmostEqual(vx, exp_vx, places=3)
                self.assertAlmostEqual(vy, exp_vy, places=3)
                self.assertTrue(abs(mag - 200.0) <= 0.01, f"Redundant keys {keys} altered magnitude to {mag}!")


class TestArenaBoundaryClamping(unittest.TestCase):
    """
    Stress-tests arena boundary clamping at all 4 edges and corners.
    Requirement 2: Verify player never escapes [0, ARENA_W - 32] and [0, ARENA_H - 32].
    """

    def setUp(self):
        self.arena_w = 1600.0
        self.arena_h = 1200.0
        self.limite_x = self.arena_w - 32.0  # 1568.0
        self.limite_y = self.arena_h - 32.0  # 1168.0

    def test_all_4_edges_clamping(self):
        """Adversarially push player past Top, Bottom, Left, Right boundaries with high dt."""
        edges = [
            # (start_x, start_y, keys, exp_x, exp_y, name)
            (500.0, 5.0, ["w"], 500.0, 0.0, "Top Edge"),
            (500.0, self.limite_y - 5.0, ["s"], 500.0, self.limite_y, "Bottom Edge"),
            (5.0, 500.0, ["a"], 0.0, 500.0, "Left Edge"),
            (self.limite_x - 5.0, 500.0, ["d"], self.limite_x, 500.0, "Right Edge"),
        ]

        for sx, sy, keys, exp_x, exp_y, name in edges:
            with self.subTest(edge=name):
                j = Jogador(x=sx, y=sy, velocidade=200.0)
                teclado = MockKeyboard(keys)
                # Apply 10 seconds of continuous push
                j.processar_input(teclado, None, dt=10.0, limite_arena=(self.arena_w, self.arena_h))
                self.assertEqual(j.x, exp_x, f"{name}: X out of bounds!")
                self.assertEqual(j.y, exp_y, f"{name}: Y out of bounds!")

    def test_all_4_corners_clamping(self):
        """Adversarially push player past Top-Left, Top-Right, Bottom-Left, Bottom-Right corners."""
        corners = [
            (5.0, 5.0, ["w", "a"], 0.0, 0.0, "Top-Left Corner"),
            (self.limite_x - 5.0, 5.0, ["w", "d"], self.limite_x, 0.0, "Top-Right Corner"),
            (5.0, self.limite_y - 5.0, ["s", "a"], 0.0, self.limite_y, "Bottom-Left Corner"),
            (self.limite_x - 5.0, self.limite_y - 5.0, ["s", "d"], self.limite_x, self.limite_y, "Bottom-Right Corner"),
        ]

        for sx, sy, keys, exp_x, exp_y, name in corners:
            with self.subTest(corner=name):
                j = Jogador(x=sx, y=sy, velocidade=200.0)
                teclado = MockKeyboard(keys)
                j.processar_input(teclado, None, dt=5.0, limite_arena=(self.arena_w, self.arena_h))
                self.assertEqual(j.x, exp_x, f"{name}: X corner violated!")
                self.assertEqual(j.y, exp_y, f"{name}: Y corner violated!")

    def test_out_of_bounds_recovery(self):
        """If player starts at extreme negative or positive coordinates, input immediately snaps to bounds."""
        wild_positions = [
            (-9999.0, -9999.0, 0.0, 0.0),
            (9999.0, 9999.0, self.limite_x, self.limite_y),
            (-50.0, 600.0, 0.0, 600.0),
            (2000.0, 600.0, self.limite_x, 600.0),
            (800.0, -100.0, 800.0, 0.0),
            (800.0, 3000.0, 800.0, self.limite_y),
        ]
        for sx, sy, exp_x, exp_y in wild_positions:
            with self.subTest(pos=(sx, sy)):
                j = Jogador(x=sx, y=sy)
                # dt=0.0 with no keys
                j.processar_input(MockKeyboard([]), None, dt=0.0, limite_arena=(self.arena_w, self.arena_h))
                self.assertEqual(j.x, exp_x)
                self.assertEqual(j.y, exp_y)


class TestWeaponFireRatesAndTrajectories(unittest.TestCase):
    """
    Stress-tests weapon fire rates, rapid clicking vs continuous holding, and bullet trajectories.
    Requirement 3: Test weapon fire rates, cooldown timers, bullet trajectories toward arbitrary mouse coordinates.
    """

    def test_cooldown_timer_precision(self):
        """Test exact ticking of weapon cooldown and single-shot firing."""
        pistola = Pistola(dano=12, cooldown=0.33)
        self.assertTrue(pistola.pode_atirar())

        # First shot
        shots = pistola.disparar(100.0, 100.0, 200.0, 100.0)
        self.assertEqual(len(shots), 1)
        self.assertAlmostEqual(pistola.tempo_recarga_restante, 0.33)
        self.assertFalse(pistola.pode_atirar())

        # Advance 0.20s -> still on cooldown
        pistola.update(0.20)
        self.assertAlmostEqual(pistola.tempo_recarga_restante, 0.13)
        self.assertFalse(pistola.pode_atirar())
        self.assertEqual(len(pistola.disparar(100, 100, 200, 100)), 0)

        # Advance remaining 0.13s -> cooldown resets to 0.0
        pistola.update(0.13)
        self.assertEqual(pistola.tempo_recarga_restante, 0.0)
        self.assertTrue(pistola.pode_atirar())

    def test_rapid_clicking_vs_continuous_holding(self):
        """
        Simulate 1.05 seconds of continuous gameplay:
        - High-frequency clicking (100 Hz, dt = 0.01s)
        - Continuous holding at 60 FPS (dt = 1/60s)
        Both must produce the exact same 4 shots at matching timestamps (governed by cooldown = 0.33s).
        """
        # Scenario A: Rapid clicking at 100Hz (dt = 0.01s, 105 frames = 1.05s)
        pistola_rapid = Pistola(cooldown=0.33)
        shots_rapid = 0
        timestamps_rapid = []
        t_rapid = 0.0
        for _ in range(105):
            if pistola_rapid.pode_atirar():
                b = pistola_rapid.disparar(0, 0, 10, 0)
                if b:
                    shots_rapid += len(b)
                    timestamps_rapid.append(round(t_rapid, 3))
            pistola_rapid.update(0.01)
            t_rapid += 0.01

        # Scenario B: Continuous holding at 60 FPS (dt = 1/60s, 64 frames = 1.0667s)
        pistola_hold = Pistola(cooldown=0.33)
        shots_hold = 0
        timestamps_hold = []
        t_hold = 0.0
        for _ in range(64):
            if pistola_hold.pode_atirar():
                b = pistola_hold.disparar(0, 0, 10, 0)
                if b:
                    shots_hold += len(b)
                    timestamps_hold.append(round(t_hold, 3))
            pistola_hold.update(1.0 / 60.0)
            t_hold += 1.0 / 60.0

        # Shots fired in [0.0s, 1.05s]: exactly 4 shots
        self.assertEqual(shots_rapid, 4, f"Rapid clicking produced {shots_rapid} shots instead of 4")
        self.assertEqual(shots_hold, 4, f"Continuous holding produced {shots_hold} shots instead of 4")
        self.assertEqual(shots_rapid, shots_hold)

        # Verify firing timestamps match expected cadence within 1 frame tolerance (~0.02s)
        for r_t, h_t in zip(timestamps_rapid, timestamps_hold):
            self.assertAlmostEqual(r_t, h_t, delta=0.02)

    def test_bullet_trajectories_arbitrary_mouse_coordinates(self):
        """
        Adversarially test bullet trajectory calculations for all quadrants,
        negative coordinates, float coordinates, and edge case when mouse == origin.
        """
        pistola = Pistola(velocidade_projetil=400.0)
        origem = (400.0, 300.0)

        test_destinations = [
            (500.0, 300.0, 1.0, 0.0, "Right"),
            (300.0, 300.0, -1.0, 0.0, "Left"),
            (400.0, 400.0, 0.0, 1.0, "Down"),
            (400.0, 200.0, 0.0, -1.0, "Up"),
            (500.0, 400.0, 0.70710678, 0.70710678, "Down-Right Diagonal"),
            (-1234.5, -9876.5, None, None, "Extreme Negative Coordinates"),
            (400.0, 300.0, 1.0, 0.0, "Zero Distance Singularity (Mouse at Player Center)"),
        ]

        for mx, my, exp_dx, exp_dy, desc in test_destinations:
            with self.subTest(case=desc):
                pistola.tempo_recarga_restante = 0.0
                bullets = pistola.disparar(origem[0], origem[1], mx, my)
                self.assertEqual(len(bullets), 1)
                b = bullets[0]

                # Assert non-NaN
                self.assertFalse(math.isnan(b.dir_x))
                self.assertFalse(math.isnan(b.dir_y))

                # Magnitude of direction vector must be exactly 1.0
                mag = math.sqrt(b.dir_x * b.dir_x + b.dir_y * b.dir_y)
                self.assertAlmostEqual(mag, 1.0, places=4)

                if exp_dx is not None and exp_dy is not None:
                    self.assertAlmostEqual(b.dir_x, exp_dx, places=3)
                    self.assertAlmostEqual(b.dir_y, exp_dy, places=3)

                # Test physical flight trajectory: in dt=0.5s, bullet must travel exactly dir * velocidade * 0.5
                start_x, start_y = b.x, b.y
                b.update(0.5)
                traveled_dist = math.sqrt((b.x - start_x)**2 + (b.y - start_y)**2)
                self.assertAlmostEqual(traveled_dist, 200.0, places=2)  # 400 px/s * 0.5s = 200 px


class TestProjectileEnemyCollisions(unittest.TestCase):
    """
    Stress-tests projectile vs enemy collision detection, damage calculation,
    bullet destruction on impact, multi-bullet hits, and overlapping enemy scenarios.
    Requirement 4: Test projectile vs enemy collision: damage calculation, bullet destruction on impact, multi-bullet hits.
    """

    def setUp(self):
        self.scene = GameplayScene()
        self.scene.auto_fire_ativo = False
        self.scene.jogador.x = 400.0
        self.scene.jogador.y = 300.0
        self.scene.inimigos = []
        self.scene.projeteis = []

    def test_single_bullet_damage_and_destruction(self):
        """Bullet deals exact damage and is immediately destroyed on contact."""
        inimigo = InimigoPadrao(x=450.0, y=300.0)  # HP = 25
        self.scene.inimigos.append(inimigo)

        # Create bullet overlapping enemy
        proj = Projetil(x=450.0, y=300.0, dir_x=1.0, dir_y=0.0, dano=12, velocidade=400.0)
        self.scene.projeteis.append(proj)

        # Run 1 physics loop step
        self.scene.loop()

        # Enemy took 12 damage: 25 - 12 = 13 HP
        self.assertEqual(inimigo.hp, 13)
        self.assertTrue(inimigo.vivo)
        # Bullet was destroyed and removed from active list
        self.assertNotIn(proj, self.scene.projeteis)
        self.assertFalse(proj.ativo)

    def test_multi_bullet_cumulative_destruction(self):
        """
        Three consecutive bullets of damage 12 hit an enemy with 25 HP:
        Hit 1: HP 25 -> 13
        Hit 2: HP 13 -> 1
        Hit 3: HP 1 -> <= 0 (Dead, Kill count +1, Score +100)
        """
        inimigo = InimigoPadrao(x=450.0, y=300.0)
        self.scene.inimigos.append(inimigo)

        abates_init = self.scene.abates
        pontos_init = self.scene.pontos

        # Shot 1
        b1 = Projetil(x=450.0, y=300.0, dir_x=1.0, dir_y=0.0, dano=12)
        self.scene.projeteis.append(b1)
        self.scene.loop()
        self.assertEqual(inimigo.hp, 13)
        self.assertTrue(inimigo.vivo)
        self.assertEqual(self.scene.abates, abates_init)

        # Shot 2
        b2 = Projetil(x=450.0, y=300.0, dir_x=1.0, dir_y=0.0, dano=12)
        self.scene.projeteis.append(b2)
        self.scene.loop()
        self.assertEqual(inimigo.hp, 1)
        self.assertTrue(inimigo.vivo)
        self.assertEqual(self.scene.abates, abates_init)

        # Shot 3 (Lethal hit with overkill)
        b3 = Projetil(x=450.0, y=300.0, dir_x=1.0, dir_y=0.0, dano=12)
        self.scene.projeteis.append(b3)
        self.scene.loop()
        self.assertLessEqual(inimigo.hp, 0)
        self.assertFalse(inimigo.vivo)
        self.assertNotIn(inimigo, self.scene.inimigos)
        self.assertEqual(self.scene.abates, abates_init + 1)
        self.assertEqual(self.scene.pontos, pontos_init + 100)

    def test_single_bullet_vs_overlapping_enemies_no_ghost_piercing(self):
        """
        Adversarial test: If two enemies occupy the exact same coordinate,
        a single non-piercing pistol bullet must damage ONLY ONE enemy and deactivate immediately.
        """
        e1 = InimigoPadrao(x=450.0, y=300.0)
        e2 = InimigoPadrao(x=450.0, y=300.0)
        self.scene.inimigos = [e1, e2]

        proj = Projetil(x=450.0, y=300.0, dir_x=1.0, dir_y=0.0, dano=12)
        self.scene.projeteis = [proj]

        self.scene.loop()

        # Exactly one enemy must have taken damage (HP=13) and the other must be untouched (HP=25)
        hps = sorted([e1.hp, e2.hp])
        self.assertEqual(hps, [13, 25], "Single bullet improperly pierced multiple overlapping enemies!")
        self.assertEqual(len(self.scene.projeteis), 0, "Bullet was not deactivated upon collision!")

    def test_overkill_and_dead_enemy_hit_rejection(self):
        """A dead enemy must not absorb further bullets from in-flight projectiles."""
        e = InimigoPadrao(x=450.0, y=300.0)
        e.hp = 0
        e.vivo = False
        self.scene.inimigos = [e]

        proj = Projetil(x=450.0, y=300.0, dir_x=1.0, dir_y=0.0, dano=12)
        self.scene.projeteis = [proj]

        self.scene.loop()

        # Bullet must NOT collide with a dead enemy
        self.assertTrue(proj.ativo)
        self.assertIn(proj, self.scene.projeteis)

    def test_out_of_bounds_bullet_deactivation(self):
        """Bullets that fly outside the arena perimeter must be cleaned up."""
        proj_far = Projetil(x=2000.0, y=2000.0, dir_x=1.0, dir_y=0.0)
        self.scene.projeteis = [proj_far]

        self.scene.loop()

        self.assertFalse(proj_far.ativo)
        self.assertNotIn(proj_far, self.scene.projeteis)

    def test_high_volume_simultaneous_projectile_collision(self):
        """Stress test: 50 bullets simultaneously colliding with 50 distinct enemies in 1 frame."""
        enemies = []
        bullets = []
        for i in range(50):
            ex = 100.0 + i * 20.0
            ey = 100.0 + i * 20.0
            e = InimigoPadrao(x=ex, y=ey)
            b = Projetil(x=ex, y=ey, dir_x=1.0, dir_y=0.0, dano=25)  # 1-shot lethal
            enemies.append(e)
            bullets.append(b)

        self.scene.inimigos = enemies
        self.scene.projeteis = bullets

        abates_init = self.scene.abates
        pontos_init = self.scene.pontos

        # Run 1 loop update
        self.scene.loop()

        # All 50 enemies should be destroyed
        self.assertEqual(len(self.scene.inimigos), 0)
        self.assertEqual(len(self.scene.projeteis), 0)
        self.assertEqual(self.scene.abates, abates_init + 50)
        self.assertEqual(self.scene.pontos, pontos_init + 50 * 100)

    def test_melee_closest_targets_knockback_stress(self):
        """
        Melee stress test: 10 enemies arranged in concentric rings within range (70px).
        All 10 must receive damage, but only the 2 closest receive knockback impulses.
        """
        melee = Melee(dano=20, alcance=70.0, knockback_forca=200.0, max_alvos_knockback=2)
        origem_x, origem_y = 500.0, 500.0

        # Create 10 enemies at distances: 10, 15, 20, 25, 30, 35, 40, 45, 50, 55 px
        enemies = []
        for i in range(10):
            dist = 10.0 + i * 5.0
            # Center of enemy is x + 14, y + 14
            e = InimigoPadrao(x=origem_x + dist - 14.0, y=origem_y - 14.0)
            enemies.append(e)

        initial_hps = [e.hp for e in enemies]

        afetados = melee.executar_ataque(origem_x, origem_y, enemies)

        # All 10 enemies were in range (dist <= 55 <= 70) and took damage
        self.assertEqual(len(afetados), 10)
        for i, e in enumerate(enemies):
            self.assertEqual(e.hp, initial_hps[i] - 20)

        # Only the 2 closest (dist 10 and 15) received knockback
        self.assertGreater(enemies[0].vx_knockback, 0.0)
        self.assertGreater(enemies[1].vx_knockback, 0.0)
        for i in range(2, 10):
            self.assertEqual(enemies[i].vx_knockback, 0.0, f"Enemy {i} at dist {10 + i*5} received unintended knockback!")

    def test_sliding_along_boundary_on_diagonal_input(self):
        """
        Sliding stress test: Player is at the Top boundary (y = 0.0) and presses W+D (Up-Right).
        Y must remain clamped at 0.0 while X moves right at the normalized diagonal rate (200 * 0.7071 px/s).
        """
        j = Jogador(x=500.0, y=0.0, velocidade=200.0)
        teclado = MockKeyboard(["w", "d"])
        dt = 1.0
        j.processar_input(teclado, None, dt=dt, limite_arena=(1600.0, 1200.0))

        # Y clamped to top boundary
        self.assertEqual(j.y, 0.0)
        # X advanced by 200 * 0.70710678118 * 1.0
        self.assertAlmostEqual(j.x, 500.0 + 200.0 * 0.70710678118, places=3)

    def test_variable_speed_normalization_scaling(self):
        """
        Stress test: Velocity scaling with buffed/nerfed player speed (e.g. +15% from config, or -30%).
        Assert ||v|| = velocidade_atual +- 0.01 for all diagonal combinations.
        """
        test_speeds = [50.0, 100.0, 200.0, 230.0, 300.0, 500.0]
        diagonals = [["w", "d"], ["s", "a"], ["up", "right"], ["down", "left"]]

        for spd in test_speeds:
            for keys in diagonals:
                with self.subTest(speed=spd, keys=keys):
                    j = Jogador(x=800.0, y=600.0, velocidade=spd)
                    j.velocidade_atual = spd
                    teclado = MockKeyboard(keys)
                    dt = 0.1
                    j.processar_input(teclado, None, dt=dt, limite_arena=(1600.0, 1200.0))

                    vx = (j.x - 800.0) / dt
                    vy = (j.y - 600.0) / dt
                    mag = math.sqrt(vx * vx + vy * vy)
                    self.assertTrue(
                        abs(mag - spd) <= 0.01,
                        f"Variable speed {spd} failed diagonal normalization: mag={mag}"
                    )


if __name__ == "__main__":
    unittest.main()

