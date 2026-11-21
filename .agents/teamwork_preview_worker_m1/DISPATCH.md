## 2026-08-28T19:45:56Z
You are Worker M1 for Milestone 1 (Phase 4 UI: Level Up 3-Card Modal & In-Game Settings Menu) in "Protocolo: Batata".
Working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_worker_m1\

Read first:
1. `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\ORIGINAL_REQUEST.md` (Specifically 2026-08-28T19:41:02Z R1 and R2)
2. `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_m1\handoff.md`
3. `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\CONFIGURACOES.md`
4. `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\s5.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Tasks:
1. Implement `src/ui/modal_level_up.py` (and/or `src/cenas/level_up.py`):
   - Interactive 3-Card Draw modal triggered when player levels up via `SistemaXP`.
   - Pauses gameplay physics/enemies/spawns/timers.
   - Draws 3 random locked configurations from `GerenciadorConfiguracoes.obter_bloqueadas()`.
   - Visual cards rendered with `assets/ui/card_upgrade_bg.png`, config icons from `assets/ui/icones_configs/icon_<id>.png`, title, category, buffs (green/yellow), nerfs/sacrifices (red/orange).
   - Selection via mouse click on card or keyboard keys `1`, `2`, `3`.
   - On selection: unlocks config in `GerenciadorConfiguracoes`, immediately recalculates and applies modifiers in real time to player, weapons, and game.
   - Fallback consumable cards for Level 20 / when all 20 configurations are already unlocked:
     - Full Heal (+100 HP / restore to max)
     - Vitality (+20 Max HP and heal 20)
     - Energy Surge (Heal 50% HP)
   - Handles multi-level queues cleanly if multiple level-ups occur in rapid succession.
2. Implement `src/ui/menu_configs.py` (and/or `src/cenas/menu_configs.py`):
   - Accessible in-game via gear button at `(752, 16)`, or keys `ESC` / `C`, and from `MenuPrincipalScene`.
   - Pauses gameplay when opened in-game.
   - Tab 1: Gameplay Configs Tab — displays the 20 unlockable configs grouped by category. Unlocked configs can be toggled/adjusted freely by the player during the run; locked configs are shown disabled/grayed-out `[🔒 BLOQUEADO]`. Changing values immediately updates `GerenciadorConfiguracoes` and live gameplay stats.
   - Tab 2: System Settings Tab — always available (no gameplay buffs): Master Volume, Music Volume, SFX Volume sliders (adjusts `pygame.mixer`), S4 Colorblind filter selector, S5 Global Scale selector (100%, 125%, 150%).
   - Close button / resume.
3. Integrate into `src/cenas/gameplay.py` and `src/cenas/menu_principal.py`:
   - Initialize `self.gerenciador_config = GerenciadorConfiguracoes()`.
   - Connect `SistemaXP` callback to Level Up modal.
   - Connect gear button and ESC/C keys to Settings Menu.
   - Apply calculated `ModificadoresGameplay` dynamically.
4. Write comprehensive unit tests in `tests/test_ui_level_up.py` and `tests/test_ui_menu_configs.py`.
5. Run tests using `.\.venv\Scripts\python.exe -m unittest discover tests` with headless environment (`os.environ["SDL_VIDEODRIVER"] = "dummy"`).
6. Write your completion report in `.agents/teamwork_preview_worker_m1/handoff.md` and send a message back.

## 2026-08-28T19:49:54Z
USER DIRECTIVE UPDATE (Tier 1 Authority) on Level Up Modal Architecture:
1. **Standard Level Ups (Levels not divisible by 5)**: Offer 3 tier-scaled utility/consumable cards (e.g., +HP heal, instant XP burst, temporary stat buffs, random weapon drops with ammo scaled to level, drone spawns). Levels 1-2 give modest buffs; higher levels give greater boosts.
2. **Milestone Levels (Every 5 levels: Lvl 5, 10, 15, 20...)**: The MIDDLE CARD (Card 2 / index 1) is replaced by an unlockable Gameplay Configuration card from locked configs.
3. **Pity Buffer**: If the player does not pick the configuration on a milestone level, it remains buffered in the middle slot on subsequent level ups until selected.
Implement this tiered card generation & milestone/pity logic in `modal_level_up.py` and ensure tests in `test_ui_level_up.py` validate standard level up consumable tiers, milestone level middle card config placement, and pity buffer persistence.
