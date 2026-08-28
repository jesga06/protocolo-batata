# Scope: Expand Procedural Assets (Phase 2, 3, 4)

## Architecture
- `tools/gerador_assets.py`: Procedural sprite & UI asset generator using Pillow (PIL).
- Output Directories: `assets/sprites/armas/`, `assets/sprites/equipamentos/`, `assets/sprites/drones/`, `assets/ui/cards/`, `assets/ui/botoes/`, `assets/ui/icones/`, etc.
- Dependencies: Python standard library, Pillow (PIL).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Weapons Visual Assets | Distinct procedural shapes/colors for all weapons (shotgun, minigun, rocket launcher, etc.) and their projectiles/effects if applicable | M1 | User Request & implementation_plan.md |
| 2 | Companion Drones | 3 types of companion drones (e.g. cura, combate, suporte) with distinct shapes and color palettes | M1 | User Request & CONFIGURACOES.md |
| 3 | UI Background Cards | Background cards for configurations menu (standard card, unlocked card, locked card, active buff card) | M1 | User Request & CONFIGURACOES.md |
| 4 | Generic Icons for Config Buttons | Generic icons/glyphs for configuration buttons and UI controls | M1 | User Request & CONFIGURACOES.md |
| 5 | Execution & Integrity Verification | Script executes cleanly and populates `assets/`, generating valid non-empty PNG files | M1 | Acceptance Criteria |
| 6 | 30% Scale Increase | Scale up base gameplay sprite dimensions by ~30% (e.g., 32x32 -> 42x42/48x48) for 1080p display readability | M1 | User Directive 2026-08-28T15:46:56Z |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Expand Asset Generator & Populate Assets | Update `tools/gerador_assets.py`, execute script, verify all PNGs | none | IN_PROGRESS |

## Code Layout & Write Boundaries
- Single file modified: `tools/gerador_assets.py`
- Generated output destination: `assets/` (subdirectories: `assets/sprites/`, `assets/ui/`, etc.)
- RESTRICTED: `src/` must NOT be touched.
