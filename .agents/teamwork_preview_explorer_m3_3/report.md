# Weapon Switching Exploration Report

## Overview
We investigated the player inventory, weapon slots, switching mechanics, and key handling to allow weapon switching with numeric keys 1, 2, and 3.

## Key Findings

### 1. Current Weapon Setup in `Jogador` (`src/entidades/jogador.py`)
- In `Jogador.__init__`:
  ```python
  self.armas = [Melee(), Pistola()]
  self.arma_especial = None
  self.drone = None
  ```
- Currently, both weapons are in `self.armas`, but there is no concept of `arma_ativa_idx` or `slot_ativo`.
- In `GameplayScene.loop()`:
  ```python
  if disparar_agora and self.jogador.vivo:
      for arma in self.jogador.armas:
          if isinstance(arma, Pistola):
              novos_tiros = arma.disparar(...)
              self.projeteis.extend(novos_tiros)
          elif isinstance(arma, Melee):
              arma.executar_ataque(...)
  ```
  Previously, whenever firing was triggered, **all** weapons in `self.armas` fired at once!

### 2. Required Behavior for Weapon Switching (Keys 1, 2, 3)
The requirements state:
> "3. Weapon Switching: Allow the player to switch between weapons using the numeric keys 1, 2, and 3."

- Slot 1 (Key '1'): Melee (Chave de Manutenção)
- Slot 2 (Key '2'): Pistola (Padrão de Fábrica)
- Slot 3 (Key '3'): Arma Especial / Arma 3 (e.g. `arma_especial` if equipped or Shotgun/Minigun/Rifle/etc. placeholder or if `arma_especial` is slot 3)
- When player presses '1', active weapon becomes Slot 1 (Melee).
- When player presses '2', active weapon becomes Slot 2 (Pistola).
- When player presses '3', active weapon becomes Slot 3 (Arma Especial, e.g. Minigun / Shotgun or `self.arma_especial` if available).
- Only the **active** selected weapon should fire when the player clicks!

### 3. Key Detection for '1', '2', '3'
In PPlay 2.0 / Pygame:
- In `Jogador.processar_input(self, teclado, mouse, dt, ...)` or `GameplayScene.loop()`:
  - `teclado.key_down("1")` or `teclado.key_down("2")` or `teclado.key_down("3")` (or `pygame.K_1`, `pygame.K_2`, `pygame.K_3`, `pygame.K_KP1`, `pygame.K_KP2`, `pygame.K_KP3`).
  - In `Jogador`:
    ```python
    self.slot_ativo = 2  # Default to Pistola (Slot 2) or Slot 1 (Melee)
    ```
    Method:
    ```python
    def selecionar_slot(self, slot: int):
        if slot in (1, 2, 3):
            self.slot_ativo = slot

    def obter_arma_ativa(self):
        if self.slot_ativo == 1:
            # Slot 1: Melee
            for a in self.armas:
                if isinstance(a, Melee) or getattr(a, "slot", None) == 1:
                    return a
            return self.armas[0] if self.armas else None
        elif self.slot_ativo == 2:
            # Slot 2: Pistola
            for a in self.armas:
                if isinstance(a, Pistola) or getattr(a, "slot", None) == 2:
                    return a
            return self.armas[1] if len(self.armas) > 1 else (self.armas[0] if self.armas else None)
        elif self.slot_ativo == 3:
            # Slot 3: Arma especial (if equipped)
            return self.arma_especial
        return None
    ```
  - In `processar_input` of `Jogador`:
    ```python
    if teclado is not None:
        if teclado.key_down("1") or teclado.key_pressed("1"): # or key_down
            self.selecionar_slot(1)
        elif teclado.key_down("2") or teclado.key_pressed("2"):
            self.selecionar_slot(2)
        elif teclado.key_down("3") or teclado.key_pressed("3"):
            self.selecionar_slot(3)
    ```

### 4. Firing Logic in `GameplayScene`
In `GameplayScene.loop`:
```python
if disparar_agora and self.jogador.vivo:
    arma_ativa = self.jogador.obter_arma_ativa()
    if arma_ativa is not None:
        if isinstance(arma_ativa, Melee):
            arma_ativa.executar_ataque(centro_jogador_x, centro_jogador_y, self.inimigos)
        else:
            novos_tiros = arma_ativa.disparar(
                centro_jogador_x, centro_jogador_y,
                mouse_mundo_x, mouse_mundo_y
            )
            if novos_tiros:
                self.projeteis.extend(novos_tiros)
```

### 5. HUD Inventory Slots Highlighting
In `src/cenas/gameplay.py` (`_desenhar_hud_tela`):
- Currently draws 4 inventory slots:
  - 1: Melee
  - 2: Pistol
  - 3: Espec
  - 4: Drone
- We can visually highlight the active slot (e.g. Slot 1, 2, or 3) with a colored border / background (e.g. `DOURADO` or `AZUL_CIANO` border) to make the active weapon immediately obvious to the player!

### 6. Tests Impact
- Existing tests in `tests/test_weapons.py` test `Pistola` and `Melee` directly in isolation.
- `tests/test_player.py` and `tests/test_gameplay_e2e.py` should be verified/updated if they rely on `jogador.armas` or shooting.
- We should ensure `jogador.armas` still contains `[Melee(), Pistola()]` for backward compatibility with any tests while adding `jogador.slot_ativo`, `jogador.selecionar_slot()`, and `jogador.obter_arma_ativa()`.

## Concrete Recommendations for Worker
1. `src/entidades/jogador.py`:
   - Add `self.slot_ativo = 2` (or 1, default active slot).
   - Add `selecionar_slot(self, slot: int)` and `obter_arma_ativa(self)`.
   - In `processar_input`: check for keys "1", "2", "3" to switch `self.slot_ativo`.
2. `src/cenas/gameplay.py`:
   - Update firing dispatch to fire only `self.jogador.obter_arma_ativa()`.
   - Update `_desenhar_hud_tela` to highlight the active weapon slot (1, 2, or 3).
