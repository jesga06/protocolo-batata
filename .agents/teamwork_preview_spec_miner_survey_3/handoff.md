# Specification Report: Scavenger AI Pure Logic (`src/sistemas/sistema_scavenger.py`)

**Author**: Spec Miner 3  
**Date**: 2026-08-28T15:47:00Z  
**Module Target**: `src/sistemas/sistema_scavenger.py`  
**Related Modules**: `src/sistemas/sistema_drops.py`, `src/entidades/inimigo_base.py`, `src/utils/math_utils.py`, `src/utils/constantes.py`  

---

## 1. Observation

### 1.1 Direct Source Evidence
- **[Observed] `ORIGINAL_REQUEST.md` (Lines 80–86)**:
  > "1. Create `src/sistemas/sistema_scavenger.py` and `src/sistemas/sistema_drops.py`."  
  > "2. Implement the pure logic for Drop items: 10s total lifetime, eligible for enemy capture after 1s."  
  > "3. Implement the Scavenger AI selector: Only 1 enemy globally can capture a drop. Target is selected pseudo-randomly, explicitly EXCLUDING enemies that are too far and EXCLUDING the 3 closest enemies to the drop."  
  > "Constraints: DO NOT touch `src/main.py` or the core entity files. Write these as decoupled, pure logic classes that we will integrate later."

- **[Observed] `CONFIGURACOES.md` (Config #15 `coleta_inimiga`, Lines 194–204)**:
  > - **Categoria**: Dificuldade  
  > - **Tipo**: Alternador (Toggle)  
  > - **Padrão**: Desligado (sem buff)  
  > - **Desligado**: Nenhum (inimigos ignoram completamente todas as caixas e itens no chão)  
  > - **Ligado**: "Ativa a Coleta Inimiga (Scavenger): Após 1s de vida de um drop (tempo total de 10s no chão), 1 inimigo na tela tenta ativamente devorar o drop antes de você (selecionado pseudo-aleatoriamente, excluindo inimigos muito distantes e os 2–3 mais próximos)."  
  > - **Buff**: "Todos os drops coletados pelo jogador valem 2× (XP em dobro, cura em dobro, munição dobrada e dobro de duração/usos de equipamentos)."

- **[Observed] `PLANO_DE_IMPLEMENTACAO.md` (Lines 267–276, 436–445)**:
  > 1. "Drops têm 10 segundos de tempo de vida (depois desaparecem)."  
  > 2. "Após 1 segundo no chão, um drop fica elegível para coleta por inimigos."  
  > 3. "Apenas 1 inimigo por vez na tela inteira pode tentar coletar um drop."  
  > 4. "O inimigo é selecionado pseudo-aleatoriamente, excluindo: Inimigos muito longe do drop (fora de um raio X); Os 2–3 inimigos mais próximos do drop."  
  > 5. "Se o inimigo scavenger morrer antes de chegar ao drop, outro pode ser designado."  
  > 6. "Inimigos coletando drops ainda perseguem o jogador normalmente — eles desviam brevemente rumo ao drop e voltam a perseguir."

- **[Observed] `src/entidades/inimigo_base.py` (Lines 70–95)**:
  > `InimigoBase.update(self, dt: float, pos_alvo: tuple[float, float])` computes beeline unit vector to `pos_alvo`:
  > ```python
  > ux, uy = vetor_direcao(cx, cy, tx, ty)
  > vx = ux * self.velocidade + self.vx_knockback
  > vy = uy * self.velocidade + self.vy_knockback
  > self.x += vx * dt
  > self.y += vy * dt
  > ```
  > This confirms that changing the enemy's destination from player `(px, py)` to drop `(dx, dy)` instantly re-routes the enemy without needing pathfinding modifications.

- **[Observed] `src/utils/math_utils.py` (Lines 9–18, 52–72)**:
  > `distancia(x1, y1, x2, y2)` and `distancia_sq(x1, y1, x2, y2)` are available for Euclidean distance calculation.

---

## 2. Logic Chain

1. **Decoupled Pure Logic Architecture**:
   - The Scavenger system must have **zero imports from Pygame or PPlay**.
   - Input data structures should accept duck-typed objects or pure Python dictionaries/tuples representing enemies and drops with properties `(x, y, vivo/alive, id, largura, altura)`.
   - The random number generator must accept an optional `random.Random` instance or integer seed to allow 100% deterministic unit testing.

2. **Mathematical Candidate Filtering & Selection Algorithm**:
   Let a drop be positioned at $D = (x_D, y_D)$.
   Let the list of active enemies be $E = [e_1, e_2, \dots, e_N]$.
   Let parameters be $R_{\text{max}} = 600.0$ (cutoff radius) and $K = 3$ (closest exclusion count).
   
   - **Step 2.1 — Alive Filter**:
     $$E_{\text{alive}} = \{ e \in E \mid e.\text{vivo} == \text{True} \}$$
   - **Step 2.2 — Distance Calculation & Cutoff**:
     For each $e \in E_{\text{alive}}$, calculate Euclidean distance $d(e, D) = \sqrt{(e.x - x_D)^2 + (e.y - y_D)^2}$ (or center-to-center).
     Filter: $P = \{ (e, d(e, D)) \mid d(e, D) \le R_{\text{max}} \}$.
   - **Step 2.3 — Ascending Sort by Distance**:
     Sort pairs in $P$ in ascending order of distance: $P_{\text{sorted}} = \text{sort}(P, \text{key}=\lambda (e, d): d)$.
     *(Note: Python's `sort` is stable, preserving list index order for equidistant enemies).*
   - **Step 2.4 — Slice $K$ Closest ($[K:]$)**:
     Candidate pool: $P_{\text{candidates}} = P_{\text{sorted}}[K:]$.
     - If $|P_{\text{sorted}}| \le K$, then $P_{\text{candidates}} = []$.
   - **Step 2.5 — Pseudo-Random Selection**:
     - If $P_{\text{candidates}} == []$, return `None` (no scavenger assigned).
     - If $P_{\text{candidates}} \ne []$, choose uniformly at random:
       $$e_{\text{scavenger}} = \text{rng.choice}(P_{\text{candidates}})[0]$$

3. **Global Singleton Constraint & Drop Targeting**:
   - **Rule**: Exactly **1 enemy globally** across the entire arena can be assigned as a scavenger at any given moment.
   - If an assigned scavenger $e_{\text{scavenger}}$ is currently active and alive, and its target drop $D$ is active and uncollected, no new candidate selection is performed.
   - If multiple eligible drops exist simultaneously (drops with $\text{tempo\_vivo} \ge 1.0\text{s}$ and uncollected):
     - Drop selection priority: Oldest eligible drop (highest `tempo_vivo` $< 10.0\text{s}$), because it has the least remaining lifetime before despawn.
     - Alternatively, first eligible drop in collection order.

4. **Scavenger State Machine & Lifecycle Transitions**:
   The scavenger system manages state transitions:

   ```
   [IDLE / NO_SCAVENGER]
         │
         │ (Drop eligible >= 1.0s && Config coleta_inimiga == True && Candidate found)
         ▼
   [HUNTING_DROP] (Scavenger moves towards drop (dx, dy))
         │
         ├──► (Scavenger dies / e.vivo == False) ───────► [IDLE] (Drop freed for new scavenger)
         ├──► (Drop despawns / lifetime >= 10s) ────────► [IDLE] (Enemy reverts to player)
         ├──► (Player collects drop) ───────────────────► [IDLE] (Enemy reverts to player)
         └──► (Scavenger dist <= pickup_radius) ────────► [IDLE] (Drop destroyed; player gets 0; enemy reverts)
   ```

5. **Decoupled API Specification**:
   `SistemaScavenger` class public API:
   - `selecionar_candidato(drop, inimigos, max_distancia=600.0, k_excluir=3, rng=None) -> Any | None`
   - `filtrar_candidatos(drop, inimigos, max_distancia=600.0, k_excluir=3) -> list[tuple[Any, float]]`
   - `atualizar(dt, inimigos, drops, pos_jogador, config_coleta_inimiga=True) -> dict`
   - `obter_posicao_alvo_inimigo(inimigo, pos_jogador) -> tuple[float, float]`
   - `reset()`

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | AI Selection | `filtrar_candidatos` | Pure mathematical candidate filtering: filters alive enemies, computes Euclidean distance, excludes $d > R_{\text{max}}$, sorts ascending, excludes $K=3$ closest | `drop` (object/tuple), `inimigos` (list), `max_distancia` (float), `k_excluir` (int) | `list[tuple[enemy, distance]]` | Returns `[]` if no candidates survive filters | `ORIGINAL_REQUEST.md` (R85), `CONFIGURACOES.md` (#15) |
| 2 | AI Selection | `selecionar_candidato` | Selects a single scavenger candidate uniformly at random from filtered candidate pool | `drop`, `inimigos`, `max_distancia`, `k_excluir`, `rng` (optional `random.Random`) | `enemy` object or `None` | Returns `None` if candidate pool is empty | `ORIGINAL_REQUEST.md` (R85), `PLANO_DE_IMPLEMENTACAO.md` (L271) |
| 3 | AI Selection | Deterministic RNG Support | Supports passing custom seed or `random.Random` instance for 100% reproducible testing | `rng_seed` (int) or `rng` instance | Deterministic candidate selection | Falls back to system default RNG if `None` | `ORIGINAL_REQUEST.md` (R85) |
| 4 | State Machine | Singleton Global Scavenger | Enforces that at most 1 enemy globally across the game arena is scavenging at any given moment | Global system state | `bool` (has active scavenger) | Rejects assigning second scavenger while one is active | `ORIGINAL_REQUEST.md` (R85), `PLANO_DE_IMPLEMENTACAO.md` (L270) |
| 5 | State Machine | Drop Eligibility Check | Ignores drops with `tempo_vivo < 1.0` second (grace period) and drops that are inactive/expired | `drops` list | List of eligible drops (`tempo_vivo >= 1.0` and `ativo`) | Ineligible drops are skipped | `CONFIGURACOES.md` (#15), `PLANO_DE_IMPLEMENTACAO.md` (L269) |
| 6 | State Machine | Scavenger Death Lifecycle | If assigned scavenger enemy dies (`vivo == False`), assignment is cleared; another enemy may be assigned on subsequent ticks | `inimigos` state update | Transition to `IDLE`, event `ENEMY_DIED` | Cleans up stale reference safely | `PLANO_DE_IMPLEMENTACAO.md` (L274) |
| 7 | State Machine | Drop Despawn Lifecycle | If target drop reaches 10s lifetime or expires, assignment is cleared; scavenger enemy returns to hunting player | `drops` state update | Transition to `IDLE`, event `DROP_EXPIRED` | Cleans up stale reference safely | `PLANO_DE_IMPLEMENTACAO.md` (L268) |
| 8 | State Machine | Player Pickup Lifecycle | If player picks up target drop before scavenger reaches it, assignment is cleared; enemy returns to hunting player | `drops` state update | Transition to `IDLE`, event `COLLECTED_PLAYER` | Cleans up stale reference safely | `CONFIGURACOES.md` (#15) |
| 9 | State Machine | Enemy Pickup Event | When scavenger reaches pickup radius ($d \le R_{\text{pickup}}$), drop is marked `coletado_por_inimigo=True`, `ativo=False`, player gets 0 reward | Scavenger & drop positions | Drop consumed, transition to `IDLE`, event `COLLECTED_ENEMY` | Drops inactive safely | `CONFIGURACOES.md` (#15) |
| 10 | AI Navigation | Target Position Override | `obter_posicao_alvo_inimigo` returns `(drop.x, drop.y)` if enemy is the active scavenger, else returns `(pos_jogador)` | `inimigo`, `pos_jogador` | `tuple[float, float]` target coordinate | Returns `pos_jogador` if enemy is not scavenger or drop is None | `PLANO_DE_IMPLEMENTACAO.md` (L275) |
| 11 | Config Integration | Config #15 Toggle Check | If `coleta_inimiga` is `False`, system disables scavenger assignment and resets any active scavenger | `config_coleta_inimiga: bool` | System remains `IDLE` | No enemies scavenge | `CONFIGURACOES.md` (#15) |
| 12 | State Machine | Multi-Drop Priority | When multiple eligible drops exist simultaneously, prioritizes oldest eligible drop (closest to despawn) | `drops` list | Single chosen target drop | Returns `None` if no eligible drops | `PLANO_DE_IMPLEMENTACAO.md` (L439-444) |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| EC-01 | Candidate Selection | 0 enemies present (`inimigos = []`) | Returns `None`, candidate pool is empty. No exception thrown. |
| EC-02 | Candidate Selection | Total enemies $N \le 3$ (e.g. 1, 2, or 3 enemies within range) | All enemies fall in the 3 closest exclusion slice ($P_{\text{sorted}}[3:] = []$). Returns `None`. |
| EC-03 | Candidate Selection | Exactly 4 enemies within range | $P_{\text{sorted}}[3:]$ contains exactly 1 candidate (the 4th closest). Selected with 100% probability. |
| EC-04 | Candidate Selection | All enemies outside $R_{\text{max}}$ ($d > 600.0$) | Distance filter excludes all enemies. Candidate pool is empty. Returns `None`. |
| EC-05 | Candidate Selection | 5 enemies total: 2 within range, 3 outside range | Distance filter keeps 2 enemies. Slicing $[3:]$ on 2 items yields `[]`. Returns `None`. |
| EC-06 | Candidate Selection | 5 enemies total: 4 within range, 1 outside range | Distance filter keeps 4 enemies. Slicing $[3:]$ yields 1 candidate (the 4th closest). 5th enemy was excluded by distance. Selected with 100% probability. |
| EC-07 | Candidate Selection | Dead enemies present in list (`vivo = False`) | Dead enemies are excluded during step 2.1 before distance calculation and ranking. |
| EC-08 | Candidate Selection | Multiple enemies at identical Euclidean distances | Stable sort preserves list ordering. Deterministic slice $[3:]$ without IndexError or tie-breaker crash. |
| EC-09 | Drop Eligibility | Drop with `tempo_vivo = 0.5s` ($< 1.0\text{s}$) | Ignored by scavenger selector; remains in grace period. |
| EC-10 | Drop Eligibility | Drop with `tempo_vivo = 1.0s` ($\ge 1.0\text{s}$) | Becomes eligible for scavenger targeting. |
| EC-11 | Drop Lifecycle | Drop reaches `tempo_vivo >= 10.0s` before scavenger arrives | Drop expires and is deactivated. Active scavenger assignment is cleared. Enemy immediately reverts to targeting player. |
| EC-12 | Scavenger Lifecycle | Active scavenger killed by player while moving towards drop | `e.vivo` becomes `False`. State machine detects death, clears assignment. Next update tick is free to designate a new scavenger if drop is still valid. |
| EC-13 | Scavenger Lifecycle | Player picks up drop while scavenger is en route | Drop becomes `coletado_pelo_jogador` (`ativo = False`). Scavenger assignment cleared. Enemy reverts to player. |
| EC-14 | Scavenger Lifecycle | Scavenger reaches pickup radius ($d \le 24.0\text{px}$) | Drop is marked `coletado_por_inimigo = True` and deactivated. Scavenger assignment cleared. Enemy reverts to player. Player receives 0 XP/heal/loot. |
| EC-15 | Multiple Drops | 3 eligible drops on ground simultaneously | Oldest eligible drop (highest `tempo_vivo`) is assigned to the single global scavenger. Other 2 drops remain unassigned until scavenger finishes or dies. |
| EC-16 | Config Dynamic Toggle | Config #15 toggled from `True` to `False` mid-game | System calls `reset()`, active scavenger assignment is canceled, and enemy returns to chasing player immediately. |
| EC-17 | Extreme Parameters | `k_excluir = 0` or `max_distancia = 0` | Handled gracefully: `k=0` does not exclude closest; `max_distancia=0` allows only enemies at distance 0. |
| EC-18 | Coordinate Formats | Objects with `.x`, `.y` vs tuples `(x, y)` | System supports duck-typed objects with attributes `.x`, `.y`, `.centro_x`, `.centro_y`, or `(x, y)` coordinate tuples. |

---

## 5. Detailed Class & Interface Specification

### 5.1 Protocol / Duck-Typing Contracts

```python
# Pure Logic Duck-Typing Contracts (No Pygame / PPlay required)

class InimigoProtocol:
    x: float
    y: float
    largura: int = 28
    altura: int = 28
    vivo: bool = True
    id: Any = None

class DropProtocol:
    x: float
    y: float
    largura: int = 20
    altura: int = 20
    tempo_vivo: float = 0.0
    ativo: bool = True
    coletado_pelo_jogador: bool = False
    coletado_por_inimigo: bool = False
    id: Any = None
```

### 5.2 `SistemaScavenger` Class Definition (`src/sistemas/sistema_scavenger.py`)

```python
"""
Sistema Scavenger — Protocolo: Batata
Módulo de lógica pura para seleção e gerenciamento de inimigos coletores de drops (Scavengers).
Desacoplado de Pygame/PPlay para suportar execução headless e testes unitários automatizados.
"""

import math
import random
from typing import Any, Sequence, Tuple, List, Optional, Dict


class SistemaScavenger:
    """
    Gerenciador de IA Scavenger pura.
    Garante que no máximo 1 inimigo globalmente atue como coletor de drops por vez.
    """

    def __init__(
        self,
        max_scavenge_distance: float = 600.0,
        closest_exclusion_count: int = 3,
        pickup_radius: float = 24.0,
        tempo_elegibilidade: float = 1.0,
        tempo_despawn_drop: float = 10.0,
        rng: Optional[random.Random] = None,
        rng_seed: Optional[int] = None
    ):
        self.max_scavenge_distance = float(max_scavenge_distance)
        self.closest_exclusion_count = int(closest_exclusion_count)
        self.pickup_radius = float(pickup_radius)
        self.tempo_elegibilidade = float(tempo_elegibilidade)
        self.tempo_despawn_drop = float(tempo_despawn_drop)

        if rng is not None:
            self.rng = rng
        elif rng_seed is not None:
            self.rng = random.Random(rng_seed)
        else:
            self.rng = random.Random()

        # Estado global do scavenger
        self.scavenger_atual: Optional[Any] = None
        self.drop_alvo: Optional[Any] = None

    @staticmethod
    def _obter_posicao(obj: Any) -> Tuple[float, float]:
        """Extrai coordenadas (x, y) de um objeto duck-typed ou tupla."""
        if hasattr(obj, "centro_x") and hasattr(obj, "centro_y"):
            return float(obj.centro_x), float(obj.centro_y)
        if hasattr(obj, "x") and hasattr(obj, "y"):
            cx = float(obj.x) + float(getattr(obj, "largura", 0)) / 2.0
            cy = float(obj.y) + float(getattr(obj, "altura", 0)) / 2.0
            return cx, cy
        if isinstance(obj, (tuple, list)) and len(obj) >= 2:
            return float(obj[0]), float(obj[1])
        raise ValueError(f"Objeto inválido para cálculo de posição: {obj}")

    @staticmethod
    def _esta_vivo(inimigo: Any) -> bool:
        """Verifica se o inimigo está vivo."""
        return bool(getattr(inimigo, "vivo", True))

    @staticmethod
    def _drop_ativo(drop: Any) -> bool:
        """Verifica se o drop está ativo e não foi coletado/expirado."""
        return bool(getattr(drop, "ativo", True)) and not bool(getattr(drop, "coletado_pelo_jogador", False)) and not bool(getattr(drop, "coletado_por_inimigo", False))

    def calcular_distancia(self, obj1: Any, obj2: Any) -> float:
        """Calcula a distância euclidiana entre dois objetos ou coordenadas."""
        x1, y1 = self._obter_posicao(obj1)
        x2, y2 = self._obter_posicao(obj2)
        return math.hypot(x2 - x1, y2 - y1)

    def filtrar_candidatos(
        self,
        drop: Any,
        inimigos: Sequence[Any],
        max_distancia: Optional[float] = None,
        k_excluir: Optional[int] = None
    ) -> List[Tuple[Any, float]]:
        """
        Filtra os inimigos elegíveis para coletar o drop:
        1. Filtra inimigos vivos.
        2. Calcula distância euclidiana até o drop.
        3. Exclui inimigos com distância > max_distancia.
        4. Ordena os candidatos por distância ascendente.
        5. Exclui os k_excluir inimigos mais próximos (slice [k:]).
        """
        cutoff = self.max_scavenge_distance if max_distancia is None else float(max_distancia)
        k = self.closest_exclusion_count if k_excluir is None else int(k_excluir)

        dx, dy = self._obter_posicao(drop)

        # 1 & 2 & 3: Vivos e dentro do raio máximo
        no_raio: List[Tuple[Any, float]] = []
        for e in inimigos:
            if not self._esta_vivo(e):
                continue
            ex, ey = self._obter_posicao(e)
            dist = math.hypot(ex - dx, ey - dy)
            if dist <= cutoff:
                no_raio.append((e, dist))

        # 4: Ordenação ascendente por distância (estável)
        no_raio.sort(key=lambda item: item[1])

        # 5: Exclusão dos k mais próximos
        if len(no_raio) <= k:
            return []
        return no_raio[k:]

    def selecionar_candidato(
        self,
        drop: Any,
        inimigos: Sequence[Any],
        max_distancia: Optional[float] = None,
        k_excluir: Optional[int] = None,
        rng: Optional[random.Random] = None
    ) -> Optional[Any]:
        """
        Seleciona pseudo-aleatoriamente 1 inimigo do pool de candidatos filtrados.
        Retorna None se o pool estiver vazio.
        """
        candidatos = self.filtrar_candidatos(drop, inimigos, max_distancia, k_excluir)
        if not candidatos:
            return None

        gerador = rng or self.rng
        escolhido = gerador.choice(candidatos)
        return escolhido[0]

    def obter_drop_prioritario(self, drops: Sequence[Any]) -> Optional[Any]:
        """
        Retorna o drop elegível com maior tempo de vida (mais próximo do despawn de 10s).
        """
        elegiveis = []
        for d in drops:
            if not self._drop_ativo(d):
                continue
            tempo_vivo = float(getattr(d, "tempo_vivo", getattr(d, "tempo_vida", 0.0)))
            if self.tempo_elegibilidade <= tempo_vivo < self.tempo_despawn_drop:
                elegiveis.append((d, tempo_vivo))

        if not elegiveis:
            return None

        # Ordena pelo tempo_vivo decrescente (o mais velho primeiro)
        elegiveis.sort(key=lambda item: item[1], reverse=True)
        return elegiveis[0][0]

    def atualizar(
        self,
        dt: float,
        inimigos: Sequence[Any],
        drops: Sequence[Any],
        pos_jogador: Tuple[float, float],
        config_coleta_inimiga: bool = True
    ) -> Dict[str, Any]:
        """
        Atualiza o ciclo de vida do Scavenger global.
        Retorna um dicionário de status/eventos do frame.
        """
        evento = "NONE"

        # Se a configuração estiver desligada, reseta o scavenger atual
        if not config_coleta_inimiga:
            if self.scavenger_atual is not None:
                self.reset()
                evento = "CONFIG_DISABLED"
            return {
                "scavenger_ativo": False,
                "scavenger": None,
                "drop_alvo": None,
                "evento": evento
            }

        # 1. Validar scavenger e drop atuais se houver
        if self.scavenger_atual is not None:
            # Checar se o scavenger morreu
            if not self._esta_vivo(self.scavenger_atual):
                self.scavenger_atual = None
                self.drop_alvo = None
                evento = "SCAVENGER_DIED"

            # Checar se o drop alvo não é mais válido (coletado pelo jogador ou expirou)
            elif self.drop_alvo is None or not self._drop_ativo(self.drop_alvo):
                self.scavenger_atual = None
                self.drop_alvo = None
                evento = "DROP_INVALIDATED"

            else:
                # Checar se o scavenger alcançou o drop
                dist = self.calcular_distancia(self.scavenger_atual, self.drop_alvo)
                if dist <= self.pickup_radius:
                    # Drop capturado pelo inimigo
                    if hasattr(self.drop_alvo, "coletado_por_inimigo"):
                        self.drop_alvo.coletado_por_inimigo = True
                    if hasattr(self.drop_alvo, "ativo"):
                        self.drop_alvo.ativo = False

                    self.scavenger_atual = None
                    self.drop_alvo = None
                    evento = "DROP_COLLECTED_BY_ENEMY"

        # 2. Se não há scavenger ativo, tentar selecionar um novo
        if self.scavenger_atual is None:
            drop_candidato = self.obter_drop_prioritario(drops)
            if drop_candidato is not None:
                novo_scavenger = self.selecionar_candidato(drop_candidato, inimigos)
                if novo_scavenger is not None:
                    self.scavenger_atual = novo_scavenger
                    self.drop_alvo = drop_candidato
                    evento = "SCAVENGER_ASSIGNED"

        return {
            "scavenger_ativo": self.scavenger_atual is not None,
            "scavenger": self.scavenger_atual,
            "drop_alvo": self.drop_alvo,
            "evento": evento
        }

    def obter_posicao_alvo_inimigo(self, inimigo: Any, pos_jogador: Tuple[float, float]) -> Tuple[float, float]:
        """
        Retorna a coordenada de destino para o inimigo:
        - Se o inimigo for o scavenger atual e houver drop válido, retorna a posição do drop.
        - Caso contrário, retorna pos_jogador.
        """
        if self.scavenger_atual is not None and inimigo is self.scavenger_atual and self.drop_alvo is not None:
            return self._obter_posicao(self.drop_alvo)
        return pos_jogador

    def reset(self) -> None:
        """Limpa o estado atual do scavenger."""
        self.scavenger_atual = None
        self.drop_alvo = None
```

---

## 6. Caveats

1. **Center vs. Top-Left Coordinates**:
   In PowerPPlay / Pygame, sprites are placed by top-left `(x, y)` with width/height `largura, altura`. Center-to-center distance calculation provides smoother visual alignment when the enemy navigates to the drop. `SistemaScavenger._obter_posicao` safely detects `.centro_x`/`.centro_y`, falls back to `(x + largura/2, y + altura/2)`, and handles `(x, y)` tuples.
2. **Drop Despawn Timing**:
   The Drop System (`sistema_drops.py`) manages the drop lifetime timer (10s). The Scavenger System reads this timer to determine eligibility ($\ge 1.0\text{s}$) and expiration. If the drop system deactivates an expired drop, the scavenger system immediately detects `not drop.ativo` and releases the scavenger back to normal behavior.
3. **Integration with `InimigoBase.update`**:
   During gameplay scene integration, `InimigoBase.update(dt, pos_alvo)` simply receives `sistema_scavenger.obter_posicao_alvo_inimigo(inimigo, (jogador.x, jogador.y))` as `pos_alvo`. No modifications to enemy internal state are necessary.

---

## 7. Conclusion

The pure logic Scavenger AI selector for `src/sistemas/sistema_scavenger.py` is fully specified with:
- Decoupled pure logic architecture (zero Pygame/PPlay dependencies).
- Exact mathematical candidate filtering: $E_{\text{alive}} \to \text{in\_range}(\le R_{\text{max}}) \to \text{sort\_ascending} \to \text{slice}[3:] \to \text{uniform\_random\_choice}$.
- Global singleton scavenger enforcement (at most 1 active scavenger enemy across the arena).
- Complete lifecycle management for scavenger death, drop expiration, player pickup, enemy pickup, and dynamic config toggling.
- Full deterministic RNG support for reliable automated unit testing.

---

## 8. Verification Method

To independently verify the specification, execute the following unit test suite using `pytest` or `python -m unittest`:

```powershell
pytest tests/test_sistema_scavenger.py -v
```

### Key Automated Verification Checks:
1. **Empty / Insufficient Candidates**:
   - Verify `selecionar_candidato` returns `None` for 0, 1, 2, 3 enemies within range.
   - Verify `selecionar_candidato` returns the 4th closest enemy when exactly 4 enemies are in range.
2. **Distance Cutoff Filtering**:
   - Verify enemies beyond `max_scavenge_distance` are excluded before slicing $[3:]$.
3. **Deterministic Selection**:
   - Verify passing `random.Random(seed)` produces identical selections across repeated runs.
4. **Lifecycle & State Machine Transitions**:
   - Verify `scavenger_atual` dies $\to$ assignment cleared, event `SCAVENGER_DIED`.
   - Verify player collects drop $\to$ assignment cleared, event `DROP_INVALIDATED`.
   - Verify scavenger reaches `pickup_radius` $\to$ drop deactivated, event `DROP_COLLECTED_BY_ENEMY`.
   - Verify navigation: `obter_posicao_alvo_inimigo` returns drop position for scavenger, player position for all other enemies.
