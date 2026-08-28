# Technical PIL Procedural Rendering Architecture & Specification Report
**Project**: Protocolo: Batata  
**Module**: `tools/gerador_assets.py` Procedural Generation Engine  
**Author**: Explorer 3 (Spec Miner / Procedural Rendering Architect)  
**Date**: 2026-08-28  
**Target Output**: Assets expansion for Phase 2, 3, and 4 (Weapons, Drones, UI Cards, Generic Config Icons)

---

## 1. Observation

Direct investigation of the codebase and project specifications revealed the following baseline state:

1. **Architecture & Single Source of Truth**:
   - `CONFIGURACOES.md` (SSOT) catalogs 20 unlockable gameplay configurations and 4 system configurations (Master, Music, SFX, Colorblind Filter).
   - `.agents/architecture_cache.md` confirms the engine is PowerPPlay 2.0 (Pygame-CE based), using standard sprite dimensions (32x32 player, 24x24/32x32 weapons, 24x24/32x32 drones, 24x24 drops, 160x220 UI cards).
   - `src/utils/constantes.py` (lines 638–718) maps asset keys to disk paths under `assets/sprites/`, `assets/tiles/`, `assets/ui/`, and `assets/audio/`.

2. **Existing Asset Generator State (`tools/gerador_assets.py`)**:
   - Utilizes Python's `PIL.Image` and `PIL.ImageDraw` for procedural 2D pixel-art rasterization and `wave`/`struct` for 8-bit PCM audio.
   - Contains basic implementations for player, 6 enemies, 7 weapons, 7 projectiles, 3 drones, 5 drops, 4 tiles, 23 config icons, and SFX/music.
   - **Gaps Identified for Expansion**:
     - *Weapons*: Existing silhouettes are simplistic geometric approximations; shotgun lacks distinct twin barrels/wooden forend texturing; minigun lacks multi-barrel rotary assembly with mounting brackets; rocket launcher lacks realistic optical sight and exhaust cone.
     - *Drones*: Existing drones are minimal 24x24 shapes lacking distinctive sci-fi identities (combat drone lacks stealth delta-wings and red targeting laser; healing drone lacks bio-aura glow and nanite dispenser; support drone lacks orbital shield emitter nodes and phased array antenna dishes).
     - *UI Configuration Cards*: Only a single static `card_upgrade_bg.png` exists. Missing stateful cards (`card_config_normal.png`, `card_config_unlocked.png`, `card_config_locked.png`, `card_config_active.png`, `card_config_hover.png`, and `card_category_header.png`).
     - *Generic Config Icons*: Missing dedicated generic UI glyphs (16x16 / 24x24 / 32x32) for gear, speaker, display, gamepad, crosshair, shield, heart, wrench, lock, unlock, checkmark, directional arrows, cpu, sliders, and cyber potato mascot emblem.

---

## 2. Logic Chain

From the observations and project requirements, the technical procedural rendering pipeline is structured as follows:

```
[PIL Coordinate System & RGBA Palette Definitions]
                    │
                    ├──> [Weapon Silhouette Generator]
                    │       ├── Double-Barrel Pump Shotgun (Walnut + Gunmetal)
                    │       ├── Rotary Multi-Barrel Minigun (Tungsten + Hazard Bands)
                    │       ├── Heavy Optical-Sight Rocket Launcher (Olive Drab + Venturi)
                    │       └── Bullpup Tactical Rifle & Revolving Grenade Launcher
                    │
                    ├──> [Companion Drone Generator]
                    │       ├── Combat Drone (Delta Stealth Hull + Twin Blasters + Red Visor)
                    │       ├── Healing Drone (Bio-Ceramic Hull + Emerald Aura + Nano Tank)
                    │       └── Support Drone (Hex Core + Orbital Shield Nodes + Sat Dishes)
                    │
                    ├──> [UI Configuration Card Suite (160x220 & Modular 9-Patch)]
                    │       ├── Normal / Available Card (Cyan Cyber Slate)
                    │       ├── Unlocked Card (Imperial Gold + Emerald Circuits)
                    │       ├── Locked Card (Charcoal Iron + Yellow Hazard Tape + Padlock)
                    │       ├── Active Buff Card (Neon Amber Overdrive + Red Alerts)
                    │       └── Hover Card & Category Ribbon Badges
                    │
                    └──> [Generic Config Icons Suite (32x32 / 24x24 / 16x16)]
                            ├── Core UI Glyphs (Gear, Speaker, Display, Gamepad)
                            ├── Gameplay Glyphs (Crosshair, Shield, Heart, Wrench)
                            ├── State Glyphs (Lock, Unlock, Checkmark, Warning Triangle)
                            └── Navigation & System Glyphs (Arrows, Sliders, CPU, Battery, Potato)
```

### 2.1 Concrete Drawing Algorithms & Helper Suite

#### A. PIL Rendering Helpers
```python
def criar_imagem_transparente(largura: int, altura: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)

def desenhar_gradiente_linear(draw: ImageDraw.ImageDraw, box: tuple, cor_topo: tuple, cor_base: tuple):
    x1, y1, x2, y2 = box
    h = max(1, y2 - y1)
    for y in range(y1, y2 + 1):
        t = (y - y1) / h
        r = int(cor_topo[0] * (1 - t) + cor_base[0] * t)
        g = int(cor_topo[1] * (1 - t) + cor_base[1] * t)
        b = int(cor_topo[2] * (1 - t) + cor_base[2] * t)
        a = int(cor_topo[3] * (1 - t) + cor_base[3] * t) if len(cor_topo) > 3 else 255
        draw.line([x1, y, x2, y], fill=(r, g, b, a), width=1)

def desenhar_cantoneiras_tech(draw: ImageDraw.ImageDraw, box: tuple, tam: int = 4, cor: tuple = (0, 220, 255, 255)):
    x1, y1, x2, y2 = box
    # Top-Left
    draw.line([x1, y1, x1 + tam, y1], fill=cor, width=2)
    draw.line([x1, y1, x1, y1 + tam], fill=cor, width=2)
    # Top-Right
    draw.line([x2 - tam, y1, x2, y1], fill=cor, width=2)
    draw.line([x2, y1, x2, y1 + tam], fill=cor, width=2)
    # Bottom-Left
    draw.line([x1, y2 - tam, x1, y2], fill=cor, width=2)
    draw.line([x1, y2, x1 + tam, y2], fill=cor, width=2)
    # Bottom-Right
    draw.line([x2 - tam, y2, x2, y2], fill=cor, width=2)
    draw.line([x2, y2 - tam, x2, y2], fill=cor, width=2)
```

---

### 2.2 Weapons Drawing Algorithms

#### 1. Shotgun (`arma_shotgun.png` — 32x32)
- **Palette**:
  - Walnut Stock: Main `(130, 75, 35, 255)`, Shadow `(85, 45, 20, 255)`, Highlight `(170, 105, 55, 255)`
  - Gunmetal Steel: Dark `(65, 70, 80, 255)`, Light `(150, 160, 175, 255)`, Top highlight `(210, 220, 230, 255)`
  - Brass / Gold: `(230, 180, 50, 255)`
  - Recoil Pad: `(30, 30, 35, 255)`
- **Algorithm**:
  1. Buttpad: `draw.rectangle([1, 17, 3, 23], fill=(30, 30, 35, 255))`
  2. Walnut Stock: `draw.polygon([(3, 17), (10, 13), (10, 20), (3, 23)], fill=(130, 75, 35, 255), outline=(60, 35, 15, 255))`
  3. Steel Receiver: `draw.rectangle([10, 12, 18, 19], fill=(65, 70, 80, 255), outline=(35, 38, 45, 255))`
  4. Brass Shell Ejection Port: `draw.rectangle([12, 13, 15, 15], fill=(230, 180, 50, 255))`
  5. Over/Under Twin Barrels:
     - Top barrel: `draw.rectangle([18, 11, 30, 14], fill=(150, 160, 175, 255), outline=(50, 55, 62, 255))`
     - Bottom barrel: `draw.rectangle([18, 14, 30, 17], fill=(120, 130, 145, 255), outline=(50, 55, 62, 255))`
     - Barrel highlight line: `draw.line([18, 11, 29, 11], fill=(210, 220, 230, 255))`
  6. Ribbed Wooden Pump Slider: `draw.rectangle([17, 17, 24, 21], fill=(130, 75, 35, 255), outline=(60, 35, 15, 255))` with grip notches at `x=19, 21, 23` in `(85, 45, 20, 255)`.
  7. Brass Bead Sight: `draw.point([29, 10], fill=(255, 215, 0, 255))`.

#### 2. Minigun (`arma_minigun.png` — 32x32)
- **Palette**:
  - Tungsten Steel Housing: `(50, 55, 68, 255)` & `(75, 82, 95, 255)`
  - Rotary Barrels: `(170, 180, 195, 255)` & `(220, 230, 240, 255)`
  - Drum Magazine: `(35, 40, 50, 255)` with Yellow Ammo Band `(255, 200, 0, 255)`
  - Power Indicator: Cyan LED `(0, 230, 255, 255)`
- **Algorithm**:
  1. Circular Ammo Drum: `draw.ellipse([2, 14, 12, 24], fill=(35, 40, 50, 255), outline=(20, 22, 28, 255))` with yellow stripe `[4, 18, 10, 20]`.
  2. Motor Shroud: `draw.rectangle([8, 10, 18, 22], fill=(50, 55, 68, 255), outline=(25, 28, 35, 255))` with horizontal radiator cooling vents at `y=12, 14, 16, 18, 20`.
  3. Top Carrying Handle & Spade Grip: `draw.line([10, 7, 16, 7], fill=(80, 85, 95, 255), width=2)` with support posts at `x=10` and `x=16`. Rear spade grip at `[4, 10, 7, 13]`.
  4. Rotary Triple-Barrel Cluster:
     - Top barrel: `draw.rectangle([18, 11, 30, 13], fill=(170, 180, 195, 255))`
     - Middle barrel: `draw.rectangle([18, 14, 31, 16], fill=(190, 200, 215, 255))`
     - Bottom barrel: `draw.rectangle([18, 17, 30, 19], fill=(150, 160, 175, 255))`
  5. Barrel Clamping Rings: Circular brackets at `x=23` and `x=29` wrapping all three barrels.
  6. Glowing Cyan Capacitor Nodule: `draw.rectangle([13, 11, 15, 13], fill=(0, 230, 255, 255))`.

#### 3. Rocket Launcher (`arma_foguetes.png` — 32x32)
- **Palette**:
  - Olive Drab Launcher Tube: `(70, 90, 50, 255)`, Shadow `(45, 60, 32, 255)`, Highlight `(105, 130, 78, 255)`
  - Ceramic Exhaust Nozzle: `(40, 42, 48, 255)`
  - Optical Scope & Rails: `(30, 32, 38, 255)` with Emerald Lens `(0, 240, 180, 255)`
  - Hazard Yellow Warning Band: `(255, 200, 20, 255)`
- **Algorithm**:
  1. Conical Exhaust Venturi: `draw.polygon([(4, 10), (0, 7), (0, 24), (4, 21)], fill=(40, 42, 48, 255), outline=(20, 20, 25, 255))`
  2. Heavy Launch Tube: `draw.rectangle([4, 11, 27, 20], fill=(70, 90, 50, 255), outline=(32, 45, 22, 255))` with top highlight `[5, 12, 26, 13]` in `(105, 130, 78, 255)`.
  3. Hazard Stripe Band: `draw.rectangle([24, 11, 26, 20], fill=(255, 200, 20, 255))`
  4. Front Muzzle Flange: `draw.rectangle([26, 9, 29, 22], fill=(45, 60, 32, 255), outline=(20, 30, 15, 255))`
  5. Rocket Warhead Tip: `draw.polygon([(29, 13), (31, 15), (29, 18)], fill=(220, 40, 40, 255))`
  6. Optical Targeting Sight Module: `draw.rectangle([11, 6, 20, 10], fill=(30, 32, 38, 255), outline=(15, 15, 20, 255))` on picatinny rail `[9, 10, 22, 11]`, with glowing emerald objective lens at `(19, 8)`.
  7. Ergonomic Dual Grips: Pistol grip at `[9, 20, 12, 27]` and foregrip at `[18, 20, 21, 26]`.

---

### 2.3 Companion Drones Drawing Algorithms

#### 1. Combat Drone (`drone_combate.png` — 32x32)
- **Palette**: Stealth Carbon `(42, 46, 56, 255)`, Gunmetal `(75, 82, 95, 255)`, Crimson Red Accents `(235, 30, 50, 255)`, Laser Eye `(255, 0, 40, 255)`.
- **Algorithm**:
  1. Wingtip Rotor Blur Discs: Left `draw.ellipse([1, 6, 8, 10], fill=(120, 140, 160, 100))`, Right `draw.ellipse([23, 6, 30, 10], fill=(120, 140, 160, 100))` with center spin hubs.
  2. Stealth Delta Hull: `draw.polygon([(15, 3), (28, 14), (22, 23), (9, 23), (3, 14)], fill=(42, 46, 56, 255), outline=(20, 22, 28, 255))`
  3. Twin Blaster Barrels: Left `draw.rectangle([8, 17, 11, 27], fill=(160, 170, 185, 255), outline=(40, 45, 55, 255))` with red heat tips, Right `draw.rectangle([20, 17, 23, 27], fill=(160, 170, 185, 255), outline=(40, 45, 55, 255))`.
  4. Crimson Chevron Armor Plate: `draw.polygon([(15, 7), (23, 15), (15, 19), (8, 15)], fill=(235, 30, 50, 255))`
  5. Threat Sensor Visor / Red Laser Eye: `draw.ellipse([13, 12, 18, 16], fill=(255, 0, 40, 255))` with white pupil `(15, 13)`.
  6. Twin Rear Plasma Thrusters: Glowing orange micro-jets at `(11, 24)` and `(20, 24)`.

#### 2. Healing Drone (`drone_cura.png` — 32x32)
- **Palette**: Bio-Ceramic White `(245, 250, 255, 255)`, Medical Green `(30, 215, 90, 255)`, Bio-Aura `(50, 230, 110, 80)`, Nano-Tank Cyan `(0, 210, 230, 200)`.
- **Algorithm**:
  1. Translucent Bio-Aura Halo: `draw.ellipse([2, 3, 29, 28], outline=(50, 230, 110, 80), width=2)`
  2. Stabilizing Rotor Ring: 3 spinning aerogel blades radiating from chassis.
  3. Main Rounded Pod Hull: `draw.ellipse([6, 6, 25, 24], fill=(245, 250, 255, 255), outline=(130, 160, 175, 255), width=2)`
  4. Glass Nano-Canister Reservoir: `draw.rounded_rectangle([11, 16, 20, 23], radius=2, fill=(0, 210, 230, 200))` with fluid meniscus line.
  5. Medical Cross Insignia: Vertical `draw.rectangle([14, 8, 17, 16], fill=(30, 215, 90, 255))`, Horizontal `draw.rectangle([10, 11, 21, 13], fill=(30, 215, 90, 255))`.
  6. Underslung Nanite Spray Dispenser: Nozzle at `[15, 24, 16, 28]` with 2 green sparkle emitter points at `(14, 29)` and `(17, 30)`.
  7. Top Beacon: Amber LED at `(15, 5)` in `(255, 210, 40, 255)`.

#### 3. Support Drone (`drone_suporte.png` — 32x32)
- **Palette**: Deep Cobalt `(25, 45, 95, 255)`, Electric Cyan `(0, 225, 255, 255)`, Shield Forcefield `(0, 180, 255, 110)`, Gold Comms `(255, 215, 40, 255)`.
- **Algorithm**:
  1. Elliptical Forcefield Ring: `draw.ellipse([2, 3, 29, 28], outline=(0, 180, 255, 110), width=2)` with energy nodes.
  2. 3 Orbital Satellite Emitter Pips: Diamond nodes at `(4, 7)`, `(27, 7)`, `(15, 28)` linked by thin cyan energy arcs.
  3. Hexagonal Dielectric Chassis Core: `draw.polygon([(15, 7), (24, 12), (24, 20), (15, 25), (7, 20), (7, 12)], fill=(25, 45, 95, 255), outline=(0, 225, 255, 255), width=1)`
  4. Concentric High-Voltage Capacitor Coil: Center diamond pulsing with gold `(255, 215, 40)` and white energy.
  5. Dual Phased-Array Satellite Dishes: Left antenna `draw.line([10, 8, 5, 3], fill=(255, 215, 40, 255), width=1)` with dish arc; Right antenna `draw.line([21, 8, 26, 3], fill=(255, 215, 40, 255), width=1)` with dish arc.

---

### 2.4 UI Configuration Cards Suite (160x220)

| Card Asset | Path | Palette & Identity | Special Visual Features |
|---|---|---|---|
| **Normal / Available** | `assets/ui/cards/card_config_normal.png` | Dark Acrylic Slate `(18, 22, 30)` + Neon Cyan `(0, 200, 255)` | Chamfered corners, cyan tech brackets, dual stat/flavor text recesses, potato watermark. |
| **Unlocked** | `assets/ui/cards/card_config_unlocked.png` | Royal Navy `(24, 32, 48)` + Imperial Gold `(255, 215, 0)` | Gold border (2px), golden header banner, unlocked padlock glyph, emerald circuit side-lines. |
| **Locked** | `assets/ui/cards/card_config_locked.png` | Charcoal Iron `(14, 16, 20)` + Hazard Yellow/Black Stripes | Caution diagonal tape across header, darkened recessed frame, heavy closed padlock watermark. |
| **Active Buff** | `assets/ui/cards/card_config_active.png` | Overdrive Crimson `(40, 16, 20)` + Neon Amber `(255, 130, 20)` | Warning chevrons, amber corona glow around icon slot, green "+BUFF ACTIVE" badge highlight. |
| **Hover / Focus** | `assets/ui/cards/card_config_hover.png` | High-Tech Slate `(32, 42, 60)` + Radiant White-Cyan | Pulsing border reticles, highlighted top specular sheen, golden corner brackets. |
| **Category Ribbon** | `assets/ui/cards/card_category_header.png` | Chamfered 240x36 Header Badge | Angled trapezoid badge with cyan border and glowing LED category slot. |

---

### 2.5 Generic Config Icons Suite (32x32, 24x24, 16x16)

All generic icons will be generated in `assets/ui/icones_genericos/` with crisp anti-aliasing and pixel-art clarity:

1. `icon_gear.png` — 8-tooth industrial gear with beveled metallic rim and cyan axle.
2. `icon_speaker.png` — Sound cone speaker with expanding concentric soundwave arcs.
3. `icon_display.png` — CRT/LCD monitor bezel with pedestal stand and glowing matrix grid.
4. `icon_gamepad.png` — Console gamepad with directional cross pad and 4 colored action buttons.
5. `icon_crosshair.png` — Segmented targeting reticle with bright crimson center point.
6. `icon_shield.png` — Heater shield with metallic border and central reinforcement diamond.
7. `icon_heart.png` — Classic arcade cardioid heart with gloss specular highlight.
8. `icon_wrench.png` — 45-degree angled pipe wrench with adjustable jaw teeth.
9. `icon_lock.png` — Solid gold padlock body with steel U-shackle locked.
10. `icon_unlock.png` — Open padlock with shackle unlatched and green status light.
11. `icon_checkmark.png` — Bold emerald tick mark with 3D drop shadow.
12. `icon_arrow_left.png`, `icon_arrow_right.png`, `icon_arrow_up.png`, `icon_arrow_down.png` — Neon directional navigation arrows.
13. `icon_battery.png` — Battery cell with terminal and 3-level colored charge gauge.
14. `icon_cpu.png` — Microprocessor chip with quad-side gold pins and silicon die.
15. `icon_sliders.png` — 3 equalizer slider channels with horizontal fader knobs.
16. `icon_eye.png` & `icon_eye_closed.png` — High-tech optic sensor open/slashed.
17. `icon_warning.png` — Hazard yellow caution triangle with exclamation mark.
18. `icon_potato_tech.png` — Mascot cybernetic potato emblem with glowing cyan eye.
19. `icon_filtro_daltonico.png` — Tripartite RGB overlapping colorblindness lens disc.

---

## 3. Caveats

1. **PPlay Virtual Buffer Scaling**:
   PowerPPlay 2.0 uses integer pixel-art scaling from the virtual resolution to the monitor's physical display. All sprites must maintain clean 1px or 2px line weights to avoid subpixel artifacting when scaled up by 2x or 3x.
2. **Backwards Compatibility**:
   Existing legacy asset paths (such as `ui/card_upgrade_bg.png` and `ui/icones_configs/*`) must remain intact and generated alongside the new expanded modular folders (`ui/cards/` and `ui/icones_genericos/`) so existing scene files (`level_up.py`, `hud.py`) continue to function without breaking.
3. **Execution Environment**:
   `tools/gerador_assets.py` must only require standard library modules (`os`, `math`, `struct`, `wave`, `random`) and `Pillow` (`PIL.Image`, `PIL.ImageDraw`), ensuring clean headless execution in any Python 3.10+ environment without external graphical display dependencies.

---

## 4. Conclusion

The formulated PIL procedural rendering architecture expands the game's asset pipeline to fully support Phases 2, 3, and 4. It provides:
- **7 distinct, highly recognizable weapon sprites** with custom silhouettes and palette themes.
- **3 uniquely stylized companion drone sprites** with active visual roles (combat, healing, support).
- **6 comprehensive UI card variants & category ribbons** with cybernetic potato aesthetic.
- **20+ crisp generic configuration and navigation glyphs**.

This technical blueprint is ready for immediate drop-in implementation into `tools/gerador_assets.py`.

---

## 5. Verification Method

To verify the procedural generation implementation once updated in `tools/gerador_assets.py`:

```powershell
# 1. Run the asset generator
python tools/gerador_assets.py

# 2. Verify all generated assets exist and are non-empty
python -c "
import os
assets = [
    'assets/sprites/armas/arma_shotgun.png',
    'assets/sprites/armas/arma_minigun.png',
    'assets/sprites/armas/arma_foguetes.png',
    'assets/sprites/equipamentos/drone_cura.png',
    'assets/sprites/equipamentos/drone_combate.png',
    'assets/sprites/equipamentos/drone_suporte.png',
    'assets/ui/cards/card_config_normal.png',
    'assets/ui/cards/card_config_unlocked.png',
    'assets/ui/cards/card_config_locked.png',
    'assets/ui/cards/card_config_active.png',
    'assets/ui/icones_genericos/icon_gear.png',
    'assets/ui/icones_genericos/icon_speaker.png',
    'assets/ui/icones_genericos/icon_display.png',
    'assets/ui/icones_genericos/icon_gamepad.png',
    'assets/ui/icones_genericos/icon_shield.png',
    'assets/ui/icones_genericos/icon_potato_tech.png'
]
for p in assets:
    assert os.path.isfile(p) and os.path.getsize(p) > 0, f'Missing or empty: {p}'
print('ALL PROCEDURAL ASSETS VERIFIED SUCCESSFULLY!')
"
```
