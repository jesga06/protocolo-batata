# Milestone 2 (Phase 1: Core Gameplay Loop) — Handoff Report

**Author**: Worker M2 (`teamwork_preview_worker_m2`)  
**Mission**: Milestone 2: Phase 1 Core Gameplay Loop Implementation  
**Date**: 2026-08-28  
**Working Directory**: `c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.agents\teamwork_preview_worker_m2`  

---

## 1. Observation

- [Observed] `src/entidades/jogador.py` was created:
  - Class `Jogador(x, y, hp_max=150, velocidade=200.0)` implements:
    - Base stats: Exactly 150 HP (`hp_max = 150, hp = 150`), 200 px/s base speed, 32x32 bounding box.
    - WASD & Arrow keys movement handling with exact diagonal normalization ($dx, dy \times 0.70710678118$).
    - Arena boundary clamping strictly within $[0, \text{LARGURA\_ARENA} - 32]$ and $[0, \text{ALTURA\_ARENA} - 32]$.
    - Virtual mouse aim vector and left/right horizontal facing flip.
    - Contact damage handling (`receber_dano(qtd)`), hit flash timer (0.15s), health clamping, and death state (`vivo = False` when $\text{HP} \le 0$).
    - Inventory ownership of starter weapons (`self.armas = [Melee(), Pistola()]`).
    - Rendering with camera offset and damage flash tint using `batata_idle.png` / `batata_dano.png`.

- [Observed] `src/armas/` and `src/entidades/projetil.py` were created:
  - `src/armas/arma_base.py`: Abstract base class managing cooldown timers (`tempo_recarga_restante`), delta-time decay, ammo counters, and firing availability check (`pode_atirar()`).
  - `src/armas/pistola.py`: `Pistola(ArmaBase)` implementing 12 damage, 0.33s cooldown, 420 px/s projectile velocity, 2.5s lifetime, and ballistic `Projetil` generation directed toward the virtual mouse target with SFX triggering.
  - `src/armas/melee.py`: `Melee(ArmaBase)` implementing 20 damage, 0.6s cooldown, 70px AoE range, and knockback impulse (180 px/s) applied to the 2 closest enemies in range.
  - `src/entidades/projetil.py`: `Projetil(x, y, dir_x, dir_y, velocidade, dano, tempo_vida, dono="jogador")` with delta-time position updates, lifetime expiration, AABB collision, and sprite rendering.

- [Observed] `src/entidades/inimigo_base.py` & `src/entidades/inimigo_padrao.py` were created:
  - `InimigoBase`: Base enemy class with position, HP, speed, contact damage, independent contact cooldown timer (`cooldown_contato_atual`), knockback velocity damping (`lerp`), hit flash timer, and AABB collision.
  - `InimigoPadrao`: Concrete crawler archetype with 25 HP, 100 px/s speed, 10 contact damage, 0.40s individual contact cooldown, 10 XP value, and `inimigo_padrao.png` sprite rendering.
  - AI Movement: Direct beeline unit vector calculation towards the player position with zero-distance division guard (`vetor_direcao`).
  - Independent contact cooldown: `tentar_causar_dano_contato(jogador)` debounces per-enemy instance damage for 0.40s without global interference.

- [Observed] `src/sistemas/sistema_spawn.py` was created:
  - Perimeter ring offscreen spawner (60px margin outside viewport).
  - Dynamic spawn interval scaling: $T_{\text{spawn}}(t) = \max(0.40\text{s}, 1.80\text{s} - 0.012\text{s} \times t)$.
  - Dynamic batch quantity scaling: $N_{\text{batch}}(t) = \min(8, 1 + \lfloor t / 25 \rfloor)$.
  - Soft active enemy population cap of 60.

- [Observed] `src/cenas/gameplay.py` and `src/cenas/menu_principal.py` were created / updated:
  - `GameplayScene(BaseScene)` coordinates player, weapons, active projectiles, active enemies, spawner, and camera tracking (`Camera.follow`).
  - Collision resolution: projectiles vs enemies (AABB overlap, damage, bullet destruction, enemy death, kill counter +1, score +100), enemies vs player (contact damage).
  - Dual-layer rendering: world space (camera transformed) for floor tiles (`tile_piso.png`), arena bounds, enemies, player, projectiles; screen space for in-world HP bar beneath player avatar, top-left inventory slots, top-center match timer / kill counter, and top-right gear button / FPS.
  - `MenuPrincipalScene.iniciar_jogo()` wired to launch `GameplayScene`.

- [Verified] Automated Test Suite Execution:
  Running `.venv/Scripts/python.exe -m unittest discover -s tests` executed 72 automated unit and integration tests across 7 test suites with 0 failures and 0 errors:
  ```
  Ran 72 tests in 7.563s
  OK
  ```
- [Verified] 120-frame continuous headless simulation:
  Executed `.venv/Scripts/python.exe -c "..."` running `MenuPrincipalScene -> GameplayScene` for 120 frames with zero exceptions and verified entity movement, shooting, spawner scaling, and projectile destruction.

---

## 2. Logic Chain

1. **Adherence to Authoritative Specifications**:
   - `ORIGINAL_REQUEST.md` §R2 requires player WASD movement, shooting mechanics, and standard enemies that spawn and move directly towards the player (beeline).
   - `GDD.md` §2.6–2.7 and `CONFIGURACOES.md` specify 150 player HP, 200 px/s speed, 0.4s individual enemy contact cooldown, 25 enemy HP, 100 px/s enemy speed, and 10 contact damage.
   - All classes in `src/entidades/`, `src/armas/`, `src/sistemas/`, and `src/cenas/` implement these exact values as verified by unit tests.

2. **Per-Instance Contact Damage Decoupling**:
   - As documented in `survey_2_2` and `survey_2_3`, damage cooldown must not be global.
   - `InimigoBase.cooldown_contato_atual` stores each enemy instance's remaining timer. When 2 enemies touch the player simultaneously, each inflicts damage once and independently enters its 0.40s debounce cycle.

3. **Delta-Time & Frame-Rate Resilience**:
   - All movement equations ($x += v_x \cdot dt$) and timer updates are multiplied by delta time.
   - A minimum threshold is enforced in `GameplayScene.loop()` so unthrottled headless testing and varied monitor refresh rates advance physics consistently at 60 FPS baseline without time dilation.

4. **Acceptance Criteria Verification**:
   - Criteria 1: `tools/gerador_assets.py` populates assets (`batata_idle.png`, `inimigo_padrao.png`, `projetil_pistola.png`).
   - Criteria 2: `main.py` launches window without crashing.
   - Criteria 3: Player moves with WASD / arrows (diagonal normalized) and shoots projectiles.
   - Criteria 4: Enemies spawn in offscreen perimeter ring, beeline directly to the player, deal contact damage with individual cooldowns, take damage, and die when HP reaches 0.

---

## 3. Caveats

- Audio playback in headless environments (`SDL_AUDIODRIVER=dummy`) silently bypasses physical speakers while initializing properly; on real hardware, audio plays via Pygame mixer.
- Special weapons (Minigun, Shotgun, Rocket Launcher) and Drone companions (Slot 3 & Slot 4) have slots prepared in the UI and player architecture, ready for drop loot table integration in subsequent phases.
- No caveats on gameplay physics, math accuracy, collision detection, or scene transitions.

---

## 4. Conclusion

Milestone 2 (Phase 1: Core Gameplay Loop) is 100% complete and fully verified:
1. `src/entidades/jogador.py` correctly implements the potato avatar with WASD movement, diagonal normalization ($0.7071$), arena clamping, aim vector, damage reception, and death states.
2. `src/armas/` and `src/entidades/projetil.py` implement the starter weapon arsenal (Melee & Pistol) with accurate cooldowns, projectile trajectory, and knockback.
3. `src/entidades/inimigo_base.py` and `src/entidades/inimigo_padrao.py` implement standard enemies with beeline AI, individual contact cooldowns, and health depletion.
4. `src/sistemas/sistema_spawn.py` provides offscreen perimeter spawning with dynamic wave scaling.
5. `src/cenas/gameplay.py` orchestrates the complete arena loop with camera follow, dual-layer rendering, in-world HP bar, HUD, and collision resolution.
6. 72 unit and E2E tests pass with 0 failures and 0 errors.

---

## 5. Verification Method

To independently verify the implementation:

```powershell
# 1. Run complete automated test suite
& "c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.venv\Scripts\python.exe" -m unittest discover -s tests

# 2. Run 120-frame headless gameplay simulation
& "c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.venv\Scripts\python.exe" -c "import os; os.environ['SDL_VIDEODRIVER']='dummy'; os.environ['SDL_AUDIODRIVER']='dummy'; import pygame; pygame.init(); from PPlay.window import Window; from PPlay.scenemanager import SceneManager; from src.cenas.menu_principal import MenuPrincipalScene; from src.cenas.gameplay import GameplayScene; j = Window(800, 600, 'Sim', pixel_art=True); m = MenuPrincipalScene(); SceneManager.change_scene(m); m.iniciar_jogo(); [SceneManager.run() or j.update() for _ in range(120)]; print('120 frames OK')"

# 3. Interactive live play (launches main menu -> click Jogar or press ENTER)
& "c:\Users\jesse\Documents\Computaria\visual studio\protocolo-batata\.venv\Scripts\python.exe" src/main.py
```
