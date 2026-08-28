# Handoff Report: Phase 1 Technical Specification (Core Gameplay Loop, Player, Weapons, Projectiles & Collision)

**Author**: Survey Explorer 2 (`teamwork_preview_explorer`)  
**Mission**: Core Gameplay & Player Mechanics Technical Survey  
**Target Phase**: Phase 1 (Core Gameplay Loop)  
**Date**: 2026-08-28  

---

## 1. Observation

Direct observations extracted from project design documentation (`GDD.md`, `gdd lab batata.md`, `s1.md`–`s6.md`, `CONFIGURACOES.md`) and the PowerPPlay 2.0 framework source code (`.venv/Lib/site-packages/PPlay`):

### 1.1 Player Specifications
- **Base HP**: Exactly **150 HP** (Source: `GDD.md` §2.6: *"HP Base: 150"*; `s2.md` §2.6: *"Base HP: 150"*).
- **HP Regeneration**: None naturally (Source: `GDD.md` §2.6: *"O HP não se regenera naturalmente"*). Healing is exclusively from drops and support drones.
- **Death Condition**: Instant death and run termination when `HP <= 0` (Source: `GDD.md` §2.6; `s2.md` §2.6).
- **Movement Speed**: Baseline of **200 px/s** (standard arena movement), modifiable by active configurations (`vsync` OFF: +10%, `motion_blur` ON: +15%, `keybinds` Arrow Keys: +15%, `suavizacao_camera` OFF: +8%).
- **Movement Controls**:
  - **Standard**: Configurable WASD / Arrow keys (`s2.md` §2.5, `CONFIGURACOES.md` #11).
  - **Mouse Movement Mode** (`CONFIGURACOES.md` #10): Robot continuously moves towards the virtual mouse cursor; keyboard movement is disabled; movement stops only if the cursor is directly on top of the player.
  - **Diagonal Normalization**: Omnidirectional movement must normalize diagonal input vectors so diagonal travel is not $\sqrt{2} \approx 1.414\times$ faster.
- **Facing & Rotation**:
  - Top-down visual presentation (`GDD.md` §2.4, `s6.md` §6.2.2).
  - Avatar faces left/right depending on the virtual mouse cursor horizontal position ($mx < player.x$ vs $mx \ge player.x$).
  - Weapon aiming vector points from the player's center directly toward virtual mouse coordinates `(mx, my) = Mouse.get_position()`.

### 1.2 Starting Weapons & Inventory
- **Inventory Structure**: 4 fixed slots (`GDD.md` §2.10, `s2.md` §2.10, `gdd lab batata.md` lines 12–13):
  - **Slot 1 (Permanent)**: Melee Attack (*Chave de Manutenção* / *Maintenance Wrench*). Short range, AoE arc, low damage (~20 dmg, 0.6s cooldown), knockback on up to 2 nearest enemies. Infinite usage.
  - **Slot 2 (Permanent)**: Pistol (*Padrão de Fábrica* / *Factory Standard*). Infinite ammunition, low damage (12 dmg), single target, projectile speed 400 px/s, fire rate 3.0 shots/s (0.33s cooldown).
  - **Slot 3 (Temporary)**: Special Weapon (e.g. Minigun, Shotgun, Assault Rifle, Rocket Launcher, Grenade Launcher).
  - **Slot 4 (Temporary)**: Equipment Drone (Healing Drone, Combat Drone, Support Drone, 30s duration).
- **Shooting Trigger & Auto-Fire**:
  - Triggered by Left Mouse Button (`Mouse.LEFT = 1`) or configurable keybind.
  - Controlled by `auto_fire` configuration (`CONFIGURACOES.md` #13):
    - `auto_fire: Ligado` (Default): Weapons shoot continuously while holding the fire button (`Mouse.button_pressed(1)`).
    - `auto_fire: Desligado` (Sacrifice): Requires discrete clicks per shot (`Mouse.button_down(1)`), rewarding **+15% global weapon damage**.

### 1.3 Collision & Damage Handling
- **Contact Damage Model**:
  - Enemies damage the player by direct contact (`GDD.md` §2.7, `s2.md` §2.7).
  - **Individual Cooldown per Enemy Instance**: Damage cooldown is **NOT global**. Each enemy instance maintains its own internal contact cooldown timer (e.g. Standard: 400 ms, Fast: 250 ms, Tank: 700 ms). When touching the player, if the enemy's cooldown timer $\le 0$, damage is dealt and that specific enemy's cooldown resets to its archetype value (`GDD.md` §2.7: *"Esse valor não é global"*).
  - Player takes damage, triggering visual flash (`ScreenEffects.flash((255, 0, 0), 0.1)`) and SFX.
- **Projectile vs Enemy Collision**:
  - Bounding box AABB collision check (`Collision.collided(proj, enemy)`).
  - Deals weapon damage (applying active multipliers from `keybinds`, `auto_fire`, `cores_invertidas`, `damage_numbers` crit roll, etc.).
  - Triggers enemy hit reaction (flash white/red, sound).
  - If enemy `HP <= 0`, enemy dies: triggers death particles, XP drop roll, removes enemy.
  - Projectile is destroyed on contact (single target) unless piercing.

### 1.4 Phase 1 Enemy Archetypes
- **Standard Enemy** (*Estagiário / Intern*): HP 30, Speed 100 px/s, Contact Damage 10, Cooldown 400 ms (0.4s), XP Value 10 (`s4.md` §4.7).
- **Fast Enemy** (*Viciado em Cafeína / Caffeine Addict*): HP 15, Speed 160 px/s, Contact Damage 8, Cooldown 250 ms (0.25s), XP Value 12 (`s4.md` §4.9, `s2.md` §2.7).
- **Tank Enemy** (*Geladeira Industrial / Industrial Refrigerator*): HP 90, Speed 50 px/s, Contact Damage 20, Cooldown 700 ms (0.7s), XP Value 25 (`s4.md` §4.8, `s2.md` §2.7).
- **Enemy AI Movement**: Direct beeline towards the player position ($px, py$) without pathfinding (`s4.md` §4.2: *"Move directly toward the player... Enemies do not dodge projectiles, avoid each other, predict player movement, flank, search for cover, retreat"*).

---

## 2. Logic Chain

```
[Requirement: Top-down 2D Shooter with PPlay]
  │
  ├──► [Observation 1: Player HP 150, Base Speed 200, WASD/Mouse modes]
  │      └──► [Logic 1.1] Player class encapsulates position, HP, velocity, state, and facing.
  │      └──► [Logic 1.2] Movement logic calculates (dx, dy). When dx != 0 and dy != 0, multiply by 0.7071.
  │      └──► [Logic 1.3] When Mouse Movement mode is active, vector = (mouse_pos - player_center).normalized().
  │      └──► [Logic 1.4] Position is clamped strictly within arena boundaries: [0, ARENA_W - w], [0, ARENA_H - h].
  │
  ├──► [Observation 2: Starter Weapons: Melee (Slot 1) & Pistol (Slot 2)]
  │      └──► [Logic 2.1] Weapon Base class handles cooldown timing, ammo (infinite for slots 1 & 2), and firing logic.
  │      └──► [Logic 2.2] Pistol calculates direction vector from player center to virtual mouse position and spawns Projetil instances.
  │      └──► [Logic 2.3] Melee checks enemies within frontal arc/radius (70px), deals 20 dmg, and pushes the 2 nearest enemies back by knockback impulse.
  │      └──► [Logic 2.4] Auto-fire switch checks `auto_fire` config: continuous `button_pressed` vs discrete `button_down`.
  │
  ├──► [Observation 3: Collision, Contact Damage & Individual Enemy Cooldowns]
  │      └──► [Logic 3.1] Each enemy instance stores `cooldown_restante` float.
  │      └──► [Logic 3.2] Every frame, decrement `cooldown_restante -= dt`.
  │      └──► [Logic 3.3] On collision with player: if `cooldown_restante <= 0`, player.receber_dano(enemy.dano_contato), enemy.cooldown_restante = enemy.cooldown_max.
  │      └──► [Logic 3.4] Projectiles check collision against active enemy group. On hit: enemy.receber_dano(proj.dano), destroy projectile.
  │      └──► [Logic 3.5] When player HP <= 0, transition to Game Over state.
  │
  └──► [Conclusion: Modular, clean Phase 1 implementation ready to code with zero ambiguities]
```

---

## 3. Caveats

- **Scope Boundary**: Phase 1 focuses strictly on the Core Gameplay Loop (Player movement, Starter weapons, Projectile physics, Baseline enemies, Collision system, Death/Game Over loop). Special weapons (Minigun, Shotgun, Rocket Launcher), support drones, XP level-up upgrade card UI, and full configuration menu scenes belong to subsequent phases (Phase 2+), though the architecture must be designed to accommodate them seamlessly.
- **Resolution & Virtual Buffer**: PowerPPlay 2.0 uses a virtual buffer (`largura=800, altura=600` or native aspect ratio) scaled to the window. Mouse coordinates must always be obtained via `Window.get_instance().screen_to_virtual_coords(mx, my)` or `Mouse.get_position()` to prevent misalignment when the window is resized or in fullscreen.
- **Frame-Rate Independence**: All velocities and cooldowns must be multiplied by `dt = Window.get_instance().delta_time()` so gameplay remains consistent across different FPS caps (15, 30, 45, 60 FPS).

---

## 4. Conclusion & Technical Specifications

### 4.1 Data Models & Constants (`src/utils/constantes.py`)

```python
# Screen & Arena Dimensions
LARGURA_TELA = 800
ALTURA_TELA = 600
LARGURA_ARENA = 1600
ALTURA_ARENA = 1200

# Player Base Stats
JOGADOR_HP_MAX = 150
JOGADOR_VELOCIDADE_BASE = 200.0  # px/s
JOGADOR_LARGURA = 32
JOGADOR_ALTURA = 32

# Starter Weapon 1: Melee (Chave de Manutenção)
MELEE_DANO_BASE = 20
MELEE_COOLDOWN = 0.6  # segundos
MELEE_ALCANCE = 70.0  # pixels
MELEE_KNOCKBACK_FORCA = 180.0  # px/s de impulso de recuo
MELEE_MAX_ALVOS_KNOCKBACK = 2

# Starter Weapon 2: Pistola (Padrão de Fábrica)
PISTOLA_DANO_BASE = 12
PISTOLA_COOLDOWN = 0.33  # segundos (~3 tiros/s)
PISTOLA_VELOCIDADE_PROJETIL = 420.0  # px/s
PISTOLA_TEMPO_VIDA_PROJETIL = 2.5  # segundos
PISTOLA_LARGURA_PROJETIL = 8
PISTOLA_ALTURA_PROJETIL = 8

# Baseline Enemy Archetypes for Phase 1
INIMIGOS_CONFIG = {
    "estagiario": {
        "nome": "Estagiário",
        "hp_max": 30,
        "velocidade": 100.0,
        "dano_contato": 10,
        "cooldown_contato": 0.40,  # 400 ms
        "xp_valor": 10,
        "largura": 28,
        "altura": 28,
        "cor": (200, 50, 50)  # Vermelho
    },
    "rapido": {
        "nome": "Viciado em Cafeína",
        "hp_max": 15,
        "velocidade": 160.0,
        "dano_contato": 8,
        "cooldown_contato": 0.25,  # 250 ms
        "xp_valor": 12,
        "largura": 20,
        "altura": 20,
        "cor": (255, 140, 0)  # Laranja
    },
    "tanque": {
        "nome": "Geladeira Industrial",
        "hp_max": 90,
        "velocidade": 50.0,
        "dano_contato": 20,
        "cooldown_contato": 0.70,  # 700 ms
        "xp_valor": 25,
        "largura": 44,
        "altura": 44,
        "cor": (100, 100, 100)  # Cinza Metálico
    }
}
```

---

### 4.2 Mathematical Formulas & Algorithms (`src/utils/math_utils.py`)

#### Vector Normalization
Given movement delta $(dx, dy)$:
$$\text{length} = \sqrt{dx^2 + dy^2}$$
$$\text{if length } > 0: \quad (\hat{dx}, \hat{dy}) = \left(\frac{dx}{\text{length}}, \frac{dy}{\text{length}}\right)$$

#### Direction Vector to Mouse Target
Given player center $(cx, cy)$ and mouse position $(mx, my)$:
$$\vec{d} = (mx - cx, my - cy)$$
$$\hat{u} = \frac{\vec{d}}{\|\vec{d}\|}$$

#### Knockback Displacement
When melee hits enemy $i$, apply velocity displacement:
$$\vec{v}_{\text{knockback}} = \frac{\text{enemy}_i.\text{pos} - \text{player}.\text{pos}}{\|\text{enemy}_i.\text{pos} - \text{player}.\text{pos}\|} \times \text{MELEE\_KNOCKBACK\_FORCA}$$

---

### 4.3 Class Interfaces & Architecture

#### 1. Player (`src/entidades/jogador.py`)
- `Jogador(x, y)`:
  - Attributes: `x, y, width, height, hp, hp_max, velocidade_base, velocidade_atual, facing_right, vivo, flash_dano_timer`.
  - `processar_input(teclado, mouse, dt, config_sistema)`: Handles WASD/Arrow/Inverted/Mouse input, normalizes vector, updates `x, y`, clamps to arena boundaries.
  - `receber_dano(quantidade)`: Decrements `hp -= quantidade`, triggers damage flash. If `hp <= 0`, sets `vivo = False`.
  - `curar(quantidade)`: Increases `hp = min(hp_max, hp + quantidade)`.
  - `desenhar(janela, camera)`: Renders potato avatar sprite (or low-poly rect if Low Graphics is active) with damage flash tint.

#### 2. Projectile (`src/entidades/projetil.py`)
- `Projetil(x, y, dir_x, dir_y, velocidade, dano, tempo_vida, dono="jogador")`:
  - Attributes: `x, y, vx, vy, dano, tempo_vida_restante, ativo, largura, altura`.
  - `update(dt)`: `x += vx * dt; y += vy * dt; tempo_vida_restante -= dt`. If `tempo_vida_restante <= 0`, `ativo = False`.
  - `desenhar(janela, camera)`: Renders projectile sprite or yellow/cyan laser rect.

#### 3. Weapons (`src/armas/`)
- `ArmaBase`:
  - Attributes: `nome, cooldown, tempo_recarga_restante, munição_infinita, slot`.
  - `update(dt)`: `tempo_recarga_restante = max(0.0, tempo_recarga_restante - dt)`.
  - `pode_atirar() -> bool`: Returns `tempo_recarga_restante <= 0`.
- `Pistola(ArmaBase)`:
  - `disparar(origem_x, origem_y, destino_x, destino_y) -> list[Projetil]`: Spawns and returns a `Projetil` directed toward destination. Resets `tempo_recarga_restante = PISTOLA_COOLDOWN`.
- `Melee(ArmaBase)`:
  - `executar_ataque(jogador, lista_inimigos) -> list[Inimigo]`: Identifies all enemies within `MELEE_ALCANCE`, damages them, sorts by distance, and applies knockback to the 2 closest.

#### 4. Enemies (`src/entidades/inimigo_*.py`)
- `InimigoBase`:
  - Attributes: `x, y, hp, hp_max, velocidade, dano_contato, cooldown_contato_max, cooldown_contato_atual, xp_valor, vivo, flash_timer, vx_knockback, vy_knockback`.
  - `update(dt, pos_jogador)`:
    - Beeline movement: calculates unit vector towards `pos_jogador`.
    - Updates position: $x += (v_x + vx_{\text{knockback}}) \cdot dt$. Damps knockback over time.
    - Updates `cooldown_contato_atual = max(0.0, cooldown_contato_atual - dt)`.
  - `receber_dano(quantidade)`: Decrements `hp -= quantidade`, triggers hit flash. If `hp <= 0`, `vivo = False`.
  - `tentar_causar_dano_contato(jogador) -> bool`: If `collided(self, jogador)` and `cooldown_contato_atual <= 0`, deals `dano_contato`, resets `cooldown_contato_atual = cooldown_contato_max`, returns True.

#### 5. Gameplay Scene (`src/cenas/gameplay.py`)
- Coordinates the main loop:
  - Updates player, active weapons, projectiles, enemy spawns, and collisions.
  - Resolves `Projetil vs Inimigo` and `Inimigo vs Jogador`.
  - Handles Game Over transition when `jogador.vivo == False`.

---

## 5. Verification Method

To verify Phase 1 implementation once written:

### 5.1 Automated Unit / Headless Test Harness
Run headless tests with Pygame dummy video driver:
```powershell
$env:SDL_VIDEODRIVER='dummy'; python -m unittest discover -s tests -p "test_*.py"
```

Unit tests should assert:
1. `test_jogador_movement_normalization`: Diagonal movement speed equals straight speed ($\|v\| = 200 \pm 0.01$).
2. `test_jogador_boundary_clamping`: Clamping prevents player coordinates from becoming negative or exceeding arena size.
3. `test_inimigo_individual_cooldown`: Contact damage triggers once and is debounced for exactly `cooldown_contato_max` seconds for that specific enemy.
4. `test_projetil_enemy_collision`: Projectile collision deals exact damage and deactivates projectile.
5. `test_jogador_death_trigger`: When player HP reaches 0, player status switches to dead and Game Over triggers.

### 5.2 Interactive Run Verification
Run the game from terminal:
```powershell
python src/main.py
```
- Verify window opens and player (potato avatar) responds smoothly to WASD / Arrow keys.
- Verify mouse click shoots bullets in the direction of the cursor.
- Verify enemies spawn, beeline towards the potato, and take damage/die when shot.
- Verify contact with enemies reduces player HP bar and ends the game upon reaching 0 HP.

---
*Report completed and self-contained per Teamwork Operational Protocol.*
