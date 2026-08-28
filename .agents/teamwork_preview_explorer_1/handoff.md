# Handoff Report: Asset Generation System Analysis & Sprite Scaling Specification

## 1. Observation

### 1.1 Architecture & Context
- **[Observed]** Project SSOT documents inspected:
  - `.agents/architecture_cache.md` (lines 10-23): Outlines module directory layout (`assets/`, `src/`, `tools/gerador_assets.py`).
  - `CONFIGURACOES.md` (lines 1-277): Defines 20 unlockable gameplay configurations and 4 system settings.
  - `PLANO_DE_IMPLEMENTACAO.md` (lines 467-552): Details asset directory tree including `assets/sprites/graficos_baixos/`, `assets/ui/cards/`, `assets/ui/botoes/`, `assets/ui/barras/`.
  - `src/utils/constantes.py` (lines 193-718): Registers `CONFIGURACOES_CATALOGO`, `CONFIGURACOES_SISTEMA`, and `ASSET_PATHS`.
  - Priority User Directive (2026-08-28T15:47:06Z): Sprites are too small on a 1080p monitor. Increase base pixel dimensions of all generated gameplay sprites by approximately 30% (e.g. 32×32 → 42×42, 24×24 → 32×32, 48×48 → 64×64, 64×64 → 84×84).

### 1.2 Analysis of `tools/gerador_assets.py` (992 lines)
- **[Observed]** The script is fully procedural, depending only on the Python standard library (`os`, `math`, `struct`, `wave`, `random`) and `Pillow` (`PIL.Image`, `PIL.ImageDraw`).
- **[Observed]** Core implementation patterns:
  - Image creation helper:
    ```python
    def criar_imagem_transparente(largura: int, altura: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        return img, draw
    ```
  - Persistence helper:
    ```python
    def salvar_png(img: Image.Image, caminho_relativo: str):
        caminho_completo = os.path.join(ASSETS_DIR, caminho_relativo)
        os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
        img.save(caminho_completo, "PNG")
    ```
  - Standard Color Palette:
    - **Cyberpunk UI Dark Panels**: `(20, 24, 32, 245)`, `(30, 38, 52, 255)`, `(18, 22, 30, 240)`
    - **Accents**: Neon Cyan `(0, 220, 255, 255)`, Gold/Amber `(255, 215, 0, 255)`, Crimson `(235, 45, 55, 255)`, Medical Green `(35, 190, 75, 255)`
    - **Potato Player**: Body `(205, 155, 75)`, Shadow `(145, 95, 45)`, Cyber Eyes `(0, 230, 255)`
    - **Weapons**: Steel `(140, 150, 165)`, Dark Metal `(40, 45, 55)`, Olive Drab `(75, 95, 55)`, Wood `(120, 70, 35)`
  - Execution Flow (`gerar_todos_os_assets()`):
    1. `gerar_sprites_jogador()`: `batata_idle.png`, `batata_walk_sheet.png`, `batata_dano.png`
    2. `gerar_sprites_inimigos()`: 6 archetypes (`padrao`, `tank`, `rapido`, `phasing`, `blindado`, `ranged`)
    3. `gerar_sprites_armas()` & `gerar_sprites_projeteis()`: 7 weapons (`melee`, `pistola`, `minigun`, `shotgun`, `rifle`, `foguetes`, `granadas`) & 7 projectiles
    4. `gerar_sprites_equipamentos()` & `gerar_sprites_drops()`: 3 companion drones & 5 drop types
    5. `gerar_tiles()`, `gerar_assets_ui()`, & `gerar_icones_configs()`: tiles, 6 UI files, 23 config icons
    6. `gerar_efeitos_sonoros()` & `gerar_musica_fase()`: 17 SFX wavs & 1 BGM chiptune

### 1.3 Audit of Existing Files in `assets/`
- **[Verified]** Exactly 96 files currently exist under `assets/`:
  - `audio/musica/` (1 file): `musica_fase.wav`
  - `audio/sfx/` (17 files): SFX for weapons, damage, death, pickups, levelup, UI
  - `sprites/jogador/` (3 files): idle, walk sheet, damage
  - `sprites/inimigos/` (6 files): 6 enemy variants
  - `sprites/armas/` (7 files): melee, pistola, minigun, shotgun, rifle, foguetes, granadas
  - `sprites/projeteis/` (7 files): 6 player projectiles + 1 enemy plasma
  - `sprites/equipamentos/` (3 files): drone_cura, drone_combate, drone_suporte
  - `sprites/drops/` (5 files): drop_xp, drop_cura, drop_arma, drop_equipamento, drop_config
  - `tiles/` (4 files): tile_piso, tile_piso_alt, tile_parede, obstaculo_caixa
  - `ui/` (6 root files): `btn_gear.png`, `card_upgrade_bg.png`, `slot_inventario.png`, `btn_bg_normal.png`, `btn_bg_hover.png`, `mira_crosshair.png`
  - `ui/icones_configs/` (23 files): 20 gameplay config icons + 3 audio system icons

---

## 2. Logic Chain

1. **Premise 1 (Priority Scaling for 1080p Displays)**:
   - User directive states that base sprites are too small on 1080p monitors and must be scaled up by ~30%.
   - Applying a ~1.31× – 1.33× scale factor maps standard sprite boundaries cleanly onto discrete pixel grids:
     - $32 \times 1.3125 \approx 42\text{px}$ (or $48\text{px}$)
     - $24 \times 1.333 \approx 32\text{px}$
     - $36 \times 1.333 \approx 48\text{px}$
     - $48 \times 1.333 \approx 64\text{px}$
     - $8 \times 1.375 \approx 11\text{px} \sim 12\text{px}$
     - $40 \times 1.35 \approx 54\text{px} \sim 56\text{px}$ (UI inventory/weapon slots)

2. **Premise 2 (Weapons & Combat FX)**:
   - `SCOPE.md` (Feature #1) requires distinct shapes/colors for all weapons, HUD cards, and combat feedback.
   - Weapons must be scaled to 32×32 / 42×42.
   - Muzzle flashes (`muzzle_flash_pistola.png` 16×16, `muzzle_flash_shotgun.png` 20×20, `muzzle_flash_pesado.png` 24×24) and explosion animation sheet (`explosao_sheet.png` 256×42 - 6 frames of 42×42) are needed for Shotgun, Minigun, Rocket Launcher, and Grenade Launcher.
   - HUD weapon slot badges (`hud_slot_arma.png` 56×56) are needed for Vampire Survivors-style weapon displays.

3. **Premise 3 (Companion Drones & FX)**:
   - 3 companion drones (Cura, Combate, Suporte) scaled from 24×24 to 32×32.
   - Drones require 4-frame hover spritesheets (`drone_cura_sheet.png`, etc. 128×32) and visual field FX:
     - `aura_escudo.png` (64×64) for Drone Suporte barrier.
     - `aura_cura.png` (64×64) for Drone Cura healing pulse.
     - `projetil_drone.png` (12×12) for Drone Combate.

4. **Premise 4 (UI Background Cards for Configs)**:
   - Only 1 generic card exists: `ui/card_upgrade_bg.png` (160×220).
   - The core gameplay progression requires 4 card states + modal background:
     1. `ui/cards/card_config_desbloqueado.png` (160×220): Unlocked card with cyber-cyan border.
     2. `ui/cards/card_config_bloqueado.png` (160×220): Locked card with dimmed palette and padlock motif.
     3. `ui/cards/card_config_ativo.png` (160×220): Active sacrifice buff card with energized amber border.
     4. `ui/cards/card_levelup.png` (160×220): Level Up reward card.
     5. `ui/painel_configs_bg.png` (640×480): Settings modal panel frame.

5. **Premise 5 (Generic Config Button Icons & UI Controls)**:
   - Interactive configuration menus require:
     - Button states: `btn_bg_pressed.png`, `btn_bg_disabled.png`, `btn_bg_selected.png` (180×45).
     - Toggle switches: `toggle_on.png`, `toggle_off.png` (48×24).
     - Sliders: `slider_trilho.png`, `slider_cursor.png`, `slider_cursor_hover.png`.
     - Checkboxes: `checkbox_marcado.png`, `checkbox_desmarcado.png` (24×24).
     - Generic UI Glyphs (24×24 & 32×32): `icon_cadeado.png`, `icon_check.png`, `icon_fechar.png`, `icon_seta_esq.png`, `icon_seta_dir.png`, `icon_daltonico.png` (for system config S4), `icon_reset.png`, `icon_ajuda.png`.
     - HUD bars: `barra_hp_fundo.png`, `barra_hp_fill.png`, `barra_xp_fundo.png`, `barra_xp_fill.png`, `barra_escudo_fill.png`.

6. **Premise 6 (Low-Graphics Mode Assets — Config #2)**:
   - Config #2 (`graficos_qualidade`: "Baixa") replaces sprites with geometric shapes.
   - Scaled flat-color geometric placeholders (`assets/sprites/graficos_baixos/`): `jogador_low.png` (42×42), `inimigo_padrao_low.png` (42×42), `inimigo_tank_low.png` (64×64), `inimigo_rapido_low.png` (32×32), `inimigo_phasing_low.png` (42×42), `inimigo_blindado_low.png` (48×48), `inimigo_ranged_low.png` (42×42), `projetil_low.png` (12×12), `drop_low.png` (32×32).

---

## 3. Caveats

- **[Observed]** No modification was made to any project source files during this read-only exploration.
- **[Inferred]** When `tools/gerador_assets.py` updates sprite sizes, entity collision boxes in `src/entidades/` or `src/utils/constantes.py` (`JOGADOR_LARGURA = 42`, `JOGADOR_ALTURA = 42`) should be updated by the appropriate implementation agent during their designated turns.
- **[Speculative]** If UI layouts (HUD and Cards) are rendered at 1080p, cards at 160×220 or 180×240 will provide comfortable readability.

---

## 4. Conclusion & Complete Asset Scaling Matrix

### 4.1 Master Sprite Dimension Matrix (~30% Increase for 1080p)

| Asset Category | Asset File Name | Previous Size | New Scaled Size (~30%+) | Description |
|---|---|---|---|---|
| **Player** | `batata_idle.png` | 32×32 | **42×42** | Mech potato idle avatar |
| **Player** | `batata_walk_sheet.png` | 128×32 | **168×42** | 4 frames (42×42 each) |
| **Player** | `batata_dano.png` | 32×32 | **42×42** | Red damage flash frame |
| **Enemy** | `inimigo_padrao.png` | 32×32 | **42×42** | Standard blue robot |
| **Enemy** | `inimigo_tank.png` | 48×48 | **64×64** | Industrial steel tank |
| **Enemy** | `inimigo_rapido.png` | 24×24 | **32×32** | Neon agile rusher |
| **Enemy** | `inimigo_phasing.png` | 32×32 | **42×42** | Translucent cyber ghost |
| **Enemy** | `inimigo_blindado.png` | 36×36 | **48×48** | Ballistic armored tank |
| **Enemy** | `inimigo_ranged.png` | 32×32 | **42×42** | Rust blaster sniper |
| **Weapon** | `arma_melee.png` | 24×24 | **32×32** | Wrench weapon |
| **Weapon** | `arma_pistola.png` | 24×24 | **32×32** | Standard pistol |
| **Weapon** | `arma_minigun.png` | 32×32 | **42×42** | Heavy rotary minigun |
| **Weapon** | `arma_shotgun.png` | 32×32 | **42×42** | Double-barrel shotgun |
| **Weapon** | `arma_rifle.png` | 32×32 | **42×42** | Assault rifle |
| **Weapon** | `arma_foguetes.png` | 32×32 | **42×42** | Olive missile launcher |
| **Weapon** | `arma_granadas.png` | 32×32 | **42×42** | Drum grenade launcher |
| **Projectile** | `projetil_pistola.png` | 8×8 | **12×12** | Yellow round bullet |
| **Projectile** | `projetil_minigun.png` | 6×6 | **8×8** | Orange rapid tracer |
| **Projectile** | `projetil_shotgun.png` | 8×8 | **12×12** | Red spread pellet |
| **Projectile** | `projetil_rifle.png` | 10×10 | **14×14** | Cyan energy bolt |
| **Projectile** | `projetil_foguete.png` | 20×10 | **28×14** | Rocket with fire plume |
| **Projectile** | `projetil_granada.png` | 12×12 | **16×16** | Green bouncing grenade |
| **Projectile** | `projetil_inimigo.png` | 10×10 | **14×14** | Purple plasma orb |
| **Drone** | `drone_cura.png` / sheet | 24×24 | **32×32** (128×32 sheet) | Medical drone with cross |
| **Drone** | `drone_combate.png` / sheet | 24×24 | **32×32** (128×32 sheet) | Lead grey combat drone |
| **Drone** | `drone_suporte.png` / sheet | 24×24 | **32×32** (128×32 sheet) | Diamond shield drone |
| **Drone FX** | `aura_escudo.png` | new | **64×64** | Cyan barrier bubble |
| **Drone FX** | `aura_cura.png` | new | **64×64** | Green pulse ring |
| **Drone FX** | `projetil_drone.png` | new | **12×12** | Red laser dart |
| **Drop** | `drop_xp.png` | 24×24 | **32×32** | Purple crate with gold gem |
| **Drop** | `drop_cura.png` | 24×24 | **32×32** | Red crate with white cross |
| **Drop** | `drop_arma.png` | 24×24 | **32×32** | Brown crate with gun badge |
| **Drop** | `drop_equipamento.png` | 24×24 | **32×32** | Orange crate with gear |
| **Drop** | `drop_config.png` | 24×24 | **32×32** | Platinum crate with gold cog |
| **UI Card** | `card_config_desbloqueado.png`| new | **160×220** | Cyan glow border card |
| **UI Card** | `card_config_bloqueado.png` | new | **160×220** | Dimmed locked card |
| **UI Card** | `card_config_ativo.png` | new | **160×220** | Amber active sacrifice card |
| **UI Card** | `card_levelup.png` | new | **160×220** | Level up choice frame |
| **UI Modal**| `painel_configs_bg.png` | new | **640×480** | Full settings panel |
| **UI Slot** | `slot_inventario.png` | 40×40 | **54×54** | Accommodates 32/42px items |
| **UI Slot** | `hud_slot_arma.png` | new | **56×56** | Weapon badge HUD frame |
| **UI Bars** | `barra_hp_fundo / fill.png` | new | **220×20 / 216×16** | Health status bar |
| **UI Bars** | `barra_xp_fundo / fill.png` | new | **220×14 / 216×10** | Experience status bar |
| **Low-GFX** | `sprites/graficos_baixos/*` | new | **32~64px** | Flat geometric placeholders |

---

## 5. Verification Method

1. **Run Asset Generator**:
   ```powershell
   .venv\Scripts\python.exe tools/gerador_assets.py
   ```
2. **Automated Verification Script**:
   ```python
   from PIL import Image
   import glob

   expected_sizes = {
       "batata_idle.png": (42, 42),
       "batata_walk_sheet.png": (168, 42),
       "inimigo_padrao.png": (42, 42),
       "inimigo_tank.png": (64, 64),
       "arma_shotgun.png": (42, 42),
       "card_config_desbloqueado.png": (160, 220),
   }

   for filename, expected_dim in expected_sizes.items():
       matches = glob.glob(f"assets/**/{filename}", recursive=True)
       assert len(matches) > 0, f"Missing file: {filename}"
       with Image.open(matches[0]) as img:
           assert img.size == expected_dim, f"Dimension mismatch for {filename}: got {img.size}, expected {expected_dim}"
   print("All scaled assets verified successfully!")
   ```
