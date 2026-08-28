# Challenger 2 Handoff Report: Milestone 2 Adversarial Stress Testing

**Reviewer**: Challenger 2 (`teamwork_preview_challenger`)  
**Target Milestone**: Milestone 2 (Phase 1 — Core Gameplay Loop)  
**Verdict**: `APPROVE` (with 1 non-blocking test-clock isolation finding documented)

---

## 1. Observation

1. **Beeline AI Vector Calculation and Convergence**:
   - File: `src/entidades/inimigo_base.py` (lines 78-90):
     ```python
     cx = self.x + self.largura / 2.0
     cy = self.y + self.altura / 2.0
     tx, ty = pos_alvo
     ux, uy = vetor_direcao(cx, cy, tx, ty)
     vx = ux * self.velocidade + self.vx_knockback
     vy = uy * self.velocidade + self.vy_knockback
     self.x += vx * dt
     self.y += vy * dt
     ```
   - Tool Command: `.venv\Scripts\python.exe -m unittest tests\test_challenger_m2_2_adversarial.py -v`
   - Output:
     ```
     test_beeline_convergence_360_degrees_sweep (tests.test_challenger_m2_2_adversarial.TestBeelineAIConvergence.test_beeline_convergence_360_degrees_sweep)
     Varrer 360 graus em incrementos de 1 grau para provar convergência omnidirecional. ... ok
     test_beeline_convergence_quadrants_and_cardinals (tests.test_challenger_m2_2_adversarial.TestBeelineAIConvergence.test_beeline_convergence_quadrants_and_cardinals)
     Testa convergência em 8 direções principais (4 cardeais, 4 ordinais). ... ok
     test_beeline_multi_step_arrival (tests.test_challenger_m2_2_adversarial.TestBeelineAIConvergence.test_beeline_multi_step_arrival)
     Verifica que o inimigo atinge a vizinhança do jogador em tempo $T = D / V$ sem orbitar. ... ok
     test_beeline_zero_distance_singularity (tests.test_challenger_m2_2_adversarial.TestBeelineAIConvergence.test_beeline_zero_distance_singularity)
     Verifica estabilidade numérica quando a distância é exatamente zero. ... ok
     ```

2. **Multi-Instance Independent Contact Damage Cooldowns**:
   - File: `src/entidades/inimigo_base.py` (lines 104-118):
     ```python
     def tentar_causar_dano_contato(self, jogador) -> bool:
         if not self.vivo or not getattr(jogador, "vivo", True):
             return False
         if colisao_aabb(self.x, self.y, self.largura, self.altura,
                         jogador.x, jogador.y, jogador.largura, jogador.altura):
             if self.cooldown_contato_atual <= 0.0:
                 jogador.receber_dano(self.dano_contato)
                 self.cooldown_contato_atual = self.cooldown_contato_max
                 return True
         return False
     ```
   - Test Results from `tests/test_challenger_m2_2_adversarial.py`:
     ```
     test_staggered_independent_cooldowns ... ok
     test_three_enemies_simultaneous_contact_and_cooldown ... ok
     ```
   - `test_three_enemies_simultaneous_contact_and_cooldown` confirmed:
     - Frame 0: 3 overlapping enemies on the player dealt 30 total damage (150 -> 120 HP).
     - Frames $t \in (0.0, 0.40s)$: 0 damage dealt by all 3 enemies (HP remained 120).
     - Frame $t = 0.41s$: All 3 cooldowns expired and dealt 30 total damage again (120 -> 90 HP).

3. **Spawner Boundary Math, Wave Progression, and Soft Population Cap**:
   - File: `src/sistemas/sistema_spawn.py` (lines 41-73, 84-116):
     - Calculates spawn coordinates strictly on perimeter outside camera viewport (`cam_x - margem`, `cam_x + view_w + margem`, etc.).
     - Interval formula: $T(t) = \max(0.40, 1.80 - 0.012 \cdot t)$.
     - Batch formula: $N(t) = \min(8, 1 + \lfloor t / 25 \rfloor)$.
     - Available capacity: $\min(N(t), \text{max\_ativos} - \text{total\_inimigos\_vivos})$.
   - Test Results from `tests/test_challenger_m2_2_adversarial.py`:
     ```
     test_soft_cap_never_exceeded_under_extreme_spawning ... ok
     test_spawner_strict_offscreen_generation_1000_samples ... ok
     test_wave_scaling_monotonicity_and_bounds ... ok
     ```
   - Tested 1000 randomized camera spawn samples across varying $(x, y)$ positions: 0 out of 1000 points were inside the visible camera viewport (100% offscreen compliance).
   - Tested 3000 continuous spawn steps under no-kill condition: active population never exceeded `max_ativos = 60`.

4. **600-Frame Long-Running Simulation under SDL Dummy Drivers**:
   - Test Execution: `test_600_frames_headless_gameplay_stress_and_memory` ran 600 continuous frames (60 FPS equivalent = 10s of full combat, weapon auto-firing, 360° mouse rotation, continuous enemy spawning, collision resolution, and PPlay buffer blitting).
   - Results: 0 exceptions, 0 crashes, 100% frame completion.
   - Memory tracking via `tracemalloc`: Net heap difference over 600 frames was under 2.5 MB (well below the 15 MB safety envelope), confirming no unbounded allocation leak.

5. **Adversarial Finding on Test Suite Coupling (`test_gameplay_e2e.py`)**:
   - Tool Command: `.venv\Scripts\python.exe -m unittest discover tests -v`
   - Observation: `test_gameplay_e2e.py:152` failed with `AssertionError: True is not false` when executed in discover mode after previous tests called `Window.update()`.
   - Root Cause: `test_combate_completo_tiro_colisao_e_morte_inimigo` in `test_gameplay_e2e.py` runs a loop calling `cena.loop()` without calling `janela.update()`. `cena.loop()` reads `dt = self.janela.delta_time()`, which retained a stale `0.006s` value from preceding tests, causing 30 frames to advance only 0.18s instead of 0.50s of physics time. Calling `janela.update()` in each test step or resetting `janela._delta_time = 0.0` resolves this isolation quirk.

---

## 2. Logic Chain

1. **Beeline Convergence (Observation 1)**:
   - Given `vetor_direcao(cx, cy, tx, ty)` computes $(tx - cx, ty - cy) / \|T - C\|$, multiplying by $V \cdot dt$ strictly decreases Euclidean distance to $(tx, ty)$ for all non-zero distances.
   - Empirical sweep across all 4 quadrants and 360 individual radial degree angles confirmed that $\Delta D = D_0 - D_1 = V \cdot dt \pm 10^{-4}$.
   - Singularity protection at $D = 0$ returned $(0, 0)$ without `ZeroDivisionError` or `NaN`.

2. **Cooldown Independence (Observation 2)**:
   - Given `cooldown_contato_atual` is an instance attribute on `InimigoBase` rather than a class/global variable, distinct enemy instances manage their timers independently.
   - Empirical test with 3 simultaneous colliders verified that all 3 inflicted 10 damage in frame 0 ($150 \rightarrow 120$), were blocked for 0.40s, and re-inflicted damage in frame $t > 0.40s$ ($120 \rightarrow 90$).

3. **Spawner Offscreen & Soft Cap (Observation 3)**:
   - Given the generation math chooses an edge from `['topo', 'base', 'esquerda', 'direita']` with offset `SPAWN_DISTANCIA_OFFSET = 60`, every coordinate is $\ge 60\text{px}$ beyond the camera viewport.
   - Verified across 1000 stochastic trials.
   - Given `min(tamanho_lote, max_ativos - total_ativos)`, when total reaches 60, generated count is $\min(N, 0) = 0$, guaranteeing the soft cap.

4. **Headless Stability (Observation 4)**:
   - 600 frames executed cleanly with dummy video/audio drivers.
   - Garbage collector sweeps combined with `tracemalloc` snapshots confirmed bounded memory profiles.

---

## 3. Caveats

- **Test harness isolation**: `test_gameplay_e2e.py` should be updated by the builder or test curator to invoke `janela.update()` inside its micro-simulation loops or explicitly set test delta time. This does not affect the production game runtime (`main.py`), which calls `janela.update()` every frame.
- **Drone and special weapon archetypes**: Evaluated baseline Melee (Slot 1) and Pistol (Slot 2); temporary dropped weapons (Shotgun, Minigun, Rocket Launcher) and drones are architecturally present in `CONFIGURACOES.md` / `constantes.py` and planned for subsequent milestone implementations.

---

## 4. Conclusion

- **Verdict**: `APPROVE`
- All four acceptance criteria of Milestone 2 and the four specific stress-test missions assigned to Challenger 2 are empirically verified and passing.
- Beeline convergence, independent contact cooldowns, offscreen perimeter spawning, wave scaling, and headless gameplay simulation stability are verified.

---

## 5. Verification Method

To independently execute and verify all findings:

1. **Adversarial Challenge Test Suite**:
   ```powershell
   .venv\Scripts\python.exe -m unittest tests\test_challenger_m2_2_adversarial.py -v
   ```
   *Expected*: 10 tests run, 10 tests `OK` in ~15s.

2. **Standalone Unit Test Suites**:
   ```powershell
   .venv\Scripts\python.exe -m unittest tests\test_enemies.py -v
   .venv\Scripts\python.exe -m unittest tests\test_player.py -v
   .venv\Scripts\python.exe -m unittest tests\test_weapons.py -v
   .venv\Scripts\python.exe -m unittest tests\test_assets.py -v
   ```
   *Expected*: 100% tests `OK`.
