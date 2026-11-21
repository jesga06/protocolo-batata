# E2E Test Suite Ready

## Test Runner
- Command: `python -m unittest discover -s tests -p "test_*.py"` (or `.\.venv\Scripts\python -m unittest discover -s tests -p "test_*.py"`)
- Expected: All 393 tests pass with exit code 0 (including dedicated Boss & Endgame tests and forensic adversarial regression tests)

## Coverage Summary
| Tier | Count | Description |
|------|------:|-------------|
| 1. Feature Coverage | 15 | R1-R5 features tested in isolation |
| 2. Boundary & Corner | 4 | Boundary conditions (60s timer, HP thresholds, XP overflow, CD timings) |
| 3. Cross-Feature | 2 | Multithreading shotgun interactions, Slot 3B lifecycle |
| 4. Real-World Application | 1 | Full boss encounter flow from Level 20 cutscene to Victory screen |
| **Total** | **22** | Dedicated Boss & Endgame Tests |

## Feature Checklist
| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---------|:------:|:------:|:------:|:------:|
| XP Curve Smoothing | 1 | 1 | - | 1 |
| Victory Decoupling | 1 | - | - | 1 |
| 4 Mini-Boss Tiers | 1 | - | - | - |
| Mini-Boss 2x Scale & Hitbox | 1 | - | - | - |
| Mini-Boss Anti-Stacking | 1 | - | - | - |
| 60.0s Thermal Overload | 1 | 1 | - | - |
| Overclock Drop & Modal | 1 | - | - | - |
| 6 BIOS Modules | 1 | 1 | 1 | - |
| Geladeira Tsunami Entity | 1 | - | - | 1 |
| Boss Speech Balloon | 1 | - | - | 1 |
| Boss 3-Phase FSM | 1 | 1 | - | 1 |
| 4-Phase Intro Cutscene | 1 | - | - | 1 |
| Boss Drop Rules | 1 | - | - | 1 |
| Boss Spawner Rules | 1 | - | - | 1 |
| MenuDebug Controls | 1 | - | - | - |
