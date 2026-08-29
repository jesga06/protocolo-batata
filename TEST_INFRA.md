# E2E Test Infra: Protocolo: Batata

## Test Philosophy
- Opaque-box & Requirement-driven derived from `ORIGINAL_REQUEST.md` and `CONFIGURACOES.md`.
- Automated test command: `.venv\Scripts\python -m unittest discover -s tests` (or `python -m unittest discover -s tests`).
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Game Session Testing.

## Feature Inventory Test Mapping
| # | Feature | Requirement | Tier 1 | Tier 2 | Tier 3 |
|---|---------|-------------|:------:|:------:|:------:|
| 1 | Neutral Defaults & Clean Save (R1) | ORIGINAL_REQUEST §1, CONFIGURACOES.md | 5 | 5 | ✓ |
| 2 | Level-Up Neutral Unlock (R1) | ORIGINAL_REQUEST §1, modal_level_up | 5 | 5 | ✓ |
| 3 | Configs 1-5 Effects (R2) | CONFIGURACOES.md §1-5 | 5 | 5 | ✓ |
| 4 | Configs 6-10 Effects (R2) | CONFIGURACOES.md §6-10 | 5 | 5 | ✓ |
| 5 | Configs 11-15 Effects (R2) | CONFIGURACOES.md §11-15 | 5 | 5 | ✓ |
| 6 | Configs 16-20 Effects (R2) | CONFIGURACOES.md §16-20 | 5 | 5 | ✓ |
| 7 | Consumables / Power-Ups Catalog (R3) | ORIGINAL_REQUEST §3 | 5 | 5 | ✓ |
| 8 | Golden Rule Inequality Constraints (R3) | ORIGINAL_REQUEST §3 | 5 | 5 | ✓ |
| 9 | Scavenger 10.0s Ground Delay AI | ORIGINAL_REQUEST §4 | 5 | 5 | ✓ |

## Test Architecture
- Tier 1: Unit & Feature Coverage (>=5 per feature)
- Tier 2: Boundary & Corner Cases (>=5 per feature, inequalities, 0/negative, max tiers, threshold 9.99s vs 10.01s)
- Tier 3: Cross-Feature Combinations (pairwise interaction of config toggles, temporary buffs, and enemy modifiers)
- Tier 4: Real-World Application Scenarios (full game runs, level-up milestones, boss waves, save-load cycles)

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Run with Config Unlocks | F1, F2, F9, F11, F12 | High |
| 2 | Heavy Modifiers Combat Simulation | F3-F8, F11 | High |
| 3 | Scavenger Survival Arena Simulation | F5, F12 | Medium |
| 4 | Save/Load Cycle Across Multiple Levels | F1, F2, F9 | Medium |
| 5 | All Consumables Usage Sequence | F9, F10, F11 | High |
