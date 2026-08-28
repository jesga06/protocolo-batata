# E2E Test Infra: Protocolo: Batata

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on internal implementation details.
- Headless test execution using `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`.
- Automated test coverage of all 4 Acceptance Criteria.

## Feature Inventory & Test Coverage Goals
| # | Feature | Requirement | Tier 1 (Unit) | Tier 2 (Boundary) | Tier 3 (Integration) | Tier 4 (E2E) |
|---|---------|-------------|:-------------:|:-----------------:|:--------------------:|:------------:|
| 1 | Asset Generation | `tools/gerador_assets.py` executes without error and generates PNG/WAV files | ✓ | ✓ | ✓ | ✓ |
| 2 | Window & Engine Launch | `src/main.py` launches window without crashing | ✓ | ✓ | ✓ | ✓ |
| 3 | Player Movement & Math | WASD input, diagonal normalization ($dx, dy \times 0.7071$), boundary clamping | ✓ | ✓ | ✓ | ✓ |
| 4 | Weapon & Projectile Mechanics | Shooting fires projectile toward target, cooldowns, lifetime expiration | ✓ | ✓ | ✓ | ✓ |
| 5 | Enemy Beeline Movement | Enemies move toward player coordinates via unit vector | ✓ | ✓ | ✓ | ✓ |
| 6 | Enemy Spawning | Enemies spawn offscreen in perimeter ring and enter screen | ✓ | ✓ | ✓ | ✓ |
| 7 | Damage & Destruction | Projectile kills enemy, enemy deals contact damage with individual cooldown | ✓ | ✓ | ✓ | ✓ |

## Test Architecture
- Test runner: `python -m unittest discover -s tests -p "test_*.py"`
- Test suites in `tests/`:
  - `tests/test_assets.py`: verifies asset generator produces valid PNG images and audio files in all expected directories.
  - `tests/test_player.py`: verifies player stats, movement normalization, arena bounds clamping.
  - `tests/test_weapons.py`: verifies pistol/melee cooldowns, projectile trajectory, and damage.
  - `tests/test_enemies.py`: verifies enemy beeline vector math, spawning, contact damage cooldowns, and death destruction.
  - `tests/test_gameplay_e2e.py`: headless simulation of full gameplay loop (gameplay scene update, movement, shooting, spawn, enemy death).
