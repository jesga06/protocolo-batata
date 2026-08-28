## 2026-08-28T15:46:35Z

You are the Implementation Worker for Protocolo: Batata.
Your working directory: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_worker_m3

Target files to read:
- ORIGINAL_REQUEST.md: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\ORIGINAL_REQUEST.md
- Architecture Cache: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\architecture_cache.md
- PROJECT.md: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\PROJECT.md
- Explorer Reports:
  - UI Text: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_m3_1\report.md
  - Inputs: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_m3_2\report.md
  - Weapons: c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_explorer_m3_3\report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Core Tasks:
1. Modify UI Text:
   - In `src/cenas/menu_principal.py`, use raw Pygame (`pygame.font.SysFont` or `pygame.font.Font` and `rect.centerx`) INSTEAD of PPlay's text module to perfectly center the main menu title, menu options, selection highlight rect, and footer instructions horizontally on the screen (`centerx = LARGURA_TELA // 2`).
   - In `src/cenas/gameplay.py`, use raw Pygame font and `rect.centerx` to perfectly center the HUD timer (`texto_tempo`), the kill counter (`texto_abates`), and modal overlays (pause and game over) horizontally on the screen (`centerx = LARGURA_TELA // 2`).
   - In `src/cenas/gameplay.py`, highlight the active weapon inventory slot (slot 1, 2, or 3) with a distinct border/glow (e.g. `DOURADO` or `AZUL_CIANO`).

2. Modify Inputs:
   - Remove auto-fire. Weapons must ONLY fire when detecting an explicit mouse click (catch `pygame.MOUSEBUTTONDOWN` via `self.mouse.button_down(1)` or event checking).
   - Continuous mouse holding must NOT auto-fire.

3. Weapon Switching:
   - In `src/entidades/jogador.py`, implement weapon slot management:
     - `self.slot_ativo = 2` (or 1, default active slot)
     - `selecionar_slot(self, slot: int)` for slots 1, 2, 3
     - `obter_arma_ativa(self)` returning the active weapon instance for the current slot (Slot 1: Melee, Slot 2: Pistola, Slot 3: `self.arma_especial` if present)
     - In `processar_input(self, teclado, mouse, dt, ...)`: check numeric keys '1', '2', '3' and switch active slot.
   - In `src/cenas/gameplay.py`, update firing logic to fire ONLY the currently active weapon returned by `self.jogador.obter_arma_ativa()`.

4. Verification & Testing:
   - Create unit/integration tests in `tests/test_ui_and_weapons_m3.py` to verify:
     a) UI text centering math (`rect.centerx == LARGURA_TELA // 2`)
     b) Click-to-shoot input detection (no firing without click)
     c) Weapon switching with keys 1, 2, 3 (only active weapon fires)
   - Run the entire test suite (`python -m unittest discover tests`) and verify all tests pass with 0 errors.
