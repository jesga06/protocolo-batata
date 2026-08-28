# UI Text Exploration Report

## Overview
We investigated the UI text rendering across the codebase to identify where PPlay's text rendering is used and how to replace it with raw Pygame font rendering (`pygame.font` and `rect.centerx`) for horizontal centering.

## Findings

### 1. Window & Screen Surface Access
In PPlay 2.0 (`PPlay.window.Window`):
- `self.janela.screen` or `Window.get_instance().screen` provides direct access to the Pygame virtual surface (`pygame.Surface`).
- `self.janela.draw_text(...)` internally uses `pygame.font.SysFont` and blits at `(x, y)`. But since string widths vary, using hardcoded offsets (`LARGURA_TELA // 2 - 100`) leads to inaccurate centering.
- Using raw `pygame.font.SysFont(None, tamanho)` or `pygame.font.Font(None, tamanho)`:
  ```python
  fonte = pygame.font.SysFont(None, tamanho) # or pygame.font.Font(None, tamanho)
  texto_surf = fonte.render(texto, True, cor)
  texto_rect = texto_surf.get_rect(centerx=LARGURA_TELA // 2, y=y) # or centery
  screen.blit(texto_surf, texto_rect)
  ```

### 2. Files with Text Elements to Center
1. **`src/cenas/menu_principal.py`**:
   - Title: `TITULO_JOGO` (currently `self.janela.draw_text(TITULO_JOGO, LARGURA_TELA // 2 - 100, 110, tamanho=36, cor=DOURADO)`) -> Render with `pygame.font`, get `rect(centerx=LARGURA_TELA // 2, top=110)`.
   - Menu Options: `opcoes = ["JOGAR [ENTER]", "CONFIGURAÇÕES [C]", "CRÉDITOS [K]", "SAIR [ESC]"]`.
     - Highlight box rect: centered with `centerx=LARGURA_TELA // 2`.
     - Option text: rendered with `pygame.font`, `rect.centerx = LARGURA_TELA // 2, centery = y + 12`.
   - Footer Instructions: "PPlay 2.0 Engine | Use [W/S] ou [Setas] para navegar e [ENTER] para confirmar" -> `rect.centerx = LARGURA_TELA // 2, bottom = ALTURA_TELA - 20`.

2. **`src/cenas/gameplay.py`**:
   - `_desenhar_hud_tela`:
     - HUD Timer: `texto_tempo = f"{minutos:02d}:{segundos:02d}"` -> raw pygame font, `rect.centerx = LARGURA_TELA // 2, top = 14`.
     - Kill Counter: `texto_abates = f"Abates: {self.abates}"` -> raw pygame font, `rect.centerx = LARGURA_TELA // 2, top = 40`.
   - Also check overlays in `gameplay.py`:
     - `_desenhar_overlay_pausa`: "JOGO PAUSADO", "[ESC] Continuar Partida", "[M] Menu Principal" -> horizontally centered with `centerx=LARGURA_TELA // 2`.
     - `_desenhar_overlay_game_over`: "PROTOCOLO FALHOU", subtitle, survival time, total kills, score, restart prompt -> horizontally centered with `centerx=LARGURA_TELA // 2`.

### 3. Font Helper Utility Recommendation
To avoid creating fonts from scratch every frame, a caching function or module-level font dictionary / helper in `src/utils/` (or directly within scenes) can be used:
```python
_font_cache = {}
def render_texto_centralizado(screen, texto, y, tamanho=20, cor=(255, 255, 255), center_x=LARGURA_TELA // 2, bold=False):
    key = (tamanho, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("Arial", tamanho, bold=bold)
    fonte = _font_cache[key]
    surf = fonte.render(texto, True, cor)
    rect = surf.get_rect(centerx=center_x, top=y)
    screen.blit(surf, rect)
    return rect
```
Or directly using `pygame.font.SysFont` / `pygame.font.Font(None, ...)` with `surf.get_rect(centerx=...)`.

### 4. Tests Impact
Checking `tests/`:
- Existing tests test logic, weapons, enemy spawns, headless scene loop.
- No tests break from switching text rendering to `pygame.font` + `rect.centerx`.
- In headless mode, `pygame.font` works as long as `pygame.font.init()` is called (which Pygame/PPlay initializes).

## Recommendation for Worker
1. In `src/cenas/menu_principal.py`: Replace `self.janela.draw_text(...)` for title, menu options, and footer with raw Pygame font rendering using `rect.centerx = LARGURA_TELA // 2`.
2. In `src/cenas/gameplay.py`: In `_desenhar_hud_tela`, replace `self.janela.draw_text` for `texto_tempo` and `texto_abates` with `pygame.font` rendered surfaces aligned with `rect.centerx = LARGURA_TELA // 2`. Also update pause and game over overlays to be centered with `rect.centerx`.
