# Technical Specification & Survey Report: PPlay Engine & Procedural Asset Architecture (Phase 0)

## Executive Summary
This report delivers the authoritative technical survey and specification for **Phase 0 (Base Architecture & Procedural Assets)** of **Protocolo: Batata**, probing the PowerPPlay 2.0 framework (`.venv/Lib/site-packages/PPlay`), game design documents (`GDD.md`, `s1.md`-`s6.md`, `CONFIGURACOES.md`), and procedural asset generation requirements with `Pillow` and Python's `wave` module.

---

## 1. Observation

### 1.1 Environment & Library Structure
- [Observed] `.venv/Lib/site-packages/PPlay` contains 28 module files implementing PowerPPlay 2.0 (authored by Kauã Neves Jesus de Paula, UFF 2026, building upon PPlay 1.0 by Esteban Clua et al.).
- [Observed] Python environment is Python 3.15.0b3 with `pygame-ce` (version 2.5.8, SDL 2.32.10) and `Pillow` (version 12.3.0).
- [Observed] `PPlay/__init__.py` (lines 24–28) executes `retro_bridge.aplicar_retrocompatibilidade()` automatically on import, binding legacy methods (`Window.width`, `Window.height`, `Window.get_keyboard`, `Window.get_mouse`, `Window.draw_text`, `Mouse.is_button_pressed`, `Animation.set_sequence_time`, etc.).

### 1.2 PPlay Core Modules & Method Signatures
1. **`PPlay.window.Window`** (`window.py`, 164 lines):
   - Singleton pattern: `Window(largura_virtual=800, altura_virtual=600, titulo="Power PPlay 2.0", resizavel=True, pixel_art=True)`.
   - `Window.get_instance()` returns the singleton instance.
   - `Window.get_screen()` returns `self.screen` (virtual buffer `pygame.Surface((largura, altura))`).
   - `w.update()`:
     - Calculates aspect ratio preserving virtual scale: `ratio = min(largura_real / self.largura, altura_real / self.altura)`.
     - Draws scaled buffer centered with letterboxing on `self.real_screen`.
     - Flips display (`pygame.display.flip()`).
     - **Clears virtual screen**: `self.screen.fill(self.cor_fundo)` (resets canvas for the next frame).
     - Polls events into `self.eventos`: handles `QUIT` (`self.close()`) and `KEYDOWN F11` (`pygame.display.toggle_fullscreen()`).
     - Computes delta time: `self._delta_time = self._clock.tick() / 1000.0`.
   - `w.delta_time()` returns `_delta_time` (float seconds).
   - `w.get_fps()` returns `_clock.get_fps()`.
   - `w.set_background_color(cor)` sets clear color (tuple RGB or string name).
   - `w.draw_text(texto, x, y, tamanho=20, cor=(255, 255, 255), fonte="Arial")`.
   - `w.screen_to_virtual_coords(px, py)` maps physical window pixels to virtual canvas coordinates.

2. **`PPlay.gameobject.GameObject`** (`gameobject.py`, 79 lines):
   - Base class attributes: `x`, `y`, `width`, `height`, `scale_x=1.0`, `scale_y=1.0`, `rotation=0.0`, `transparency=255`.
   - `collided(outro_obj)`: AABB overlap check (`x < o.x + o.w and x + w > o.x and y < o.y + o.h and y + h > o.y`).
   - Transform methods: `set_position(x, y)`, `get_position()`, `set_scale(sx, sy=None)`, `get_scale()`, `set_rotation(deg)`, `get_rotation()`, `set_transparency(0..255)`, `get_transparency()`.

3. **`PPlay.gameimage.GameImage`** (`gameimage.py`, 88 lines):
   - Inherits `GameObject`.
   - Memory cache: `GameImage._resource_cache = {}` keyed by filepath.
   - `draw()`: Applies alpha, rotation, scale and blits directly to `Window.get_screen()` at `(self.rect.x, self.rect.y)`.
   - **Crucial Behavior**: `GameImage.draw()` does **NOT** apply `Camera` coordinates (always draws in screen space).

4. **`PPlay.animation.Animation`** (`animation.py`, 116 lines):
   - Inherits `GameImage`.
   - Splits spritesheet width by `total_frames`: `self.width = self.width / total_frames`.
   - Frame timing: `self.tempo_por_frame = 0.1` (10 FPS default), controlled via `Window.delta_time()`.
   - `update()`: Advances frames based on accumulated delta time.
   - `draw()`: Subsurfaces active frame, applies transforms, and **transforms coordinates using `Camera.get_instance()`** (`draw_x = cam.transform_x(self.x) if cam else self.x`).
   - Methods: `play()`, `stop()`, `pause()`, `set_total_duration(ms)`, `set_curr_frame(idx)`, `get_curr_frame()`, `set_loop(bool)`.

5. **`PPlay.sprite.Sprite`** (`sprite.py`, 70 lines):
   - Inherits `Animation`.
   - Initializer: `Sprite(caminho_imagem, total_frames=1)`.
   - Traditional movement methods: `move_key_x(vel)`, `move_key_y(vel)`, `move_x(vel)`, `move_y(vel)`.
   - Physics integration: `setup_physics(engine)`, `update_physics(lista_solidos)`.

6. **`PPlay.keyboard.Keyboard`** (`keyboard.py`, 58 lines):
   - Key lookup mapping: `"LEFT"`, `"RIGHT"`, `"UP"`, `"DOWN"`, `"SPACE"`, `"ESC"`, `"ENTER"`, `"LSHIFT"`, or any key string (`"w"`, `"a"`, `"s"`, `"d"`, etc. via `pygame.K_<key>`).
   - `key_pressed(key)`: Continuous state check via `pygame.key.get_pressed()`.
   - `key_down(key)`: Discrete single-frame press check by iterating over `Window.get_instance().eventos`.

7. **`PPlay.mouse.Mouse`** (`mouse.py`, 52 lines):
   - Constants: `Mouse.LEFT = 1`, `Mouse.MIDDLE = 2`, `Mouse.RIGHT = 3`.
   - `get_position()`: Returns `(vx, vy)` virtual canvas coordinates via `Window.screen_to_virtual_coords()`.
   - `button_pressed(button)`: Continuous state via `pygame.mouse.get_pressed()`.
   - `button_down(button)`: Discrete single-frame click via `Window.get_instance().eventos`.
   - `is_over_object(obj)`: Checks if mouse virtual coordinate is within `(obj.x, obj.y, obj.width, obj.height)`.

8. **`PPlay.sound.SoundManager` / `Sound` / `Music`** (`sound.py`, 113 lines):
   - `SoundManager.inicializar()`: `pygame.mixer.pre_init(44100, -16, 2, 512)` and `pygame.mixer.init()`.
   - `SoundManager.set_sfx_volume(volume_0_to_100)`: Scales all cached sounds in `_sfx_cache`.
   - `SoundManager.set_music_volume(volume_0_to_100)`: Sets `pygame.mixer.music.set_volume()`.
   - `Sound(caminho)`: Loaded in RAM for immediate SFX playback. `play(repeticoes=0)`, `stop()`, `set_volume(pct)`.
   - `Music(caminho)`: Streamed BGM. `play(loops=-1, fade_in_ms=2000)`, `stop(fade_out_ms=1000)`, `pause()`, `unpause()`, `is_playing()`.

9. **`PPlay.scenemanager.Scene` / `SceneManager`** (`scenemanager.py`, 68 lines):
   - `Scene`: Base class storing `self.janela`, `self.teclado`, `self.mouse`. Requires `loop()` and `draw()`.
   - `SceneManager.change_scene(next_scene)`: Sets `_current_scene`.
   - `SceneManager.run()`: Calls `_current_scene.loop()` then `_current_scene.draw()`.

10. **Supplementary Modules**:
    - `Camera` (`camera.py`): Singleton with `follow(target, suavizacao=0.1)`, `set_world_bounds(w, h)`, `transform_x()`, `transform_y()`.
    - `Collision` (`collision.py`): `collided(o1, o2)` (AABB), `collided_circle(o1, o2)`, `perfect_collision(o1, o2)` (pixel mask overlap), `raycast()`.
    - `ObjectGroup` (`object_group.py`): Container for batch update, draw, physics update, and collision testing.
    - `ScreenEffects` (`effects.py`): Class methods `shake(intensidade, duracao)`, `flash(cor, duracao)`, `update()`, `apply_to_camera()`, `draw_flash()`.
    - `LightingSystem` (`effects.py`): Dynamic darkness fog surface with alpha lights blended via `BLEND_RGBA_ADD` and `BLEND_RGBA_MULT`.
    - `ParticleEmitter` (`particles.py`): Particle emitter with fadeout alpha, camera support, and `explodir(qtd)`.
    - `Button` & `ProgressBar` (`uikit.py`): Hover/click UI button and fillable progress bar.
    - `Timer` (`timer.py`): `after(sec, func, *args)`, `every(sec, func, *args)`, `update()`.
    - `Tween` (`tween.py`): Easing property interpolation (`to(obj, attr, val, dur, tipo)`).

---

## 2. Logic Chain

1. **Window Update & Loop Lifecycle**:
   - `Window.update()` clears the canvas buffer (`self.screen.fill(self.cor_fundo)`) at the end of every frame.
   - Therefore, in the game loop, a scene's `draw()` method must draw onto `Window.get_screen()` during the frame, and `Window.update()` presents that frame to the screen and prepares the canvas for the next frame.
   - `Window.update()` also fetches events into `Window.eventos`, which `Keyboard.key_down()` and `Mouse.button_down()` rely on.
2. **Camera & Coordinate System Separation**:
   - World objects (Player, Enemies, Projectiles, Drops, Floor Tiles) that inherit `Sprite` or `Animation` automatically apply `Camera.get_instance().transform_x / transform_y` when drawn.
   - Screen-space objects (HUD, Buttons, ProgressBars, Pause Overlay, Config Cards) must be drawn in screen coordinates without world translation. Because `GameImage` does not transform by `Camera`, HUD icons drawn with `GameImage` or direct pygame surfaces/buttons will remain anchored to the viewport.
3. **Asset Generation & File Loading Resilience**:
   - In `gameimage.py`, loading non-existent files with `pygame.image.load()` in modern Python / pygame-ce raises `FileNotFoundError` (subclass of `OSError`), not `pygame.error`.
   - Therefore, missing asset files will raise an unhandled exception rather than triggering PPlay's magenta fallback square.
   - `tools/gerador_assets.py` must proactively generate **all** asset files required by Phase 0, Phase 1, and future systems before the game initializes.
4. **FPS Cap & Time Step Control**:
   - `Window._clock.tick()` in `window.py` is called with 0 args by default.
   - To enforce the `fps_cap` configuration (15, 30, 45, 60 FPS), the game loop must either pass the desired framerate to clock tick or throttle frame presentation accordingly.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Window | Resizable Virtual Canvas | Letterboxed scaling with aspect ratio preservation and pixel art nearest-neighbor rendering | Virtual `(w, h)`, `pixel_art=True` | Scaled display on `real_screen` | Fallback blit on transform error | `PPlay/window.py:85-119` |
| 2 | Window | Coordinate Translation | Translates physical window cursor coordinates to virtual canvas coordinates | `(px, py)` screen coords | `(vx, vy)` virtual coords | Clamps/returns identity if minimized | `PPlay/window.py:154-160` |
| 3 | Window | Event Polling & Shortcuts | Captures Pygame events, manages `QUIT`, and toggles fullscreen on F11 | OS events / F11 key | Updates `self.eventos` | Calls `sys.exit()` on QUIT | `PPlay/window.py:123-130` |
| 4 | Input | Discrete Key Down Detection | Detects single-frame key presses by scanning window events | Key string or code (e.g. `"SPACE"`, `"ESC"`, `"w"`) | `bool` (True only on frame pressed) | Returns `False` on unknown key | `PPlay/keyboard.py:44-51` |
| 5 | Input | Virtual Mouse Interaction | Mouse position, continuous press, single-frame click, and AABB object hover | Button ID (`1, 2, 3`), GameObject | `(vx, vy)`, `bool` | Returns `False` if out of bounds | `PPlay/mouse.py:26-47` |
| 6 | Graphics | Resource Cache | Caches loaded image surfaces in memory to prevent duplicate disk reads | Image file path | `pygame.Surface` (convert_alpha) | Raises `FileNotFoundError` if missing | `PPlay/gameimage.py:32-50` |
| 7 | Graphics | Camera-Aware Sprites | Animated spritesheet slicing with delta-time updates and automatic camera offset | Image path, `total_frames`, `loop` | Sliced frame drawn at camera offset | Clamps to last frame if not looping | `PPlay/animation.py:29-113` |
| 8 | Audio | Sound & Music Management | RAM-cached SFX playback with volume scaling, and streamed BGM with fade-in/out | Audio path, volume (0-100), loops | Audio playback | Silent fail / log error if missing | `PPlay/sound.py:21-113` |
| 9 | Scene | Scene Lifecycle State Machine | Base `Scene` with `loop()` / `draw()` and `SceneManager` switching | `Scene` subclass instances | Executes active scene lifecycle | Red screen fallback if no scene | `PPlay/scenemanager.py:20-68` |
| 10 | Camera | Smooth Follow & World Bounds | Smooth lerp camera tracking player with world boundary clamping | Target GameObject, `suavizacao` (0.1) | Modifies `Camera.x, Camera.y` | Clamps to world bounds | `PPlay/camera.py:38-67` |
| 11 | Effects | Screen Shake & Damage Flash | Camera shake offset and colored screen flash overlays | Intensity, duration, RGB color | Screen offsets & overlay blit | Degrades gracefully when expired | `PPlay/effects.py:23-69` |
| 12 | Effects | Dynamic Lighting System | Darkness fog surface with circular alpha light punches (`BLEND_RGBA_ADD/MULT`) | Opacity, light tuples `(x, y, r, int)` | Darkness overlay on screen | Reset on each frame | `PPlay/effects.py:70-98` |
| 13 | UI | UIKit Button & Progress Bar | Interactive UI button with hover/press states and fillable progress bar | Size, label, colors, current/max value | Renders interactive UI | Clamps progress to 0..max | `PPlay/uikit.py:22-113` |
| 14 | Architecture | Retro-Compatibility Bridge | Injects legacy PPlay 1.0 method mappings (`Window.width`, `Window.get_keyboard`, etc.) | None (auto-executes on import) | Patches PPlay classes | Logs warning on failure | `PPlay/retro_bridge.py:28-108` |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | `GameImage` / `Sprite` Loading | Non-existent file path (`'non_existent.png'`) | Raises `FileNotFoundError` in Python 3.15 / pygame-ce because `gameimage.py:45` only catches `pygame.error`. All assets must exist on disk prior to instantiation. |
| 2 | `Window.update()` Delta Time | First frame of execution | `delta_time()` returns `0` before the first `w.update()` call, then accurately returns frame duration in seconds (e.g. `0.016s` for 60 FPS). Movement calculations must multiply by `dt`. |
| 3 | `Animation.draw()` vs `GameImage.draw()` | Instantiated `Camera` active | `Animation` and `Sprite` automatically offset their rendering by `(cam.x, cam.y)`, whereas `GameImage` ignores `Camera` and draws in screen space. HUD/UI elements must use `GameImage` or screen-space draws, not world `Sprite`. |
| 4 | `Window` Minimized / Zero Size | Window minimized to taskbar (`largura_real < 1`) | `Window.update()` intercepts `w < 1 or h < 1` and skips transform scaling to avoid `pygame.error: Cannot scale to zero width/height`. |
| 5 | `Keyboard.key_pressed` Case Sensitivity | String keys passed in lowercase or uppercase (`"left"` vs `"LEFT"`, `"w"` vs `"W"`) | Handled cleanly: `Keyboard._get_code()` converts string to uppercase for standard keys (`"LEFT"`) and uses lowercase for `pygame.K_<key>` attributes (`pygame.K_w`). |
| 6 | Mouse Virtual Coords with Letterboxing | Window resized to non-standard aspect ratio | `Window.screen_to_virtual_coords()` subtracts letterbox padding and scales by `ratio`, keeping mouse position aligned with internal virtual resolution. |
| 7 | Sound Playback in Headless Mode | `SDL_AUDIODRIVER='dummy'` | `SoundManager.inicializar()` succeeds without throwing errors, and `Sound.play()` executes silently without crashing. |

---

## 5. Procedural Asset Specification (`tools/gerador_assets.py`)

To satisfy Phase 0 and Phase 1 requirements completely and prevent `FileNotFoundError` during runtime, `tools/gerador_assets.py` will generate the following assets using `Pillow` for pixel art and `wave` for 8-bit audio:

```
assets/
├── sprites/
│   ├── jogador/
│   │   ├── batata_idle.png         (32x32 pixel art potato avatar)
│   │   ├── batata_walk_sheet.png   (128x32 4-frame walking spritesheet)
│   │   └── batata_dano.png         (32x32 red flash damage frame)
│   ├── inimigos/
│   │   ├── inimigo_padrao.png      (32x32 blue/gray intern enemy)
│   │   ├── inimigo_tank.png        (48x48 heavy metallic refrigerator enemy)
│   │   ├── inimigo_rapido.png      (24x24 neon agile caffeine enemy)
│   │   ├── inimigo_phasing.png     (32x32 cyan translucent ghost enemy)
│   │   ├── inimigo_blindado.png    (36x36 armored helmet bulletproof enemy)
│   │   └── inimigo_ranged.png      (32x32 orange ranged blaster enemy)
│   ├── armas/
│   │   ├── arma_melee.png          (24x24 wrench icon)
│   │   ├── arma_pistola.png        (24x24 factory pistol)
│   │   ├── arma_minigun.png        (32x32 rotary minigun)
│   │   ├── arma_shotgun.png        (32x32 double barrel shotgun)
│   │   ├── arma_rifle.png          (32x32 assault rifle)
│   │   ├── arma_foguetes.png       (32x32 rocket launcher tube)
│   │   └── arma_granadas.png       (32x32 grenade launcher)
│   ├── projeteis/
│   │   ├── projetil_pistola.png    (8x8 yellow bullet)
│   │   ├── projetil_minigun.png    (6x6 tracer bullet)
│   │   ├── projetil_shotgun.png    (8x8 spread pellet)
│   │   ├── projetil_rifle.png      (10x10 high-speed round)
│   │   ├── projetil_foguete.png    (20x10 rocket with exhaust flame)
│   │   ├── projetil_granada.png    (12x12 explosive canister)
│   │   └── projetil_inimigo.png    (10x10 purple plasma orb)
│   ├── equipamentos/
│   │   ├── drone_cura.png          (24x24 green cross medical drone)
│   │   ├── drone_combate.png       (24x24 turret attack drone)
│   │   └── drone_suporte.png       (24x24 energy support drone)
│   └── drops/
│       ├── drop_xp.png             (24x24 purple crate with XP gem)
│       ├── drop_cura.png           (24x24 red crate with white medical cross)
│       ├── drop_arma.png           (24x24 military brown crate with gun emblem)
│       ├── drop_equipamento.png    (24x24 orange crate with tool emblem)
│       └── drop_config.png         (24x24 gray crate with golden gear emblem)
├── tiles/
│   ├── tile_piso.png               (32x32 dark tech grid floor tile)
│   ├── tile_piso_alt.png           (32x32 accented floor tile)
│   ├── tile_parede.png             (32x32 arena boundary block)
│   └── obstaculo_caixa.png         (32x32 industrial obstacle box)
├── ui/
│   ├── btn_gear.png                (32x32 settings gear icon for in-game HUD)
│   ├── card_upgrade_bg.png         (160x220 upgrade card frame)
│   ├── slot_inventario.png         (40x40 dark inventory slot frame)
│   ├── btn_bg_normal.png           (180x45 normal button texture)
│   ├── btn_bg_hover.png            (180x45 hovered button texture)
│   ├── mira_crosshair.png          (16x16 targeting crosshair)
│   └── icones_configs/             (20 gameplay + 3 audio configuration icons)
│       ├── icon_fps_cap.png
│       ├── icon_graficos_qualidade.png
│       ├── icon_resolucao.png
│       ├── icon_vsync.png
│       ├── icon_screen_shake.png
│       ├── icon_motion_blur.png
│       ├── icon_hud.png
│       ├── icon_damage_numbers.png
│       ├── icon_zoom.png
│       ├── icon_movimento_mouse.png
│       ├── icon_keybinds.png
│       ├── icon_suavizacao_camera.png
│       ├── icon_auto_fire.png
│       ├── icon_inimigos_ranged.png
│       ├── icon_coleta_inimiga.png
│       ├── icon_velocidade_inimigos.png
│       ├── icon_vida_inimigos.png
│       ├── icon_iluminacao.png
│       ├── icon_cores_invertidas.png
│       └── icon_fogo_amigo.png
└── audio/
    ├── sfx/
    │   ├── tiro_pistola.wav
    │   ├── tiro_minigun.wav
    │   ├── tiro_shotgun.wav
    │   ├── tiro_rifle.wav
    │   ├── tiro_foguete.wav
    │   ├── tiro_granada.wav
    │   ├── ataque_melee.wav
    │   ├── explosao.wav
    │   ├── dano_jogador.wav
    │   ├── morte_jogador.wav
    │   ├── morte_inimigo.wav
    │   ├── pickup_xp.wav
    │   ├── pickup_cura.wav
    │   ├── pickup_arma.wav
    │   ├── pickup_equipamento.wav
    │   ├── levelup.wav
    │   ├── btn_hover.wav
    │   └── btn_click.wav
    └── musica/
        └── musica_fase.wav         (Looping 8-bit chiptune BGM)
```

---

## 6. Game Architecture & Entry Point Specification (`src/main.py`)

### 6.1 Architecture Blueprint
- **Framework**: PowerPPlay 2.0 (`PPlay.window.Window`, `PPlay.scenemanager.SceneManager`, `PPlay.scenemanager.Scene`).
- **Logical Resolution**: 960 × 540 or 1280 × 720 (virtual canvas), scaled smoothly or nearest-neighbor to the physical monitor size.
- **Entry Point Flow**:
  1. Initialize `Window(1280, 720, "Protocolo: Batata", resizavel=True, pixel_art=True)`.
  2. Initialize Core Systems (Singletons / Services):
     - `ConfigSistema`: Loads persistent configs from `data/save.json` adhering to `CONFIGURACOES.md`.
     - `GerenciadorAudio`: Initializes PPlay `SoundManager`, binds volume sliders.
  3. Change active scene to `MenuPrincipalScene` via `SceneManager.change_scene()`.
  4. Main game loop:
     ```python
     while True:
         # 1. Update and draw active scene
         SceneManager.run()
         
         # 2. Enforce FPS Cap if configured (e.g. 15, 30, 45, 60 FPS)
         # 3. Present frame, process events, and clear virtual buffer
         janela.update()
     ```

### 6.2 Scene Decomposition
- `cenas/menu_principal.py`: Play, Settings, Credits, Exit buttons, title banner, high scores.
- `cenas/gameplay.py`:
  - Player entity (`Jogador`), Camera follow (`Camera.get_instance().follow(player)`), Infinite arena tiled background (`TileMap` or procedural tile culling).
  - Enemy spawn system (`SistemaSpawn`), projectile pool, drops pool.
  - HUD overlay (Health bar, XP bar, 4 Inventory slots, survival timer, pause gear button).
  - Screen effects integration (`ScreenEffects.apply_to_camera()`, `ScreenEffects.draw_flash()`).
  - Lighting overlay (`LightingSystem.draw()`).
- `cenas/menu_pausa.py`: Pauses gameplay logic while keeping rendered game state in background, provides Resume, Settings, Quit options.
- `cenas/level_up.py`: Shows 3 upgrade cards for locked gameplay configurations, applies unlock permanently, saves to `data/save.json`.
- `cenas/game_over.py`: Shows survival time, enemies defeated, retry and main menu options.

---

## 7. Caveats
1. No caveats on PPlay 2.0 core mechanics — all classes, signatures, and behaviors were directly observed from source and verified under Python execution.
2. The Pygame audio backend in headless testing mode (`SDL_AUDIODRIVER=dummy`) suppresses audio output without errors; real audio hardware on Windows will play WAV streams directly through `pygame.mixer`.

---

## 8. Conclusion
The PowerPPlay 2.0 engine in `.venv/Lib/site-packages/PPlay` is fully functional with `pygame-ce` and `Pillow`. Phase 0 can be executed cleanly by:
1. Creating the complete `assets/` and `src/` directory hierarchy.
2. Implementing `tools/gerador_assets.py` to programmatically render all pixel art PNGs and 8-bit sound WAVs.
3. Implementing `src/main.py` with `Window` and `SceneManager` to launch the title and gameplay scenes.

---

## 9. Verification Method

To independently verify all findings and test Phase 0 execution:

```powershell
# 1. Run PPlay integration & import test
& "c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.venv\Scripts\python.exe" -c "
import PPlay.window, PPlay.sprite, PPlay.animation, PPlay.sound, PPlay.scenemanager, PPlay.camera, PPlay.effects, PPlay.uikit
print('PPlay 2.0 Engine Verification: SUCCESS')
"

# 2. Run Asset Generator when created
& "c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.venv\Scripts\python.exe" tools/gerador_assets.py

# 3. Launch Main Game
& "c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.venv\Scripts\python.exe" src/main.py
```
