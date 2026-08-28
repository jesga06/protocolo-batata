## 2026-08-28T15:45:21Z
You are Spec Miner 2 for the Drop System pure logic specification in Protocolo: Batata.

MANDATORY INPUTS:
- Read ORIGINAL_REQUEST.md at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\ORIGINAL_REQUEST.md
- Read architecture cache at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\architecture_cache.md
- Read CONFIGURACOES.md at: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\CONFIGURACOES.md

YOUR WORKING DIRECTORY:
c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_spec_miner_survey_2

OBJECTIVE:
Specify all requirements and edge cases for the Drop System pure logic in `src/sistemas/sistema_drops.py`:
- 10s total lifetime
- Eligible for enemy capture after 1s (grace period of 1.0s before enemies can scavenge it; player can pick it up immediately)
- Drop expiration when lifetime reaches 0 (or >= 10s elapsed)
- State transitions (active, expired, collected_by_player, collected_by_enemy)
- Drop types / payloads (XP, health, potato seeds, configs, etc.)
- Update method with delta time (dt)
- Pure decoupled logic interface (no Pygame/PPlay dependencies required for pure logic unit testing).

Produce a detailed specification report in `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_spec_miner_survey_2\handoff.md` and send a message when done.
