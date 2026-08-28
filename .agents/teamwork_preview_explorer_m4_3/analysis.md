# Protocolo: Batata — Relatório de Análise Matemática e Regras de Agregação de Configurações

**Autor**: Explorer 3 (Especialista em Matemática e Cálculo de Stacking)  
**Data**: 2026-08-28  
**SSOT de Referência**: `CONFIGURACOES.md`  
**Taxonomia de Evidência**: Todas as afirmações estão rotuladas como [Observed], [Verified], [Inferred] ou [Speculative].

---

## 1. Visão Geral e Princípios Matemáticos

[Observed] No jogo *Protocolo: Batata*, o sistema de 20 configurações de gameplay funciona como o mecanismo central de progressão permanente. Cada configuração oferece um sacrifício (nerf de usabilidade/conforto/dificuldade) em troca de um benefício matemático palpável (buff de dano, velocidade, XP, drop rate, etc.).

### Princípios de Stacking:
1. **Multiplicação entre Dimensões Independentes (Multiplicative Stacking)**:
   - Modificadores originários de fontes ou categorias conceituais distintas multiplicam-se entre si:
     $$M_{total} = \prod_{i} M_i$$
   - Isso evita distorções aritméticas (como bônus que somados ultrapassam 100% sem controle) e preserva o valor relativo de cada sacrifício escolhido pelo jogador.
2. **Soma em Bônus de Probabilidade Direta (Additive Stacking)**:
   - Bônus diretos de chance percentual (ex: $+10\%$, $+25\%$, $+50\%$ de drop de itens por resolução ou vida de inimigos) somam-se à probabilidade base antes de receber multiplicadores globais:
     $$P_{final} = \text{clamp}\left((P_{base} + \sum B_{aditivo}) \times M_{mult}, 0.0, 1.0\right)$$
3. **Estado Padrão Neutro (Baseline Invariante)**:
   - Quando qualquer configuração está bloqueada (locked) ou em seu valor padrão (default), seu modificador multiplicativo é rigorosamente **$1.0$**, seu modificador aditivo é **$0.0$**, sua chance de crítico é **$0.0$** e suas flags comportamentais são **`False`**.

---

## 2. Análise Detalhada dos 10 Domínios de Cálculo

---

### Domínio 1: Multiplicador de Dano de Armas (`dano_armas_mult`)

[Observed] As seguintes configurações afetam o dano das armas do jogador:

| Configuração | Opção Ativa | Modificador | Aplicação |
|---|---|---|---|
| `zoom` | `125%` | $\times 1.10$ (+10%) | Todas as armas |
| `zoom` | `150%` | $\times 1.20$ (+20%) | Todas as armas |
| `keybinds` | `invertido` | $\times 1.10$ (+10%) | Todas as armas |
| `keybinds` | `pesadelo` | $\times 1.30$ (+30%) | Todas as armas |
| `auto_fire` | `desligado` | $\times 1.15$ (+15%) | Todas as armas |
| `cores_invertidas` | `ligado` | $\times 1.20$ (+20%) | Todas as armas |
| `fogo_amigo` | `ligado` | $\times 1.25$ (+25%) | Todas as armas |
| `screen_shake` | `ligado` | $\times 1.20$ (+20%) | **Apenas Armas Explosivas** (Lança-Foguetes e Lança-Granadas) |

#### Fórmulas de Agregação:
1. **Dano Global (Armas Comuns e Melee)**:
   $$M_{dano\_global} = M_{zoom} \times M_{keybinds} \times M_{autofire} \times M_{cores\_invertidas} \times M_{fogo\_amigo}$$

2. **Dano Específico para Armas Explosivas**:
   $$M_{dano\_explosivo} = M_{dano\_global} \times M_{screen\_shake}$$

3. **Dano Final da Arma**:
   $$Dano_{arma} = Dano_{base} \times (M_{dano\_explosivo} \text{ se explosiva senão } M_{dano\_global})$$

#### Valores Extremos:
- **Baseline (Padrão)**: $1.00 \times 1.00 \times 1.00 \times 1.00 \times 1.00 = 1.00$ ($\mathbf{1.0\times}$)
- **Máximo Global (Zoom 150% + Pesadelo + AutoFire Off + Cores Inv + Fogo Amigo)**:
  $$1.20 \times 1.30 \times 1.15 \times 1.20 \times 1.25 = 2.691 \quad (\mathbf{+169.1\%})$$
- **Máximo Explosivo (+ Screen Shake)**:
  $$2.691 \times 1.20 = 3.2292 \quad (\mathbf{+222.92\%})$$

---

### Domínio 2: Modificador de Vida Máxima dos Inimigos (`hp_inimigos_mult`)

[Observed] As seguintes configurações afetam o HP dos inimigos:

| Configuração | Opção Ativa | Modificador | Descrição |
|---|---|---|---|
| `graficos_qualidade` | `baixa` | $\times 0.80$ (-20%) | Redução por simplificação visual |
| `vida_inimigos` | `+50%` | $\times 1.50$ (+50%) | Aumento por blindagem |
| `vida_inimigos` | `+100%` | $\times 2.00$ (+100%) | Aumento por densidade dobrada |

#### Fórmula de Agregação Sequencial / Multiplicativa:
$$M_{hp\_inimigo} = M_{graficos\_qualidade} \times M_{vida\_inimigos}$$
$$HP_{max\_final} = \max(1, \text{int}(\text{round}(HP_{base} \times M_{hp\_inimigo})))$$

#### Matriz de Todos os Casos Possíveis:
| Qualidade Gráfica | Vida Inimigos | Multiplicador Exato | Exemplo: Estagiário (Base 25) | Exemplo: Tanque (Base 120) |
|---|---|---|---|---|
| `alta` (1.0) | `normal` (1.0) | **$1.00$** | $25$ HP | $120$ HP |
| `alta` (1.0) | `+50%` (1.5) | **$1.50$** | $38$ HP ($25 \times 1.5 = 37.5 \to 38$) | $180$ HP |
| `alta` (1.0) | `+100%` (2.0) | **$2.00$** | $50$ HP | $240$ HP |
| `baixa` (0.8) | `normal` (1.0) | **$0.80$** | $20$ HP | $96$ HP |
| `baixa` (0.8) | `+50%` (1.5) | **$1.20$** ($0.8 \times 1.5$) | $30$ HP | $144$ HP |
| `baixa` (0.8) | `+100%` (2.0) | **$1.60$** ($0.8 \times 2.0$) | $40$ HP | $192$ HP |

---

### Domínio 3: Modificador de Velocidade dos Inimigos (`vel_inimigos_mult`)

[Observed] As seguintes configurações afetam a velocidade de marcha dos inimigos:

| Configuração | Opção Ativa | Modificador | Descrição |
|---|---|---|---|
| `fps_cap` | `30` | $\times 0.90$ (-10%) | Slow motion de frames |
| `fps_cap` | `15` | $\times 0.81$ (-19%) | Composição quadrática $0.90 \times 0.90$ |
| `velocidade_inimigos` | `+25%` | $\times 1.25$ (+25%) | Overclock |
| `velocidade_inimigos` | `+50%` | $\times 1.50$ (+50%) | Surto turbo |

#### Fórmula de Agregação:
$$M_{vel\_inimigo} = M_{fps\_cap\_vel} \times M_{velocidade\_inimigos}$$
$$Vel_{inimigo\_final} = Vel_{base} \times M_{vel\_inimigo}$$

#### Matriz de Casos Relevantes:
| `fps_cap` | `velocidade_inimigos` | Multiplicador Exato | Exemplo: Estagiário (Base 100 px/s) |
|---|---|---|---|
| `60` / `45` ($1.00$) | `normal` ($1.00$) | **$1.0000$** | $100.0$ px/s |
| `60` / `45` ($1.00$) | `+25%` ($1.25$) | **$1.2500$** | $125.0$ px/s |
| `60` / `45` ($1.00$) | `+50%` ($1.50$) | **$1.5000$** | $150.0$ px/s |
| `30` ($0.90$) | `normal` ($1.00$) | **$0.9000$** | $90.0$ px/s |
| `30` ($0.90$) | `+25%` ($1.25$) | **$1.1250$** | $112.5$ px/s |
| `30` ($0.90$) | `+50%` ($1.50$) | **$1.3500$** | $135.0$ px/s |
| `15` ($0.81$) | `normal` ($1.00$) | **$0.8100$** | $81.0$ px/s |
| `15` ($0.81$) | `+25%` ($1.25$) | **$1.0125$** | $101.25$ px/s |
| `15` ($0.81$) | `+50%` ($1.50$) | **$1.2150$** | $121.5$ px/s |

---

### Domínio 4: Modificador de Velocidade do Jogador (`vel_jogador_mult`)

[Observed] As seguintes configurações afetam a velocidade de movimento da batata:

| Configuração | Opção Ativa | Modificador | Descrição |
|---|---|---|---|
| `vsync` | `desligado` | $\times 1.10$ (+10%) | Screen tearing boost |
| `motion_blur` | `ligado` | $\times 1.15$ (+15%) | Rastro visual boost |
| `keybinds` | `arrow_keys` | $\times 1.15$ (+15%) | Nostalgia teclas direcionais |
| `suavizacao_camera` | `desligado` | $\times 1.08$ (+8%) | Câmera rígida |

#### Fórmula de Agregação:
$$M_{vel\_jogador} = M_{vsync} \times M_{motion\_blur} \times M_{keybinds\_vel} \times M_{suavizacao}$$
$$Vel_{jogador\_final} = Vel_{base} \times M_{vel\_jogador}$$

#### Valores Extremos:
- **Baseline (Padrão)**: $1.00 \times 1.00 \times 1.00 \times 1.00 = 1.00$ ($200.0$ px/s)
- **Máximo Acumulado (Todos os 4 buffs)**:
  $$1.10 \times 1.15 \times 1.15 \times 1.08 = 1.57113 \quad (\mathbf{+57.113\%})$$
  $$Vel_{jogador\_max} = 200.0 \times 1.57113 = \mathbf{314.226}\text{ px/s}$$

---

### Domínio 5: Redução de Dano Recebido pelo Jogador (`dano_recebido_mult`)

[Observed] As seguintes configurações reduzem o dano que a batata sofre dos inimigos:

| Configuração | Opção Ativa | Modificador | Condição |
|---|---|---|---|
| `fps_cap` | `45` | $\times 0.85$ (-15%) | Incondicional |
| `fps_cap` | `15` | $\times 0.7225$ (-27.75%) | Incondicional ($0.85 \times 0.85$) |
| `iluminacao` | `ligado` | $\times 0.50$ (-50%) | **Apenas quando o inimigo está fora do cone/raio de visão** |

#### Fórmula de Agregação:
$$M_{dano\_recebido} = M_{fps\_cap\_dano} \times (0.50 \text{ se } \text{iluminacao\_ativa e inimigo\_fora\_cone else } 1.00)$$
$$Dano_{sofrido} = \max(1, \text{int}(\text{round}(Dano_{inimigo} \times M_{dano\_recebido})))$$

#### Casos Críticos:
- `fps_cap 15` + Inimigo Fora da Visão:
  $$M_{dano\_min} = 0.7225 \times 0.50 = \mathbf{0.36125} \quad (\mathbf{63.875\%}\text{ de redução})$$
  Exemplo: Dano base 20 (Tanque) $\to 20 \times 0.36125 = 7.225 \to 7$ de dano.
- `fps_cap 45` + Inimigo Dentro da Visão:
  $$20 \times 0.85 = 17\text{ de dano}$$

---

### Domínio 6: Modificador de Chance de Drop de Itens (`chance_drop`)

[Observed] As seguintes configurações aumentam a chance de drop ao derrotar inimigos:

| Configuração | Opção Ativa | Tipo | Valor |
|---|---|---|---|
| `resolucao` | `75%` | Aditivo | $+0.10$ (+10%) |
| `resolucao` | `50%` | Aditivo | $+0.25$ (+25%) |
| `resolucao` | `25%` | Aditivo | $+0.50$ (+50%) |
| `vida_inimigos` | `+50%` | Aditivo | $+0.20$ (+20%) |
| `vida_inimigos` | `+100%` | Aditivo | $+0.40$ (+40%) |
| `movimento_mouse` | `ligado` | Multiplicativo | $\times 1.40$ (+40%) |

#### Fórmula de Agregação:
1. **Soma dos Bônus Aditivos**:
   $$B_{aditivo} = B_{resolucao} + B_{vida\_inimigos}$$
2. **Aplicação sobre a Probabilidade Base com Multiplicador do Mouse**:
   $$P_{calculada} = (P_{base} + B_{aditivo}) \times M_{movimento\_mouse}$$
3. **Clamping no Intervalo $[0.0, 1.0]$**:
   $$P_{final} = \min(1.0, \max(0.0, P_{calculada}))$$

#### Exemplos de Teste (com $P_{base} = 0.20$ ou 20%):
- **Padrão**: $(0.20 + 0.0 + 0.0) \times 1.00 = 0.20$ (20%)
- **Apenas Mouse**: $(0.20 + 0.0 + 0.0) \times 1.40 = 0.28$ (28%)
- **Resolução 50% + Vida +50%**: $(0.20 + 0.25 + 0.20) \times 1.00 = 0.65$ (65%)
- **Resolução 25% + Vida +100% + Mouse Ligado**:
  $$(0.20 + 0.50 + 0.40) \times 1.40 = 1.10 \times 1.40 = 1.54 \to \mathbf{1.00}\text{ (100\% garantido)}$$

---

### Domínio 7: Modificador de Ganho de Experiência (`xp_ganho_mult`)

[Observed] As seguintes configurações afetam o ganho de XP:

| Configuração | Opção Ativa | Modificador | Descrição |
|---|---|---|---|
| `hud` | `desligado` | $\times 1.25$ (+25%) | Jogando sem interface |
| `keybinds` | `uma_mao` | $\times 1.20$ (+20%) | Controle em QWER |
| `velocidade_inimigos` | `+25%` | $\times 1.20$ (+20%) | Inimigos mais rápidos |
| `velocidade_inimigos` | `+50%` | $\times 1.40$ (+40%) | Inimigos turbo |
| `coleta_inimiga` | `ligado` | $\times 2.00$ (+100%) | **No momento da coleta do drop gem pelo jogador** |

#### Fórmula de Agregação de XP por Abate:
$$M_{xp\_abate} = M_{hud} \times M_{keybinds\_xp} \times M_{velocidade\_inimigos}$$

#### Multiplicador Máximo de Abate:
$$M_{xp\_max} = 1.25 \times 1.20 \times 1.40 = \mathbf{2.10} \quad (\mathbf{+110\%})$$

#### Valor Efetivo Coletado com `coleta_inimiga`:
$$XP_{final} = \text{int}(\text{round}(XP_{base} \times M_{xp\_abate} \times M_{coleta\_inimiga}))$$
Com todos os buffs: $10 \text{ XP} \times 2.10 \times 2.0 = \mathbf{42}\text{ XP}$ ($420\%$ do baseline!).

---

### Domínio 8: Sistema de Acertos Críticos (`critico_chance`, `critico_mult`)

[Observed] A configuração `damage_numbers` controla integralmente o subsistema de críticos:

| `damage_numbers` | Chance de Crítico | Multiplicador de Dano | Comportamento |
|---|---|---|---|
| `desligado` (Padrão) | **$0.0$** ($0\%$) | **$1.0$** | Críticos completamente desativados |
| `ligado` | **$0.15$** ($15\%$) | **$2.0$** ($2\times$) | Habilita 15% de chance de causar o dobro de dano |

#### Algoritmo de Resolução de Crítico:
```python
def calcular_dano_impacto(dano_calculado: float, damage_numbers_ativo: bool, rng_valor: float) -> tuple[float, bool]:
    if not damage_numbers_ativo:
        return dano_calculado, False
    is_crit = rng_valor < 0.15
    dano_final = dano_calculado * 2.0 if is_crit else dano_calculado
    return dano_final, is_crit
```

---

### Domínio 9: Caixa de Colisão de Projéteis (`hitbox_projeteis_mult`)

[Observed] A configuração `zoom` afeta a escala da hitbox de todos os projéteis disparados pelo jogador:

| Nível de Zoom | Modificador de Hitbox | Descrição |
|---|---|---|
| `75%` (Zoom Out) | $\times 1.50$ (+50%) | Facilita acertar alvos distantes |
| `100%`, `125%`, `150%` | $\times 1.00$ (Normal) | Hitbox padrão |

#### Fórmula de Aplicação:
$$Raio_{projetil\_final} = Raio_{base} \times M_{hitbox}$$
$$Largura_{AABB} = Largura_{base} \times M_{hitbox}, \quad Altura_{AABB} = Altura_{base} \times M_{hitbox}$$

---

### Domínio 10: Flags Comportamentais e Mecânicas Especiais

[Observed] As 10 configurações a seguir ativam regras de negócio e subsistemas de gameplay:

1. **`auto_fire`**:
   - `ligado` (Padrão): Disparo contínuo ao manter o botão pressionado.
   - `desligado`: Disparo estritamente semiautomático (1 clique = 1 tiro), concedendo $+15\%$ de dano.
2. **`inimigos_ranged`**:
   - `desligado` (Padrão): Apenas inimigos corpo a corpo spawnando.
   - `ligado`: Habilita o spawn do *Atirador Blaster* e tabela de loot enriquecida (`loot_enriquecido = True`).
3. **`coleta_inimiga` (Scavenger)**:
   - `desligado` (Padrão): Inimigos ignoram caixas e drops no chão.
   - `ligado`: Ativa a IA Scavenger (após 1s de drop, 1 inimigo tenta devorar o drop); todos os drops pegos pelo jogador concedem valor dobrado ($2\times$).
4. **`iluminacao`**:
   - `desligado` (Padrão): Arena completamente iluminada.
   - `ligado`: Renderização de *Fog of War* com cone de visão ao redor da batata; inimigos fora do cone causam $-50\%$ de dano.
5. **`cores_invertidas`**:
   - `desligado` (Padrão): Renderização RGB padrão.
   - `ligado`: Shading invertido em tela inteira; concede $+20\%$ de dano em todas as armas.
6. **`fogo_amigo`**:
   - `desligado` (Padrão): Tiros e explosões do jogador não afetam a si mesmo nem seus drones.
   - `ligado`: Auto-dano ativado; drones possuem 1 HP e são destruídos por fogo amigo; concede $+25\%$ de dano em todas as armas.
7. **`keybinds`**:
   - Mapeamentos de controle: `padrao` (WASD), `invertido` (WASD invertido), `arrow_keys` (Setas), `uma_mao` (QWER), `pesadelo` (IJKL + Mouse Y invertido).
8. **`movimento_mouse`**:
   - `desligado` (Padrão): Movimentação controlada pelas teclas.
   - `ligado`: Batata caminha ininterruptamente em direção ao cursor do mouse; teclas desabilitadas; concede $+40\%$ de chance de drop multiplicativa.
9. **`suavizacao_camera`**:
   - `ligado` (Padrão): Câmera com interpolação linear (`lerp`).
   - `desligado`: Câmera rigidamente travada no jogador; concede $+8\%$ de velocidade de movimento.
10. **`screen_shake`**:
    - `desligado` (Padrão): Câmera sem tremor.
    - `ligado`: Tremor aplicado na tela durante disparos e explosões; concede $+20\%$ de dano a armas explosivas.

---

## 3. Matriz de Cenários de Teste e Casos de Borda

### Cenário A: Baseline Completo (All Defaults / All Locked)
- **Condição**: Nenhuma configuração ativada ou todas nos valores padrão.
- **Valores Esperados**:
  - `dano_armas_mult` = $1.0000$
  - `dano_explosivos_mult` = $1.0000$
  - `hp_inimigos_mult` = $1.0000$
  - `vel_inimigos_mult` = $1.0000$
  - `vel_jogador_mult` = $1.0000$
  - `dano_recebido_mult` = $1.0000$
  - `drop_chance_bonus_aditivo` = $0.0000$
  - `drop_chance_mult` = $1.0000$
  - `xp_ganho_mult` = $1.0000$
  - `critico_chance` = $0.0000$
  - `critico_mult` = $1.0000$
  - `hitbox_projeteis_mult` = $1.0000$
  - Todas as flags comportamentais = `False` (exceto `auto_fire` e `suavizacao_camera` que são `True` no padrão).

### Cenário B: Ativação Unitária Isolada (20 Testes)
Cada configuração ativada individualmente deve produzir exatamente o multiplicador/efeito declarado em `CONFIGURACOES.md` sem contaminar os outros domínios.

### Cenário C: Acúmulo Máximo Extremo (All Buffs Active)
- **Condição**: Todas as 20 configurações configuradas em seus valores de benefício máximo.
- **Valores Esperados**:
  - `dano_armas_mult` = $1.20 \times 1.30 \times 1.15 \times 1.20 \times 1.25 = \mathbf{2.6910}$
  - `dano_explosivos_mult` = $2.6910 \times 1.20 = \mathbf{3.2292}$
  - `vel_jogador_mult` = $1.10 \times 1.15 \times 1.15 \times 1.08 = \mathbf{1.57113}$
  - `hp_inimigos_mult` (com Baixa + 100% HP) = $0.80 \times 2.00 = \mathbf{1.6000}$
  - `vel_inimigos_mult` (com 15 FPS + 50% Vel) = $0.81 \times 1.50 = \mathbf{1.2150}$
  - `xp_ganho_mult` = $1.25 \times 1.20 \times 1.40 = \mathbf{2.1000}$
  - `drop_chance` (com Base 0.20 + 0.50 + 0.40 = 1.10 * 1.40 = 1.54) $\to \mathbf{1.0000}$ (Clamped)
  - `dano_recebido_min` = $0.7225 \times 0.50 = \mathbf{0.36125}$
  - `critico_chance` = $\mathbf{0.15}$, `critico_mult` = $\mathbf{2.0}$
  - `hitbox_projeteis_mult` = $\mathbf{1.50}$ (se Zoom 75%)

### Cenário D: Casos de Borda e Validações Defensivas
1. **Transição Bloqueado $\to$ Desbloqueado**:
   - Enquanto `desbloqueado == False`, chamadas para alterar o valor ativo são rejeitadas ou ignoradas, mantendo o valor padrão.
2. **Entrada Inválida / Opção Inexistente**:
   - Caso o estado receba uma opção inválida (ex: `fps_cap = "120"` ou `zoom = "300%"`), o sistema faz fallback seguro para o valor padrão e registra log/aviso.
3. **Clamping de Dano Mínimo e HP Mínimo**:
   - $HP_{final} \ge 1$
   - $Dano_{final} \ge 1$ (quando $Dano_{base} \ge 1$)
4. **Precisão de Ponto Flutuante**:
   - Comparações em testes automatizados devem utilizar tolerância $\varepsilon = 10^{-5}$ (`math.isclose` ou `pytest.approx`).

---

## 4. Estrutura de Dados Recomendada para `ModificadoresAgregados`

[Inferred] Para fornecer uma interface limpa aos sistemas de gameplay (armas, entidades, drops, spawn), recomenda-se uma dataclass imutável ou dict consolidado retornado por `ConfigEfeitos.calcular_modificadores()`:

```python
@dataclass(frozen=True)
class ModificadoresCalculados:
    # Multiplicadores de Dano
    dano_global_mult: float
    dano_explosivos_mult: float
    
    # Multiplicadores de Velocidade
    vel_jogador_mult: float
    vel_inimigos_mult: float
    
    # Modificadores de Inimigos
    hp_inimigos_mult: float
    dano_recebido_mult: float
    dano_fora_visao_mult: float
    
    # Drops e Economia
    drop_chance_bonus_aditivo: float
    drop_chance_mult: float
    xp_ganho_mult: float
    drops_valor_mult: float
    
    # Combate e Projéteis
    critico_chance: float
    critico_mult: float
    hitbox_projeteis_mult: float
    
    # Flags Comportamentais
    auto_fire_ativo: bool
    fogo_amigo_ativo: bool
    inimigos_ranged_ativo: bool
    coleta_inimiga_ativo: bool
    iluminacao_ativo: bool
    cores_invertidas_ativo: bool
    movimento_mouse_ativo: bool
    suavizacao_camera_ativo: bool
    screen_shake_ativo: bool
    motion_blur_ativo: bool
    hud_visivel: bool
    damage_numbers_ativo: bool
    preset_keybinds: str
    qualidade_grafica: str
    fps_cap_valor: int
    resolucao_fator: float
    zoom_fator: float
```
