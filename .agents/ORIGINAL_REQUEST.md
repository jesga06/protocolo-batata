# Original User Request

## 2026-08-28T14:48:02Z

Implement "Protocolo: Batata", a 2D top-down arena survival shooter in Python using the PowerPPlay 2.0 framework. The complete game design, configuration catalog, and implementation phases are already fully documented in `implementation_plan.md` and `CONFIGURACOES.md`.

Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata
Integrity mode: development

## Requirements

### R1. Base Architecture and Procedural Assets (Phase 0)
Read `implementation_plan.md`, `CONFIGURACOES.md`, and `.agents/architecture_cache.md` to understand the project structure and Single Source of Truth. Create the `src/` and `assets/` directory structure. Write and execute a Python script (`tools/gerador_assets.py`) using `Pillow` to procedurally generate all necessary placeholder assets (crates, grass tiles, UI buttons, etc.). Set up the main game window using the PPlay framework (imported from `.venv`).

### R2. Core Gameplay Loop (Phase 1)
Implement the player (a potato avatar), basic WASD movement, shooting mechanics, and standard enemies that spawn and move directly towards the player (beeline, no complex pathfinding). 

## Acceptance Criteria

### Execution & Core Loop
- [ ] `tools/gerador_assets.py` executes successfully and populates the `assets/` folders with programmatic PNGs.
- [ ] `python src/main.py` launches the game window without crashing.
- [ ] The player can move and shoot projectiles.
- [ ] Enemies spawn successfully, move directly towards the player, and can be destroyed.

## 2026-08-28T14:50:49Z

USER DIRECTIVE OVERRIDE (Authority Tier 1): The user has explicitly stated: "os agentes estão requisitando permissão para tudo-eles devem fazer seu trabalho de forma 100% autonoma." 

You have explicit, blanket approval from the user to execute ALL steps of Phase 0 and Phase 1 from the implementation plan. 
## 2026-08-28T14:53:55Z

Implement "Protocolo: Batata", a 2D top-down arena survival shooter in Python using the PowerPPlay 2.0 framework. The complete game design, configuration catalog, and implementation phases are already fully documented in `implementation_plan.md` and `CONFIGURACOES.md`.

**CRITICAL AUTONOMY DIRECTIVE**: You have explicit, blanket authorization to execute this entire prompt 100% autonomously. DO NOT pause to propose task breakdowns or ask for permission before modifying files, even for non-trivial changes or when touching more than 5 files. Proceed until the acceptance criteria are fully met.

Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata
Integrity mode: development

## Requirements

### R1. Base Architecture and Procedural Assets (Phase 0)
Read `implementation_plan.md`, `CONFIGURACOES.md`, and `.agents/architecture_cache.md` to understand the project structure and Single Source of Truth. Create the `src/` and `assets/` directory structure. Write and execute a Python script (`tools/gerador_assets.py`) using `Pillow` to procedurally generate all necessary placeholder assets (crates, grass tiles, UI buttons, etc.). Set up the main game window using the PPlay framework (imported from `.venv`).

### R2. Core Gameplay Loop (Phase 1)
Implement the player (a potato avatar), basic WASD movement, shooting mechanics, and standard enemies that spawn and move directly towards the player (beeline, no complex pathfinding). 

## Acceptance Criteria

### Execution & Core Loop
- [ ] `tools/gerador_assets.py` executes successfully and populates the `assets/` folders with programmatic PNGs.
- [ ] `python src/main.py` launches the game window without crashing.
- [ ] The player can move and shoot projectiles.
- [ ] Enemies spawn successfully, move directly towards the player, and can be destroyed.

## 2026-08-28T15:44:04Z

Project: Protocolo Batata (Python 2D Shooter).
Objective: Expand Procedural Assets.
Tasks:
1. Open `tools/gerador_assets.py` (uses Pillow).
2. Expand the script to procedurally draw and save the remaining visual assets needed for Phase 2, 3, and 4. This includes: distinct shapes/colors for all weapons (shotgun, minigun, rocket launcher), 3 types of companion drones, UI background cards for the configurations menu, and generic icons for configuration buttons.
3. Run the script so the `assets/` folders are populated.
Constraints: DO NOT touch any file inside the `src/` directory. Focus entirely on Python Pillow asset generation. Execute autonomously.


## 2026-08-28T15:44:04Z

Project: Protocolo Batata (Python 2D Shooter). 
Objective: UI Alignment and Input Mechanics.
Context: The project uses PPlay 2.0 as the base engine. DO NOT remove PPlay entirely. The user explicitly wants PPlay to remain the core engine.
Tasks:
1. Modify UI Text: Use raw Pygame (`pygame.font` and `rect.centerx`) INSTEAD of PPlay's text module to perfectly center the main menu texts, the HUD timer, and the kill counter horizontally on the screen.
2. Modify Inputs: Remove auto-fire. Weapons must ONLY fire when detecting an explicit mouse click (catch `pygame.MOUSEBUTTONDOWN`).
3. Weapon Switching: Allow the player to switch between weapons using the numeric keys 1, 2, and 3.
Constraints: You are the ONLY agent authorized to touch `src/main.py` and the entity files right now. Execute autonomously and do not pause for permissions.

## 2026-08-28T15:44:10Z

Project: Protocolo Batata (Python 2D Shooter).
Objective: Scavenger Enemy and Drop Logic.
Tasks:
1. Create `src/sistemas/sistema_scavenger.py` and `src/sistemas/sistema_drops.py`.
2. Implement the pure logic for Drop items: 10s total lifetime, eligible for enemy capture after 1s.
3. Implement the Scavenger AI selector: Only 1 enemy globally can capture a drop. Target is selected pseudo-randomly, explicitly EXCLUDING enemies that are too far and EXCLUDING the 3 closest enemies to the drop.
Constraints: DO NOT touch `src/main.py` or the core entity files. Write these as decoupled, pure logic classes that we will integrate later. Execute autonomously.

## 2026-08-28T15:45:00Z

Project: Protocolo Batata (Python 2D Shooter).
Objective: Configuration System Logic.
Tasks:
1. Create isolated backend modules `src/sistemas/config_sistema.py` and `src/sistemas/config_efeitos.py`.
2. Implement the mathematical logic, stacking multipliers, and data structures for the 20 unlockable configurations listed in `CONFIGURACOES.md` (e.g., multiplicative stacking for damage, sequential for HP, direct modifiers).
Constraints: DO NOT touch `src/main.py` or any existing gameplay files to avoid git conflicts with other parallel agents. Build this as a pure, importable logic system. Execute autonomously.

## 2026-08-28T15:46:50Z

USER DIRECTIVE (Priority Update): The user requested a general non-gameplay scaling configuration because the game feels small on 1080p. Please add a new SYSTEMIC configuration (no buffs/nerfs, accessibility only) called 'S5: Escala Global' (values e.g., 100%, 125%, 150%) to the config system logic you are building. This is separate from the gameplay 'Zoom Level' config.


## 2026-08-28T15:46:43Z

USER DIRECTIVE (Priority Update): The user requested that the base sprites (player potato, enemies, weapons) are too small on a 1080p monitor. Please increase the base pixel dimensions of all generated game sprites in `tools/gerador_assets.py` by approximately 30% (e.g., if they were 32x32, make them 42x42 or 48x48) before generating them.

## 2026-08-28T19:00:08Z

Implement directional 45-degree cone melee combat tuning, Phase 2 (Drops & XP progression), and Phase 3 (Configuration Engine) for "Protocolo: Batata", keeping PPlay 2.0 as the base engine with native Pygame optimizations.

**CRITICAL AUTONOMY DIRECTIVE**: You have explicit, blanket authorization to execute this prompt 100% autonomously. DO NOT pause for permissions. Keep the subagent hierarchy minimal (max 5 agents total) to respect API quotas.

Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata
Integrity mode: development

## Requirements

### R1. Directional Cone Melee Tuning (45° Arc & 2x Potato Reach)
- **Hitbox & Target Selection**: Melee attacks must ONLY hit enemies inside a directional cone with a **45-degree arc** pointed directly towards the mouse cursor. No 360-degree all-around hits.
- **Range**: Set range to exactly 2.0× the potato avatar's width (~84px).
- **Damage & Knockback**: Set damage to 10 per hit (requiring exactly 5 hits to defeat a standard 50 HP enemy). Increase knockback force to 2× baseline (360.0 px/s).
- **Visuals**: Draw a directional 45° cone/sector indicator pointing towards the mouse cursor (idle aim guide while equipped, and an expanding directional shockwave/slash when swinging).

### R2. Phase 2 — Drops & XP System
- **Loot Spawning**: Enemies drop XP items upon death, plus chance for weapon/heal crates.
- **Drop Lifetime & Collection**: Drops have a 10s lifetime. Collected on player contact.
- **XP Progression**: Implement XP gain, level tracking, level-up trigger ($XP_{prox} = 10 + 5 \times level$), and a screen-space XP progress bar under the top HUD.

### R3. Phase 3 — Configuration Engine Backend
- **Data & Multiplier Pipeline**: Implement `src/sistemas/config_dados.py` and `config_efeitos.py` to calculate the multiplicative stat stackings for all 20 gameplay configurations and 5 systemic configs from `CONFIGURACOES.md`.

## Acceptance Criteria

### Combat & Progression
- [ ] Melee attack only damages enemies within the mouse-facing 45° cone and ~84px range.
- [ ] Standard enemy takes exactly 5 melee hits to die and receives 2× stronger knockback.
- [ ] Melee aim guide and swing effects render as a directional 45° cone, not a full 360 circle.
- [ ] Defeated enemies spawn XP gems that grant experience and level up the player.
- [ ] Configuration calculation module passes unit tests for multiplicative stacking.
- [ ] All automated tests pass (`python -m unittest discover tests`).

## 2026-08-28T19:09:57Z

USER DIRECTIVE UPDATE (Balance Tuning):
The user specified that:
1. Pistol damage must kill a standard enemy in exactly 3 hits. With standard enemy HP = 50, set Pistol damage = 17 (17 * 3 = 51 >= 50).
2. Melee damage remains 10 (10 * 5 = 50, taking 5 hits).
Please ensure `src/armas/pistola.py` is updated and tests reflect this 3-hit threshold for the pistol.
