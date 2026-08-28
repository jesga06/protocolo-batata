# BRIEFING — 2026-08-28T15:47:30Z

## Mission
Specify pure decoupled logic, candidate selection algorithms, state machine, and edge cases for the Scavenger AI system (`src/sistemas/sistema_scavenger.py`).

## 🔒 My Identity
- Archetype: Specification Miner
- Roles: Spec Miner 3 (Scavenger AI selector pure logic)
- Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_spec_miner_survey_3
- Original parent: 21fb4cb2-d6fa-4593-9395-4d1409debecc
- Milestone: Scavenger AI Pure Logic Specification

## 🔒 Key Constraints
- Pure decoupled logic interface (zero Pygame/PPlay dependencies required for pure logic unit testing).
- Only 1 enemy globally can capture/be designated for a drop at any time.
- Target enemy selection rules:
  1. Exclude enemies too far (> max_scavenge_distance / cutoff radius).
  2. Exclude the 3 closest enemies to the drop (sorted by Euclidean distance ascending, slice [3:]).
  3. If candidate pool is empty -> return None / no scavenger assigned.
  4. Pseudo-random selection among remaining candidate pool with deterministic seed support for testing.
- Lifecycle / Scavenger state handling: what happens when assigned scavenger dies, drop despawns/is collected, or scavenger reaches pickup radius.
- Read-only on codebase: do NOT edit project files.

## Current Parent
- Conversation ID: 21fb4cb2-d6fa-4593-9395-4d1409debecc
- Updated: 2026-08-28T15:47:30Z

## Task Summary
- **What to build**: Specification report for Scavenger AI selector pure logic in `src/sistemas/sistema_scavenger.py`.
- **Success criteria**: Comprehensive specification with full mathematical/algorithmic rules, class/function signatures, edge cases, state machine, and test cases.
- **Interface contracts**: `CONFIGURACOES.md` (#15 `coleta_inimiga`), `PLANO_DE_IMPLEMENTACAO.md`, `ORIGINAL_REQUEST.md`.
- **Code layout**: `src/sistemas/sistema_scavenger.py`.

## Key Decisions Made
- Scavenger logic operates on duck-typed data objects (x, y, vivo/alive, id) to ensure 100% headless testability without Pygame/PPlay initialization.
- Random selection accepts an optional `random.Random` instance or seed to guarantee 100% deterministic unit testing.
- State machine handles singleton global scavenger lifecycle events: `SCAVENGER_ASSIGNED`, `SCAVENGER_DIED`, `DROP_INVALIDATED`, `DROP_COLLECTED_BY_ENEMY`, `CONFIG_DISABLED`.

## Artifact Index
- `.agents/teamwork_preview_spec_miner_survey_3/DISPATCH.md` — Prompt and assignment log
- `.agents/teamwork_preview_spec_miner_survey_3/BRIEFING.md` — Persistent situational awareness
- `.agents/teamwork_preview_spec_miner_survey_3/progress.md` — Progress tracker and heartbeat
- `.agents/teamwork_preview_spec_miner_survey_3/handoff.md` — Final 5-component specification report
