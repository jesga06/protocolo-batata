## 2026-08-28T14:55:18Z

<USER_REQUEST>
You are Survey Explorer 3 (Enemy Systems & Scene Flow Specialist).
Your Identity: teamwork_preview_spec_miner
Your Working Directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_survey_2_3
Project Workspace Root: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata

MANDATORY RULES:
1. Read the Authoritative Request at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\ORIGINAL_REQUEST.md
2. Read the Architecture Cache at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\architecture_cache.md
3. USER DIRECTIVE: You have blanket autonomous authorization to explore, read, test/run scripts if needed, and extract full requirements without asking for permission.

YOUR MISSION:
Extract and document the technical specification for Enemy Spawning, Enemy AI, and Game Scene Flow for Phase 0 & Phase 1.
Investigate:
1. Read `GDD.md`, `gdd lab batata.md`, `s1.md` through `s6.md`, `CONFIGURACOES.md`.
2. Extract Enemy specifications for Phase 1:
   - Standard enemy archetype (Potato bug / basic crawler): Base HP, Base Speed, Contact Damage, Drop rate / XP value.
   - AI Behavior: Beeline towards player (calculate unit vector from enemy to player and move each frame).
   - Spawning system: Spawn timer, spawn location (just outside the screen edges/viewport radius so enemies enter screen naturally), spawn scaling/intervals.
   - Death & Destruction: When enemy HP <= 0, enemy dies, score/kill counter increments, optionally drops placeholder gem/XP.
3. Scene & UI layout for Phase 0/1:
   - Minimal HUD: Player HP bar / current HP, Score / Wave / Timer / Kill count.
   - Scene architecture: `main.py` -> `cenas/gameplay.py` (and placeholder menu if needed).

Deliverable:
Write a comprehensive report to `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_survey_2_3\handoff.md` and send a completion message back to parent.
</USER_REQUEST>
