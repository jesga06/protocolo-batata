# E2E Test Infra: Protocolo: Batata — Boss & Endgame Progression

## Test Philosophy
- Opaque-box, requirement-driven, deterministic test suite.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Interaction Testing + End-to-End Game Scenarios.

## Feature Inventory
| # | Feature | Source | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---------|--------|:-----------------:|:-----------------:|:-----------------:|:-----------------:|
| 1 | XP Curve Smoothing (>Lvl 10) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 2 | Victory Condition Decoupling | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 3 | 4-Tier Mini-Boss Schedule | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 4 | Mini-Boss 2x Scale & Hitbox | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 5 | Mini-Boss Anti-Stacking | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 6 | 60.0s Thermal Overload | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 7 | Overclock Drop & Modal | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 8 | 6 Overclock BIOS Modules | ORIGINAL_REQUEST §R1 | 6 | 6 | ✓ | ✓ |
| 9 | Geladeira Tsunami Entity | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 10 | Boss Speech Balloon | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 11 | Boss 3-Phase FSM & Attacks | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| 12 | 4-Phase Intro Cutscene | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 13 | Boss-Mode Drop Rules | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 14 | Boss-Mode Spawner Rules | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| 15 | Debug Controls in MenuDebug | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: Python standard `unittest` (`python -m unittest discover -s tests -p "test_*.py"`)
- Main Target: `tests/test_boss_geladeira_tsunami.py` + 4 Forensic Regression Suites (`test_config_ssot_and_no_cheats.py`, `test_render_visibility_regression.py`, `test_mechanics_e2e_real_loop.py`, `test_engine_and_input_contracts.py`)
- Pre-condition: All 393 tests covering 100% of subsystems continue passing with zero regressions.
