# Technical Analysis & Architecture Specification Report: Directional Cone Melee (R1), Drops & XP Progression (R2), and Configuration Engine Backend (R3)

**Project**: Protocolo: Batata  
**Agent**: `teamwork_preview_explorer_1`  
**Working Directory**: `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_1`  
**Date**: 2026-08-28  
**Scope**: Exploration, Mathematical Modeling, Architectural Specification, and Test Planning for R1, R2, and R3.

---

## 1. Observation

Direct investigation of the codebase, documentation, and test infrastructure yielded the following verified facts:

### 1.1 Mandatory Documents & Architecture SSOT
- **`CONFIGURACOES.md` (SSOT)**:
  - `[Observed]` Single Source of Truth for game progression. Catalogs exactly 20 unlockable gameplay configurations and system configs.
  - `[Observed]` Fundamental Rule: Locked configs strictly default to neutral baseline (`padrao`, $\times 1.0$, $0\%$ bonus). Desbloqueio on level-up allows switching.
  - `[Observed]` Max Level: 20 (equal to the number of unlockable gameplay configs).
- **`ORIGINAL_REQUEST.md`**:
  - `[Observed]` R1 Requirements (Lines 117–122): Directional cone melee with 45° arc pointed directly at mouse cursor (no 360° hits), reach = $2.0\times$ potato width (~84px), damage = 10 (5 hits to kill standard 50 HP enemy), knockback force = 360.0 px/s ($2\times$ baseline), 45° directional cone visual guide & swing shockwave.
  - `[Observed]` R2 Requirements (Lines 123–127): Loot spawning on enemy death, 10s drop lifetime, player collection, XP gain, level tracking, level-up trigger ($XP_{\text{prox}} = 10 + 5 \times \text{level}$), and screen-space XP progress bar under top HUD.
  - `[Observed]` R3 Requirements (Lines 128–130, 99): Implement `src/sistemas/config_dados.py` and `config_efeitos.py` calculating multiplicative stat stacking for all 20 gameplay configs + 5 systemic configs (including `S5: Escala Global`).
- **`.agents/architecture_cache.md`**:
  - `[Observed]` Engine: PowerPPlay 2.0 (Pygame-CE based) at `.venv/Lib/site-packages/PPlay`.
  - `[Observed]` Module layout: `src/armas/`, `src/entidades/`, `src/sistemas/`, `src/cenas/`, `src/ui/`, `src/utils/`, `tests/`.

### 1.2 Existing Source Code State
1. **Melee Weapon (`src/armas/melee.py`, lines 19–95)**:
   - `[Observed]` Currently initialized with: `dano = 20`, `cooldown = 0.6`, `alcance = 140.0`, `knockback_forca = 180.0`, `max_alvos_knockback = 2`.
   - `[Observed]` `executar_ataque(origem_x, origem_y, lista_inimigos)` only checks `dist <= self.alcance`, which hits all enemies radially in a full 360° circle. It lacks mouse aim vector/angle parameters.
2. **Player Entity (`src/entidades/jogador.py`, lines 25–75)**:
   - `[Observed]` Width/Height: `largura = 32`, `altura = 32` (or updated 42px in asset generator). Slot 1 holds `Melee()`, Slot 2 holds `Pistola()`, Slot 3 holds `arma_especial`.
   - `[Observed]` Currently lacks integrated XP/Level tracking attributes (`xp`, `nivel`, `xp_proximo`).
3. **Enemy Base (`src/entidades/inimigo_base.py`, lines 20–140)**:
   - `[Observed]` `InimigoPadrao` baseline HP was 25; requires alignment to 50 HP for 5 melee hits (10 damage $\times 5 = 50$).
   - `[Observed]` `aplicar_knockback(dir_x, dir_y, forca)` applies impulse decaying smoothly via `lerp(v, 0, 10.0*dt)`.
4. **Gameplay Scene (`src/cenas/gameplay.py`, lines 137–215, 321–344)**:
   - `[Observed]` Currently invokes `arma_ativa.executar_ataque(centro_jogador_x, centro_jogador_y, self.inimigos)` without mouse direction.
   - `[Observed]` Melee aim indicator at line 327 draws a full circle `pygame.draw.circle(surf_alcance, (0, 220, 255, 20), ...)` instead of a 45° sector.
   - `[Observed]` Swing visual effect at line 342 expands a full concentric circle rather than a directional slash cone.
   - `[Observed]` Currently lacks `drops` list, `SistemaDrops`, `SistemaXP`, `SistemaScavenger`, and XP HUD bar.
5. **Math Utils (`src/utils/math_utils.py`, lines 9–95)**:
   - `[Observed]` Functions available: `distancia`, `distancia_sq`, `vetor_direcao`, `clamp`, `lerp`, `colisao_aabb`, `colisao_circulo`, `angulo_radianos`, `angulo_graus`, `rotacionar_vetor`.
6. **Constants (`src/utils/constantes.py`)**:
   - `[Observed]` Lines 124–129: `MELEE_DANO = 15`, `MELEE_ALCANCE = 60.0`, `MELEE_KNOCKBACK = 200.0`.
   - `[Observed]` Lines 182–186: `DROP_XP_VALOR_BASE = 10`, `DROP_CURA_VALOR_BASE = 35`, `DROP_TEMPO_DESAPARECER = 10.0`, `DROP_TEMPO_SCAVENGER_ATIVAR = 1.0`.
   - `[Observed]` Lines 193–595: `CONFIGURACOES_CATALOGO` with 20 gameplay configs.
   - `[Observed]` Lines 601–633: `CONFIGURACOES_SISTEMA` with 3 volume configs.
7. **Test Suite Execution**:
   - `[Verified]` Command `.\.venv\Scripts\python.exe -m unittest discover tests` ran 118 tests in 26.4s with 0 errors (`OK`).

---

## 2. Logic Chain & Technical Specifications

```
                     ┌─────────────────────────────────────────────────────────┐
                     │                 PROTOCOLO: BATATA                       │
                     │          Requirements Specification Pipeline            │
                     └───────────────────────────┬─────────────────────────────┘
                                                 │
         ┌───────────────────────────────────────┼──────────────────────────────────────┐
         │                                       │                                      │
         ▼                                       ▼                                      ▼
┌─────────────────────────┐           ┌─────────────────────────┐            ┌─────────────────────────┐
│     REQUIREMENT 1       │           │      REQUIREMENT 2      │            │      REQUIREMENT 3      │
│ Directional Cone Melee  │           │   Drops & XP Progress   │            │  Configuration Engine   │
├─────────────────────────┤           ├─────────────────────────┤            ├─────────────────────────┤
│ • 45° Arc Sector Filter │           │ • ItemDrop (10s decay)  │            │ • config_dados.py       │
│ • Reach ~84px (2x width)│           │ • 1s Scavenger Grace    │            │   (20 gameplay + 5 sys) │
│ • 10 Dmg (5 hits / 50HP)│           │ • SistemaXP:            │            │ • config_efeitos.py     │
│ • Knockback 360.0 px/s  │           │   XP_prox = 10 + 5*lvl  │            │   (Multiplicative Model)│
│ • Pygame Cone Visuals   │           │ • Screen-space XP Bar   │            │ • config_sistema.py     │
└─────────────────────────┘           └─────────────────────────┘            └─────────────────────────┘
```

---

### 2.1 R1: Directional Cone Melee Tuning

#### A. Target File Modifications
1. `src/utils/constantes.py`:
   - `MELEE_DANO = 10`
   - `MELEE_ALCANCE = 84.0` (2.0x 42px)
   - `MELEE_KNOCKBACK = 360.0`
   - `INIMIGO_PADRAO_HP = 50`
2. `src/armas/melee.py`: Update defaults and `executar_ataque` logic.
3. `src/cenas/gameplay.py`: Pass mouse world coordinates to `executar_ataque`, update idle aim cone and swing slash visual renderers.

#### B. Hitbox Mathematics & Target Selection Logic
Let player center be $P = (x_p, y_p)$ and mouse aim target in world space be $M = (m_x, m_y)$.
Let an enemy center be $E = (e_x, e_y)$ with enemy bounding box $(x_e, y_e, w_e, h_e)$.

1. **Aim Angle & Aim Unit Vector**:
   $$\theta_{\text{aim}} = \text{atan2}(m_y - y_p, m_x - x_p)$$
   $$\vec{u}_{\text{aim}} = (\cos \theta_{\text{aim}}, \sin \theta_{\text{aim}})$$

2. **Distance & Radial Reach Test**:
   $$d = \sqrt{(e_x - x_p)^2 + (e_y - y_p)^2}$$
   Condition 1: $d \le R_{\text{melee}}$ where $R_{\text{melee}} = 84.0\text{ px}$.

3. **Angular Delta & Cone Aperture Test (45° Arc)**:
   The total arc is $45^\circ = \frac{\pi}{4}\text{ rad}$. The half-angle threshold is $\alpha = 22.5^\circ = \frac{\pi}{8}\text{ rad} \approx 0.392699\text{ rad}$.
   
   - **Method 1 (Angular Difference with Wrap-around Normalization)**:
     $$\theta_e = \text{atan2}(e_y - y_p, e_x - x_p)$$
     $$\Delta \theta = |\text{atan2}(\sin(\theta_e - \theta_{\text{aim}}), \cos(\theta_e - \theta_{\text{aim}}))|$$
     Condition 2: $\Delta \theta \le \alpha = \frac{\pi}{8}$.

   - **Method 2 (Vector Dot Product)**:
     $$\vec{u}_e = \frac{E - P}{d} = \left(\frac{e_x - x_p}{d}, \frac{e_y - y_p}{d}\right)$$
     $$\text{dot} = \vec{u}_{\text{aim}} \cdot \vec{u}_e = u_{\text{aim}, x} u_{e, x} + u_{\text{aim}, y} u_{e, y}$$
     Condition 2: $\text{dot} \ge \cos(22.5^\circ) = \frac{\sqrt{2 + \sqrt{2}}}{2} \approx 0.9238795$.

4. **Damage & Knockback Application**:
   - Filtered candidates meeting Condition 1 AND Condition 2 are sorted ascending by distance $d$.
   - All enemies in the cone receive $10$ damage (`inimigo.receber_dano(10)`).
   - The up to $2$ closest enemies receive directional knockback impulse:
     $$\vec{u}_{\text{kb}} = \vec{u}_e \quad (\text{or } \vec{u}_{\text{aim}} \text{ if } d < 1e-4)$$
     $$\text{inimigo.aplicar\_knockback}(u_{\text{kb}, x}, u_{\text{kb}, y}, 360.0)$$

#### C. Visual Rendering with Pygame

1. **Idle Aim Guide (Equipped Slot 1)**:
   - On a transparent surface of size $(2R + 8, 2R + 8)$ with `pygame.SRCALPHA`:
   - Compute vertices for a 45° pie sector: center $(R+4, R+4)$, arc sample points from $\theta_{\text{aim}} - 22.5^\circ$ to $\theta_{\text{aim}} + 22.5^\circ$ (e.g. 10 segments).
   - `pygame.draw.polygon(surf, (0, 220, 255, 25), vertices)` (translucent fill).
   - `pygame.draw.lines(surf, (0, 220, 255, 80), True, vertices, width=1)` (outline).
   - Blit centered at camera-transformed player position.

2. **Directional Swing Slash (Active Effect)**:
   - Record effect event: `{"x": xp, "y": yp, "angulo": theta_aim, "alcance": 84.0, "tempo": 0.15, "tempo_total": 0.15}`.
   - For progress $p = 1.0 - \text{tempo}/\text{tempo\_total} \in [0.0, 1.0]$:
     - Radius $r(p) = 84.0 \times (0.4 + 0.6 \times p)$.
     - Alpha $\alpha(p) = \text{int}(240 \times (1.0 - p))$.
     - Draw directional arc fan spanning $[\theta_{\text{aim}} - 22.5^\circ, \theta_{\text{aim}} + 22.5^\circ]$ with outer bright arc `(255, 255, 255, alpha)` width 3 and golden body `(255, 215, 0, alpha // 3)`.

---

### 2.2 R2: Phase 2 — Drops & XP System

#### A. Target File Modifications & Creations
1. Create `src/entidades/drop.py`: `ItemDrop` class handling position, rendering, lifetime (10.0s), and grace period (1.0s).
2. Create `src/sistemas/sistema_drops.py`: Decoupled pure logic for drop spawning, loot tables, lifetime expiration, and proximity pickups.
3. Create `src/sistemas/sistema_xp.py`: XP progression manager, level calculation, $XP_{\text{prox}} = 10 + 5 \times \text{level}$, level-up event triggers.
4. Create `src/sistemas/sistema_scavenger.py`: Scavenger AI selector (singleton global, exclusion of 3 closest, exclusion of $> 600\text{px}$).
5. Create `src/ui/hud.py`: Screen-space XP bar renderer under top HUD.
6. Modify `src/cenas/gameplay.py`: Integrate drops update, player collision, enemy drops on death, Scavenger AI update, and HUD XP bar rendering.
7. Modify `src/entidades/jogador.py`: Add `ganhar_xp(qtd)`, `curar(qtd)`, `xp`, `nivel` properties.

#### B. Architectural Integration & Workflow

```
[Enemy Destroyed / HP <= 0]
             │
             ├──► Roll Drop Chance: min(1.0, (ChanceBase + BonusAditivos) * MultMouse)
             │
             ▼
[Spawn ItemDrop] ───► Lifetime = 10.0s
             │
   ┌─────────┴────────────────────────────────┐
   │                                          │
   │ (0.0s <= t < 1.0s)                       │ (1.0s <= t < 10.0s)
   ▼                                          ▼
[Player Contact Only]                [Player & Scavenger Eligible]
   │                                          │
   │ Collides with Player                     ├──► Scavenger Reaches Drop:
   ▼                                          │    Drop destroyed, 0 reward
[Collect Payload]                             │
   ├── XP Gem: xp_sys.adicionar_xp()          └──► Player Collides:
   ├── Heal: jogador.curar(35)                     If coleta_inimiga: Payload * 2x
   ├── Weapon / Drone: equip slot 3/4              xp_sys.adicionar_xp(payload["valor"])
   └── (If coleta_inimiga active: 2x)              
```

#### C. XP Progression Formula & Level Scaling
- Base Level: $\text{level} = 1$, $\text{XP} = 0$.
- Required XP for Level $L$:
  $$XP_{\text{prox}}(L) = 10 + 5 \times L$$
- Progression Table:
  - Level 1 $\to$ 2: $10 + 5(1) = 15\text{ XP}$ (Cumulative: 15)
  - Level 2 $\to$ 3: $10 + 5(2) = 20\text{ XP}$ (Cumulative: 35)
  - Level 3 $\to$ 4: $10 + 5(3) = 25\text{ XP}$ (Cumulative: 60)
  - Level 4 $\to$ 5: $10 + 5(4) = 30\text{ XP}$ (Cumulative: 90)
  - Level 19 $\to$ 20: $10 + 5(19) = 105\text{ XP}$ (Cumulative: 1140)
- Carryover XP Handling:
  $$\text{while } \text{xp} \ge XP_{\text{prox}}(\text{level}) \text{ and } \text{level} < 20:$$
  $$\text{xp} -= XP_{\text{prox}}(\text{level})$$
  $$\text{level} += 1$$
  $$\text{trigger\_level\_up\_callback}()$$

#### D. Screen-Space HUD XP Bar
- Screen Coordinates: `centerx = LARGURA_TELA // 2` (400), `top = 62`, `width = 360`, `height = 10`, `border_radius = 3`.
- Fill proportion: $p = \text{clamp}(\text{xp} / XP_{\text{prox}}, 0.0, 1.0)$.
- Colors: Background `(20, 25, 35)`, Fill `(255, 215, 0)` with highlight `(255, 235, 100)`, Border `(50, 65, 85)`.
- Label: `"Nv. {level} - {xp}/{xp_prox} XP"` in `Arial 11 bold` centered.

---

### 2.3 R3: Phase 3 — Configuration Engine Backend

#### A. Target File Modifications & Creations
1. Create `src/sistemas/config_dados.py`: Dataclass models (`ConfiguracaoDef`, `CategoriaConfig`, `TipoControleConfig`), and complete definitions for all 20 gameplay configs + 5 systemic configs.
2. Create `src/sistemas/config_efeitos.py`: Pure mathematical calculator `calcular_modificadores(unlocked_configs, active_configs)` outputting `ModificadoresGameplay`.
3. Create `src/sistemas/config_sistema.py`: High-level persistence and state manager.

#### B. Exact 20 Gameplay Configs Catalog & Modifiers Data Specification

| # | ID | Category | Type | Default | Selectable Options | Applied Modifiers |
|---|---|---|---|---|---|---|
| 1 | `fps_cap` | Performance | Grupo | `"60"` | `["60", "45", "30", "15"]` | `"45"`: `dano_inimigos_mult=0.85`<br>`"30"`: `vel_inimigos_mult=0.90`<br>`"15"`: `dano_inimigos_mult=0.7225`, `vel_inimigos_mult=0.81` |
| 2 | `graficos_qualidade` | Performance | Toggle | `"alta"` | `["alta", "baixa"]` | `"baixa"`: `hp_inimigos_mult=0.80` |
| 3 | `resolucao` | Performance | Grupo | `"100%"` | `["100%", "75%", "50%", "25%"]` | `"75%"`: `drop_chance_bonus=0.10`<br>`"50%"`: `drop_chance_bonus=0.25`<br>`"25%"`: `drop_chance_bonus=0.50` |
| 4 | `vsync` | Performance | Toggle | `"ligado"` | `["ligado", "desligado"]` | `"desligado"`: `vel_jogador_mult=1.10` |
| 5 | `screen_shake` | Perf/Visual | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `dano_explosivos_mult=1.20` |
| 6 | `motion_blur` | Perf/Visual | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `vel_jogador_mult=1.15` |
| 7 | `hud` | Interface | Toggle | `"ligado"` | `["ligado", "desligado"]` | `"desligado"`: `xp_ganho_mult=1.25` |
| 8 | `damage_numbers` | Interface | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `critico_chance=0.15`, `critico_mult=2.0` |
| 9 | `zoom` | Interface | Grupo | `"100%"` | `["75%", "100%", "125%", "150%"]` | `"75%"`: `hitbox_projeteis_mult=1.50`<br>`"125%"`: `dano_armas_mult=1.10`<br>`"150%"`: `dano_armas_mult=1.20` |
| 10 | `movimento_mouse` | Controles | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `drop_chance_mult=1.40` |
| 11 | `keybinds` | Controles | Grupo | `"padrao"` | `["padrao", "invertido", "arrow_keys", "uma_mao", "pesadelo"]` | `"invertido"`: `dano_armas_mult=1.10`<br>`"arrow_keys"`: `vel_jogador_mult=1.15`<br>`"uma_mao"`: `xp_ganho_mult=1.20`<br>`"pesadelo"`: `dano_armas_mult=1.30` |
| 12 | `suavizacao_camera` | Câmera | Toggle | `"ligado"` | `["ligado", "desligado"]` | `"desligado"`: `vel_jogador_mult=1.08` |
| 13 | `auto_fire` | Combate | Toggle | `"ligado"` | `["ligado", "desligado"]` | `"desligado"`: `dano_armas_mult=1.15` |
| 14 | `inimigos_ranged` | Dificuldade | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `loot_enriquecido=True` |
| 15 | `coleta_inimiga` | Dificuldade | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `drops_valor_mult=2.0` |
| 16 | `velocidade_inimigos` | Dificuldade | Grupo | `"normal"` | `["normal", "+25%", "+50%"]` | `"+25%"`: `vel_inimigos_mult=1.25`, `xp_ganho_mult=1.20`<br>`"+50%"`: `vel_inimigos_mult=1.50`, `xp_ganho_mult=1.40` |
| 17 | `vida_inimigos` | Dificuldade | Grupo | `"normal"` | `["normal", "+50%", "+100%"]` | `"+50%"`: `hp_inimigos_mult=1.50`, `drop_chance_bonus=0.20`<br>`"+100%"`: `hp_inimigos_mult=2.00`, `drop_chance_bonus=0.40` |
| 18 | `iluminacao` | Atmosfera | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `dano_fora_visao_mult=0.50` |
| 19 | `cores_invertidas` | Visual | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `dano_armas_mult=1.20` |
| 20 | `fogo_amigo` | Risco | Toggle | `"desligado"` | `["desligado", "ligado"]` | `"ligado"`: `dano_armas_mult=1.25`, `auto_dano=True` |

#### C. Exact 5 Systemic Configs Specification (Always Available, No Buffs)
1. `volume_master`: Slider $0$ to $100\%$ (Default: $100$)
2. `volume_musica`: Slider $0$ to $100\%$ (Default: $100$)
3. `volume_sfx`: Slider $0$ to $100\%$ (Default: $100$)
4. `filtro_daltonico`: Selector `["desligado", "protanopia", "deuteranopia", "tritanopia"]` (Default: `"desligado"`)
5. `escala_global`: Selector `["100%", "125%", "150%"]` (Default: `"100%"`) — Systemic global UI/sprite rendering scale.

#### D. Mathematical Stacking Pipeline Formulas

1. **Player Weapon Damage Multiplier**:
   $$M_{\text{dano}} = \prod M_{\text{dano\_armas}} = M_{\text{auto\_fire}} \times M_{\text{keybinds}} \times M_{\text{cores\_invertidas}} \times M_{\text{fogo\_amigo}} \times M_{\text{zoom}}$$
   - Explosive weapons (Rocket / Grenade) multiply further by $M_{\text{screen\_shake}} = 1.20$.
   - Max general weapon damage multiplier: $1.15 \times 1.30 \times 1.20 \times 1.25 \times 1.20 = 2.691\times$.

2. **Player Movement Speed Multiplier**:
   $$M_{\text{vel\_jogador}} = M_{\text{vsync}} \times M_{\text{motion\_blur}} \times M_{\text{suavizacao\_camera}} \times M_{\text{keybinds\_arrow}}$$
   - Max speed multiplier: $1.10 \times 1.15 \times 1.08 \times 1.15 \approx 1.571\times$.

3. **XP Gain Multiplier**:
   $$M_{\text{xp}} = M_{\text{hud}} \times M_{\text{keybinds\_uma\_mao}} \times M_{\text{vel\_inimigos}}$$
   - Max XP multiplier: $1.25 \times 1.20 \times 1.40 = 2.10\times$.

4. **Drop Chance Calculation**:
   $$\text{ChanceTotal} = \min\left(1.0, \left(\text{ChanceBase} + \sum \text{BonusAditivos}\right) \times M_{\text{mouse}}\right)$$
   - where $\sum \text{BonusAditivos} = B_{\text{resolucao}} + B_{\text{vida\_inimigos}}$.

5. **Enemy Spawn HP Multiplier**:
   $$M_{\text{hp\_inimigo}} = M_{\text{graficos}} \times M_{\text{vida\_inimigos}}$$

6. **Enemy Speed Multiplier**:
   $$M_{\text{vel\_inimigo}} = M_{\text{fps\_vel}} \times M_{\text{vel\_inimigos}}$$

7. **Enemy Contact Damage Multiplier**:
   $$M_{\text{dano\_inimigo}} = M_{\text{fps\_dano}} \times (0.50 \text{ if outside vision and } \text{iluminacao}=\text{ligado})$$

---

## 3. Caveats & Assumptions

1. **Read-Only Scope Compliance**: This exploration report synthesized all requirements and verified equations without modifying project source code outside `.agents/teamwork_preview_explorer_1/`.
2. **Backwards Compatibility with Legacy Tests**: Existing tests in `tests/test_weapons.py` called `executar_ataque(origem_x, origem_y, lista_inimigos)`. The updated signature must support optional parameters `mira_x=None, mira_y=None, angulo_mira=None, arco_graus=45.0` to avoid breaking older test suites while enabling strict directional cone checks when coordinates are passed.
3. **PPlay & Pygame Environment**: Tests must run using `.venv\Scripts\python.exe` with `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` to ensure fast, deterministic headless test execution.

---

## 4. Conclusion

The architectural investigation and mathematical modeling for R1, R2, and R3 are complete:
- **R1 (Directional Melee)**: 45° cone sector mathematical filtering ($\Delta \theta \le 22.5^\circ$ and $d \le 84\text{px}$) with $10$ damage and $360.0\text{ px/s}$ knockback is fully formulated alongside Pygame sector rendering.
- **R2 (Drops & XP)**: Complete data flow from enemy death roll, 10s lifetime / 1s scavenger delay, player proximity pickup, $XP_{\text{prox}} = 10 + 5 \times \text{level}$, and screen-space HUD progress bar is fully specified.
- **R3 (Config Engine)**: All 20 gameplay configurations and 5 systemic configs from `CONFIGURACOES.md` are mapped to pure dataclass models and multiplicative stacking formulas in `config_dados.py` and `config_efeitos.py`.

---

## 5. Verification Method & Test Plan

To verify the implementation once coded:

### 5.1 Proposed Automated Test Suites
1. **`tests/test_melee_cone.py`**:
   - `test_melee_cone_directional_filtering`: Enemy in front at 0° ($d=50$) is hit; enemy at 45° ($d=50$) is missed; enemy behind at 180° ($d=50$) is missed.
   - `test_melee_reach_boundary`: Enemy at $d=84\text{px}$ is hit; enemy at $d=85\text{px}$ is missed.
   - `test_melee_damage_and_knockback`: Enemy takes exactly 10 damage; 50 HP enemy dies in exactly 5 hits; 2 closest enemies receive $v_{\text{knockback}} = 360.0\text{ px/s}$.
2. **`tests/test_drops_xp.py`**:
   - `test_drop_lifetime_and_grace_period`: Drop is active at $t=9.9\text{s}$, expires at $t=10.0\text{s}$; scavenger ineligible at $t=0.9\text{s}$, eligible at $t=1.0\text{s}$.
   - `test_player_xp_progression`: XP required is $15, 20, 25$ for levels 1, 2, 3; verifies level-up triggers and carryover XP.
   - `test_scavenger_selection`: Singleton constraint (1 global scavenger); ignores 3 closest enemies; ignores enemies $> 600\text{px}$.
3. **`tests/test_config_backend.py`**:
   - `test_all_25_configs_cataloged`: Checks 20 gameplay + 5 systemic configs exist.
   - `test_locked_baseline_neutrality`: Unlocked empty set produces strictly neutral $1.0\times$ multipliers.
   - `test_multiplicative_stacking`: Tests combined active configs against exact mathematical formulas ($2.691\times$ max damage, $1.571\times$ max speed, etc.).

### 5.2 Test Execution Command
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
All existing and new tests must pass with 0 errors.
