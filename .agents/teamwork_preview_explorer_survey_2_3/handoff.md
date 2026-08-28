# Technical Specification & Handoff Report: Enemy Systems & Game Scene Flow (Phase 0 & Phase 1)

**Agent Identity**: `teamwork_preview_spec_miner` (Survey Explorer 3 — Enemy Systems & Scene Flow Specialist)  
**Workspace**: `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata`  
**Target Path**: `.agents/teamwork_preview_explorer_survey_2_3/handoff.md`  
**Date**: 2026-08-28  

---

## 1. Observation

Direct observations extracted from project files and authoritative sources:

1. **`ORIGINAL_REQUEST.md` (lines 12–25, 42–55)**:
   - Phase 0 requires base architecture, procedural asset generator (`tools/gerador_assets.py`), and main game window via PPlay framework in `.venv`.
   - Phase 1 requires player avatar (potato), basic WASD movement, shooting mechanics, and standard enemies that spawn and move directly towards the player (beeline, no complex pathfinding).
   - Acceptance criteria: window launches, player moves and shoots, enemies spawn, move directly towards player, and can be destroyed.

2. **`.agents/architecture_cache.md` (lines 10–37)**:
   - Module layout: `src/main.py`, `src/cenas/` (`menu_principal.py`, `gameplay.py`, `menu_pausa.py`, `level_up.py`, `game_over.py`), `src/entidades/` (`jogador.py`, `inimigo_*.py`, `projetil.py`, `drop.py`), `src/sistemas/` (`sistema_spawn.py`, `sistema_xp.py`, `sistema_drops.py`, `config_sistema.py`), `src/ui/` (`hud.py`, `card_config.py`, `botao.py`), `src/utils/` (`constantes.py`, `math_utils.py`, `asset_loader.py`).
   - Single Source of Truth (SSOT): `CONFIGURACOES.md` is the authoritative definition for numeric balancing, buffs, and nerfs.
   - PPlay 2.0 engine located in `.venv/Lib/site-packages/PPlay`.

3. **`GDD.md`, `gdd lab batata.md`, `s1.md`–`s6.md`**:
   - `s4.md` §4.2 & §4.7: Standard enemy ("Intern" / "Estagiário") spawns offscreen, acquires player position, moves directly towards player, deals contact damage with independent damage cooldown, dies at HP $\le 0$, drops XP/crates.
   - `s2.md` §2.6–2.7: Player base HP is 150 (no natural regen). Contact damage has per-enemy cooldown (e.g. standard 400 ms, fast 250 ms, tank 700 ms).
   - `s4.md` §4.5–4.6: Enemies spawn continuously outside the visible viewport; wave density and frequency scale smoothly over survival time.
   - `s5.md` §5.4 & `gdd lab batata.md` §18–26: Minimal HUD contains: HP bar (green/red) and XP bar (yellow) beneath player avatar; top-left inventory (4 slots with ammo/cooldown); top-right settings button + FPS counter; timer and kill counter.
   - `CONFIGURACOES.md` §1–20: 20 unlockable gameplay configs directly alter enemy HP (Config #2: -20% HP; Config #17: +50%/+100% HP), enemy speed (Config #1: 30 FPS -> -10% speed, 15 FPS -> -19% speed; Config #16: +25%/+50% speed), enemy damage (Config #1: 45 FPS -> -15% damage, 15 FPS -> -27.75% damage; Config #18: Fog of War -> -50% damage outside FOV), drops (Config #3, #10, #15), and XP (Config #7, #11, #16).

4. **PPlay Framework Inspection (`.venv/Lib/site-packages/PPlay`)**:
   - `scenemanager.py`: `Scene` base class provides `.janela`, `.teclado`, `.mouse`, `.loop()`, `.draw()`. `SceneManager.change_scene(next_scene)` and `SceneManager.run()`.
   - `window.py`: Virtual canvas buffer (`Window(largura_virtual=800, altura_virtual=600, resizavel=True, pixel_art=True)`). Provides `janela.delta_time()`, `janela.get_fps()`, `janela.draw_text(...)`, `janela.screen`, and `janela.update()`.
   - `camera.py`: `Camera(largura, altura)` with `camera.follow(target, suavizacao=0.1)` and `transform_x(world_x)`, `transform_y(world_y)`.

---

## 2. Logic Chain

From these observations, we deduce the following technical architecture for Phase 0 & Phase 1:

1. **Enemy System Modular Architecture**:
   - An abstract/base class `InimigoBase` in `src/entidades/inimigo_base.py` defining common state: `x, y, width, height, hp, max_hp, speed, damage, damage_cooldown, damage_timer, xp_value, score_value, sprite`.
   - Concrete standard archetype `InimigoPadrao` in `src/entidades/inimigo_padrao.py` implementing the baseline crawler.
   - Decoupled `SistemaSpawn` in `src/sistemas/sistema_spawn.py` holding the spawn timer, wave scaling formulas, offscreen coordinate generator, and active enemy collection.

2. **Mathematical Vector AI Formulation**:
   - Target position: $(x_p, y_p)$ = Player center $(x_{\text{player}} + w/2, y_{\text{player}} + h/2)$.
   - Enemy center: $(x_e, y_e) = (x_{\text{enemy}} + w/2, y_{\text{enemy}} + h/2)$.
   - Displacement: $\Delta x = x_p - x_e$, $\Delta y = y_p - y_e$.
   - Distance: $d = \sqrt{\Delta x^2 + \Delta y^2}$.
   - Unit vector: $\hat{u} = (\Delta x / d, \Delta y / d)$ if $d > 0$, else $(0, 0)$.
   - Effective speed: $v_{\text{eff}} = v_{\text{base}} \times M_{\text{speed\_configs}}$.
   - Position increment per frame: $x \leftarrow x + \hat{u}_x \cdot v_{\text{eff}} \cdot \Delta t$, $y \leftarrow y + \hat{u}_y \cdot v_{\text{eff}} \cdot \Delta t$.

3. **Spawn Geometry & Spatial Generation**:
   - Spawning must happen outside the visible camera view to prevent visual pop-in.
   - Screen bounds in world space: $[x_{\text{cam}}, y_{\text{cam}}, x_{\text{cam}} + W_{\text{virt}}, y_{\text{cam}} + H_{\text{virt}}]$.
   - Offscreen margin: $M = 60\text{ px}$.
   - Perimeter edge random selection: choose one of 4 edges (Top, Bottom, Left, Right) uniformly, generating random point along chosen edge.

4. **Scene Management & Coordinate Space Segregation**:
   - `main.py` instantiates `Window(800, 600)` and invokes `SceneManager.run()`.
   - `GameplayScene` inherits from `PPlay.scenemanager.Scene`.
   - Rendering requires strict separation of coordinate systems:
     - **World Space Rendering** (Camera transformed): Map tiles, Player, Enemies, Projectiles, Drops, In-world HP/XP bars.
     - **Screen Space Rendering** (Fixed 2D canvas): Inventory slots, Kill count, Timer, Settings button, Pause overlay, Level-up card overlay.

---

## 3. Specifications for Phase 0 & Phase 1

### 3.1 Enemy Specifications (Baseline Crawler: "Inimigo Padrão")

| Parameter | Baseline Value | Config / Scaling Modifiers | Evidence Tier |
|---|---|---|---|
| **Archetype Name** | Inimigo Padrão (*Intern / Potato Bug*) | `inimigo_padrao.py` | [Verified] |
| **Base HP** | **25 HP** | Scaled by Config #2 (-20% if low graphics), Config #17 (+50%/+100% HP) | [Verified] |
| **Base Speed** | **100 px/s** | Scaled by Config #1 (30 FPS $\to 0.90\times$, 15 FPS $\to 0.81\times$), Config #16 (+25%/+50%) | [Verified] |
| **Contact Damage** | **10 damage** | Scaled by Config #1 (45 FPS $\to 0.85\times$, 15 FPS $\to 0.7225\times$), Config #18 (Fog $\to 0.5\times$ outside FOV) | [Verified] |
| **Damage Cooldown** | **400 ms (0.4 s)** | Individual timer per enemy instance | [Observed] (`s2.md` §2.7) |
| **Hitbox Dimensions** | **24 × 24 px** (sprite 32 × 32 px) | Centered on sprite | [Inferred] |
| **XP Value** | **10 XP** | Scaled by Config #7 (+25% if HUD off), Config #11 (+20%), Config #16 (+20%/+40%), Config #15 (2× if scavenger active) | [Verified] |
| **Score Value** | **100 points** | Direct score increment per kill | [Inferred] |
| **Drop Rates** | XP Drop: **100%** (gem/crate); Item Crate: **15% base** (Heal 10%, Weapon 3%, Equip 2%) | Modified by Config #3 (Res +10%/+25%/+50%), Config #10 (+40%), Config #17 (+20%/+40%) | [Observed] (`s4.md` §4.14–4.20) |
| **Visual Asset** | `assets/inimigos/inimigo_padrao.png` (red outline) | Low Graphics: Purple/Red filled rectangle `(24, 24)` | [Observed] (`s6.md` §6.2.3, `gdd lab batata.md`) |

---

### 3.2 Spawning System Specifications

#### A. Spatial Spawning Algorithm (Perimeter Ring)
```python
def get_random_spawn_point(camera_x, camera_y, view_w=800, view_h=600, margin=60):
    edge = random.choice(['top', 'bottom', 'left', 'right'])
    if edge == 'top':
        x = random.uniform(camera_x - margin, camera_x + view_w + margin)
        y = camera_y - margin
    elif edge == 'bottom':
        x = random.uniform(camera_x - margin, camera_x + view_w + margin)
        y = camera_y + view_h + margin
    elif edge == 'left':
        x = camera_x - margin
        y = random.uniform(camera_y - margin, camera_y + view_h + margin)
    else:  # right
        x = camera_x + view_w + margin
        y = random.uniform(camera_y - margin, camera_y + view_h + margin)
    return x, y
```

#### B. Dynamic Wave Scaling Formulas
1. **Spawn Interval ($T_{\text{spawn}}$)**:
   $$T_{\text{spawn}}(t) = \max\left(0.40\text{s},\; 1.80\text{s} - 0.012\text{s} \times t\right)$$
   - At $t = 0\text{s}$: 1.80s between spawns.
   - At $t = 60\text{s}$: 1.08s between spawns.
   - At $t = 120\text{s}$: 0.40s (clamped minimum).

2. **Batch Spawn Quantity ($N_{\text{batch}}$)**:
   $$N_{\text{batch}}(t) = \min\left(8,\; 1 + \left\lfloor \frac{t}{25} \right\rfloor\right)$$
   - $0 \le t < 25\text{s}$: 1 enemy per spawn tick.
   - $25 \le t < 50\text{s}$: 2 enemies per spawn tick.
   - $50 \le t < 75\text{s}$: 3 enemies per spawn tick.
   - $t \ge 175\text{s}$: 8 enemies per spawn tick (max cap per batch).

3. **Active Enemy Population Soft Cap**:
   - $N_{\text{max\_active}} = 60$ enemies (Phase 1). Prevents framerate drops before spatial partitioning is added.

4. **Despawn / Cleanup Boundary**:
   - If distance $d(P_{\text{enemy}}, P_{\text{player}}) > 1800\text{ px}$, remove or teleport the enemy to a new spawn position around the player.

---

### 3.3 Enemy AI & Combat Life Cycle

```
  [OFFSCREEN SPAWN]
         │
         ▼
     [CHASING] ◄────────────────────────────────────┐
         │                                          │
         ├─► Calculate Unit Vector to Player        │
         ├─► Multiply by Config-Modified Speed      │
         ├─► Update World Position (x, y)           │
         │                                          │
         ├─► Check Collision with Player Hitbox     │
         │       │                                  │
         │       ▼ (Colliding)                      │
         ├─► [CONTACT ATTACK]                       │
         │       ├─ If cooldown <= 0:               │
         │       │    Player HP -= EffectiveDamage  │
         │       │    cooldown = 0.4s               │
         │       └─ cooldown -= dt ─────────────────┘
         │
         ├─► Check Hit by Projectile / Melee Attack
         │       │
         │       ▼ (Damage Received)
         │   Enemy HP -= WeaponDamage
         │   Flash sprite / Trigger Damage Number (Config #8)
         │   Check Enemy HP <= 0 ?
         │       │
         │       ▼ (YES)
         └──► [DEATH & DESTRUCTION]
                 ├─ Kill Count += 1, Score += 100
                 ├─ Play SFX: Enemy Death
                 ├─ Spawn Death Particle Effect
                 ├─ Drop XP Crate/Gem at (x, y) with hop impulse
                 ├─ Roll for Item Crate (Heal/Weapon/Equip)
                 └─ Remove Enemy from Active Group
```

---

### 3.4 Scene Flow & UI Layout Architecture

#### A. Scene State Machine (`src/cenas/`)
1. `src/main.py`: Entry point. Creates `Window(800, 600, "Protocolo: Batata", pixel_art=True)`. Initializes `ConfigSistema` and sets scene to `MenuPrincipalScene` (or directly `GameplayScene` in Phase 1 debug mode).
2. `src/cenas/menu_principal.py`:
   - Buttons: **Jogar**, **Configurações**, **Créditos**, **Sair**.
   - Background: Tiled arena background + Title logo.
3. `src/cenas/gameplay.py`:
   - Core gameplay controller.
   - Owns instances of: `Jogador`, `Camera`, `SistemaSpawn`, `ProjetilManager`, `DropManager`, `HUD`, `ConfigSistema`.
   - Sub-states:
     - `RUNNING`: Normal game updates and rendering.
     - `PAUSED`: Pause menu active (`MenuPausaOverlay`).
     - `LEVEL_UP`: Level up menu active (`LevelUpOverlay` with 3 config cards).
     - `GAME_OVER`: Player HP reached 0 (`GameOverOverlay`).
4. `src/cenas/menu_pausa.py`:
   - Modal overlay. Options: **Continuar**, **Configurações**, **Menu Principal**.
5. `src/cenas/level_up.py`:
   - Modal overlay. Darkens screen with alpha fill `(0, 0, 0, 180)`.
   - Selects 3 random locked configs from `ConfigSistema`.
   - Displays 3 clickable cards. On click: unlocks chosen config, saves to `data/save.json`, resumes `RUNNING`.
6. `src/cenas/game_over.py`:
   - Displays: Survival Time, Total Kills, Score, Unlocked Configs.
   - Buttons: **Tentar Novamente**, **Menu Principal**.

#### B. Minimal HUD Specifications (Phase 0/1)

```
+-------------------------------------------------------------------------+
| [Slot 1] [Slot 2] [Slot 3] [Slot 4]        Time: 02:45   [⚙] FPS: 60    |
| (Melee)  (Pistol) (Special) (Drone)         Kills: 42                   |
|           [Inf]   [Ammo: 24] [Timer: 18s]                               |
|                                                                         |
|                                                                         |
|                                (World)                                  |
|                                                                         |
|                              [  Potato  ]                               |
|                              [██████████]  <-- In-World HP Bar (Green)  |
|                              [██████░░░░]  <-- In-World XP Bar (Yellow) |
|                                                                         |
|                                                                         |
|                                                                         |
|                                                                         |
+-------------------------------------------------------------------------+
```

1. **In-World Health Bar (`barra_hp`)**:
   - Location: Centered horizontally beneath player avatar: $(x_{\text{player}} + w/2 - 20 - x_{\text{cam}},\; y_{\text{player}} + h + 6 - y_{\text{cam}})$.
   - Size: $40 \text{ px}$ width, $6 \text{ px}$ height.
   - Colors: Border `(30, 30, 30)`, Background `(180, 40, 40)`, Fill `(40, 220, 60)` proportional to `hp / max_hp`.
2. **In-World Experience Bar (`barra_xp`)**:
   - Location: Directly beneath HP bar: $(x_{\text{player}} + w/2 - 20 - x_{\text{cam}},\; y_{\text{player}} + h + 14 - y_{\text{cam}})$.
   - Size: $40 \text{ px}$ width, $4 \text{ px}$ height.
   - Colors: Border `(30, 30, 30)`, Background `(40, 40, 40)`, Fill `(240, 210, 30)` proportional to `xp / xp_next_level`.
3. **Screen-Space Inventory HUD (Top-Left)**:
   - Position: $(16\text{ px}, 16\text{ px})$.
   - 4 boxes ($36 \times 36\text{ px}$ each, $8\text{ px}$ padding):
     - Slot 1: Wrench icon (Melee, cooldown indicator).
     - Slot 2: Pistol icon (Permanent, "∞").
     - Slot 3: Special weapon icon (e.g. Shotgun, numeric ammo remaining).
     - Slot 4: Support drone icon (e.g. Heal drone, numeric duration remaining in seconds).
4. **Screen-Space Match Metrics (Top-Center)**:
   - Match Timer: `MM:SS` (Font size 22, White, centered at $x=400, y=16$).
   - Kill Counter: `Abates: XX` (Font size 16, Light Yellow, centered at $x=400, y=42$).
5. **Screen-Space Gear Button & FPS (Top-Right)**:
   - Gear Button: $32 \times 32\text{ px}$ at $(752\text{ px}, 16\text{ px})$. Clicking pauses and opens configs.
   - FPS Counter: Directly to the left of the gear button $(690\text{ px}, 22\text{ px})$.
6. **HUD Toggle Behavior (Config #7 `hud`)**:
   - If `hud == "Desligado"`: Hide HP bar, XP bar, inventory, timer, kill count, and FPS counter. **Retain ONLY the Gear button** so player can pause and access settings. Apply **+25% XP multiplier**.

---

## 4. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Enemy Archetype | Inimigo Padrão (*Intern / Potato Bug*) | Baseline swarm enemy; moves directly toward player; deals contact damage | Position $(x, y)$, Target $(x_p, y_p)$, Speed $(100\text{ px/s})$, HP $(25)$ | Movement $\Delta(x, y)$, Contact damage $(10)$, XP drop | Graceful clamp if distance is 0 | `s4.md` §4.7, `GDD.md` §2.7 |
| 2 | Enemy AI | Unit Vector Beeline Movement | Calculates normalized Euclidean vector to player and advances position per frame | $\vec{P}_e, \vec{P}_p, \Delta t, v_{\text{eff}}$ | Updated $(x_e, y_e)$ | If distance $< 10^{-5}$, vector defaults to $(0,0)$ | `s4.md` §4.2, `ORIGINAL_REQUEST.md` |
| 3 | Enemy Combat | Independent Contact Damage Cooldown | Each enemy instance tracks its own cooldown timer $(0.4\text{s})$ before dealing damage again | Collision state, `cooldown_timer`, $\Delta t$ | Damage applied to player, timer reset to $0.4\text{s}$ | Timer ignores sub-zero decrements | `s2.md` §2.7 |
| 4 | Enemy Spawning | Offscreen Perimeter Spawn Generator | Generates random coordinates along a perimeter ring $60\text{ px}$ outside visible camera viewport | Camera bounds $(x_{cam}, y_{cam}, W, H)$, Margin $(60)$ | Random spawn coordinate $(x_s, y_s)$ | Clamped to world boundaries if bounded | `s4.md` §4.5 |
| 5 | Enemy Spawning | Continuous Wave & Density Scaling | Gradually reduces spawn interval from $1.8\text{s}$ to $0.4\text{s}$ and increases batch size from $1$ to $8$ | Elapsed game time $t$ | Current $T_{\text{spawn}}$ and $N_{\text{batch}}$ | Clamped to defined min/max bounds | `s4.md` §4.4–4.6 |
| 6 | Enemy Spawning | Far-Distance Despawn / Cleanup | Despawns or recycles enemies exceeding $1800\text{ px}$ distance from player | Enemy distance $d$ | Despawn / reposition event | Memory freed / object recycled | `s4.md` §4.5 |
| 7 | Death & Destruction | Health Depletion & Kill Event | When enemy HP $\le 0$, increments kill counter and score, plays SFX and visual explosion | Enemy damage event, Current HP | Kill count $+1$, Score $+100$, Death particle | Prevents multi-death execution on same frame | `s4.md` §4.2, `ORIGINAL_REQUEST.md` |
| 8 | Drops & Economy | XP Gem / Crate Generation | On death, drops a purple XP crate with upward hop physics that grants XP on player overlap | Enemy death coordinate $(x, y)$, XP value $(10)$ | Drop entity in world, XP granted on pickup | Crate position clamped within walkable world | `s4.md` §4.15–4.17, `gdd lab batata.md` |
| 9 | Drops & Economy | Item Crate Drop Table | Rolls probability for Healing Crate $(10\%)$, Weapon Crate $(3\%)$, Equipment Crate $(2\%)$ | Enemy death event, Drop rate multipliers | Crate entity spawn | Safe fallback if loot table roll fails | `s4.md` §4.14, `CONFIGURACOES.md` |
| 10 | Scene Flow | Scene Lifecycle Architecture | Modular scene system using PPlay `Scene` and `SceneManager` (`main.py` $\to$ `GameplayScene`) | Scene transition events | Active scene execution (`loop()` and `draw()`) | Fallback to default scene if target missing | PPlay `scenemanager.py`, `architecture_cache.md` |
| 11 | Scene Flow | In-Game Pause Overlay | Pauses game physics and updates, opens modal pause menu with Continue / Configs / Menu | ESC key press or Gear icon click | Game state $\to$ `PAUSED`, renders overlay | Blocks background game input while paused | `s5.md` §5.6 |
| 12 | Scene Flow | Level-Up Selection Overlay | Pauses game upon XP threshold, presents 3 randomly selected locked config cards | Level-up event (`xp >= xp_next`) | Game state $\to$ `LEVEL_UP`, card selection UI | If $< 3$ configs locked, displays only remaining | `GDD.md` §2.15, `s3.md` §3.3 |
| 13 | Scene Flow | Game Over Screen | Triggered upon player HP $\le 0$; displays statistics and retry/menu buttons | Player death event | Game state $\to$ `GAME_OVER` | Disables player controls and stops spawn timer | `s2.md` §2.6, `s5.md` |
| 14 | UI / HUD | Dual-Layer Coordinate Rendering | Renders world entities with camera transformation and UI elements with screen coordinates | World entities, UI components, Camera $(x, y)$ | Rendered canvas on `Window.screen` | Prevents UI drift during camera movement | `s5.md` §5.4, PPlay `camera.py` |
| 15 | UI / HUD | Minimal In-World HP & XP Bars | Draws dynamic color-coded HP and XP bars floating directly beneath the player | Player HP, Max HP, Player XP, Next Level XP | Rendered bar graphics at player screen pos | Clamps bar width between $0\%$ and $100\%$ | `gdd lab batata.md` §18–20, `s5.md` §5.4 |
| 16 | UI / HUD | Modular 4-Slot Inventory Display | Displays equipped melee, pistol, special weapon (ammo count), and equipment (timer) | Inventory slot data, Ammo counts, Durations | Top-left inventory UI graphic | Displays empty state gracefully | `s2.md` §2.10, `s5.md` §5.15 |
| 17 | UI / HUD | HUD Visibility Toggle (Config #7) | Hides all HUD elements except Gear button and grants $+25\%$ XP gain when disabled | Config `hud` state (`"Ligado"` / `"Desligado"`) | Selective HUD rendering, XP multiplier $+25\%$ | Gear button remains accessible at all times | `CONFIGURACOES.md` #7, `s5.md` §5.5 |
| 18 | Config Modifiers | Config-Driven Enemy Stats Hook | Dynamically scales enemy HP, speed, and damage based on active configs (FPS, Graphics, Speed, HP) | Active config registry dictionary | Modified enemy base parameters | Fallback to baseline $(1.0\times)$ if config absent | `CONFIGURACOES.md` #1, #2, #16, #17 |

---

## 5. Edge Cases & Boundary Conditions

| # | Feature | Input / Scenario | Observed / Expected Behavior |
|---|---|---|---|
| EC-001 | Enemy AI Vector Math | Enemy and player centers are at the exact same coordinate ($d = 0$) | Division by zero avoided by condition `if dist > 0.0001: ... else: (0, 0)`. Enemy does not crash or teleport to NaN. |
| EC-002 | Enemy Damage Cooldown | Multiple enemies collide with player on the same frame | Each enemy tracks its own `damage_timer`. All eligible enemies apply their initial damage, then enter independent $0.4\text{s}$ cooldowns. Player takes cumulative damage without frame-rate dependent multiplication. |
| EC-003 | Enemy Spawning | Camera is moving rapidly at edge of arena | Perimeter spawner evaluates camera coordinates $(x_{\text{cam}}, y_{\text{cam}})$ each frame, ensuring enemies spawn strictly outside the current rendered window view. |
| EC-004 | Wave Scaling Overflow | Survival time exceeds 30 minutes ($t > 1800\text{s}$) | $T_{\text{spawn}}$ is clamped to a minimum floor ($0.40\text{s}$) and $N_{\text{batch}}$ is capped at 8 enemies per tick; total active enemies are capped at $N_{\text{max}} = 60$, preventing memory leaks and frame-rate collapse. |
| EC-005 | Death on Same Frame | Enemy takes lethal damage from 2 projectiles simultaneously | Enemy health drops $\le 0$; death handler sets `is_dead = True` immediately to ensure kill count, XP drops, and SFX trigger exactly once. |
| EC-006 | Zero Locked Configs Left | Player reaches Level 20+ when all 20 gameplay configs are unlocked | Level-up check detects `len(locked_configs) == 0` and disables further level-up pause menus, allowing endless survival without crash. |
| EC-007 | HUD Disabled State | Config #7 (`hud = "Desligado"`) is enabled during gameplay | HUD bars, timer, and inventory are hidden, but the Gear button $(752, 16)$ remains interactive, allowing the player to pause and adjust settings. |
| EC-008 | Window Minimization / Resize | Player resizes or minimizes game window during wave | PPlay `Window.update()` maintains aspect ratio and clamps virtual resolution to $(800, 600)$ buffer; virtual coordinates for mouse input remain mapped via `screen_to_virtual_coords`. |
| EC-009 | Delta Time Spike | Game lag or pause causes large $\Delta t > 0.5\text{s}$ | $\Delta t$ in physics and AI is clamped to $\min(\Delta t, 0.1\text{s})$ to prevent enemies from teleporting through player or walls. |

---

## 6. Caveats & Assumptions

1. **No Complex Pathfinding (As Designed)**: Enemies intentionally do not use A* or obstacle avoidance. If obstacles (e.g. crates/rocks) are present, beeline AI will cause enemies to slide or press against the obstacle until they clear it.
2. **Phase 1 Asset Generation**: Placeholder procedural graphics for enemies, drops, and HUD will be generated by `tools/gerador_assets.py` using Pillow.
3. **PPlay Integration Convention**: Because PPlay's `Sprite` handles drawing directly to `Window.screen`, world-space sprites must update their screen position using `camera.transform_x(self.x)` and `camera.transform_y(self.y)` before calling `sprite.draw()`, or blit manually with camera offset.

---

## 7. Conclusion

The technical specifications for Enemy Spawning, Enemy AI, Death/Destruction, XP/Drop systems, and Scene Flow for Phase 0 & Phase 1 are fully defined, authoritative, and aligned with `ORIGINAL_REQUEST.md`, `architecture_cache.md`, `GDD.md`, and `CONFIGURACOES.md`.

Implementation agents can directly construct:
1. `src/entidades/inimigo_base.py` and `src/entidades/inimigo_padrao.py` with standard crawler parameters (25 HP, 100 px/s, 10 damage, 400 ms cooldown, 10 XP).
2. `src/sistemas/sistema_spawn.py` with perimeter ring spawning, wave scaling ($1.8\text{s} \to 0.4\text{s}$), and soft cap (60 active enemies).
3. `src/cenas/gameplay.py` and `src/main.py` with dual-layer rendering (world vs screen space), minimal HUD (in-world HP/XP bars, top-left inventory, top-right gear button), and modal pause/level-up overlays.

---

## 8. Verification Method

To independently verify these specifications during implementation:

1. **Module Import & Scene Test**:
   ```powershell
   .venv\Scripts\python -c "import PPlay; from PPlay.window import Window; from PPlay.scenemanager import Scene, SceneManager; print('PPlay engine ready')"
   ```
2. **AI Vector Unit Test**:
   Create a standalone test verifying $\hat{u}$ calculation, distance normalization, and $\Delta t$ clamping:
   ```python
   dx, dy = target_x - enemy_x, target_y - enemy_y
   dist = (dx**2 + dy**2)**0.5
   ux, uy = (dx / dist, dy / dist) if dist > 0 else (0, 0)
   assert abs((ux**2 + uy**2)**0.5 - 1.0) < 1e-4
   ```
3. **Spawning Perimeter Test**:
   Verify generated coordinates $(x, y)$ satisfy:
   $x < x_{\text{cam}} \lor x > x_{\text{cam}} + W \lor y < y_{\text{cam}} \lor y > y_{\text{cam}} + H$.
4. **Gameplay Launch Test**:
   ```powershell
   .venv\Scripts\python src/main.py
   ```
