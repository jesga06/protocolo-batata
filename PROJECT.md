# Project: Protocolo: Batata

## Architecture
- Core Engine: Python / Pygame modular architecture
- State & Config Management: `src/sistemas/gerenciador_config.py`, `src/sistemas/config_dados.py`, `src/sistemas/config_efeitos.py`, `src/sistemas/salvamento.py`
- Gameplay & Scene Coordination: `src/cenas/gameplay.py`, `src/cenas/menu_configuracoes.py`
- Entity Subsystems: `src/entidades/jogador.py`, `src/entidades/inimigo_base.py`, `src/entidades/projetil.py`, `src/entidades/drop.py`
- Systems & Spawning: `src/sistemas/sistema_spawn.py`, `src/sistemas/sistema_drops.py`, `src/sistemas/sistema_scavenger.py`, `src/sistemas/sistema_colisoes.py`, `src/sistemas/sistema_particulas.py`
- UI & Level Up: `src/ui/modal_level_up.py`, `src/ui/hud.py`
- Test Infrastructure: `tests/` automated test suite executed via `python -m unittest discover -s tests` (285/285 passing)

## Feature Inventory
| # | Feature | Description | Milestone | Status | Source |
|---|---------|-------------|-----------|--------|--------|
| F1 | Neutral Defaults & Clean Save (R1) | All 20 configs start strictly in neutral values in new games, clean saves, and fallback data | M1 | DONE | CONFIGURACOES.md / ORIGINAL_REQUEST |
| F2 | Level-Up Neutral Unlock (R1) | Unlocking a config in level-up modal keeps it in neutral state until player explicitly toggles it | M1 | DONE | ORIGINAL_REQUEST / Survey |
| F3 | Config 1-5 Implementation (R2) | `qualidade_grafica`, `volume_geral`, `resolucao_tela`, `vsync`, `tela_cheia` exact bonus and sacrifice | M2 | DONE | CONFIGURACOES.md |
| F4 | Config 6-10 Implementation (R2) | `motion_blur`, `modo_daltonico`, `damage_numbers`, `hitbox_debug`, `mouse_cursor` exact bonus and sacrifice | M2 | DONE | CONFIGURACOES.md |
| F5 | Config 11-15 Implementation (R2) | `keybinds`, `suavizacao_camera`, `auto_fire`, `inimigos_ranged`, `coleta_inimiga` exact bonus and sacrifice | M2 | DONE | CONFIGURACOES.md |
| F6 | Config 16-20 Implementation (R2) | `drop_raro`, `iluminacao`, `cores_invertidas`, `screen_shake`, `dano_direcional` exact bonus and sacrifice | M2 | DONE | CONFIGURACOES.md |
| F7 | Player Speed Modifier Consistency | Fix `Jogador.update()` speed overwrite so `vel_jogador_mult` applies reliably | M2 | DONE | Survey Explorer 1 |
| F8 | Combat & Spawning Parameter Wiring | Wire enemy hp/speed scaling, ranged spawn toggle, drop bonus, xp mult, crit chance into gameplay | M2 | DONE | Survey Explorer 1 |
| F9 | Consumables / Power-Ups Catalog (R3) | 12 cards: Heals (+25/+50), XP (+15/+30), 15s Buffs (Dmg, Speed, Cadence, Res), Shield, Magnet Pulse, Crates | M3 | DONE | ORIGINAL_REQUEST / Survey |
| F10 | Golden Rule Enforcement (R3) | Consumables must be temporary (15s) and strictly weaker than permanent/toggle config buffs | M3 | DONE | ORIGINAL_REQUEST / Survey |
| F11 | Temporary Buffs & Shield in Jogador | Timers for 15s buffs, shield absorption, resistance calculation in `Jogador` | M3 | DONE | Survey Explorer 2 |
| F12 | Scavenger 10-Second Ground Delay | `DROP_TEMPO_SCAVENGER_ATIVAR = 10.0`, Scavenger only targets drops with age >= 10.0s | M4 | DONE | ORIGINAL_REQUEST / Survey |
| F13 | Automated Test Suite Expansion (R4) | Unit & integration tests for all 20 configs, neutral defaults, consumables, golden rule, scavenger 10s rule | M5 | DONE | ORIGINAL_REQUEST / Survey |
| F14 | 100% Test Pass Verification (R4) | Ensure entire test suite passes cleanly with 0 failures and 0 errors (285/285 tests) | M5 | DONE | ORIGINAL_REQUEST |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Neutral Defaults & Unlock State (R1) | F1, F2: Fix modal unlock logic, save defaults, fallback data | none | DONE |
| M2 | 20 Gameplay Config Effects & Sacrifices (R2) | F3, F4, F5, F6, F7, F8: Complete wiring of 20 configs across gameplay, entities, spawner, drops | M1 | DONE |
| M3 | Power-Ups / Consumables Catalog & Golden Rule (R3) | F9, F10, F11: 12 consumable cards, temporary buffs, shield, magnet pulse, crates | M1 | DONE |
| M4 | Scavenger 10-Second Ground Delay AI | F12: Update constants, drop timestamps, scavenger targeting | none | DONE |
| M5 | E2E & Unit Test Suite Pass (R4) | F13, F14: Update and expand tests in `tests/` covering M1-M4, verify 100% pass | M1, M2, M3, M4 | DONE |
| M6 | Adversarial Hardening & Forensic Audit | Deep adversarial testing and Forensic Audit (All Approved / Clean) | M5 | DONE |

## Interface Contracts
### `Jogador` Buffs & Modifiers Contract
- `jogador.mult_vel_config: float = 1.0`
- `jogador.buff_dano_timer: float = 0.0` (active buff: +5% dmg, duration 15.0s)
- `jogador.buff_vel_timer: float = 0.0` (active buff: +8% vel, duration 15.0s)
- `jogador.buff_cadencia_timer: float = 0.0` (active buff: +8% RPM / -8% cooldown, duration 15.0s)
- `jogador.buff_resistencia_timer: float = 0.0` (active buff: -8% dano recebido, duration 15.0s)
- `jogador.escudo_ativo: bool = False` (absorbs 1 hit, triggers 4s invulnerability)
- `jogador.aplicar_pulso_magnetico(drops)`: pulls all active drops toward player

### `ItemDrop` & `SistemaScavenger` Delay Contract
- `DROP_TEMPO_SCAVENGER_ATIVAR = 10.0`
- `drop.elegivel_scavenger() -> bool`: `return self.ativo and not self.coletado and (self.tempo_decorrido >= self.tempo_scavenger)` where `self.tempo_scavenger >= 10.0`

### `ModalLevelUp` Selection Contract
- Unlocking config card: `gerenciador_config.desbloquear_config(cid)` without altering current value (remains `cdef.valor_padrao`).
