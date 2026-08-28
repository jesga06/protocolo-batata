# BRIEFING — 2026-08-28T15:45:21Z

## Mission
Specify all requirements, data structures, state machines, math/timing, interfaces, and edge cases for the Drop System pure logic (`src/sistemas/sistema_drops.py`) in Protocolo: Batata.

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Teamwork specialist, Specification Miner
- Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_spec_miner_survey_2
- Original parent: 21fb4cb2-d6fa-4593-9395-4d1409debecc
- Milestone: Pure Logic Drop System Specification

## 🔒 Key Constraints
- Pure logic decoupled from rendering (no Pygame/PPlay dependencies required for unit tests).
- 10.0s total lifetime.
- 1.0s grace period before enemy scavenging is allowed (player can pick up immediately).
- Drop expiration when lifetime reaches 0 (or >= 10s elapsed).
- State transitions (active, expired, collected_by_player, collected_by_enemy).
- Support various drop types / payloads (XP, health, potato seeds, configs, etc.).
- Update method with delta time (dt).
- Document features, edge cases, error conditions, and interface definitions thoroughly.
- Label evidence tiers (Observed / Verified / Inferred / Speculative).

## Current Parent
- Conversation ID: 21fb4cb2-d6fa-4593-9395-4d1409debecc
- Updated: not yet

## Task Summary
- **What to build**: Pure logic specification for Drop System (`src/sistemas/sistema_drops.py`).
- **Success criteria**: Comprehensive handoff report detailing data models, states, timings, collision/pickup criteria, drop rates/spawning, payload processing, edge cases, and test verification methods.
- **Interface contracts**: `src/sistemas/sistema_drops.py` pure logic interface.
- **Code layout**: Pure logic in `src/sistemas/sistema_drops.py` or `src/`, tested via `pytest`.

## Key Decisions Made
- [TBD]

## Artifact Index
- `.agents/teamwork_preview_spec_miner_survey_2/handoff.md` — Final specification report
- `.agents/teamwork_preview_spec_miner_survey_2/progress.md` — Progress tracker and heartbeat
