# Project Plan: Protocolo Batata - Melee Cone Tuning, Drops & XP, and Configuration Engine

## Objective
Implement R1 (Directional 45° cone melee tuning, 2x avatar reach, damage=10, knockback=360 px/s, cone visuals), R2 (Drops & XP Progression system, 10s drop lifetime, XP bar in HUD), and R3 (Configuration Engine Backend in src/sistemas/config_dados.py and config_efeitos.py with 20 gameplay configs + 5 systemic configs from CONFIGURACOES.md).

## Subagent Quota & Strategy
Maximum 5 subagents total:
1. `teamwork_preview_explorer_1`: Deep inspection of current codebase (`src/armas/melee.py`, `src/entidades/jogador.py`, `src/entidades/drop.py`, `src/sistemas/sistema_xp.py`, `src/sistemas/sistema_drops.py`, `src/sistemas/config_dados.py`, `src/sistemas/config_efeitos.py`, `src/cenas/gameplay.py`, `src/ui/hud.py`, `tests/`).
2. `teamwork_preview_worker_1`: Complete implementation of R1, R2, R3, and comprehensive unit tests in `tests/`. Runs `python -m unittest discover tests`.
3. `teamwork_preview_reviewer_1`: Code review, verifying 45° cone math, XP formulas, and configuration multiplier stackings against acceptance criteria and `CONFIGURACOES.md`.
4. `teamwork_preview_challenger_1`: Adversarial testing against edge cases (boundary angles, multi-drop collection, level-up formula correctness, config stacking multiplications). Runs tests.
5. `teamwork_preview_auditor_1`: Forensic integrity audit confirming authentic implementation and zero hardcoded test facades.

Plan established. Commencing Step 1.
