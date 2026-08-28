# BRIEFING — 2026-08-28T19:13:00Z

## Mission
Implement R1 (Directional Cone Melee), R2 (Drops & XP Progression System), and R3 (Configuration Engine Backend) with comprehensive unit tests for Protocolo Batata.

## 🔒 My Identity
- Archetype: preview_worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_worker_1
- Original parent: d3d496fa-cbc4-4e06-a862-b9fc8c05c2e8
- Milestone: Preview Release Implementation (R1, R2, R3)

## 🔒 Key Constraints
- Pure logic & pygame implementation adhering to architecture standards
- Directional cone melee: 45° arc, 84px reach, 10 dmg, 360 px/s knockback on max 2 closest targets, enemy base HP 50 (5 hits).
- Drops & XP: ItemDrop (xp, cura, arma), 10s lifetime, 1s scavenger grace period, formula XP_prox = 10 + 5 * level (max lvl 20), multi-level overflow, scavenger AI target selector excluding 3 closest and >600px.
- Configuration Engine: 20 gameplay + 5 systemic configs cataloged matching CONFIGURACOES.md, neutral baseline when locked, multiplicative stacking.
- Unit tests in `tests/` passing 100%.
- Never commit .agents/architecture_cache.md.

## Current Parent
- Conversation ID: d3d496fa-cbc4-4e06-a862-b9fc8c05c2e8
- Updated: 2026-08-28T19:13:00Z

## Task Summary
- **What to build**: Melee cone tuning & rendering, Drop/XP/Scavenger systems & HUD integration, Configuration engine catalog/modifiers/state backend, and unit tests.
- **Success criteria**: All requirements R1, R2, R3 implemented, 100% test pass rate with `python -m unittest discover tests`.
- **Interface contracts**: `PROJECT.md` / `CONFIGURACOES.md` / `.agents/architecture_cache.md`.
- **Code layout**: `src/` modules + `tests/`.

## Key Decisions Made
- Implemented 45° directional cone melee in `src/armas/melee.py` with angular difference normalization ($\Delta \theta \le 22.5^\circ$), reach $84.0\text{px}$, 10 damage, 360 px/s knockback on 2 closest targets, maintaining backward compatibility when aim target is omitted.
- Created `src/entidades/drop.py`, `src/sistemas/sistema_drops.py`, `src/sistemas/sistema_xp.py`, `src/sistemas/sistema_scavenger.py`, `src/ui/hud.py` with complete gameplay integration in `src/entidades/jogador.py` and `src/cenas/gameplay.py`.
- Created `src/sistemas/config_dados.py`, `src/sistemas/config_efeitos.py`, `src/sistemas/config_sistema.py` with 25 configs (20 gameplay + 5 systemic including S5: Escala Global), strict neutral baseline when locked, and pure multiplicative stacking.
- Adjusted Pistol damage to 17 and enemy HP to 50 so pistol takes 3 hits (17*3=51) and melee takes 5 hits (10*5=50).

## Artifact Index
- `.agents/teamwork_preview_worker_1/DISPATCH.md` — assignment dispatch log
- `.agents/teamwork_preview_worker_1/BRIEFING.md` — situational memory
- `.agents/teamwork_preview_worker_1/progress.md` — heartbeat & execution log
- `.agents/teamwork_preview_worker_1/handoff.md` — final completion report
- `tests/test_melee_cone.py` — R1 directional melee unit tests
- `tests/test_drops_xp.py` — R2 drops & XP progression unit tests
- `tests/test_config_backend.py` — R3 configuration engine unit tests

## Change Tracker
- **Files modified**:
  - `src/utils/constantes.py`: Melee & enemy baseline tuning (`MELEE_DANO=10`, `MELEE_ALCANCE=84.0`, `MELEE_KNOCKBACK=360.0`, `MELEE_ARCO_GRAUS=45.0`, `INIMIGO_PADRAO_HP=50`, `PISTOLA_DANO=17`)
  - `src/armas/melee.py`: 45° cone sector geometry, reach 84px, 10 dmg, 360 px/s knockback to 2 closest
  - `src/entidades/inimigo_base.py`: Updated default hp to `INIMIGO_PADRAO_HP` (50)
  - `src/entidades/jogador.py`: Integrated XP progression & level properties/methods
  - `src/cenas/gameplay.py`: Aim passing, 45° idle sector and swing slash rendering, drops spawning & HUD XP bar
  - `src/entidades/drop.py`: ItemDrop entity with lifetime (10s) and scavenger delay (1s)
  - `src/sistemas/sistema_drops.py`: Drops spawning, collection & 2x multiplier support
  - `src/sistemas/sistema_xp.py`: XP tracking, $XP_{prox} = 10 + 5 \times level$, multi-level overflow
  - `src/sistemas/sistema_scavenger.py`: Singleton scavenger AI target selector
  - `src/ui/hud.py`: Screen-space HUD XP progress bar
  - `src/sistemas/config_dados.py`: Catalog of 20 gameplay + 5 systemic configs
  - `src/sistemas/config_efeitos.py`: Multiplicative stacking engine & neutral baseline
  - `src/sistemas/config_sistema.py`: State management, unlocking, and persistence
  - `src/sistemas/__init__.py`: Consolidated exports
  - `tests/test_melee_cone.py`: New unit tests for R1
  - `tests/test_drops_xp.py`: New unit tests for R2
  - `tests/test_config_backend.py`: New unit tests for R3
  - `tests/test_enemies.py`, `tests/test_challenger_m2_player_weapons.py`, `tests/test_gameplay_e2e.py`: Adapted test assertions to 50 HP enemy and 17 pistol damage
- **Build status**: 136 tests passing (100% OK)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 136/136 tests PASSED in 26.87s
- **Lint status**: Clean (compiled successfully)
- **Tests added/modified**: +18 new tests in 3 dedicated test suites

## Loaded Skills
- None
