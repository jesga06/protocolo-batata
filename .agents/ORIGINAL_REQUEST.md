# Original User Request

## Initial Request — 2026-08-29T19:19:25Z

Implement the endgame progression and boss encounter systems in **Protocolo: Batata**, introducing the 4-tier Mini-Boss Overclock System (2x scale, 60s thermal overload escape, and 6 Overclock BIOS modules) and the climactic Final Boss **Geladeira Tsunami** (*"The Perfect Sound™"*, 112x156 px, 3-phase FSM, cinematic intro, speech balloon, boss-mode drop and spawner rules, and victory integration), adhering strictly to the naming conventions in `CATALOGO_ARQUITETURAL.md`.

Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata
Integrity mode: development

## Requirements

### R1. Mini-Boss Overclock Ecosystem & 2x Scaling
- Update mini-boss schedule to 4 distinct tiers aligned with `CATALOGO_ARQUITETURAL.md`:
  - 1:00 — `MINI-BOSS: ESTAGIÁRIO SÊNIOR` (`InimigoRapido`)
  - 2:00 — `MINI-BOSS: ARQUIVO MORTO PRIORITÁRIO` (`InimigoTank`)
  - 3:00 — `MINI-BOSS: FANTASMA DO RH` (`InimigoPhasing`)
  - 4:00 — `MINI-BOSS: SEGURANÇA-CHEFE` (`InimigoBlindado`)
- Scale all `is_elite=True` mini-bosses to **2x sprite size and 2x physics hitbox**.
- Enforce anti-stacking: only 1 mini-boss can be active at a time; subsequent spawn timers pause while an elite is alive.
- Implement a 60.0s Thermal Overload timer: if the mini-boss is not defeated within 60s, it overheats, explodes into scrap with zero loot, and displays the exact toast: `O MINI-BOSS SUPERAQUECEU. VOCÊ NÃO RECEBERÁ RECOMPENSAS POR ELE.`
- When defeated within 60s, the mini-boss drops a `drop_overclock` item that opens `ModalOverclock` with 3 random selections from the 6 Overclock modules:
  1. `Multithreading`: +1 full additional shot instance per player attack click (ignoring weapon cooldown, with 0.08s delay and ±6° dispersion; for shotgun, fires a full second 9-pellet volley).
  2. `Refrigeração a Nitrogênio`: +35% weapon firerate (cadência de tiro).
  3. `Overvolt`: +30% Critical Strike Chance with 2x Critical Damage multiplier.
  4. `BIOS Modding`: +1 secondary special weapon slot (Slot 3B) displayed directly below Slot 3 in the HUD; pressing '3' toggles between 3A and 3B when Slot 3 is active.
  5. `Proteção contra Surtos`: +50 Max HP + 1 reactive fatal damage shield granting 5s invulnerability, with a 45s cooldown starting **after** the 5s invulnerability expires.
  6. `Upgrade de Barramento`: +40% Movement Speed.

### R2. Progression Pacing & Victory Condition Update
- Update `SistemaXP`: for lvl > 10, reduce XP requirement by 25% (`int(round(base * 0.75))`).
- Remove the automatic 10-minute timer victory condition (`TEMPO_VITORIA`). Victory only triggers when **Geladeira Tsunami is defeated**.

### R3. Final Boss "Geladeira Tsunami" Entity & Assets
- Implement `GeladeiraTsunami` (112 x 156 px sprite and physics hitbox) using `assets/sprites/inimigos/geladeira_tsunami.png` pre-scaled to 112x156.
- Register asset keys `"musica_boss": "audio/musica/geladeira tsunami.wav"` and `"boss_geladeira_tsunami": "sprites/inimigos/geladeira_tsunami.png"`.
- Implement speech balloon rendering above boss:
  *"Você já passou da validade.<br>Sente a pressão, neném."*
- Implement 3-Phase FSM:
  - `ESTADO_INTRO`: Ascends from bottom, displays speech balloon for 3.5s.
  - `ESTADO_FASE1` (HP > 66%): Heavy Stalk + Subwoofer Pulse (expanding concentric sonic rings with dodge gaps).
  - `ESTADO_FASE2` (33% < HP <= 66%): Telegraphed Bass Rush Dash (420 px/s, wall bounce screen shake, 4 acoustic bounce shards) + Subwoofer Totems.
  - `ESTADO_FASE3` (HP <= 33%): Center Stage Anchor + Sonic Tsunami Helix (rotating spiral wave beams + radial bass blasts).
  - `ESTADO_MORTE`: 1.5s flashing explosion cascade, screen shake, victory drop, signals victory screen.

### R4. Boss Encounter Flow, Drop Overrides & HUD
- Trigger cutscene upon closing the Level 20 upgrade selection modal:
  - Phase 1 (2.0s): BGM fades out, screen fades to solid white, hostile bullets clear.
  - Phase 2 (1.0s): Screen cuts to solid black, ambient mobs purged, player teleported to arena center (Xc, Yc).
  - Phase 3 (5.0s): `geladeira tsunami.wav` fades in, black screen clears, boss rises from bottom edge.
  - Phase 4 (3.5s): Speech balloon renders, Boss Health Bar animates at top center, player movement unlocks.
- Boss-Mode Drop Rules:
  - Drops **never despawn** during the boss fight (`pausar_despawn=True`).
  - 0% XP drops.
  - Drop rate reduced by 60% (40% of baseline).
  - Drop distribution: 10% Cura, 45% Arma, 45% Equipamento.
- Spawner Rules during Boss: throttled to 20% density, containing only `InimigoPadrao` (Estagiários Novatos).
- HUD: Render Boss Health Bar with name **GELADEIRA TSUNAMI — The Perfect Sound™** and render Slot 3B below Slot 3 when BIOS Modding is unlocked.

### R5. Debug Tools & Comprehensive Automated Test Suite
- Add debug controls in `MenuDebug`:
  - `[DEBUG] Forçar Boss Cutscene (Level 20)`
  - `[DEBUG] Spawn Direto Geladeira Tsunami`
  - `[DEBUG] Spawn Mini-Boss Elite`
  - `[DEBUG] Conceder Overclock`
  - `[DEBUG] Definir Boss HP (100% / 50% / 10%)`
  - `[DEBUG] Matar Geladeira Tsunami`
- Create `tests/test_boss_geladeira_tsunami.py` testing XP curve smoothing, mini-boss 2x size and 60s overload timer, Overclock effects, boss FSM, drop rules, and victory transition.
