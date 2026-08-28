# Milestone 2 Adversarial Challenge Report — Challenger 1

**Reviewer / Archetype**: `teamwork_preview_challenger` (Challenger 1, Milestone 2)  
**Date**: 2026-08-28T15:18:30Z  
**Verdict**: `APPROVE`  
**Test Suite File**: `tests/test_challenger_m2_player_weapons.py` (19 tests executed, 19 passed)

---

## 1. Observation

Direct empirical observations from inspecting code files, creating test harnesses, and running verification commands:

1. **Diagonal Movement Normalization**:
   - In `src/entidades/jogador.py:101-108`:
     ```python
     if dx != 0.0 and dy != 0.0:
         dx *= 0.70710678118
         dy *= 0.70710678118

     self.x += dx * self.velocidade_atual * dt
     self.y += dy * self.velocidade_atual * dt
     ```
   - Running `.venv\Scripts\python -m unittest tests/test_challenger_m2_player_weapons.py` yielded:
     - Cardinal movement ($D, A, W, S, \text{Right}, \text{Left}, \text{Up}, \text{Down}$): $\|v\| = 200.0000 \text{ px/s}$.
     - Diagonal combinations ($W+D, W+A, S+D, S+A, \text{Up}+\text{Right}, \text{Up}+\text{Left}, \text{Down}+\text{Right}, \text{Down}+\text{Left}$, mixed WASD/Arrows, Uppercase keys):
       - Measured $|v_x| = |v_y| = 141.421356236 \text{ px/s}$.
       - Measured $\|v\| = \sqrt{v_x^2 + v_y^2} = 200.0000000000007 \text{ px/s}$.
       - Deviation from $200.0$: $|200.0000000000007 - 200.0| = 7.0 \times 10^{-13} \text{ px/s} \ll 0.01 \text{ px/s}$.
     - Opposing keys ($W+S, A+D, \text{Up}+\text{Down}, W+S+A+D$): Net $\|v\| = 0.0000 \text{ px/s}$.
     - Redundant key stacking ($D + \text{Right}$ pressed simultaneously): Single increment ($v_x = 200.0 \text{ px/s}$), preventing double-speed exploits.
     - Speed multiplier scaling: For speeds $\in \{50.0, 100.0, 200.0, 230.0, 300.0, 500.0\}$, $\|v\| = \text{speed} \pm 0.0001 \text{ px/s}$.

2. **Arena Boundary Clamping**:
   - In `src/entidades/jogador.py:110-115`:
     ```python
     max_x = max(0.0, float(limite_arena[0]) - self.largura)
     max_y = max(0.0, float(limite_arena[1]) - self.altura)
     self.x = clamp(self.x, 0.0, max_x)
     self.y = clamp(self.y, 0.0, max_y)
     ```
   - For arena dimensions $(1600.0, 1200.0)$ and player dimensions $(32, 32)$:
     - Permitted interval: $X \in [0.0, 1568.0]$, $Y \in [0.0, 1168.0]$.
   - Empirical stress tests confirmed:
     - Top edge ($y=0.0$), Bottom edge ($y=1168.0$), Left edge ($x=0.0$), Right edge ($x=1568.0$) clamped correctly under $10\text{s}$ continuous push.
     - All 4 corners ($(0,0), (1568,0), (0,1168), (1568,1168)$) clamped tightly.
     - Wall sliding: Diagonal input against a blocked boundary (e.g. $W+D$ while at $y=0$) clamps $Y=0.0$ while permitting tangential sliding along $X$ at $200 \times 0.7071 \approx 141.42 \text{ px/s}$.
     - Out-of-bounds recovery: Extreme starting coordinates ($(-9999, -9999)$ or $(9999, 9999)$) instantly snap to $[0, 1568] \times [0, 1168]$.

3. **Weapon Fire Rates and Trajectories**:
   - In `src/armas/pistola.py:23` and `src/armas/arma_base.py:34-45`:
     - Default cooldown $0.33\text{s}$ ($3.03 \text{ shots/s}$).
   - In `src/cenas/gameplay.py:157-172`:
     - Firing logic executes on mouse button press or `auto_fire_ativo = True`.
   - Empirical comparison between Rapid Clicking ($100\text{ Hz}$, $dt=0.01\text{s}$) and Continuous Holding ($60\text{ FPS}$, $dt=1/60\text{s}$) over $1.05\text{s}$ simulation:
     - Rapid clicking produced exactly 4 shots at timestamps $[0.00\text{s}, 0.33\text{s}, 0.66\text{s}, 0.99\text{s}]$.
     - Continuous holding produced exactly 4 shots at matching timestamps within $0.02\text{s}$ (1 frame) delta.
     - Rapid clicking cannot bypass weapon cooldown.
   - Bullet Trajectories:
     - Tested directional unit vectors across all quadrants: $||\vec{d}|| = 1.0000 \pm 0.0001$.
     - Arbitrary negative/floating point mouse targets correctly computed.
     - Zero-distance singularity (mouse cursor at player origin): Gracefully falls back to $(1.0, 0.0)$ (rightward) without NaN or crash (`src/armas/pistola.py:48-49`).
     - Flight displacement: Bullet traveled exactly $200.0\text{ px}$ in $0.5\text{s}$ at $v=400\text{ px/s}$.

4. **Projectile vs Enemy Collisions**:
   - In `src/cenas/gameplay.py:208-232`:
     ```python
     for proj in self.projeteis:
         if not proj.ativo:
             continue
         for inimigo in self.inimigos:
             if not inimigo.vivo:
                 continue
             if colisao_aabb(proj.x, proj.y, proj.largura, proj.altura,
                             inimigo.x, inimigo.y, inimigo.largura, inimigo.altura):
                 inimigo.receber_dano(proj.dano)
                 proj.ativo = False
                 if not inimigo.vivo:
                     self.abates += 1
                     self.pontos += inimigo.score_valor
                 break
     ```
   - Empirical combat tests confirmed:
     - Single bullet on Standard Enemy ($25\text{ HP}$, $12\text{ damage}$): Enemy HP reduced to $13\text{ HP}$, bullet immediately deactivated (`ativo = False`) and purged from `self.projeteis`.
     - Overlapping enemies test: When 2 enemies occupy identical positions, a single bullet hits exactly 1 enemy ($13\text{ HP}$ and $25\text{ HP}$); `break` statement prevents unintended ghost piercing.
     - Multi-bullet lethal sequence: 3 consecutive bullets ($12 + 12 + 12 = 36\text{ dmg}$) destroyed the enemy, removed it from `self.inimigos`, incremented `abates` by $1$, and added $100$ score points.
     - Dead enemy hit rejection: Inactive/dead enemies do not absorb subsequent projectiles.
     - High volume stress test: 50 bullets simultaneously colliding with 50 distinct enemies resolved in 1 physics step with $100\%$ kill rate and exact score/abates tally.
     - Out-of-bounds cleanup: Projectiles flying $>100\text{ px}$ past arena bounds are automatically deactivated and collected.

5. **Full Test Execution Output**:
   ```
   .venv\Scripts\python -m unittest tests/test_player.py tests/test_weapons.py tests/test_enemies.py tests/test_gameplay_e2e.py tests/test_challenger_m2_player_weapons.py
   ----------------------------------------------------------------------
   Ran 42 tests in 1.010s
   OK
   ```

---

## 2. Logic Chain

1. **Movement Normalization**: Observation 1 proves that diagonal inputs scale by $0.70710678118$, giving $\|v\| = 200.0000000000007 \text{ px/s}$. Since $|\|v\| - 200.0| \le 0.01$, Requirement 1 is fully satisfied.
2. **Boundary Clamping**: Observation 2 proves that `clamp()` bounds both coordinates to $[0, \text{ARENA\_W}-32]$ and $[0, \text{ARENA\_H}-32]$ under all vectors, corners, large time-steps, and wall sliding. Requirement 2 is fully satisfied.
3. **Weapon Fire Rates and Aiming**: Observation 3 proves that weapon cooldowns govern shot intervals identically regardless of continuous holding or 100 Hz clicking, and arbitrary mouse coordinates produce normalized direction vectors with zero-distance safety. Requirement 3 is fully satisfied.
4. **Combat and Collisions**: Observation 4 proves that projectile AABB collision correctly deals damage, eliminates bullets on contact, rejects dead entities, increments abates/points, and handles multi-target high concurrency. Requirement 4 is fully satisfied.
5. **Verdict Derivation**: All 4 requirements passed 100% of empirical tests with zero blocking issues. The implementation is robust and ready for Milestone 2 approval.

---

## 3. Caveats

- **Enemy HP on Overkill**: `InimigoBase.receber_dano(quantidade)` allows `self.hp` to drop below 0 (e.g. -11 on fatal overkill) before setting `self.vivo = False`, whereas `Jogador.receber_dano` clamps at `0`. This is safe and standard as `self.vivo = False` governs entity lifecycle, but clamping `self.hp = max(0, ...)` is recommended in future polish for symmetry.
- **Review Scope Boundary**: Reviewer 2 test suite (`test_challenger_m2_reviewer2.py`) has an independent attribute error in its test mock (`SceneManager.current_scene` vs `_current_scene`), which does not affect project source code or Milestone 2 player/weapons mechanics.

---

## 4. Conclusion

**Verdict: `APPROVE`**  
The Player Entity, Movement Normalization, Arena Boundary Clamping, Starter Weapons (Melee & Pistol), and Projectile Collision mechanics meet all specifications and mathematical tolerances defined in `ORIGINAL_REQUEST.md`, `architecture_cache.md`, and `PROJECT.md`.

---

## 5. Verification Method

To independently verify these results:

```powershell
# Run the complete Challenger M2 test harness
.venv\Scripts\python -m unittest tests/test_challenger_m2_player_weapons.py

# Run all Milestone 2 core unit and E2E test suites
.venv\Scripts\python -m unittest tests/test_player.py tests/test_weapons.py tests/test_enemies.py tests/test_gameplay_e2e.py tests/test_challenger_m2_player_weapons.py
```

**Invalidation Conditions**:
- Any diagonal velocity magnitude deviating from $200.0$ by more than $0.01$.
- Any coordinate escaping $[0, \text{ARENA\_W}-32]$ or $[0, \text{ARENA\_H}-32]$.
- Any bullet penetrating multiple enemies without piercing attribute.
- Any discrepancy between continuous holding and rapid clicking fire rates.
