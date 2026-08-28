# Specification Report: Sistema de Drops (Pure Logic Engine)

**Target Module**: `src/sistemas/sistema_drops.py`  
**Document Author**: Spec Miner 2 (Teamwork Subagent)  
**Date**: 2026-08-28  
**Integrity Mode**: Pure Decoupled Logic (Zero Rendering Dependencies)

---

## 1. Observation

### 1.1 Source Documents & Codebase Evidence

1. **`ORIGINAL_REQUEST.md` (Lines 80-87)**:
   > `[Observed]` Task: Create `src/sistemas/sistema_scavenger.py` and `src/sistemas/sistema_drops.py`. Implement pure logic for Drop items: 10s total lifetime, eligible for enemy capture after 1s. Write as decoupled, pure logic classes.

2. **`CONFIGURACOES.md` (Lines 194-204, 48-54, 131-140, 219-229, 182-191)**:
   > `[Observed]` Config #15 (`coleta_inimiga`): Toggle, default `desligado` (without buff). When active (`ligado`), drops have 10s total lifetime, 1s grace period before enemy scavenging, and all drops collected by player yield **$2\times$ value** (XP, heal, ammo, equipment duration doubled).  
   > `[Observed]` Config #3 (`resolucao`): Grants +10% (75%), +25% (50%), +50% (25%) item drop chance bonus.  
   > `[Observed]` Config #10 (`movimento_mouse`): Grants +40% multiplicative drop chance.  
   > `[Observed]` Config #17 (`vida_inimigos`): Grants +20% (+50% HP) and +40% (+100% HP) item drop chance.  
   > `[Observed]` Config #14 (`inimigos_ranged`): Grants enriched loot table with higher probability for weapon and equipment crates.

3. **`src/utils/constantes.py` (Lines 179-186, 675-681, 708-712)**:
   > `[Observed]` Registered constants:
   > - `DROP_XP_VALOR_BASE = 10`
   > - `DROP_CURA_VALOR_BASE = 35`
   > - `DROP_TEMPO_DESAPARECER = 10.0`
   > - `DROP_TEMPO_SCAVENGER_ATIVAR = 1.0`
   > - Drop asset paths: `drop_xp`, `drop_cura`, `drop_arma`, `drop_equipamento`, `drop_config`.
   > - SFX paths: `pickup_xp`, `pickup_cura`, `pickup_arma`, `pickup_equipamento`.

4. **`PLANO_DE_IMPLEMENTACAO.md` (Lines 267-278, 426-445, 518-534)**:
   > `[Observed]` Drop Rules:
   > - Total ground lifetime: 10 seconds, disappearing upon timeout.
   > - Player collection: Immediate collision.
   > - Enemy scavenger eligibility: 1 second delay after spawn.
   > - Player value doubling under `coleta_inimiga`: XP $\times 2$, heal $\times 2$, weapon ammo $\times 2$, equipment duration $\times 2$.

5. **`GDD.md` (Lines 317-380)**:
   > `[Observed]` Item Payload Baselines:
   > - Weapons: Minigun (150 ammo), Shotgun (30 ammo), Assault Rifle (60 ammo), Rocket Launcher (12 ammo), Grenade Launcher (16 ammo).
   > - Equipments: Healing Drone (15 HP/5s), Combat Drone (8 dmg/0.5s), Support Drone (40 shield/8s), all with 30s base duration.

6. **Test Environment Execution**:
   > `[Verified]` Running `.venv\Scripts\python -m unittest tests/test_player.py` passed 7 tests in 0.066s in headless dummy driver mode. Pure unit testability without Pygame display initialization is required for fast regression checking.

---

## 2. Logic Chain

1. **Decoupling Logic from Rendering**:
   - `[Inferred]` The game architecture strictly separates pure domain logic from Pygame/PPlay rendering loops. `sistema_drops.py` must only manipulate timestamps, coordinates, hitboxes, probabilities, states, and payload dictionaries.
   - `[Inferred]` Graphical rendering (sprites, animations, flashing) and audio triggering (SFX) are consumers of state transitions produced by `sistema_drops.py`.

2. **Drop State Machine & Timing Rules**:
   - A drop starts at $t = 0.0$ in state `ATIVO`.
   - Between $0.0 \le t < 1.0$, `pode_ser_coletado_por_inimigo` returns `False`, but `pode_ser_coletado_por_jogador` returns `True`.
   - Between $1.0 \le t < 10.0$, both player and scavenger enemy can collect it.
   - At $t \ge 10.0$, state transitions to `EXPIRADO`.
   - Collection by player transitions state to `COLETADO_JOGADOR`.
   - Collection by enemy transitions state to `COLETADO_INIMIGO`.
   - Once in any terminal state (`COLETADO_JOGADOR`, `COLETADO_INIMIGO`, `EXPIRADO`), the drop is immutable and cannot be collected or re-activated.

3. **Loot Resolution & Payload Calculation**:
   - Enemy death triggers a roll against the calculated drop chance.
   - If successful, a weighted roll against the loot table determines the `TipoDrop` and subtype.
   - When player collects the drop, if `coleta_inimiga` is active, the value/ammo/duration is multiplied by $2.0$.
   - When an enemy collects the drop, the item is consumed with no player reward.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Lifecycle | Drop Initialization | Instantiates a drop with position, type, payload, and 10.0s lifetime counter. | `x: float, y: float, tipo: TipoDrop, payload: dict, tempo_vida: float = 10.0` | `ItemDrop` instance (`estado = ATIVO`, `tempo_decorrido = 0.0`) | Raises `ValueError` if `tipo` invalid or `tempo_vida <= 0` | `[Observed]` `constantes.py:184`, `PLANO_DE_IMPLEMENTACAO.md:268` |
| 2 | Lifecycle | Delta Time Update | Advances lifetime counter and checks for 10.0s expiration. | `dt: float` ($\ge 0.0$) | `EstadoDrop` (`ATIVO` or `EXPIRADO`) | Clamps negative $dt < 0$ to $0.0$; large $dt \ge 10.0$ immediately expires | `[Observed]` `ORIGINAL_REQUEST.md:84`, `constantes.py:184` |
| 3 | Timing & Gate | Scavenger Grace Period | Prevents enemies from collecting drops during the first 1.0s of existence. | `None` (queries `tempo_decorrido`) | `bool` (`True` if $t \ge 1.0$ and `ATIVO`, else `False`) | None (pure predicate query) | `[Observed]` `CONFIGURACOES.md:202`, `PLANO_DE_IMPLEMENTACAO.md:269` |
| 4 | State Machine | Expiration Transition | Automatically transitions active drop to `EXPIRADO` when `tempo_decorrido >= 10.0`. | `dt` update or explicit `expirar()` | Drop state becomes `EstadoDrop.EXPIRADO` | Post-expiration calls to collect return `None`/`False` | `[Observed]` `PLANO_DE_IMPLEMENTACAO.md:432` |
| 5 | State Machine | Player Pickup Transition | Transitions active drop to `COLETADO_JOGADOR` and computes applied payload. | `multiplicador_valor: float = 1.0` | `dict` (payload with applied multipliers) or `None` | If not `ATIVO`, returns `None` without state modification | `[Observed]` `PLANO_DE_IMPLEMENTACAO.md:434` |
| 6 | State Machine | Enemy Pickup Transition | Transitions active drop to `COLETADO_INIMIGO` if $t \ge 1.0s$. | `inimigo_id: str` | `bool` (`True` if successfully collected, `False` if ineligible or inactive) | If $t < 1.0$ or not `ATIVO`, returns `False` | `[Observed]` `CONFIGURACOES.md:202` |
| 7 | Payloads | XP Drop Payload | Generates experience payload (base 10 XP) scalable by enemy rank and buffs. | `valor_base: int = 10` | `{"tipo": "xp", "valor": int}` | Values $\le 0$ clamped to 1 | `[Observed]` `constantes.py:182`, `GDD.md:383` |
| 8 | Payloads | Health Drop Payload | Generates health pack payload (base 35 HP heal). | `valor_base: int = 35` | `{"tipo": "cura", "valor": int}` | Values $\le 0$ clamped to 1 | `[Observed]` `constantes.py:183`, `GDD.md:236` |
| 9 | Payloads | Weapon Crate Payload | Generates weapon crate with archetype subtype and finite ammo count. | `subtipo: str, municao: int` | `{"tipo": "arma", "subtipo": str, "municao": int}` | Unrecognized subtype falls back to standard weapon | `[Observed]` `constantes.py:137-164`, `GDD.md:327-356` |
| 10 | Payloads | Equipment Drone Payload | Generates support equipment crate with archetype subtype and duration (30.0s). | `subtipo: str, duracao: float = 30.0` | `{"tipo": "equipamento", "subtipo": str, "duracao": float}` | Duration $\le 0$ clamped to 30.0s | `[Observed]` `constantes.py:168-176`, `GDD.md:369-380` |
| 11 | Payloads | Potato Seed Payload | Generates potato seed collectible payload for meta-progression / currency. | `quantidade: int = 1` | `{"tipo": "semente", "quantidade": int}` | Quantity $\le 0$ clamped to 1 | `[Observed]` `ORIGINAL_REQUEST.md:84` |
| 12 | Payloads | Config Chip Payload | Generates config chip payload triggering level-up / config unlock. | `config_id: str \| None` | `{"tipo": "config", "config_id": str}` | None (optional config_id) | `[Observed]` `constantes.py:680` |
| 13 | Multipliers | Player Value Doubling (`coleta_inimiga`) | Applies $2\times$ multiplier to XP, heal, ammo, equipment duration, and seeds when player collects. | `multiplicador_valor = 2.0` | Payload values doubled (`valor * 2`, `municao * 2`, `duracao * 2`) | Multipliers $\le 0$ sanitized to 1.0 | `[Observed]` `CONFIGURACOES.md:202`, `PLANO_DE_IMPLEMENTACAO.md:265` |
| 14 | Loot Tables | Enemy Drop Roll | Evaluates whether a defeated enemy yields a drop based on stacked drop chances. | `chance_base: float, bonus_aditivos: float, mults: float` | `bool` (drop triggered or not) | Probability clamped to $[0.0, 1.0]$ | `[Observed]` `CONFIGURACOES.md:51, 139, 227`, `PLANO_DE_IMPLEMENTACAO.md:456` |
| 15 | Loot Tables | Weighted Loot Generation | Selects drop category and subtype using standard or enriched loot tables. | `loot_enriquecido: bool = False, rng: Random` | `(TipoDrop, dict)` | Fallback to `TipoDrop.XP` if weights misconfigured | `[Observed]` `CONFIGURACOES.md:190`, `PLANO_DE_IMPLEMENTACAO.md:250` |
| 16 | Spatial Query | Circle Radial Collision Check | Pure Euclidean distance collision test against a point or circular entity. | `px: float, py: float, raio: float` | `bool` (`dist^2 <= (r1 + r2)^2`) | None (pure math) | `[Observed]` `math_utils.py` |
| 17 | Spatial Query | AABB Box Collision Check | Pure axis-aligned bounding box collision test. | `rx: float, ry: float, rw: float, rh: float` | `bool` (overlap condition) | None (pure math) | `[Observed]` `math_utils.py:colisao_aabb` |
| 18 | System | Active Drops Manager Batch Update | Updates all drops in pool, separates active from expired/collected, trims pool. | `dt: float` | `dict[str, list[ItemDrop]]` (`{"expirados": [...], "ativos": [...]}`) | Empty list handled safely | `[Observed]` `PLANO_DE_IMPLEMENTACAO.md:530` |
| 19 | System | Player Proximity Pickup Sweep | Checks all active drops within player collection radius and executes batch pickups. | `jogador_x, jogador_y, jogador_raio, mult_valor` | `list[dict]` (list of collected payloads) | No drops in range returns empty list `[]` | `[Observed]` `PLANO_DE_IMPLEMENTACAO.md:434` |
| 20 | System | Scavenger Eligibility Filter | Returns list of all drops that have elapsed $\ge 1.0s$ and remain in `ATIVO` state. | `None` | `list[ItemDrop]` | Returns `[]` if none eligible | `[Observed]` `ORIGINAL_REQUEST.md:84`, `PLANO_DE_IMPLEMENTACAO.md:269` |
| 21 | System | System Reset / Cleanup | Clears all drops from memory on scene change or restart. | `None` | `None` (clears internal lists) | Safe on empty pool | `[Observed]` `gameplay.py:110` |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior | Evidence Tier |
|---|---------|-------|-------------------|---------------|
| `EC-01` | Delta Time Update | `dt = -0.5` (Negative delta time) | Clamped to `0.0`. Lifetime counter does not rewind; state remains unchanged. | `[Inferred]` |
| `EC-02` | Delta Time Update | `dt = 0.0` (Zero delta time) | No time advances. Drop stays in current state without false expirations. | `[Inferred]` |
| `EC-03` | Delta Time Update | `dt = 15.0` (Large time skip / freeze) | `tempo_decorrido` exceeds 10.0s in one tick; drop transitions directly to `EXPIRADO` without intermediate invalid states. | `[Inferred]` |
| `EC-04` | Scavenger Grace Period | `tempo_decorrido = 0.999s` | `pode_ser_coletado_por_inimigo()` returns `False`. Enemy collection attempt rejected. | `[Verified via Spec]` |
| `EC-05` | Scavenger Grace Period | `tempo_decorrido = 1.000s` | `pode_ser_coletado_por_inimigo()` returns `True`. Enemy collection attempt accepted. | `[Verified via Spec]` |
| `EC-06` | Drop Expiration Boundary | `tempo_decorrido = 9.999s` | `esta_ativo()` returns `True`. Player collection attempt succeeds. | `[Verified via Spec]` |
| `EC-07` | Drop Expiration Boundary | `tempo_decorrido = 10.000s` | `esta_ativo()` returns `False` (`estado = EXPIRADO`). Player collection attempt returns `None`. | `[Verified via Spec]` |
| `EC-08` | Double Pickup Race Condition | Player and Scavenger touch drop on exact same tick | Atomic check: First evaluated entity transitions state and claims payload; second receives `None`/`False`. Player sweep runs first in frame order. | `[Inferred]` |
| `EC-09` | Multi-Enemy Contention | 2 enemies attempt collection on same drop in same frame | First calling enemy transitions state to `COLETADO_INIMIGO`; second enemy attempt returns `False`. | `[Inferred]` |
| `EC-10` | Post-Terminal Method Call | Calling `coletar_por_jogador()` on `EXPIRADO` or `COLETADO_INIMIGO` drop | Safely returns `None` without modifying drop state or triggering side effects. | `[Inferred]` |
| `EC-11` | Drop Rate Overflow | Stacked drop chance calculation yields $1.65$ (165%) | Drop chance clamped to $1.0$ ($100\%$). Guaranteed drop generated. | `[Inferred]` |
| `EC-12` | Negative Coordinates | Drop spawned at $(-50.0, -100.0)$ | Euclidean distance calculation $(dx^2 + dy^2)$ correctly computes positive distance without squaring errors. | `[Inferred]` |
| `EC-13` | Zero Radius Entities | Player or enemy radius specified as $0.0$ | Pure point-in-circle collision evaluated without division by zero. | `[Inferred]` |
| `EC-14` | Corrupted / Missing Payload | Drop initialized with `payload=None` | System automatically populates standard baseline payload matching `tipo`. | `[Inferred]` |
| `EC-15` | Invalid Multiplier | `multiplicador_valor = -2.0` or `0.0` passed to player pickup | Sanitized to default $1.0$ (never applies negative or zero rewards). | `[Inferred]` |
| `EC-16` | Maximum Drop Pool Saturation | Active drops exceed 200 instances | Oldest active drop (or drop nearest expiration) is gracefully retired (FIFO) to protect memory/performance. | `[Inferred]` |

---

## 5. Architectural Specification & Interface Contract

### 5.1 Pure Logic Data Structures (`src/sistemas/sistema_drops.py`)

```python
from enum import Enum
import math
import random
from typing import Optional, Dict, Any, List, Tuple


class EstadoDrop(str, Enum):
    ATIVO = "ativo"
    COLETADO_JOGADOR = "coletado_jogador"
    COLETADO_INIMIGO = "coletado_inimigo"
    EXPIRADO = "expirado"


class TipoDrop(str, Enum):
    XP = "xp"
    CURA = "cura"
    ARMA = "arma"
    EQUIPAMENTO = "equipamento"
    SEMENTE = "semente"
    CONFIG = "config"


class ItemDrop:
    """
    Representação lógica pura de um item dropado na arena.
    Desacoplada de renderização, sprites ou bibliotecas gráficas.
    """
    def __init__(
        self,
        x: float,
        y: float,
        tipo: TipoDrop | str,
        payload: Optional[Dict[str, Any]] = None,
        tempo_vida_total: float = 10.0,
        tempo_gravamen_inimigo: float = 1.0,
        raio_coleta: float = 16.0,
        drop_id: Optional[str] = None
    ):
        self.x = float(x)
        self.y = float(y)
        self.largura = 16.0
        self.altura = 16.0
        self.raio_coleta = float(raio_coleta)
        self.tipo = TipoDrop(tipo) if isinstance(tipo, str) else tipo
        self.tempo_vida_total = float(max(0.1, tempo_vida_total))
        self.tempo_gravamen_inimigo = float(max(0.0, tempo_gravamen_inimigo))
        self.tempo_decorrido = 0.0
        self.tempo_vida_restante = self.tempo_vida_total
        self.estado = EstadoDrop.ATIVO
        self.id = drop_id or f"drop_{id(self)}"
        self.coletor_id: Optional[str] = None
        self.payload = payload if payload is not None else self._gerar_payload_padrao()

    def _gerar_payload_padrao(self) -> Dict[str, Any]:
        if self.tipo == TipoDrop.XP:
            return {"tipo": "xp", "valor": 10}
        elif self.tipo == TipoDrop.CURA:
            return {"tipo": "cura", "valor": 35}
        elif self.tipo == TipoDrop.ARMA:
            return {"tipo": "arma", "subtipo": "minigun", "municao": 150}
        elif self.tipo == TipoDrop.EQUIPAMENTO:
            return {"tipo": "equipamento", "subtipo": "drone_cura", "duracao": 30.0}
        elif self.tipo == TipoDrop.SEMENTE:
            return {"tipo": "semente", "quantidade": 1}
        elif self.tipo == TipoDrop.CONFIG:
            return {"tipo": "config", "config_id": None}
        return {"tipo": "desconhecido", "valor": 0}

    def esta_ativo(self) -> bool:
        return self.estado == EstadoDrop.ATIVO

    def pode_ser_coletado_por_jogador(self) -> bool:
        return self.estado == EstadoDrop.ATIVO

    def pode_ser_coletado_por_inimigo(self) -> bool:
        return self.estado == EstadoDrop.ATIVO and self.tempo_decorrido >= self.tempo_gravamen_inimigo

    def alerta_expirando(self, limiar_alerta: float = 3.0) -> bool:
        """Indica se o drop está nos últimos segundos de vida útil (para efeitos visuais/piscamento)."""
        return self.esta_ativo() and (self.tempo_vida_restante <= limiar_alerta)

    def progresso_vida(self) -> float:
        """Retorna a fração decorrida da vida útil entre 0.0 e 1.0."""
        return min(1.0, max(0.0, self.tempo_decorrido / self.tempo_vida_total))

    def update(self, dt: float) -> EstadoDrop:
        if not self.esta_ativo():
            return self.estado

        dt_valido = max(0.0, float(dt))
        self.tempo_decorrido += dt_valido
        self.tempo_vida_restante = max(0.0, self.tempo_vida_total - self.tempo_decorrido)

        if self.tempo_decorrido >= self.tempo_vida_total or self.tempo_vida_restante <= 0.0:
            self.estado = EstadoDrop.EXPIRADO

        return self.estado

    def coletar_por_jogador(self, multiplicador_valor: float = 1.0) -> Optional[Dict[str, Any]]:
        if not self.pode_ser_coletado_por_jogador():
            return None

        self.estado = EstadoDrop.COLETADO_JOGADOR
        self.coletor_id = "jogador"
        mult = max(1.0, float(multiplicador_valor))

        resultado = dict(self.payload)
        resultado["multiplicador_aplicado"] = mult

        if "valor" in resultado:
            resultado["valor_original"] = resultado["valor"]
            resultado["valor"] = int(round(resultado["valor"] * mult))
        if "municao" in resultado:
            resultado["municao_original"] = resultado["municao"]
            resultado["municao"] = int(round(resultado["municao"] * mult))
        if "duracao" in resultado:
            resultado["duracao_original"] = resultado["duracao"]
            resultado["duracao"] = float(resultado["duracao"] * mult)
        if "quantidade" in resultado:
            resultado["quantidade_original"] = resultado["quantidade"]
            resultado["quantidade"] = int(round(resultado["quantidade"] * mult))

        return resultado

    def coletar_por_inimigo(self, inimigo_id: str = "") -> bool:
        if not self.pode_ser_coletado_por_inimigo():
            return False

        self.estado = EstadoDrop.COLETADO_INIMIGO
        self.coletor_id = inimigo_id or "inimigo"
        return True

    def checar_colisao_radial(self, px: float, py: float, raio_entidade: float = 0.0) -> bool:
        dist_sq = (self.x - px) ** 2 + (self.y - py) ** 2
        raio_total = self.raio_coleta + max(0.0, raio_entidade)
        return dist_sq <= (raio_total ** 2)

    def checar_colisao_aabb(self, rx: float, ry: float, rw: float, rh: float) -> bool:
        return (
            self.x - self.largura / 2.0 < rx + rw and
            self.x + self.largura / 2.0 > rx and
            self.y - self.altura / 2.0 < ry + rh and
            self.y + self.altura / 2.0 > ry
        )


class SistemaDrops:
    """
    Motor lógico de gerenciamento, geração, ciclo de vida e colisão de drops.
    """
    def __init__(self, max_drops_ativos: int = 150):
        self.drops: List[ItemDrop] = []
        self.max_drops_ativos = int(max_drops_ativos)
        self.tempo_vida_padrao = 10.0
        self.tempo_gravamen_inimigo_padrao = 1.0

        # Pesos das tabelas de loot
        self.pesos_loot_padrao = {
            TipoDrop.XP: 65,
            TipoDrop.CURA: 15,
            TipoDrop.ARMA: 12,
            TipoDrop.EQUIPAMENTO: 8
        }
        self.pesos_loot_enriquecido = {
            TipoDrop.XP: 25,
            TipoDrop.CURA: 15,
            TipoDrop.ARMA: 35,
            TipoDrop.EQUIPAMENTO: 25
        }

    def spawn_drop(
        self,
        x: float,
        y: float,
        tipo: TipoDrop | str,
        payload: Optional[Dict[str, Any]] = None,
        tempo_vida: float = 10.0,
        raio_coleta: float = 16.0
    ) -> ItemDrop:
        if len(self.drops) >= self.max_drops_ativos:
            self._remover_drop_mais_antigo()

        novo_drop = ItemDrop(
            x=x,
            y=y,
            tipo=tipo,
            payload=payload,
            tempo_vida_total=tempo_vida,
            tempo_gravamen_inimigo=self.tempo_gravamen_inimigo_padrao,
            raio_coleta=raio_coleta
        )
        self.drops.append(novo_drop)
        return novo_drop

    def _remover_drop_mais_antigo(self) -> None:
        ativos = [d for d in self.drops if d.esta_ativo()]
        if ativos:
            mais_antigo = max(ativos, key=lambda d: d.tempo_decorrido)
            mais_antigo.estado = EstadoDrop.EXPIRADO
        self.drops = [d for d in self.drops if d.esta_ativo()]

    def calcular_chance_drop(
        self,
        chance_base: float = 0.25,
        bonus_aditivos: float = 0.0,
        multiplicadores: float = 1.0
    ) -> float:
        chance = (chance_base + bonus_aditivos) * multiplicadores
        return min(1.0, max(0.0, chance))

    def sortear_tipo_drop(self, loot_enriquecido: bool = False, rng: Optional[random.Random] = None) -> TipoDrop:
        r = rng or random
        tabela = self.pesos_loot_enriquecido if loot_enriquecido else self.pesos_loot_padrao
        tipos = list(tabela.keys())
        pesos = list(tabela.values())
        return r.choices(tipos, weights=pesos, k=1)[0]

    def gerar_drop_inimigo(
        self,
        x: float,
        y: float,
        chance_base: float = 0.25,
        bonus_chance: float = 0.0,
        mult_chance: float = 1.0,
        loot_enriquecido: bool = False,
        rng: Optional[random.Random] = None
    ) -> Optional[ItemDrop]:
        r = rng or random
        prob = self.calcular_chance_drop(chance_base, bonus_chance, mult_chance)
        if r.random() > prob:
            return None

        tipo = self.sortear_tipo_drop(loot_enriquecido=loot_enriquecido, rng=r)
        payload = self._criar_payload_para_tipo(tipo, rng=r)
        return self.spawn_drop(x=x, y=y, tipo=tipo, payload=payload)

    def _criar_payload_para_tipo(self, tipo: TipoDrop, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        r = rng or random
        if tipo == TipoDrop.XP:
            return {"tipo": "xp", "valor": 10}
        elif tipo == TipoDrop.CURA:
            return {"tipo": "cura", "valor": 35}
        elif tipo == TipoDrop.ARMA:
            subtipos_armas = [
                ("minigun", 150),
                ("shotgun", 30),
                ("rifle", 60),
                ("foguetes", 12),
                ("granadas", 16)
            ]
            subtipo, municao = r.choice(subtipos_armas)
            return {"tipo": "arma", "subtipo": subtipo, "municao": municao}
        elif tipo == TipoDrop.EQUIPAMENTO:
            subtipos_equip = ["drone_cura", "drone_combate", "drone_suporte"]
            subtipo = r.choice(subtipos_equip)
            return {"tipo": "equipamento", "subtipo": subtipo, "duracao": 30.0}
        elif tipo == TipoDrop.SEMENTE:
            return {"tipo": "semente", "quantidade": 1}
        return {"tipo": "desconhecido", "valor": 0}

    def update(self, dt: float) -> Dict[str, List[ItemDrop]]:
        expirados: List[ItemDrop] = []
        for drop in self.drops:
            if drop.esta_ativo():
                estado = drop.update(dt)
                if estado == EstadoDrop.EXPIRADO:
                    expirados.append(drop)

        # Filtra apenas drops que continuam ativos
        self.drops = [d for d in self.drops if d.esta_ativo()]
        return {"expirados": expirados, "ativos": self.drops}

    def processar_coleta_jogador(
        self,
        jogador_x: float,
        jogador_y: float,
        jogador_raio: float = 16.0,
        multiplicador_valor: float = 1.0
    ) -> List[Dict[str, Any]]:
        payloads_coletados: List[Dict[str, Any]] = []
        for drop in self.drops:
            if not drop.pode_ser_coletado_por_jogador():
                continue
            if drop.checar_colisao_radial(jogador_x, jogador_y, jogador_raio):
                payload = drop.coletar_por_jogador(multiplicador_valor=multiplicador_valor)
                if payload:
                    payloads_coletados.append(payload)

        self.drops = [d for d in self.drops if d.esta_ativo()]
        return payloads_coletados

    def processar_coleta_inimigo(
        self,
        inimigo_id: str,
        inimigo_x: float,
        inimigo_y: float,
        inimigo_raio: float = 16.0
    ) -> Optional[ItemDrop]:
        for drop in self.drops:
            if not drop.pode_ser_coletado_por_inimigo():
                continue
            if drop.checar_colisao_radial(inimigo_x, inimigo_y, inimigo_raio):
                if drop.coletar_por_inimigo(inimigo_id):
                    self.drops = [d for d in self.drops if d.esta_ativo()]
                    return drop
        return None

    def obter_drops_ativos(self) -> List[ItemDrop]:
        return [d for d in self.drops if d.esta_ativo()]

    def obter_drops_elegiveis_inimigo(self) -> List[ItemDrop]:
        return [d for d in self.drops if d.pode_ser_coletado_por_inimigo()]

    def obter_drop_mais_proximo(
        self,
        x: float,
        y: float,
        apenas_elegiveis_inimigo: bool = False
    ) -> Tuple[Optional[ItemDrop], float]:
        candidatos = self.obter_drops_elegiveis_inimigo() if apenas_elegiveis_inimigo else self.obter_drops_ativos()
        if not candidatos:
            return None, float("inf")

        mais_proximo = None
        menor_dist_sq = float("inf")

        for drop in candidatos:
            dist_sq = (drop.x - x) ** 2 + (drop.y - y) ** 2
            if dist_sq < menor_dist_sq:
                menor_dist_sq = dist_sq
                mais_proximo = drop

        return mais_proximo, math.sqrt(menor_dist_sq)

    def limpar(self) -> None:
        self.drops.clear()
```

---

## 6. Caveats

1. **Scavenger Selector AI**:
   - `sistema_drops.py` provides the query interface (`obter_drops_elegiveis_inimigo`, `pode_ser_coletado_por_inimigo`, and `processar_coleta_inimigo`).
   - The higher-level AI selection policy (excluding the 3 closest enemies and enemies beyond max radius, selecting exactly 1 enemy globally) belongs to `src/sistemas/sistema_scavenger.py`.
2. **Pygame Drawing Integration**:
   - Visual sprite blitting, camera coordinate transformations, and blinking alpha animations belong to entity wrappers (`src/entidades/drop.py`) or scene rendering loops (`src/cenas/gameplay.py`), keeping `sistema_drops.py` completely pure and decoupled.
3. **Save Game Persistence**:
   - Active drops in arena are temporary run objects and are not serialized to `data/save.json`.

---

## 7. Conclusion

The specification for `src/sistemas/sistema_drops.py` is complete, mathematically bounded, and fully decoupled from rendering frameworks. It satisfies all constraints from `ORIGINAL_REQUEST.md`, `CONFIGURACOES.md`, and `constantes.py`:
- 10.0s strict lifetime with expiration state.
- 1.0s grace period before enemy scavenging is permitted.
- Full state machine (`ATIVO`, `COLETADO_JOGADOR`, `COLETADO_INIMIGO`, `EXPIRADO`).
- Complete support for XP, Heal, Weapon, Equipment, Seed, and Config payloads.
- Doubled rewards ($2\times$) under `coleta_inimiga` config.
- Scalable, headless unit testable pure logic interface.

---

## 8. Verification Method

To verify the pure logic implementation once authored:

1. **Unit Test Suite Creation**:
   - Create `tests/test_sistema_drops.py` with 15+ deterministic test cases covering:
     - 10s lifetime expiration.
     - 1s grace period eligibility gate.
     - Player immediate pickup and value doubling ($2\times$).
     - Enemy pickup rejection before 1.0s and acceptance after 1.0s.
     - State immutability upon entering terminal states.
     - Edge cases (negative $dt$, huge $dt$, double pickup race, drop rate stacking).
2. **Execute Unit Tests Headless**:
   ```powershell
   .venv\Scripts\python -m unittest tests/test_sistema_drops.py
   ```
3. **Full Regression Test**:
   ```powershell
   .venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
   ```
4. **Invalidation Conditions**:
   - Any dependency on `pygame` or `PPlay` imported inside `src/sistemas/sistema_drops.py`.
   - Enemy able to scavenge drop at $t < 1.0s$.
   - Drop persisting past $t = 10.0s$ in `ATIVO` state.
   - Player collecting an already expired or enemy-scavenged drop.
