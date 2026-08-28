# Input Mechanics Exploration Report

## Overview
We investigated the input event handling, auto-fire mechanism, and mouse button event processing across `src/main.py`, `src/cenas/gameplay.py`, `src/entidades/jogador.py`, `src/armas/`, and PPlay 2.0 framework (`PPlay.mouse.Mouse`, `PPlay.window.Window`).

## Key Findings

### 1. Current Auto-fire & Firing Trigger in `src/cenas/gameplay.py`
In `src/cenas/gameplay.py` lines 63 and 157-172:
- `self.auto_fire_ativo = True` is set by default in `__init__`.
- Line 157:
  ```python
  disparar_agora = self.mouse.button_pressed(1) or self.auto_fire_ativo
  ```
  `button_pressed(1)` checks `pygame.mouse.get_pressed()[0]`, which returns `True` continuously as long as the mouse button is held down. Combined with `or self.auto_fire_ativo`, weapons were firing automatically on cooldown without any click requirement.

### 2. Explicit Click Requirement (`pygame.MOUSEBUTTONDOWN`)
The requirement states:
> "Remove auto-fire. Weapons must ONLY fire when detecting an explicit mouse click (catch `pygame.MOUSEBUTTONDOWN`)."

In PPlay 2.0:
- `self.mouse.button_down(1)` (or `self.mouse.button_down(Mouse.LEFT)`) checks `window.eventos` for `evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1`.
- Alternatively, direct check of `pygame.event` or `self.janela.eventos` for `pygame.MOUSEBUTTONDOWN` with button 1 (left click).
- When `self.mouse.button_down(1)` or `pygame.MOUSEBUTTONDOWN` occurs, `disparar_agora` is set to `True` for that frame only.
- Continuous mouse holding (`button_pressed`) will NOT trigger firing anymore; each shot requires an explicit fresh click (`button_down(1)` / `pygame.MOUSEBUTTONDOWN`).

### 3. Gear Button Interaction vs Weapon Firing
Note that clicking on the gear icon (pause button at (752, 16, 32x32)) in `gameplay.py` also checks `self.mouse.button_down(1)`:
```python
if self.mouse.button_down(1):
    if 752 <= mx <= 784 and 16 <= my <= 48:
        self.pausado = True
        return
```
Because `return` is called immediately when clicking the gear icon, it will not fire a weapon when pausing. This is clean and avoids unintended shooting when interacting with HUD buttons.

### 4. Direct Pygame Event Handling vs PPlay Window
In PPlay 2.0:
- `janela.update()` processes `pygame.event.get()` and populates `janela.eventos`.
- During `SceneManager.run()`, `janela.eventos` contains all `pygame.event.Event` instances from that frame, including `pygame.MOUSEBUTTONDOWN` and `pygame.KEYDOWN`.
- `self.mouse.button_down(1)` inspects `self.janela.eventos` for `evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1`.
- In `gameplay.py`, we can also directly check:
  ```python
  clique_disparo = False
  for evento in self.janela.eventos:
      if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
          clique_disparo = True
          break
  ```
  or simply `self.mouse.button_down(1)`. Both are 100% equivalent since `self.mouse.button_down(1)` iterates over `self.janela.eventos`.

### 5. Weapon Update vs Weapon Firing
- Weapons' cooldown timers (`arma.update(dt)`) continue to tick down in `jogador.update(dt)`.
- When an explicit mouse click (`pygame.MOUSEBUTTONDOWN`) is caught, we check `arma.pode_atirar()`. If ready, it fires and resets `tempo_recarga_restante = cooldown`.
- If the player clicks while cooldown is active, the click is ignored (no buffer queue) and player must click again after cooldown expires, exactly as standard semi-auto / explicit-click mechanics work.

## Concrete Recommendations for Worker
1. In `src/cenas/gameplay.py`:
   - Remove `self.auto_fire_ativo = True` (or set `self.auto_fire_ativo = False` and remove auto-fire logic).
   - Change `disparar_agora` from `self.mouse.button_pressed(1) or self.auto_fire_ativo` to:
     ```python
     disparar_agora = self.mouse.button_down(1)
     ```
     (or checking `any(e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 for e in self.janela.eventos)`).
2. Ensure no auto-fire remains anywhere in `gameplay.py` or `jogador.py`.
