# Dispatch Record

## 2026-08-28T15:50:11Z
Project: Protocolo Batata (Python 2D Shooter)
Parent Conversation ID: 3a372232-f8ee-48c6-9570-8b0fb40c25f3

Tasks:
1. Modify UI Text: Use raw Pygame (`pygame.font` and `rect.centerx`) INSTEAD of PPlay's text module to perfectly center the main menu texts, the HUD timer, and the kill counter horizontally on the screen.
2. Modify Inputs: Remove auto-fire. Weapons must ONLY fire when detecting an explicit mouse click (catch `pygame.MOUSEBUTTONDOWN`).
3. Weapon Switching: Allow the player to switch between weapons using the numeric keys 1, 2, and 3.

Constraints & Notes:
- The project uses PPlay 2.0 as the base engine. DO NOT remove PPlay entirely. PPlay remains the core engine.
- You have blanket autonomy to execute all tasks and coordinate any necessary subagents/workers.
- Run tests and verify the game launches and mechanics work cleanly before reporting completion.
- When finished, write your handoff.md and send a completion message back to the Sentinel.
