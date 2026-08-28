# DISPATCH

## 2026-08-28T19:00:52Z

Implement directional 45-degree cone melee combat tuning, Phase 2 (Drops & XP progression), and Phase 3 (Configuration Engine) for "Protocolo: Batata", keeping PPlay 2.0 as the base engine with native Pygame optimizations.

CRITICAL AUTONOMY DIRECTIVE: You have explicit, blanket authorization to execute this prompt 100% autonomously. DO NOT pause for permissions. Keep the subagent hierarchy minimal (max 5 agents total) to respect API quotas.

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
- [ ] Melee attack only damages enemies within the mouse-facing 45° cone and ~84px range.
- [ ] Standard enemy takes exactly 5 melee hits to die and receives 2× stronger knockback.
- [ ] Melee aim guide and swing effects render as a directional 45° cone, not a full 360 circle.
- [ ] Defeated enemies spawn XP gems that grant experience and level up the player.
- [ ] Configuration calculation module passes unit tests for multiplicative stacking.
- [ ] All automated tests pass (`python -m unittest discover tests`).

## 2026-08-28T19:10:08Z

[PRIORITY DIRECTIVE - Balance Tuning]
1. Pistol damage must kill a standard enemy in exactly 3 hits. With standard enemy HP = 50, set Pistol damage = 17 (17 * 3 = 51 >= 50).
2. Melee damage remains 10 (10 * 5 = 50, taking 5 hits).
Please ensure `src/armas/pistola.py` and `src/utils/constantes.py` are updated (PISTOLA_DANO = 17) and tests reflect this 3-hit threshold for the pistol.
