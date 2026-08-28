# Protocolo: Batata — Plano de Implementação (v3 FINAL)

## Resumo das Decisões

| Decisão | Resposta |
|---|---|
| **Engine** | PowerPPlay 2.0 — importada do `.venv` (`site-packages/PPlay`) |
| **Linguagem do código** | Português de preferência; inglês quando mais limpo |
| **Personagem** | Batata (não robô) |
| **IA dos inimigos** | Nenhuma. Beeline direto pro jogador |
| **Arte** | Placeholders procedurais agora; arte humana depois |
| **Escopo v1.0** | Todas as features |
| **Persistência** | JSON (`data/save.json`) |
| **Resolução base** | Resolução máxima do monitor |
| **Configs não desbloqueadas** | Defaultam para a opção que **não dá buff** |

---

## Regra Global de Defaults

> [!IMPORTANT]
> Quando o jogador ainda não desbloqueou uma configuração de gameplay, ela fica travada no valor padrão — que é **sempre** a opção que não concede nenhum buff. Exemplo: FPS Cap trava em 60 (sem buff), HUD fica Ligado (sem buff), Auto-Fire fica Ligado (sem buff). Só após desbloquear a config o jogador pode alterar para a opção que sacrifica conforto em troca de poder.

---

## ⚙️ CATÁLOGO FINAL DE CONFIGURAÇÕES (SSOT: `CONFIGURACOES.md`)

> **SSOT**: O arquivo [`CONFIGURACOES.md`](file:///c:/Users/jesse/Documents/Computaria/visual%20studio/protocolo-batata/CONFIGURACOES.md) é a **Única Fonte da Verdade** do projeto para todas as definições numéricas, buffs, nerfs, comportamentos e flavor texts de configurações.
>
> **Total de configs de gameplay desbloqueáveis: 20**
> **Nível máximo do jogador: 20**
> **Configs de sistema (sempre disponíveis, sem gameplay): 4** (Volume Master, Música, SFX e Filtro Daltônico)

---

### GRUPO 1: PERFORMANCE

#### 1. FPS Cap — `fps_cap`

**Tipo**: grupo mutuamente exclusivo (unlock 1×, depois alterna)
**Padrão (antes de desbloquear)**: 60 FPS (sem buff)

| Valor | Nerf | Buff | Cálculo |
|---|---|---|---|
| 60 FPS | — | — | baseline |
| 45 FPS | Jogo roda a 45 FPS | Dano dos inimigos ×0.85 (−15%) | direto |
| 30 FPS | Jogo roda a 30 FPS | Velocidade dos inimigos ×0.90 (−10%) | direto |
| 15 FPS | Jogo quase injogável | Dano ×0.7225 (−27.75%) **E** velocidade ×0.81 (−19%) | multiplicativo: 0.85² e 0.90² |

> **Stacking**: multiplicativo. 15 FPS aplica cada multiplicador ao quadrado.
>
> **Flavor Texts**: "Performance Mode" / "Slow Motion" / "Cinematic Experience" — *"Every frame was handcrafted."*

---

#### 2. Qualidade Gráfica — `graficos_qualidade`

**Tipo**: toggle (High / Low)
**Padrão**: Alta (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Alta | — | — |
| Baixa | Todos os sprites viram retângulos coloridos. Partículas simplificadas. | **HP dos inimigos −20%** |

> **Flavor**: "Corporate Budget Cuts" — *"Textures are expensive."*

---

#### 3. Resolução — `resolucao`

**Tipo**: grupo mutuamente exclusivo
**Padrão**: Nativa / máxima do monitor (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Nativa (100%) | — | — |
| 75% | Tela menor/pixelada | **+10% chance de drop** |
| 50% | Bem pixelado | **+25% chance de drop** |
| 25% | Quase impossível de ver | **+50% chance de drop** |

> **Efeito escolhido**: chance de drop aumentada.
> **Flavor**: "Pixel Archaeology" — *"If you can't count the pixels, you're wasting performance."*

---

#### 4. VSync — `vsync`

**Tipo**: toggle (Ligado / Desligado)
**Padrão**: Ligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Ligado | — | — |
| Desligado | Possível screen tearing visual | **+10% velocidade de movimento do jogador** |

> **Flavor**: "Tearing Season" — *"Your monitor filed a complaint."*

---

#### 5. Screen Shake — `screen_shake`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — | — |
| Ligado | Tela treme em explosões e dano (desconforto visual) | **+20% dano de rocket launcher e grenade launcher** |

> **Filosofia invertida**: LIGAR é o sacrifício.
> **Flavor**: "Earthquake Protocol" — *"The screen shakes. So does your aim."*

---

#### 6. Motion Blur — `motion_blur`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — | — |
| Ligado | Rastro visual nos sprites em movimento (dificulta leitura) | **+15% velocidade de movimento do jogador** |

> **Implementação**: desenhar cópias semi-transparentes do sprite nas posições anteriores.
> **Flavor**: "Afterimage" — *"You're so fast even your pixels can't keep up."*

---

### GRUPO 2: INTERFACE

#### 7. HUD — `hud`

**Tipo**: toggle (Ligado / Desligado)
**Padrão**: Ligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Ligado | — | — |
| Desligado | Sem barra de HP, XP, inventário, timer, FPS counter. Só o botão de settings. | **+25% XP ganha por kill** |

> **Flavor**: "Trust Me Bro" — *"Surely you're still alive."*

---

#### 8. Damage Numbers — `damage_numbers`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — | — |
| Ligado | Números de dano flutuam em cada hit (spam visual com centenas de inimigos) | **Ativa sistema de dano crítico: 8% chance de crit (2× dano)** |

> **Nota**: sem esta config ligada, crits simplesmente não existem no jogo.
> **Flavor**: "Math Class" — *"Finally, a use for arithmetic."*

---

#### 9. Zoom Level — `zoom`

**Tipo**: grupo mutuamente exclusivo
**Padrão**: 100% (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| 75% (zoom out) | Sprites menores, mais difícil de ver | **Hitbox dos projéteis do jogador +50%** |
| 100% | — | — |
| 125% (zoom in) | Campo de visão reduzido | **+10% dano do jogador** |
| 150% (zoom in) | Campo de visão bem reduzido | **+20% dano do jogador** |

> **Flavor**: "Microscope Mode" — *"You can see their pores."* / "Satellite View" — *"Is that an ant or the player?"*

---

### GRUPO 3: CONTROLES

#### 10. Movimento pelo Mouse — `movimento_mouse`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado (WASD) | — | — |
| Ligado | Batata anda continuamente em direção ao cursor. Teclado desabilitado. Nunca para. | **+40% chance multiplicativa de drop** |

> **Flavor**: "Autopilot" — *"Who needs legs when destiny has a cursor?"*

---

#### 11. Keybind Modifiers — `keybinds`

**Tipo**: grupo mutuamente exclusivo (presets fixos)
**Padrão**: Padrão / WASD + Mouse (sem buff)

| Preset | Binds | Buff |
|---|---|---|
| Padrão | WASD + mouse normal | — |
| Invertido | WASD invertido (W=baixo, S=cima, A=direita, D=esquerda) | **+10% dano** |
| Arrow Keys | Setas em vez de WASD | **+15% velocidade de movimento** |
| Uma Mão Só | QWER pra mover, mouse pra tudo | **+20% XP** |
| Pesadelo | IJKL + mouse invertido (eixo Y) | **+30% dano** |

> **Flavor**: "Keyboard Anarchy" — *"Your muscle memory resigned."*

---

#### 12. Camera Smoothing — `suavizacao_camera`

**Tipo**: toggle (Ligado / Desligado)
**Padrão**: Ligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Ligado | — (câmera suave, confortável) | — |
| Desligado | Câmera trava rigidamente no jogador (sem interpolação) | **+8% velocidade de movimento do jogador** |

> **Implementação**: `Camera.follow(jogador, suavidade=1.0)` = snap direto.
> **Flavor**: "Raw Footage" — *"Stabilization costs extra."*

---

#### 13. Auto-Fire — `auto_fire`

**Tipo**: toggle (Ligado / Desligado)
**Padrão**: Ligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Ligado | — (armas automáticas atiram segurando o botão) | — |
| Desligado | Precisa clicar pra **cada tiro** em **todas** as armas (incluindo minigun!) | **+15% dano em todas as armas** |

> **Flavor**: "Trigger Discipline" — *"Every bullet is a decision."*

---

### GRUPO 4: DIFICULDADE

#### 14. Ataques Ranged dos Inimigos — `inimigos_ranged`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — (inimigos só atacam por contato) | — |
| Ligado | Inimigos Ranged passam a spawnar (atiram projéteis no jogador) | **Inimigos Ranged dropam loot com qualidade maior** (mais chance de weapon/equipment crates em vez de XP/heal) |

> **Implementação**: loot table separada para Ranged enemies com pesos maiores para weapon crates e equipment crates.
> **Flavor**: "Fairness Patch" — *"They finally discovered projectile weapons."*

---

#### 15. Captura de Drops por Inimigos — `coleta_inimiga`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — (inimigos ignoram completamente drops no chão) | — |
| Ligado | **Ativa a Coleta Inimiga (Scavenger)** (ver regras abaixo) | **Todos os drops que o jogador coleta valem 2×** (XP, cura, munição de armas, usos/duração de equipamentos — tudo dobra) |

**Regras do Enemy Scavenger:**
1. Drops têm **10 segundos de tempo de vida** (depois desaparecem).
2. Após **1 segundo** no chão, um drop fica elegível para coleta por inimigos.
3. Apenas **1 inimigo por vez** na tela inteira pode tentar coletar um drop.
4. O inimigo é selecionado **pseudo-aleatoriamente**, excluindo:
   - Inimigos **muito longe** do drop (fora de um raio X);
   - Os **2–3 inimigos mais próximos** do drop (evita que o mais perto sempre pegue).
5. Se o inimigo scavenger morrer antes de chegar ao drop, outro pode ser designado.
6. Inimigos coletando drops **ainda perseguem o jogador normalmente** — eles desviam brevemente rumo ao drop e voltam a perseguir.

> **Flavor**: "Artificial Competence" — *"Alguém acidentalmente atualizou o firmware dos monstros com um apetite voraz."*

---

#### 16. Velocidade dos Inimigos — `velocidade_inimigos`

**Tipo**: grupo mutuamente exclusivo
**Padrão**: Normal (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Normal | — | — |
| +25% | Todos os inimigos 25% mais rápidos | **+20% XP por kill** |
| +50% | Todos os inimigos 50% mais rápidos | **+40% XP por kill** |

> **Flavor**: "Overclock" — *"They found the turbo button."*

---

#### 17. HP dos Inimigos — `vida_inimigos`

**Tipo**: grupo mutuamente exclusivo
**Padrão**: Normal (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Normal | — | — |
| +50% HP | Todos os inimigos com 50% mais HP | **+20% chance de drop** |
| +100% HP | Todos os inimigos com HP dobrado | **+40% chance de drop** |

> **Flavor**: "Patch Notes v2" — *"Somebody buffed the enemies and forgot to nerf them."*

---

### GRUPO 5: EXPERIMENTAIS

#### 18. Dynamic Lighting — `iluminacao`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — (tudo visível) | — |
| Ligado | Fog of war — campo de visão limitado ao redor do jogador | **Inimigos que entram no campo de visão "nascem" com 50% do HP** |

> **Implementação**: `LightingSystem` do PPlay com fog of war. Inimigos fora do raio de luz existem com HP normal, mas quando entram no raio pela primeira vez, perdem 50% do HP atual (flag `ja_revelado` por inimigo).
> **Flavor**: "Energy Saving Mode" — *"Rendering darkness is cheaper."*

---

#### 19. Inverted Colors — `cores_invertidas`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — | — |
| Ligado | Cores da tela inteira invertidas (muito desconfortável) | **+20% dano global** |

> **Implementação**: post-processing pass invertendo RGB do buffer virtual.
> **Flavor**: "Negative Space" — *"Your retinas are filing a complaint."*

---

#### 20. Friendly Fire — `fogo_amigo`

**Tipo**: toggle (Desligado / Ligado)
**Padrão**: Desligado (sem buff)

| Valor | Nerf | Buff |
|---|---|---|
| Desligado | — | — |
| Ligado | Explosões e projéteis do jogador podem machucar o próprio jogador **e** equipamentos ativos | **+25% dano global** |

**Regras especiais:**
- Projéteis do jogador checam colisão com o próprio jogador.
- Explosões (rocket launcher, grenade launcher) têm AoE que inclui o jogador.
- **Equipamentos (drones) têm 1 HP** — qualquer dano de friendly fire os destrói instantaneamente (perdem todo o tempo restante).
- O dano de friendly fire usa o mesmo valor de dano da arma (já com o buff de +25%).

> **Flavor**: "Collateral Damage" — *"Turns out, explosions don't check IDs."*

---

#### 21. Movimento pelo Mouse — `movimento_mouse`
*(já listado no Grupo 3, #10 — não duplicar)*

---

### CONFIGS DE SISTEMA (Sempre disponíveis, sem gameplay effect)

Estas configs **não são desbloqueáveis**. Estão sempre disponíveis no menu de settings.

| # | Config | Tipo | Valores |
|---|---|---|---|
| S1 | Volume Master | Slider 0–100% | Padrão: 100% |
| S2 | Volume Música | Slider 0–100% | Padrão: 100% |
| S3 | Volume SFX | Slider 0–100% | Padrão: 100% |
| S4 | Filtro Daltônico | Toggle / seletor | Desligado / Protanopia / Deuteranopia / Tritanopia |

> Filtro daltônico é config de acessibilidade pura. Sem buff, sem nerf, sem unlock necessário.

---

### CONFIGS REMOVIDAS (não entram na v1.0)

| Config | Motivo |
|---|---|
| Bloom | Removida pelo usuário |
| Minimap | Removida pelo usuário |
| Hit Markers | Removida pelo usuário |
| Permadeath Timer | Removida pelo usuário |

---

## Tabela de Resumo Final — Todas as 21 Configs de Gameplay

| # | ID | Nome | Tipo | Padrão (sem buff) | Buff (sacrifício) |
|---|---|---|---|---|---|
| 1 | `fps_cap` | FPS Cap | Grupo 4 vals | 60 FPS | 45: dmg×0.85 / 30: spd×0.90 / 15: dmg×0.72, spd×0.81 |
| 2 | `graficos_qualidade` | Qualidade Gráfica | Toggle | Alta | Baixa: HP inimigos −20% |
| 3 | `resolucao` | Resolução | Grupo 4 vals | Nativa | 75%: drop+10% / 50%: drop+25% / 25%: drop+50% |
| 4 | `vsync` | VSync | Toggle | Ligado | Desl: mov+10% |
| 5 | `screen_shake` | Screen Shake | Toggle | Desligado | Ligado: dano explosivo+20% |
| 6 | `motion_blur` | Motion Blur | Toggle | Desligado | Ligado: mov+15% |
| 7 | `hud` | HUD | Toggle | Ligado | Desl: XP+25% |
| 8 | `damage_numbers` | Damage Numbers | Toggle | Desligado | Ligado: ativa crits (8% chance, 2× dano) |
| 9 | `zoom` | Zoom Level | Grupo 4 vals | 100% | 75%: proj hitbox+50% / 125%: dano+10% / 150%: dano+20% |
| 10 | `movimento_mouse` | Movimento Mouse | Toggle | Desligado | Ligado: drop chance+40% mult |
| 11 | `keybinds` | Keybind Modifiers | Grupo 5 vals | Padrão | Invertido: dano+10% / Arrow: mov+15% / Uma Mão: XP+20% / Pesadelo: dano+30% |
| 12 | `suavizacao_camera` | Camera Smoothing | Toggle | Ligado | Desl: mov+8% |
| 13 | `auto_fire` | Auto-Fire | Toggle | Ligado | Desl: dano+15% |
| 14 | `inimigos_ranged` | Ataques Ranged | Toggle | Desligado | Ligado: ranged dropam loot melhor |
| 15 | `coleta_inimiga` | Captura de Drops | Toggle | Desligado | Ligado: drops valem 2×, mas scavenger ativo |
| 16 | `velocidade_inimigos` | Veloc. Inimigos | Grupo 3 vals | Normal | +25%: XP+20% / +50%: XP+40% |
| 17 | `vida_inimigos` | HP Inimigos | Grupo 3 vals | Normal | +50%HP: drop+20% / +100%HP: drop+40% |
| 18 | `iluminacao` | Dynamic Lighting | Toggle | Desligado | Ligado: inimigos revelados nascem com 50% HP |
| 19 | `cores_invertidas` | Inverted Colors | Toggle | Desligado | Ligado: dano global+20% |
| 20 | `fogo_amigo` | Friendly Fire | Toggle | Desligado | Ligado: dano global+25%, equip tem 1HP |

> **Contagem real: 20 configs únicas de gameplay** (a #21 era duplicata).

> [!NOTE]
> Com 20 configs desbloqueáveis, o nível máximo do jogador é **20**. A cada level-up, 3 configs aleatórias entre as restantes são oferecidas. Em ~20 level-ups totais (ao longo de múltiplas runs), o jogador desbloqueia tudo.

---

## Regras Globais de Drops (Novo)

Baseado nas decisões do scavenger system, estas regras se aplicam a **todos os drops**, independentemente da config de Graphics Detail:

| Regra | Valor |
|---|---|
| Tempo de vida de drops no chão | **10 segundos** |
| Drops desaparecem após timeout | Sim |
| Coleta pelo jogador | Colisão imediata (walk over) |

Quando a config `detalhe_grafico` está em Baixo (scavenger ativo):
| Regra | Valor |
|---|---|
| Delay antes de elegibilidade para scavenger | **1 segundo** após spawn |
| Inimigos scavengers simultâneos | **Apenas 1** na tela inteira |
| Seleção do scavenger | Pseudo-aleatória, excluindo inimigos muito distantes e os 2–3 mais próximos do drop |
| Comportamento do scavenger | Desvia brevemente rumo ao drop, depois volta a perseguir jogador |
| Se scavenger morre | Outro pode ser designado |
| Valor dos drops para o jogador | **Tudo vale 2×** (XP, cura, munição, duração de equipamentos) |

---

## Stacking de Buffs — Regras de Multiplicação

Quando múltiplas configs afetam a mesma stat, como elas interagem?

| Stat | Configs que afetam | Regra de stacking sugerida |
|---|---|---|
| **Dano do jogador** | Auto-Fire(+15%), Keybinds(+10/30%), Inverted Colors(+20%), Friendly Fire(+25%), Zoom in(+10/20%), Screen Shake(+20% explosivo) | **Multiplicativo**: 1.15 × 1.30 × 1.20 × 1.25 = ... |
| **Velocidade do jogador** | VSync(+10%), Motion Blur(+15%), Camera Smoothing(+8%), Keybinds Arrow(+15%) | **Multiplicativo** |
| **Chance de drop** | Resolução(+10/25/50%), Mouse Movement(+40% mult), HP Inimigos(+20/40%) | **Multiplicativo** |
| **XP ganha** | HUD(+25%), Keybinds Uma Mão(+20%), Velocidade Inimigos(+20/40%) | **Multiplicativo** |
| **HP dos inimigos** | Graphics Quality(−20%), Dynamic Lighting(−50% na revelação) | **Sequencial** (−20% base, depois −50% do restante ao revelar) |
| **Dano dos inimigos** | FPS Cap(×0.85 / ×0.72) | **Direto** (único modificador) |
| **Velocidade dos inimigos** | FPS Cap(×0.90 / ×0.81), Velocidade Inimigos(+25/50%) | **Multiplicativo** |

> [!IMPORTANT]
> **Decisão necessária**: confirmar que stacking multiplicativo é desejado para tudo. Isso significa que combinar muitas configs pode ficar absurdamente forte (ex: Pesadelo+Inverted+Friendly Fire+Auto-Fire Off = 1.30 × 1.20 × 1.25 × 1.15 = **2.24× dano**, mais que dobrando). Isso é intencional e engraçado, ou precisa de cap?

---

## Estrutura do Projeto (Atualizada)

```
protocolo-batata/
├── assets/
│   ├── sprites/
│   │   ├── jogador/                # Batata sprite sheets
│   │   ├── inimigos/               # Por arquétipo
│   │   ├── armas/                  # Sprites de armas
│   │   ├── drops/                  # Crates coloridos
│   │   ├── equipamentos/           # Drones
│   │   └── graficos_baixos/        # Retângulos coloridos (Low Graphics)
│   ├── ui/
│   │   ├── botoes/                 # Estados (idle/hover/pressed/disabled)
│   │   ├── icones/                 # Configs, inventário
│   │   ├── cards/                  # Frame do card de level-up
│   │   └── barras/                 # HP, XP
│   ├── audio/
│   │   ├── musica/                 # Track 8-bit em loop
│   │   └── sfx/                    # Todos os efeitos sonoros
│   └── tiles/
│       └── grama/                  # Background
├── src/
│   ├── main.py                     # Entry point
│   ├── cenas/
│   │   ├── menu_principal.py
│   │   ├── gameplay.py
│   │   ├── menu_pausa.py
│   │   ├── level_up.py
│   │   ├── game_over.py
│   │   └── creditos.py
│   ├── entidades/
│   │   ├── jogador.py
│   │   ├── inimigo_base.py
│   │   ├── inimigo_padrao.py
│   │   ├── inimigo_tanque.py
│   │   ├── inimigo_rapido.py
│   │   ├── inimigo_phasing.py
│   │   ├── inimigo_blindado.py
│   │   ├── inimigo_ranged.py
│   │   ├── projetil.py
│   │   └── drop.py
│   ├── armas/
│   │   ├── arma_base.py
│   │   ├── melee.py
│   │   ├── pistola.py
│   │   ├── minigun.py
│   │   ├── shotgun.py
│   │   ├── rifle_assalto.py
│   │   ├── lanca_foguetes.py
│   │   └── lanca_granadas.py
│   ├── equipamentos/
│   │   ├── equipamento_base.py     # 30s duração, 1HP se friendly fire ativo
│   │   ├── drone_cura.py
│   │   ├── drone_combate.py
│   │   └── drone_suporte.py
│   ├── sistemas/
│   │   ├── config_sistema.py       # Registry, unlock, toggle
│   │   ├── config_dados.py         # Todas as 20 definições
│   │   ├── config_efeitos.py       # Aplicação dos modificadores
│   │   ├── sistema_spawn.py        # Waves + scaling
│   │   ├── sistema_xp.py           # XP + level-up trigger
│   │   ├── inventario.py           # 4 slots
│   │   ├── sistema_drops.py        # Loot tables + drop lifetime (10s)
│   │   ├── sistema_scavenger.py    # Enemy scavenger logic
│   │   ├── sistema_save.py         # JSON persistence
│   │   └── gerenciador_audio.py    # SFX + música
│   ├── ui/
│   │   ├── hud.py
│   │   ├── menu_configs.py
│   │   ├── card_config.py
│   │   ├── botao.py
│   │   ├── notificacao.py
│   │   └── texto.py
│   └── utils/
│       ├── constantes.py
│       ├── math_utils.py
│       └── asset_loader.py
├── data/
│   └── save.json
├── tools/
│   └── gerador_assets.py           # Pillow script para placeholders
├── POWER-PPLAY-2.0.pdf
├── GDD.md
└── s1.md ... s6.md
```

---

## Fases de Implementação (Sem mudanças vs. plano v1)

| Fase | Conteúdo | Sessões |
|---|---|---|
| 0 | Bootstrap + gerador de assets procedurais | 1 (Concluído) |
| 1 | Core loop: mover, atirar, morrer | 1 (Concluído) |
| **1.5** | **Refatoração Pygame-CE + UI + Controles (Mudança Arquitetural)** | 1 |
| 2 | Drops, XP, inventário, armas especiais, equipamentos | 1 |
| 3 | Sistema de configurações (as 20 configs) | 1–2 |
| 4 | UI: HUD, menus, cards, settings menu | 1–2 |
| 5 | Inimigos restantes, partículas, áudio, screen effects | 1 |
| 6 | Integração e teste completo do loop | 1 |

**Total: ~7–10 sessões**

---

## Detalhes da Fase 1.5 (Refatoração Pygame-CE)

> [!WARNING]
> **Necessita Revisão do Usuário**: Esta fase marca o abandono da engine educacional PPlay em prol do **Pygame-CE** puro.

### Motivação:
O PPlay é ótimo para propósitos educativos simples, mas peca severamente no controle fino de renderização (como centralizar textos dinâmicos) e captura de inputs complexos. O Pygame-CE nativo resolve isso elegantemente.

### O que será alterado nesta fase:
1. **Troca de Engine**: Todas as chamadas de `Window`, `GameImage`, e `Sprite` do PPlay serão convertidas para lógicas nativas do `pygame` (Surface, Rect, Font). Isso melhorará o gerenciamento espacial.
2. **Centralização de UI**: Refatorar os textos do Menu Principal, Cronômetro e Contador de Abates usando `rect.centerx = tela.centerx` para garantir alinhamento perfeito.
3. **Controle de Disparo**: Remover o sistema de "auto-fire" passivo. Armas só vão disparar mediante a captura explícita de `pygame.MOUSEBUTTONDOWN`.
4. **Troca de Armas**: Implementar listener de teclado (`K_1`, `K_2`, `K_3`) no jogador para alternar entre as 3 armas base implementadas na Fase 1.

---

## Verificação

Mesma do plano v1, com adição de:
- Testar que **todas as 20 configs defaultam para o valor sem buff** antes de desbloquear
- Testar **stacking multiplicativo** de múltiplas configs ativas
- Testar **scavenger enemy** com as regras de elegibilidade
- Testar **friendly fire** destruindo equipamentos
- Testar **drop lifetime** (desaparecem após 10s)
- Testar **inverted colors** post-processing
- Testar **dynamic lighting** com fog of war + HP reduction na revelação
