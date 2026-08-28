## 2026-08-28T15:45:21Z
You are Spec Miner 3 for the Scavenger AI pure logic specification in Protocolo: Batata.

MANDATORY INPUTS:
- Read ORIGINAL_REQUEST.md at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\ORIGINAL_REQUEST.md
- Read architecture cache at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\architecture_cache.md
- Read CONFIGURACOES.md at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\CONFIGURACOES.md

YOUR WORKING DIRECTORY:
c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_spec_miner_survey_3

OBJECTIVE:
Specify all requirements and mathematical/algorithmic edge cases for the Scavenger AI selector in `src/sistemas/sistema_scavenger.py`:
- Only 1 enemy globally can capture a drop at any time (or only 1 designated scavenger per drop / globally).
- Target enemy is selected pseudo-randomly among candidates.
- Candidate filtering rules:
  1. Exclude enemies that are too far (distance > max_scavenge_distance / cutoff radius).
  2. Exclude the 3 closest enemies to the drop (sorted by Euclidean distance ascending, slice [3:]).
  3. If after exclusions, candidate pool is empty -> return None / no scavenger assigned.
  4. If candidate pool has candidates -> pseudo-random selection (deterministic seed support for testing).
- Lifecycle / Scavenger state handling: what happens if the assigned scavenger enemy dies, or drop despawns, or scavenger reaches pickup radius.
- Pure decoupled logic interface (no Pygame/PPlay dependencies required for pure logic unit testing).

Produce a detailed specification report in `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_spec_miner_survey_3\handoff.md` and send a message when done.
