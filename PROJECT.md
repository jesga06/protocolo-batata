# Project: Protocolo: Batata

## Architecture
Protocolo: Batata is a 2D top-down arena survival shooter built in Python using PowerPPlay 2.0 (`.venv/Lib/site-packages/PPlay` / `pygame-ce`).
The game uses a virtual canvas resolution (800x600 or 1280x720) with nearest-neighbor scaling and letterboxing.
The core progression loop allows unlocking game configurations (FPS, resolution, UI, controls) by leveling up with XP from defeated enemies.

### Directory Layout
- `assets/`:
  - `assets/sprites/` (`jogador/`, `inimigos/`, `armas/`, `projeteis/`, `equipamentos/`, `drops/`)
  - `assets/tiles/` (floors, walls, crates)
  - `assets/ui/` (buttons, slots, crosshairs, upgrade cards, config icons)
  - `assets/audio/` (`sfx/`, `musica/`)
- `src/`:
  - `main.py`: Entry point, window initialization, scene loop.
  - `cenas/`: Game scenes (`menu_principal.py`, `gameplay.py`, `menu_pausa.py`, `level_up.py`, `game_over.py`).
  - `entidades/`: Game entities (`jogador.py`, `inimigo_base.py`, `inimigo_padrao.py`, `projetil.py`, `drop.py`).
  - `armas/`: Weapon implementations (`arma_base.py`, `melee.py`, `pistola.py`).
  - `sistemas/`: Core systems (`sistema_spawn.py`, `config_sistema.py`, `gerenciador_audio.py`).
  - `ui/`: UI components (`hud.py`, `botao.py`).
  - `utils/`: Utilities & constants (`constantes.py`, `math_utils.py`, `asset_loader.py`).
- `tools/`: `gerador_assets.py` for procedural placeholder generation.
- `tests/`: Automated test suite for headless verification.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Procedural Asset Generator | `tools/gerador_assets.py` generates all PNG sprites, UI, tiles, and WAV audio | M1 (Phase 0) | ORIGINAL_REQUEST §R1, survey_1 |
| 2 | Base Window & Loop | PPlay `Window` initialization with virtual buffer, title, delta time, and `SceneManager` | M1 (Phase 0) | ORIGINAL_REQUEST §R1, survey_1 |
| 3 | Core Math & Constants | Vector normalization, distance, AABB math, stat baselines in `src/utils/` | M1 (Phase 0) | survey_1, survey_2 |
| 4 | Player Entity & Movement | Potato avatar, WASD/Arrow movement, diagonal normalization, boundary clamping | M2 (Phase 1) | ORIGINAL_REQUEST §R2, survey_2 |
| 5 | Weapons & Projectiles | Permanent Melee (Slot 1) & Pistol (Slot 2), projectile physics, auto-fire | M2 (Phase 1) | ORIGINAL_REQUEST §R2, survey_2 |
| 6 | Enemy Entity & Beeline AI | Standard crawler enemy (25 HP, 100 px/s, 10 dmg), direct beeline vector to player | M2 (Phase 1) | ORIGINAL_REQUEST §R2, survey_3 |
| 7 | Contact Damage & Hit Cooldown | Per-enemy instance contact cooldown (0.4s), player damage, damage flash | M2 (Phase 1) | GDD §2.7, survey_2, survey_3 |
| 8 | Spawner System | Offscreen perimeter spawning, wave scaling (1.8s -> 0.4s), soft population cap | M2 (Phase 1) | survey_3 |
| 9 | Combat & Destruction | Projectile-enemy collision, enemy health depletion, death, score/kill tracking | M2 (Phase 1) | ORIGINAL_REQUEST §R2, survey_2, survey_3 |
| 10 | Gameplay Scene & In-World HUD | `GameplayScene` coordinate handling (world vs screen), player HP/XP bars | M2 (Phase 1) | survey_2, survey_3 |
| 11 | Headless Test Suite & Acceptance Gate | Opaque-box & unit tests verifying all 4 acceptance criteria | M3 (E2E & Gate) | ORIGINAL_REQUEST §Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Phase 0 - Base Architecture & Assets | `tools/gerador_assets.py`, `src/utils/`, `src/main.py`, directory structure | none | DONE |
| 2 | M2: Phase 1 - Core Gameplay Loop | `src/entidades/`, `src/armas/`, `src/sistemas/`, `src/cenas/gameplay.py` | M1 | DONE |
| 3 | M3: Acceptance & E2E Validation | Pass 100% of acceptance criteria tests, runtime execution validation | M1, M2 | DONE |

## Interface Contracts
### Player ↔ Weapon
- `Jogador` owns weapon instances in `jogador.armas = [Melee(), Pistola()]`.
- `jogador.processar_input()` receives mouse virtual position `(mx, my)` and calls active weapon firing logic.
- Weapons return lists of spawned `Projetil` objects added to `GameplayScene.projeteis`.

### Projectile ↔ Enemy
- `Projetil` checks collision with `InimigoBase` via AABB (`projetil.collided(inimigo)` or `math_utils.check_collision`).
- On collision: `inimigo.receber_dano(projetil.dano)`, `projetil.ativo = False`.

### Enemy ↔ Player
- `InimigoBase.update(dt, (jogador.x, jogador.y))` moves toward player center.
- `inimigo.tentar_causar_dano_contato(jogador)` checks collision and individual cooldown: `jogador.receber_dano(inimigo.dano_contato)`.

### Scene ↔ PPlay Window
- `main.py` creates `Window(800, 600, "Protocolo: Batata", resizavel=True, pixel_art=True)`.
- `GameplayScene` inherits `PPlay.scenemanager.Scene`, implements `loop()` and `draw()`.
