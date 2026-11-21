# Handoff Report — Explorer 1 (Phase 6: Waves, Elite Mini-Bosses, Boss HUD & Drops)

## 1. Observation

### 1.1 Spawning Subsystem (`src/sistemas/sistema_spawn.py`)
- **Lines 23-46**: `SistemaSpawn` defines:
  - `intervalo_spawn(tempo_s)`: `max(0.75, 3.00 - 0.012 * tempo_s)`
  - `tamanho_lote(tempo_s)`: `min(8, 1 + int(tempo_s // 25.0))`
- **Lines 47-81**: `escolher_arquetipo(tempo_s)` transitions through 4 temporal tiers:
  - Tier 1 (`t < 25s`): `InimigoPadrao` (100%)
  - Tier 2 (`t < 55s`): `InimigoRapido` (25%), `InimigoPadrao` (75%)
  - Tier 3 (`t < 90s`): `InimigoRapido` (30%), `InimigoPhasing` (15%), `InimigoBlindado` (15%), `InimigoPadrao` (40%)
  - Tier 4 (`t >= 90s`): `InimigoRapido` (25%), `InimigoRanged` (18%), `InimigoPhasing` (14%), `InimigoBlindado` (13%), `InimigoTank` (5%), `InimigoPadrao` (25%)
- **Lines 82-113**: `gerar_posicao_spawn(...)` places spawns outside the camera viewport on a chosen edge with `margem = 80.0` px.
- **Lines 115-158**: `update(...)` manages elapsed time and spawns batch quantities. Currently, there is **no tracking of minute boundaries** or dedicated elite boss spawn schedule.

### 1.2 Enemy Entities Subsystem (`src/entidades/`)
- `InimigoBase` (`src/entidades/inimigo_base.py`, lines 20-56):
  - Base attributes: `x, y, largura, altura, hp_max, hp, velocidade, dano_contato, cooldown_contato_max, cooldown_contato_atual, xp_valor, score_valor, vivo, flash_timer, vx_knockback, vy_knockback, sprite_key`.
  - Flash on damage: `flash_timer = 0.10` with `BLEND_ADD` tint.
  - Rendering in lines 150-178 handles screen bounds checking and blitting sprite or fallback rect.
- Subclasses:
  - `InimigoPadrao` (`src/entidades/inimigo_padrao.py`): 40 HP, 28x28px, 5 XP.
  - `InimigoTank` (`src/entidades/inimigo_tank.py`): 120 HP, 62x62px, 25 XP.
  - `InimigoRapido` (`src/entidades/inimigo_rapido.py`): 20 HP, 31x31px, 8 XP.
  - `InimigoPhasing` (`src/entidades/inimigo_phasing.py`): 35 HP, 42x42px, 12 XP, 3.0s cycle with 1.2s intangibility.
  - `InimigoBlindado` (`src/entidades/inimigo_blindado.py`): 50 HP, 47x47px, 15 XP, 30% damage reduction on 90° frontal cone.
  - `InimigoRanged` (`src/entidades/inimigo_ranged.py`): 30 HP, 42x42px, 15 XP, 280px stand-off, shoots projectiles every 1.2s at <= 350px.
- **Gaps**: None of the enemy classes currently possess `is_elite`, `nome_elite`, 3x HP scaling, or purple/gold aura render routines.

### 1.3 Drops Subsystem (`src/sistemas/sistema_drops.py` & `src/entidades/drop.py`)
- `SistemaDrops.gerar_drop_morte_inimigo` (`src/sistemas/sistema_drops.py`, lines 25-117):
  - Always creates 1 XP gem (`tipo="xp"`, `valor=xp_base or 5`).
  - RNG rolls for heal crate (`chance_cura_base = 0.08`).
  - RNG rolls for weapon crate (`chance_arma_base = 0.04` or `0.15` if `loot_enriquecido`).
  - RNG rolls for equipment crate (`chance_equip_base = 0.03` or `0.15` if `loot_enriquecido`).
- `ItemDrop` (`src/entidades/drop.py`, lines 18-58):
  - Supports types: `"xp"`, `"cura"`, `"arma"`, `"equipamento"`, `"config"`.
  - Lifetime: `DROP_TEMPO_DESAPARECER = 60.0`s.
  - Scavenger activation delay: `DROP_TEMPO_SCAVENGER_ATIVAR = 5.0`s.

### 1.4 HUD and UI Layout (`src/ui/hud.py` & `src/cenas/gameplay.py`)
- `HUD` (`src/ui/hud.py`):
  - `desenhar_barra_xp(screen, sistema_xp, visivel=True)` at `pos_x = (LARGURA_TELA - 360) // 2 = 220`, `pos_y = 62`, `dim = 360x10 px`.
- `GameplayScene._desenhar_hud_tela` (`src/cenas/gameplay.py`, lines 720-858):
  - Slots 1-4 at top-left (`16, 14` to `208, 56`).
  - Timer at top-center (`centerx = 400, top = 14`).
  - Kill counter at top-center (`centerx = 400, top = 40`).
  - XP Bar at top-center (`centerx = 400, top = 62`).
  - Gear button & FPS at top-right (`752, 16`).
- **Gaps**: There is currently no `HUD.desenhar_barra_boss` method or active boss detection in `gameplay.py`.

### 1.5 Automated Test Suite (`tests/`)
- Current status: **139 tests running and passing** in 0.92s (`python -m unittest discover -s tests`).
- Existing coverage:
  - `test_enemies.py`: standard enemy, beeline, contact cooldown, spawn scaling, camera perimeter generation.
  - `test_advanced_enemies.py`: rapid, ranged, phasing, and blindado mechanics.
  - `test_drops_xp.py`: drop lifecycle, XP scaling, scavenger AI.
  - `test_challenger_enemies_scavenger_stress.py`: angular and timing boundary stress tests.

---

## 2. Logic Chain

### 2.1 Wave & Elite Spawning Schedule
1. **[Observed]** `SistemaSpawn.update` receives `dt` and tracks `self.tempo_decorrido`.
2. **[Observed]** Requirement R1 specifies spawning a designated Elite/Mini-Boss every 60s (1:00, 2:00, 3:00, etc.).
3. **[Inferred]** `SistemaSpawn` should maintain `self.ultimo_minuto_elite: int = 0`.
4. **[Inferred]** When `minuto_atual = int(self.tempo_decorrido // 60.0)` is greater than `self.ultimo_minuto_elite` (and `minuto_atual >= 1`):
   - Determine elite archetype based on minute index:
     - Minute 1 (60s): Elite `InimigoPadrao` (or `InimigoRapido`) — "MINI-BOSS: ESTAGIÁRIO SÊNIOR"
     - Minute 2 (120s): Elite `InimigoTank` — "MINI-BOSS: GELADEIRA INDUSTRIAL TURBO"
     - Minute 3 (180s): Elite `InimigoPhasing` — "MINI-BOSS: PHANTOM EXECUTIVO"
     - Minute 4 (240s): Elite `InimigoBlindado` — "MINI-BOSS: BASTIÃO TITÂNICO"
     - Minute 5 (300s): Elite `InimigoRanged` — "MINI-BOSS: COMANDANTE ARTILHEIRO"
     - Minute 6+ (360s, 420s, 480s, 540s): Advanced rotation with scaled difficulty.
   - Instantiate elite enemy with `is_elite=True`, `nome_elite="..."` and append to spawn output list.
   - Update `self.ultimo_minuto_elite = minuto_atual`.

### 2.2 Elite Enemy Mechanics & Aura Rendering
1. **[Observed]** All enemies inherit from `InimigoBase`.
2. **[Inferred]** Modifying `InimigoBase.__init__` to accept `is_elite: bool = False` and `nome_elite: str = ""` allows any archetype to be instantiated as an Elite without breaking class hierarchy or polymorphous behavior.
3. **[Inferred]** When `is_elite=True`:
   - `hp_max = int(hp * 3)`
   - `hp = self.hp_max`
   - `score_valor = score_valor * 10` (e.g. 1000 to 3000 pts)
   - `xp_valor = 50`
   - `largura` / `altura` can be scaled by ~1.25x for imposing physical presence.
4. **[Inferred]** In `InimigoBase.desenhar(self, janela, camera=None)`:
   - If `self.is_elite`:
     - Render a pulsing radial purple (`ROXO_ACENTO` = `(175, 75, 255)`) and gold (`DOURADO` = `(255, 215, 0)`) aura around the enemy position using `pygame.SRCALPHA`.
     - Aura pulse factor: `pulso = math.sin(pygame.time.get_ticks() / 150.0) * 4.0`.
     - Blit halo surface centered on the enemy prior to or surrounding sprite blit.

### 2.3 Guaranteed Elite Drops
1. **[Observed]** `SistemaDrops.gerar_drop_morte_inimigo` handles item instantiation on enemy death.
2. **[Observed]** Requirement R1 states: "Defeating an Elite Boss is guaranteed to drop a high-value XP cluster (+50 XP) and guaranteed weapon/equipment crates."
3. **[Inferred]** In `SistemaDrops.gerar_drop_morte_inimigo(..., is_elite: bool = False)`:
   - When `is_elite=True`:
     - **XP Cluster (+50 XP)**: Spawn 5 XP gem drops of 10 XP each arranged in a small ring around `(x, y)` (radius ~24px), or 1 super cluster gem of 50 XP. (A ring of 5 gems of 10 XP provides immediate visual satisfaction as a "cluster").
     - **Guaranteed Weapon Crate**: Force `drop_arma` spawn (100% chance).
     - **Guaranteed Equipment Crate**: Force `drop_equipamento` spawn (100% chance).
     - **Bonus Heal Drop**: High chance (50% or 100%) for medical box.

### 2.4 Dedicated Top-Screen Boss HP Bar
1. **[Observed]** The top HUD currently has slots on left, timer at `top=14`, abates at `top=40`, XP bar at `top=62` (y=62..72).
2. **[Inferred]** Vertical space between `y = 76` and `y = 96` is available for a prominent Boss HP Bar.
3. **[Inferred]** Add `HUD.desenhar_barra_boss(screen, boss_elite, visivel=True)`:
   - Dimensions: width = `400px`, height = `12px`, centered horizontally at `x = 200`, `y = 78`.
   - Layout:
     - Name label: Arial 11 bold in `DOURADO` (e.g. `"★ MINI-BOSS: GELADEIRA TURBO ★"`) rendered at `y = 66` (or inside bar).
     - Background: Dark purple container `(35, 20, 50)`.
     - Fill: `ROXO_CLARO` / `(215, 140, 255)` with gold/white highlight based on `boss.hp / boss.hp_max`.
     - Border: 2px metallic gold border `(255, 215, 0)` with corner radius 3.
     - Text: `f"{boss.hp}/{boss.hp_max} HP"` in white with black shadow centered on the bar.
4. **[Inferred]** In `GameplayScene._desenhar_hud_tela`:
   - Query `boss_ativo = next((e for e in self.inimigos if getattr(e, "is_elite", False) and e.vivo), None)`.
   - If `boss_ativo is not None` and HUD is visible, call `self.hud.desenhar_barra_boss(screen, boss_ativo)`.

---

## 3. Caveats

1. **[Assumption]** The 60-second boss trigger should activate at `t = 60s, 120s, 180s, 240s, 300s, 360s, 420s, 480s, 540s`. At `t = 600s` (10 minutes), the game triggers the 10-Minute Victory Condition (handled by Phase 6 Victory Scene task).
2. **[Assumption]** If an elite boss from minute 1 is still alive when minute 2 arrives, both can co-exist in the arena; the HUD Boss HP bar displays the primary active boss (e.g. highest remaining HP or closest) without crashing.
3. **[Scope Boundary]** Particle effects (hit sparks, pickup sparkle, explosion shockwaves) and Screen Shake hook into the particle system task, but Elite entities should provide convenient trigger points (e.g., spawn particles, death burst).
4. **[No Caveats on Compatibility]** No breaking changes to existing enemy constructors, as `is_elite=False` defaults maintain 100% backward compatibility for all 139 existing unit tests.

---

## 4. Conclusion & Actionable Blueprint

### 4.1 Implementation Checklist for Implementer:
1. **`src/entidades/inimigo_base.py`**:
   - Update `InimigoBase.__init__` with optional parameters: `is_elite: bool = False`, `nome_elite: str = ""`.
   - If `is_elite`: scale `self.hp_max = int(hp * 3)`, `self.hp = self.hp_max`, `self.score_valor = score_valor * 10`, `self.xp_valor = 50`.
   - In `InimigoBase.desenhar`: add purple/gold pulsing aura rendering when `self.is_elite == True`.
2. **`src/sistemas/sistema_spawn.py`**:
   - Add `self.ultimo_minuto_elite: int = 0`.
   - In `SistemaSpawn.update`: check if `int(self.tempo_decorrido // 60.0) > self.ultimo_minuto_elite` (and `tempo_decorrido >= 60.0`).
   - If triggered, spawn designated elite enemy archetype outside camera bounds and record minute.
   - Implement `obter_arquetipo_elite(minuto: int) -> tuple[type, str]`.
3. **`src/sistemas/sistema_drops.py`**:
   - In `gerar_drop_morte_inimigo(..., is_elite: bool = False)`:
     - When `is_elite == True`: spawn 5 XP gems (10 XP each, total 50 XP) in a cluster, plus 1 guaranteed weapon drop (`drop_arma`), plus 1 guaranteed equipment drop (`drop_equipamento`).
4. **`src/ui/hud.py`**:
   - Add `HUD.desenhar_barra_boss(screen, boss, visivel: bool = True)`.
   - Render top-screen boss bar with name, HP fill, gold border, and text.
5. **`src/cenas/gameplay.py`**:
   - Pass `is_elite=getattr(inim, "is_elite", False)` in all drop generation calls upon enemy death (melee, projectiles, explosions).
   - In `_desenhar_hud_tela`: detect active elite enemy in `self.inimigos` and call `self.hud.desenhar_barra_boss(screen, boss)`.

---

## 5. Verification Method

### 5.1 Automated Unit Tests
Run the test suite using Python:
```powershell
.venv\Scripts\python -m unittest discover -s tests
```

### 5.2 New Unit Tests to Create (`tests/test_elite_bosses_and_waves.py`):
1. `test_sistema_spawn_elite_cadence_60s`:
   - Advance `SistemaSpawn` across 59.9s -> no elite spawned.
   - Advance to 60.1s -> exactly 1 elite enemy spawned with `is_elite == True`.
   - Advance to 65.0s -> no duplicate elite spawned in same minute.
   - Advance to 120.1s -> second elite spawned.
2. `test_elite_enemy_3x_hp_and_stats`:
   - Instantiate standard enemy vs elite standard enemy.
   - Verify elite HP is 3x standard (`40 * 3 = 120 HP`).
   - Verify elite Tank HP is 3x standard (`120 * 3 = 360 HP`).
3. `test_elite_guaranteed_drops_cluster`:
   - Trigger `gerar_drop_morte_inimigo` with `is_elite=True`.
   - Verify total XP generated >= 50.
   - Verify exactly 1 `drop_arma` and 1 `drop_equipamento` in generated drops.
4. `test_hud_boss_hp_bar_rendering`:
   - Create mock pygame screen surface.
   - Render `HUD.desenhar_barra_boss` with 100% HP, 50% HP, and 0% HP.
   - Verify correct text and no rendering exceptions.
5. `test_gameplay_elite_defeat_flow`:
   - Add elite enemy to `GameplayScene`.
   - Damage elite until death.
   - Verify player receives score, kill count, and guaranteed crates on arena floor.
