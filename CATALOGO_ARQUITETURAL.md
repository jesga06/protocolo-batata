# Protocolo: Batata — Catálogo Arquitetural Completo

> **Documento de Inventário e Referência Arquitetural**: Este arquivo consolida todas as entidades, nomes, arquétipos de inimigos, chefes, armas, equipamentos, coletáveis, cartas consumíveis, configurações de gameplay e sistema, textos de sabor (*flavor text*), efeitos mecânicos/visuais, buffs, desvantagens (*nerfs*), telas e textos de interface do projeto **Protocolo: Batata**, com a localização exata de cada item no código-fonte.

---

# 📑 Sumário da Arquitetura
1. [Inimigos, Chefes e Elites](#1-inimigos-chefes-e-elites)
2. [Arsenal de Armas e Projéteis](#2-arsenal-de-armas-e-projéteis)
3. [Equipamentos e Drones Orbitais](#3-equipamentos-e-drones-orbitais)
4. [Drops, Coletáveis e Recursos da Arena](#4-drops-coletáveis-e-recursos-da-arena)
5. [Cartas Consumíveis e Power-Ups de Level-Up](#5-cartas-consumíveis-e-power-ups-de-level-up)
6. [Catálogo Completo das 20 Configurações de Gameplay](#6-catálogo-completo-das-20-configurações-de-gameplay)
7. [Configurações de Sistema e Acessibilidade](#7-configurações-de-sistema-e-acessibilidade)
8. [O Protagonista (A Batata)](#8-o-protagonista-a-batata)
9. [Telas, HUD, Modais, Toasts e Textos de Interface](#9-telas-hud-modais-toasts-e-textos-de-interface)
10. [Fórmulas Matemáticas e Mecânicas Centrais](#10-fórmulas-matemáticas-e-mecânicas-centrais)

---

# 1. Inimigos, Chefes e Elites

### 1.1 Inimigos Regulares (Arquétipos Base)

| Inimigo & Nomes | Origem no Código / Docs | Atributos Base | Mecânicas, Efeitos & Comportamento |
|---|---|---|---|
| **Inimigo Padrão**<br>*(Estagiário / Robô Azul)* | `src/entidades/inimigo_padrao.py:1-47`<br>`src/utils/constantes.py:68-74`<br>`src/cenas/tutorial.py:173` | • **HP:** 40<br>• **Velocidade:** 100.0 px/s<br>• **Dano Contato:** 10<br>• **Cooldown:** 0.4s<br>• **XP Base:** 5<br>• **Score:** 100 | • **Mecânica:** Perseguição direta em linha reta (*beeline*).<br>• **Efeito:** Causa 10 de dano por contato quando o cooldown individual zera.<br>• **Visual:** Sprite `sprites/inimigos/inimigo_padrao.png` (28x28px). |
| **Inimigo Rápido**<br>*(Viciado em Cafeína / Verde)* | `src/entidades/inimigo_rapido.py:1-47`<br>`src/utils/constantes.py:82-88`<br>`src/cenas/tutorial.py:174` | • **HP:** 20<br>• **Velocidade:** 180.0 px/s<br>• **Dano Contato:** 8<br>• **Cooldown:** 0.25s<br>• **XP Base:** 8<br>• **Score:** 150 | • **Mecânica:** Alta mobilidade, baixo HP (morre com 2 tiros de pistola).<br>• **Efeito:** Assédio veloz contínuo ao jogador.<br>• **Visual:** Sprite em cunha verde neon `sprites/inimigos/inimigo_rapido.png` (31x31px). |
| **Inimigo Tanque**<br>*(Geladeira Industrial)* | `src/entidades/inimigo_tank.py:1-47`<br>`src/utils/constantes.py:75-81`<br>`src/cenas/tutorial.py:179` | • **HP:** 120<br>• **Velocidade:** 50.0 px/s<br>• **Dano Contato:** 20<br>• **Cooldown:** 0.7s<br>• **XP Base:** 25<br>• **Score:** 300 | • **Mecânica:** Marcha lenta, alta resistência corporal e alto dano de contato.<br>• **Efeito:** Absorve múltiplos disparos e bloqueia rotas de fuga.<br>• **Visual:** Chassi pesado `sprites/inimigos/inimigo_tank.png` (62x62px). |
| **Inimigo Blindado**<br>*(Ballistic Enthusiast)* | `src/entidades/inimigo_blindado.py:1-134`<br>`src/utils/constantes.py:97-103`<br>`src/cenas/tutorial.py:176` | • **HP:** 50<br>• **Velocidade:** 75.0 px/s<br>• **Dano Contato:** 15<br>• **Cooldown:** 0.5s<br>• **XP Base:** 15<br>• **Score:** 250 | • **Mecânica:** Placa balística frontal (cone de 90° ao redor da visão).<br>• **Efeito:** Sofre **-30% de dano** em impactos frontais (x0.70). Ataques laterais ou pelas costas sofrem 100% de dano pleno.<br>• **Visual:** Sprite couraçado `sprites/inimigos/inimigo_blindado.png` (47x47px). |
| **Inimigo Phasing**<br>*(Warranty Void / Fantasma Ciano)* | `src/entidades/inimigo_phasing.py:1-113`<br>`src/utils/constantes.py:89-96`<br>`src/cenas/tutorial.py:175` | • **HP:** 35<br>• **Velocidade:** 90.0 px/s<br>• **Dano Contato:** 12<br>• **Cooldown:** 0.4s<br>• **XP Base:** 12<br>• **Score:** 200 | • **Mecânica:** Ciclo temporal de 3.0s (durante 1.2s entra em fase etérea).<br>• **Efeito:** **Imunidade absoluta** a qualquer dano de projéteis ou melee enquanto em fase.<br>• **Visual:** Translúcido (alpha = 90) com aura ciano pulsante em `sprites/inimigos/inimigo_phasing.png` (42x42px). |
| **Inimigo Ranged**<br>*(Atirador Blaster / Ferrugem)* | `src/entidades/inimigo_ranged.py:1-156`<br>`src/utils/constantes.py:104-111`<br>`src/cenas/tutorial.py:177` | • **HP:** 30<br>• **Velocidade:** 80.0 px/s<br>• **Dano Contato:** 10<br>• **Dano Projétil:** 10<br>• **Vel. Projétil:** 260.0 px/s<br>• **Cooldown Tiro:** 1.2s<br>• **Standoff:** 280.0 px<br>• **XP Base:** 15<br>• **Score:** 200 | • **Mecânica:** Mantém distância tática de 280px e atira projéteis vermelhos a cada 1.2s em alcance <= 350px.<br>• **Buff de Drop:** Tabela de loot enriquecida (15% chance de arma e 15% de equipamento).<br>• **Visual:** Chassi ferrugem com canhão frontal `sprites/inimigos/inimigo_ranged.png` (42x42px). |

---

### 1.2 Mini-Bosses e Chefes de Elite
Spawnados a cada 60 segundos de sobrevivência com **3x HP base**, 10x Score (500 pts), cluster garantido de 50 XP (5 gemas de 10 XP), caixa de arma garantida, caixa de equipamento garantida e 50% de chance de cura. Carregam auras pulsantes roxas/douradas e barra de vida dedicada no topo do HUD.

| Tempo de Spawn | Nome Oficial do Mini-Boss | Classe Base | Origem no Código |
|---|---|---|---|
| **Minuto 1 (01:00)** | `MINI-BOSS: ESTAGIÁRIO SÊNIOR` | `InimigoRapido` | `src/sistemas/sistema_spawn.py:53` |
| **Minuto 2 (02:00)** | `MINI-BOSS: GELADEIRA INDUSTRIAL TURBO` | `InimigoTank` | `src/sistemas/sistema_spawn.py:54` |
| **Minuto 3 (03:00)** | `MINI-BOSS: PHANTOM EXECUTIVO` | `InimigoPhasing` | `src/sistemas/sistema_spawn.py:55` |
| **Minuto 4 (04:00)** | `MINI-BOSS: BASTIÃO TITÂNICO` | `InimigoBlindado` | `src/sistemas/sistema_spawn.py:56` |
| **Minuto 5 (05:00)** | `MINI-BOSS: COMANDANTE ARTILHEIRO` | `InimigoRanged` | `src/sistemas/sistema_spawn.py:57` |
| **Minuto 6 (06:00)** | `MINI-BOSS: HYPER GELADEIRA MK-II` | `InimigoTank` | `src/sistemas/sistema_spawn.py:58` |
| **Minuto 7 (07:00)** | `MINI-BOSS: ESPECTRO CORPORATIVO` | `InimigoPhasing` | `src/sistemas/sistema_spawn.py:59` |
| **Minuto 8 (08:00)** | `MINI-BOSS: FORTALEZA CIBERNÉTICA` | `InimigoBlindado` | `src/sistemas/sistema_spawn.py:60` |
| **Minuto 9 (09:00)** | `MINI-BOSS: GENERAL BALÍSTICO` | `InimigoRanged` | `src/sistemas/sistema_spawn.py:61` |
| **Minuto 10+ (10:00+)**| `MINI-BOSS: OVERLORD DA MEMÓRIA MK-{minuto}` | `InimigoTank` | `src/sistemas/sistema_spawn.py:66` |
| **Debug Spawn** | `Chefe de Elite` | `InimigoPadrao` (Elite) | `src/ui/menu_debug.py:69` |

---

# 2. Arsenal de Armas e Projéteis

### 2.1 Armas Permanentes (Slots 1 e 2)

| Arma | Slot | Flavor Text | Atributos & Mecânicas | Efeitos Visuais / Sonoros | Origem no Código |
|---|---|---|---|---|---|
| **Chave de Manutenção**<br>*(Melee)* | 1 | *"Manutenção percussiva resolve a maioria dos problemas."* | • **Dano:** 10<br>• **Cooldown:** 0.6s<br>• **Alcance:** 109.0 px<br>• **Arco:** Cone de 60.0°<br>• **Knockback:** 360.0 px/s nos 2 alvos mais próximos<br>• **Munição:** Infinita | • **Visual:** Cone azul-ciano translúcido de mira + corte dourado (*slash fan*).<br>• **SFX:** `audio/sfx/ataque_melee.wav` | `src/armas/melee.py:1-132`<br>`GDD.md:289-291`<br>`src/utils/constantes.py:127-134` |
| **Padrão de Fábrica**<br>*(Pistola)* | 2 | *"Tecnicamente qualifica como 'armado'."* | • **Dano:** 10<br>• **Cooldown:** 0.33s (0.35s base)<br>• **Vel. Projétil:** 420.0 px/s<br>• **Tempo Vida:** 2.5s<br>• **Munição:** Infinita | • **Visual:** Projétil amarelo pontual `sprites/projeteis/projetil_pistola.png`.<br>• **SFX:** `audio/sfx/tiro_pistola.wav` | `src/armas/pistola.py:1-72`<br>`GDD.md:305-307`<br>`src/utils/constantes.py:135-140` |

---

### 2.2 Armas Especiais Temporárias (Slot 3)

| Arma | Munição | Flavor / Descrição | Atributos Mecânicos | Efeitos Visuais / Sonoros | Origem no Código |
|---|---|---|---|---|---|
| **Escopeta**<br>*(Shotgun)* | 45 cartuchos | *"Disparo de múltiplos projéteis em leque cônico com alto impacto a curta distância."* | • **Dano:** 10 por pellet<br>• **Pellets:** 9 projéteis<br>• **Cooldown:** 0.70s<br>• **Dispersão:** 0.45 rad<br>• **Vel. Projétil:** 420.0 px/s | • **Visual:** Leque simétrico de 9 projéteis `sprites/projeteis/projetil_shotgun.png`.<br>• **SFX:** `audio/sfx/tiro_shotgun.wav` | `src/armas/shotgun.py:1-89`<br>`src/utils/constantes.py:147-153` |
| **Minigun** | 225 tiros | *"Altíssima cadência de tiro, leve dispersão e grande capacidade de munição."* | • **Dano:** 6<br>• **Cooldown:** 0.08s<br>• **Vel. Projétil:** 550.0 px/s<br>• **Dispersão:** +-0.06 rad | • **Visual:** Projétil veloz `sprites/projeteis/projetil_minigun.png`.<br>• **SFX:** `audio/sfx/tiro_minigun.wav` | `src/armas/minigun.py:1-81`<br>`src/utils/constantes.py:142-146` |
| **Rifle de Assalto** | 90 tiros | *"Disparos precisos em linha reta com projéteis de altíssima velocidade."* | • **Dano:** 18<br>• **Cooldown:** 0.18s<br>• **Vel. Projétil:** 650.0 px/s<br>• **Dispersão:** 0.0 rad (perfeita) | • **Visual:** Traço balístico veloz `sprites/projeteis/projetil_rifle.png`.<br>• **SFX:** `audio/sfx/tiro_rifle.wav` | `src/armas/rifle_assalto.py:1-72`<br>`src/utils/constantes.py:154-158` |
| **Lança-Foguetes** | 18 foguetes | *"Dispara ogivas de alto impacto com grande raio de explosão (AoE de 80px)."* | • **Dano Base:** 60<br>• **Impacto Direto:** 2x dano (120 dano)<br>• **Raio AoE:** 80.0 px<br>• **Cooldown:** 1.20s<br>• **Vel. Projétil:** 300.0 px/s | • **Visual:** Ogiva `sprites/projeteis/projetil_foguete.png` + onda de choque expansiva laranja e detritos.<br>• **SFX:** `audio/sfx/tiro_foguete.wav` e `audio/sfx/explosao.wav` | `src/armas/lanca_foguetes.py:1-77`<br>`src/utils/constantes.py:159-164` |
| **Lança-Granadas** | 24 granadas | *"Dispara granadas explosivas com raio de ação de 65px e boa cadência."* | • **Dano Base:** 45<br>• **Impacto Direto:** 2x dano (90 dano)<br>• **Raio AoE:** 65.0 px<br>• **Cooldown:** 0.90s<br>• **Vel. Projétil:** 280.0 px/s | • **Visual:** Projétil esférico `sprites/projeteis/projetil_granada.png` + detonação AoE.<br>• **SFX:** `audio/sfx/tiro_granada.wav` e `audio/sfx/explosao.wav` | `src/armas/lanca_granadas.py:1-77`<br>`src/utils/constantes.py:165-170` |
| **Railgun**<br>*(Canhão Eletromagnético)* | 22 disparos | *"Requer 1.0s de carga energética e dispara projétil perfurante hipersônico."* | • **Dano:** 50<br>• **Tempo de Carga:** 1.0s<br>• **Cooldown:** 1.20s<br>• **Vel. Projétil:** 1400.0 px/s<br>• **Propriedade:** Atravessa infinitos inimigos (*Piercing*) | • **Visual:** Feixe perfurante de alta energia (12x12px).<br>• **SFX:** `audio/sfx/tiro_foguete.wav` (carregando) e `audio/sfx/tiro_rifle.wav` (disparo) | `src/armas/railgun.py:1-114`<br>`src/utils/constantes.py:171-176` |

---

# 3. Equipamentos e Drones Orbitais (Slot 4)
Drones orbitam o jogador com raio R = 48.0 px, velocidade angular omega = 2.5 rad/s, duração de **30.0 segundos** (ou 60.0s com bônus de drops 2x), possuem **1 HP** (destruídos por Fogo Amigo) e operam simultaneamente em enxame com órbitas defasadas em 90 graus.

| Equipamento | Efeito Mecânico / Benefício | Efeitos Visuais / Assets | Origem no Código |
|---|---|---|---|
| **Drone de Cura** | Restaura **+5 HP periodicamente a cada 3.0s** até o teto de vida máxima do jogador. | Sprite orbital verde `sprites/equipamentos/drone_cura.png` (24x24px). | `src/equipamentos/drone_cura.py:1-49`<br>`src/utils/constantes.py:184-185` |
| **Drone de Combate** | Rastreia o inimigo mais próximo em um raio de 350px e dispara automaticamente a cada 1.0s (**8 de dano** por projétil). | Sprite orbital azul-ciano `sprites/equipamentos/drone_combate.png` (24x24px). | `src/equipamentos/drone_combate.py:1-108`<br>`src/utils/constantes.py:186-188` |
| **Drone de Suporte** | Concede **+15% de velocidade de movimento** à batata e **atrai magneticamente todos os drops** no chão em um raio de 150px (velocidade de atração: 250 px/s). | Sprite orbital dourado `sprites/equipamentos/drone_suporte.png` (24x24px). | `src/equipamentos/drone_suporte.py:1-63`<br>`src/utils/constantes.py:189-191` |

---

# 4. Drops, Coletáveis e Recursos da Arena
Todos os itens duram **60.0 segundos no chão** (`DROP_TEMPO_DESAPARECER = 60.0`), piscam nos últimos 4 segundos antes de expirar, pulsam dinamicamente e ativam a mecânica Scavenger após 10.0s se a Configuração 15 estiver ativa.

| Drop & Tipo | Valor / Efeito Imediato | Chance Base | Visual & SFX | Origem no Código |
|---|---|---|---|---|
| **Gema de XP** (`xp`) | Concede **+5 XP** (Padrão), **+8 XP** (Rápido), **+12 XP** (Phasing), **+15 XP** (Blindado/Ranged), **+25 XP** (Tanque) ou cluster de **50 XP** (5x10 em Elites). | 100% garantido por abate | • Sprite amarelo `sprites/drops/drop_xp.png` (42x42px).<br>• Burst dourado.<br>• SFX: `audio/sfx/pickup_xp.wav`. | `src/entidades/drop.py:1-131`<br>`src/sistemas/sistema_drops.py:48-114` |
| **Caixa de Cura** (`cura`) | Restaura imediatamente **+35 HP** do jogador (ou +70 HP com dobro de drop). | 8% base (+50% em Elites) | • Sprite médico vermelho `sprites/drops/drop_cura.png`.<br>• Burst verde.<br>• SFX: `audio/sfx/pickup_cura.wav`. | `src/entidades/drop.py:80`<br>`src/sistemas/sistema_drops.py:116-132` |
| **Caixa de Arma** (`arma`) | Equipa uma arma especial aleatória no Slot 3 com **+50% de munição** (Minigun, Shotgun, Rifle, Foguetes, Granadas, Railgun). | 5.6% base (21% em Ranged / Loot Enriquecido / 100% Elites) | • Sprite dourado de arma `sprites/drops/drop_arma.png`.<br>• Burst laranja.<br>• SFX: `audio/sfx/pickup_arma.wav`. | `src/entidades/drop.py:81`<br>`src/sistemas/sistema_drops.py:134-153` |
| **Caixa de Equipamento** (`equipamento`) | Ativa um drone companheiro orbital aleatório no Slot 4 com duração de **30.0 segundos**. | 4.2% base (21% em Ranged / Loot Enriquecido / 100% Elites) | • Sprite roxo de drone `sprites/drops/drop_equipamento.png`.<br>• Burst roxo.<br>• SFX: `audio/sfx/pickup_equipamento.wav`. | `src/entidades/drop.py:82`<br>`src/sistemas/sistema_drops.py:155-174` |
| **Drop de Configuração** (`config`) | Utilizado em drops de eventos especiais / UI. | Configuração permanente | • Sprite ciano `sprites/drops/drop_config.png`.<br>• Burst ciano. | `src/utils/constantes.py:696` |

---

# 5. Cartas Consumíveis e Power-Ups de Level-Up
Oferecidas nos níveis regulares (1-4, 6-9, 11-14, 16-19) e nos slots laterais em níveis de marco. Concedem bônus temporários (15s) estritamente inferiores aos buffs permanentes das Configurações.

| Card & Identificador | Categoria | Flavor Text | Benefício (Buff) | Sacrifício / Nerf | Tier de Aparição | Origem no Código |
|---|---|---|---|---|---|---|
| **Cura Rápida**<br>(`cura_pequena`) | Consumível | *"Curativo biológico de ação rápida."* | Restaura **+25 HP** imediatamente | Nenhum sacrifício | Tiers 1, 2 | `src/ui/modal_level_up.py:105-116` |
| **Cura Enriquecida**<br>(`cura_grande`) | Consumível | *"Regenerador celular enriquecido."* | Restaura **+50 HP** imediatamente | Nenhum sacrifício | Tiers 2, 3, 4 | `src/ui/modal_level_up.py:117-128` |
| **Carga de Dados**<br>(`xp_pequeno`) | Consumível | *"Pequeno cluster de dados brutos."* | **+15 XP** instantâneo para progressão | Nenhum sacrifício | Tiers 1, 2 | `src/ui/modal_level_up.py:129-140` |
| **Surto de Dados**<br>(`xp_grande`) | Consumível | *"Banco de dados concentrado descompactado."* | **+30 XP** instantâneo para progressão | Nenhum sacrifício | Tiers 2, 3, 4 | `src/ui/modal_level_up.py:141-152` |
| **Calibração Térmica**<br>(`buff_dano_temp`) | Consumível | *"Ajuste fino nos percursores de tiro."* | **+5% Dano** em todas as armas por 15s | Duração temporária (15 segundos) | Tiers 1, 2, 3, 4 | `src/ui/modal_level_up.py:153-165` |
| **Sobrecarga de Passos**<br>(`buff_vel_temp`) | Consumível | *"Lubrificação de emergência nas esteiras."* | **+8% Velocidade** de movimento por 15s | Duração temporária (15 segundos) | Tiers 1, 2, 3, 4 | `src/ui/modal_level_up.py:166-178` |
| **Acelerador de Gatilho**<br>(`buff_cadencia_temp`) | Consumível | *"Mecanismo de repetição acelerado."* | **+8% Cadência** de Tiro (-8% Cooldown) por 15s | Duração temporária (15 segundos) | Tiers 1, 2, 3, 4 | `src/ui/modal_level_up.py:179-191` |
| **Matriz Protetora**<br>(`buff_resistencia_temp`) | Consumível | *"Campos de dispersão de impacto."* | **-8% Dano Recebido** por 15s (x0.92) | Duração temporária (15 segundos) | Tiers 1, 2, 3, 4 | `src/ui/modal_level_up.py:192-204` |
| **Escudo Biológico**<br>(`escudo`) | Consumível | *"Película bioenergética repelente."* | **Absorve 1 hit** e concede 4.0s de invulnerabilidade ao quebrar | Uso único até sofrer impacto | Tiers 2, 3, 4 | `src/ui/modal_level_up.py:205-216` |
| **Pulso Magnético**<br>(`pulso_magnetico`) | Consumível | *"Pulso eletromagnético sintonizado na frequência dos drops."* | **Atrai instantaneamente todos os drops** da arena para a batata | Uso instantâneo | Tiers 2, 3, 4 | `src/ui/modal_level_up.py:217-228` |
| **Remessa Bélica**<br>(`caixa_arma`) | Consumível | *"Suprimento tático direto das fábricas."* | Equipa arma especial aleatória no Slot 3 | Até esgotar munição | Tiers 3, 4 | `src/ui/modal_level_up.py:229-240` |
| **Drone Utilitário**<br>(`caixa_equip`) | Consumível | *"Unidade orbital autônoma de assistência."* | Spawna drone companheiro aleatório no Slot 4 | Duração de 30 segundos | Tiers 3, 4 | `src/ui/modal_level_up.py:241-252` |

---

# 6. Catálogo Completo das 20 Configurações de Gameplay
SSOT Oficial: `CONFIGURACOES.md` e `src/sistemas/config_dados.py`. As opções padrão nunca concedem bônus.

| ID & Nome Oficial | Categoria & Tipo | Opções Disponíveis | Flavor Texts | Sacrifício (Nerf) | Benefício (Buff Mecânico) | Origem no Código |
|---|---|---|---|---|---|---|
| **1. Limite de Quadros**<br>(`fps_cap`) | Performance<br>*(Grupo)* | • `60` (Padrão)<br>• `45`<br>• `30`<br>• `15` | • **60:** *"O olho humano não consegue ver além de 30 FPS."*<br>• **45 (Modo Performance):** *"Os inimigos também estão perdendo frames."*<br>• **30 (Modo Slow Motion):** *"Só é lag se você estiver perdendo."*<br>• **15 (Experiência Cinematográfica):** *"Cada frame foi desenhado à mão por monges tibetanos."* | • **60:** Nenhum<br>• **45:** Fluidez a 45 FPS<br>• **30:** Fluidez a 30 FPS<br>• **15:** Quase injogável (15 FPS) | • **60:** Nenhum<br>• **45:** Dano de inimigos **-15%** (x0.85)<br>• **30:** Vel. de inimigos **-10%** (x0.90)<br>• **15:** Dano **-27.75%** (x0.7225) e Vel. **-19%** (x0.81) | `src/sistemas/config_dados.py:59-100`<br>`CONFIGURACOES.md:17-28` |
| **2. Qualidade Gráfica**<br>(`graficos_qualidade`) | Performance<br>*(Toggle)* | • `alta` (Padrão)<br>• `baixa` | • **Alta:** *"Sprites nítidos para quem aprecia os pequenos detalhes."*<br>• **Baixa (Cortes no Orçamento):** *"Texturas são um luxo que o departamento financeiro cortou."* | • **Alta:** Nenhum<br>• **Baixa:** Todos os sprites viram formas geométricas e retângulos simplificados | • **Alta:** Nenhum<br>• **Baixa:** HP máximo de todos os inimigos reduzido em **-20%** (x0.80) | `src/sistemas/config_dados.py:103-128`<br>`CONFIGURACOES.md:31-40` |
| **3. Resolução da Tela**<br>(`resolucao`) | Performance<br>*(Grupo)* | • `100%` (Padrão)<br>• `75%`<br>• `50%`<br>• `25%` | • **100%:** *"Cada pixel em seu devido lugar."*<br>• **75% (Anti-Aliasing Reverso):** *"Menos pixels na tela, mais caixas no chão."*<br>• **50% (Nostalgia Forçada):** *"Lembranças de uma época de monitores CRT."*<br>• **25% (Arqueologia de Pixels):** *"Se você consegue contar os pixels nos dedos, está economizando processamento."* | • **100%:** Nenhum<br>• **75%:** Visão levemente borrada<br>• **50%:** Visão consideravelmente pixelada<br>• **25%:** Tela quase indecifrável | • **100%:** Nenhum<br>• **75%:** Chance de drop **+10%**<br>• **50%:** Chance de drop **+25%**<br>• **25%:** Chance de drop **+50%** | `src/sistemas/config_dados.py:131-172`<br>`CONFIGURACOES.md:43-54` |
| **4. Sincronização Vertical**<br>(`vsync`) | Performance<br>*(Toggle)* | • `ligado` (Padrão)<br>• `desligado` | • **Ligado:** *"Estabilidade garantida para monitores sensíveis."*<br>• **Desligado (Morte por Mil Cortes):** *"Espero que seu monitor tenha FreeSync."* | • **Ligado:** Nenhum<br>• **Desligado:** Possível quebra visual (*screen tearing*) | • **Ligado:** Nenhum<br>• **Desligado:** Velocidade de movimento da batata aumentada em **+10%** (x1.10) | `src/sistemas/config_dados.py:175-200`<br>`CONFIGURACOES.md:57-66` |
| **5. Tremor de Tela**<br>(`screen_shake`) | Performance / Visual<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Uma experiência suave."*<br>• **Ligado (Protocolo: Terremoto):** *"A tela treme. A sua mira também."* | • **Desligado:** Nenhum<br>• **Ligado:** A tela treme violentamente a cada explosão, disparo pesado e dano | • **Desligado:** Nenhum<br>• **Ligado:** Dano das armas explosivas (Foguetes e Granadas) aumentado em **+20%** (x1.20) | `src/sistemas/config_dados.py:203-228`<br>`CONFIGURACOES.md:69-78` |
| **6. Desfoque de Movimento**<br>(`motion_blur`) | Performance / Visual<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Uma experiência suave."*<br>• **Ligado (Fantasmagórico):** *"Você se move tão rápido que até seus pixels ficaram para trás."* | • **Desligado:** Nenhum<br>• **Ligado:** Rastro visual (*ghosting*) borra elementos rápidos | • **Desligado:** Nenhum<br>• **Ligado:** Velocidade de movimento da batata aumentada em **+15%** (x1.15) | `src/sistemas/config_dados.py:231-256`<br>`CONFIGURACOES.md:81-90` |
| **7. Exibição de Interface**<br>(`hud`) | Interface<br>*(Toggle)* | • `ligado` (Padrão)<br>• `desligado` | • **Ligado:** *"Barras de vida, experiência, inventário e cronômetro visíveis."*<br>• **Desligado ("Trust Me Bro"):** *"Com certeza você ainda tem vida sobrando. Provavelmente."* | • **Ligado:** Nenhum<br>• **Desligado:** Oculta completamente HP, XP, inventário, munição e timer na tela | • **Ligado:** Nenhum<br>• **Desligado:** Ganho de experiência (XP) aumentado em **+25%** (x1.25) | `src/sistemas/config_dados.py:259-284`<br>`CONFIGURACOES.md:93-102` |
| **8. Números de Dano**<br>(`damage_numbers`) | Interface<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Inimigos sofrem dano em silêncio."*<br>• **Ligado (Aula de Matemática):** *"Finalmente uma aplicação prática para aritmética básica."* | • **Desligado:** Nenhum (críticos desativados)<br>• **Ligado:** Poluição visual com centenas de números flutuantes | • **Desligado:** Nenhum<br>• **Ligado:** Habilita o Sistema de Críticos: **15% de chance de causar 2x de dano** | `src/sistemas/config_dados.py:287-312`<br>`CONFIGURACOES.md:105-114` |
| **9. Nível de Zoom**<br>(`zoom`) | Interface<br>*(Grupo)* | • `75%`<br>• `100%` (Padrão)<br>• `125%`<br>• `150%` | • **75% (Visão de Satélite):** *"Aquilo é uma batata ou uma formiga armada?"*<br>• **100%:** *"Campo de visão padrão e equilibrado."*<br>• **125% (Lupa):** *"Foco total no que está na sua cara."*<br>• **150% (Modo Microscópio):** *"Você consegue ver de perto os inimigos."* | • **75%:** Câmera distante, sprites menores<br>• **100%:** Nenhum<br>• **125%:** Visão periférica reduzida<br>• **150%:** Visão extremamente restrita do mapa | • **75%:** Hitbox de todos os projéteis aumentada em **+50%** (x1.50)<br>• **100%:** Nenhum<br>• **125%:** Dano global **+10%** (x1.10)<br>• **150%:** Dano global **+20%** (x1.20) | `src/sistemas/config_dados.py:315-356`<br>`CONFIGURACOES.md:117-128` |
| **10. Movimento pelo Mouse**<br>(`movimento_mouse`) | Controles<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Controle manual com pés firmes nas teclas."*<br>• **Ligado (Piloto Automático):** *"Para que servem as pernas quando o destino tem um cursor?"* | • **Desligado:** Nenhum<br>• **Ligado:** A batata caminha Processo incessante em direção ao mouse; teclas de movimento desativadas | • **Desligado:** Nenhum<br>• **Ligado:** Chance de drop multiplicativa aumentada em **+40%** (x1.40) | `src/sistemas/config_dados.py:359-384`<br>`CONFIGURACOES.md:131-140` |
| **11. Modificadores de Teclas**<br>(`keybinds`) | Controles<br>*(Grupo)* | • `padrao` (Padrão)<br>• `invertido`<br>• `arrow_keys`<br>• `uma_mao`<br>• `pesadelo` | • **Padrão:** *"Ergonomia convencional para seres humanos normais."*<br>• **Invertido (Horizontes Invertidos):** *"Para cima é o novo para baixo."*<br>• **Arrow Keys (Nostalgia):** *"Lembranças dolorosas de jogar no teclado de 1998."*<br>• **Uma Mão Só:** *"Uma mão no volante, a outra no carinho."*<br>• **Pesadelo (Anarquia das Teclas):** *"Sua memória muscular acabou de pedir demissão."* | • **Padrão:** Nenhum<br>• **Invertido:** W: baixo, S: cima, A: dir, D: esq<br>• **Arrow Keys:** Movimento apenas nas setas<br>• **Uma Mão:** Movimento em `QWER`<br>• **Pesadelo:** `IJKL` com eixo Y do mouse invertido | • **Padrão:** Nenhum<br>• **Invertido:** Dano global **+10%**<br>• **Arrow Keys:** Velocidade **+15%**<br>• **Uma Mão:** Ganho de XP **+20%**<br>• **Pesadelo:** Dano global **+30%** | `src/sistemas/config_dados.py:387-436`<br>`CONFIGURACOES.md:143-155` |
| **12. Suavização de Câmera**<br>(`suavizacao_camera`) | Controles / Câmera<br>*(Toggle)* | • `ligado` (Padrão)<br>• `desligado` | • **Ligado:** *"Transições suaves para evitar tontura."*<br>• **Desligado (Raw Footage):** *"Estabilização de imagem é cobrada à parte."* | • **Ligado:** Nenhum<br>• **Desligado:** Câmera trava rigidamente no centro do avatar sem interpolação | • **Ligado:** Nenhum<br>• **Desligado:** Velocidade de movimento da batata aumentada em **+8%** (x1.08) | `src/sistemas/config_dados.py:439-464`<br>`CONFIGURACOES.md:158-167` |
| **13. Disparo Automático**<br>(`auto_fire`) | Controles / Combate<br>*(Toggle)* | • `ligado` (Padrão)<br>• `desligado` | • **Ligado:** *"Segure o botão e reze."*<br>• **Desligado (Trigger Discipline):** *"Cada projétil disparado é uma decisão de vida ou morte."* | • **Ligado:** Nenhum<br>• **Desligado:** Exige clicar manualmente a cada disparo para todas as armas | • **Ligado:** Nenhum<br>• **Desligado:** Dano global de todas as armas aumentado em **+15%** (x1.15) | `src/sistemas/config_dados.py:467-492`<br>`CONFIGURACOES.md:170-179` |
| **14. Inimigos à Distância**<br>(`inimigos_ranged`) | Dificuldade<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Inimigos civilizados."*<br>• **Ligado (Evolução Tecnológica):** *"Eles finalmente descobriram a tecnologia dos projéteis balísticos."* | • **Desligado:** Nenhum<br>• **Ligado:** Inimigos com disparos balísticos (*Ranged*) passam a spawnar no mapa | • **Desligado:** Nenhum<br>• **Ligado:** Inimigos Ranged possuem tabela de loot enriquecida (**15% arma / 15% drone**) | `src/sistemas/config_dados.py:495-520`<br>`CONFIGURACOES.md:182-191` |
| **15. Captura de Drops por Inimigos**<br>(`coleta_inimiga`) | Dificuldade<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Raposo, não pegue."*<br>• **Ligado (Modo Raciocínio):** *"Os inimigos se sentiram inspirados pelo Gemini 3.7 Flash."* | • **Desligado:** Nenhum<br>• **Ligado:** Inimigos tentam ativamente devorar drops após 10s no chão (Scavenger) | • **Desligado:** Nenhum<br>• **Ligado:** **Todos os drops valem 2x** (XP em dobro, cura em dobro, munição dobrada e 60s em drones) | `src/sistemas/config_dados.py:523-548`<br>`CONFIGURACOES.md:194-203` |
| **16. Velocidade dos Inimigos**<br>(`velocidade_inimigos`) | Dificuldade<br>*(Grupo)* | • `normal` (Padrão)<br>• `+25%`<br>• `+50%` | • **Normal:** *"Inimigos marcham normalmente."*<br>• **+25% (Overclock):** *"Eles encontraram o botão turbo."*<br>• **+50% (Surto):** *"Injetaram energético na corrente de dados."* | • **Normal:** Nenhum<br>• **+25%:** Inimigos se movem +25% mais rápido<br>• **+50%:** Inimigos se movem +50% mais rápido | • **Normal:** Nenhum<br>• **+25%:** Ganho de XP aumentado em **+20%** (x1.20)<br>• **+50%:** Ganho de XP aumentado em **+40%** (x1.40) | `src/sistemas/config_dados.py:551-584`<br>`CONFIGURACOES.md:206-216` |
| **17. Vida dos Inimigos**<br>(`vida_inimigos`) | Dificuldade<br>*(Grupo)* | • `normal` (Padrão)<br>• `+50%`<br>• `+100%` | • **Normal:** *"Inimigos com vida padrão."*<br>• **+50% (Blindados):** *"Blindagem adicional direto da fábrica."*<br>• **+100% (Pesados):** *"Eles estão mais densos."* | • **Normal:** Nenhum<br>• **+50%:** Inimigos possuem +50% de HP (x1.50)<br>• **+100%:** Inimigos possuem dobro de HP (x2.00) | • **Normal:** Nenhum<br>• **+50%:** Chance de drop **+20%**<br>• **+100%:** Chance de drop **+40%** | `src/sistemas/config_dados.py:587-620`<br>`CONFIGURACOES.md:219-229` |
| **18. Iluminação Dinâmica**<br>(`iluminacao`) | Experimental / Atmosfera<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Luz do dia perpétua sobre o campo de batalha."*<br>• **Ligado (Modo Escuridão):** *"Eles estão com dificuldade de te enxergar."* | • **Desligado:** Nenhum<br>• **Ligado:** Névoa de escuridão (*Fog of War*): visão restrita a 170px | • **Desligado:** Nenhum<br>• **Ligado:** Inimigos fora do círculo de visão **causam -50% de dano** (x0.50) | `src/sistemas/config_dados.py:623-648`<br>`CONFIGURACOES.md:232-241` |
| **19. Cores Invertidas**<br>(`cores_invertidas`) | Experimental / Visual<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Paleta de cores original e aconchegante."*<br>• **Ligado (Espaço Negativo):** *"Seus olhos registraram uma reclamação no Procon."* | • **Desligado:** Nenhum<br>• **Ligado:** Inversão total de RGB da tela (negativo fotográfico) | • **Desligado:** Nenhum<br>• **Ligado:** Dano global de todas as armas aumentado em **+20%** (x1.20) | `src/sistemas/config_dados.py:651-676`<br>`CONFIGURACOES.md:244-253` |
| **20. Fogo Amigo**<br>(`fogo_amigo`) | Experimental / Risco Extremo<br>*(Toggle)* | • `desligado` (Padrão)<br>• `ligado` | • **Desligado:** *"Seus tiros e explosões atravessam você inofensivamente."*<br>• **Ligado (Collateral Damage):** *"Aparentemente, estilhaços de granada não leem crachá de identificação."* | • **Desligado:** Nenhum<br>• **Ligado:** Próprios projéteis e explosões causam dano à batata; Drones têm 1 HP e são destruídos | • **Desligado:** Nenhum<br>• **Ligado:** Dano global de todas as armas aumentado em **+25%** (x1.25) | `src/sistemas/config_dados.py:679-704`<br>`CONFIGURACOES.md:256-265` |

---

# 7. Configurações de Sistema e Acessibilidade

| Configuração & ID | Tipo & Padrão | Valores | Descrição de Interface | Origem no Código |
|---|---|---|---|---|
| **S1. Volume Geral**<br>(`volume_master`) | Slider (100%) | `0%` a `100%` | *"Controla o volume geral de toda a aplicação (0% a 100%)."* | `src/sistemas/config_dados.py:714-723` |
| **S2. Volume da Música**<br>(`volume_musica`) | Slider (100%) | `0%` a `100%` | *"Controla a trilha sonora 8-bit em loop (0% a 100%)."* | `src/sistemas/config_dados.py:726-735` |
| **S3. Volume dos Efeitos**<br>(`volume_sfx`) | Slider (100%) | `0%` a `100%` | *"Controla tiros, explosões, pickups e menus (0% a 100%)."* | `src/sistemas/config_dados.py:737-746` |
| **S4. Filtro Daltônico**<br>(`filtro_daltonico`) | Seletor (`desligado`) | `desligado`, `protanopia`, `deuteranopia`, `tritanopia` | *"Aplica matrizes de acessibilidade para protanopia, deuteranopia ou tritanopia."* | `src/sistemas/config_dados.py:749-764` |
| **S5. Escala Global**<br>(`escala_global`) | Seletor (`100%`) | `100%`, `125%`, `150%` | *"Escala sistêmica de renderização e elementos gráficos para telas de alta resolução."* | `src/sistemas/config_dados.py:767-782` |

---

# 8. O Protagonista (A Batata)
- **High Concept:** Avatar robótico em formato de batata, desprovido de diálogos ou história complexa, que se torna mais forte aceitando desconforto nas configurações do jogo.
- **HP Base:** 150 HP (`JOGADOR_HP_MAX_PADRAO = 150`).
- **Velocidade Base:** 200.0 px/s (`JOGADOR_VELOCIDADE_PADRAO = 200.0`).
- **Dimensões do Sprite:** 32x32px base / 42x42px visual (`batata_idle.png`, `batata_dano.png`, `batata_walk_sheet.png`).
- **Invulnerabilidade pós-dano:** 0.2s mínimo (`JOGADOR_INVULNERABILIDADE_TEMPO = 0.2`) e flash vermelho de 0.15s (`JOGADOR_COOLDOWN_DANO_FLASH = 0.15`).
- **Origem no Código:** `src/entidades/jogador.py:1-441`, `src/utils/constantes.py:57-63`, `GDD.md:173-184`.

---

# 9. Telas, HUD, Modais, Toasts e Textos de Interface

### 9.1 Menu Principal
- **Título:** `Protocolo: Batata` (Dourado, centralizado em y=100)
- **Badge de Recorde:** `RECORDE: {high_score:,} PTS   |   MELHOR TEMPO: {m_tempo:02d}:{s_tempo:02d}`
- **Opções:**
  - `JOGAR [ENTER]`
  - `CONFIGURAÇÕES [C]`
  - `TUTORIAL [T]`
  - `SAIR [ESC]`
- **Rodapé:** `PPlay 2.0 Engine | Use [W/S] ou [Setas] para navegar e [ENTER] para confirmar`
- **Origem no Código:** `src/cenas/menu_principal.py:24-155`

### 9.2 Modal de Level Up (3-Card Upgrade Draw)
- **Título:** `LEVEL UP!` (Dourado em y=45)
- **Subtítulo:** `ESCOLHA UM UPGRADE DO SISTEMA` (Roxo claro em y=85)
- **Fila de Upgrades:** `+{fila_level_ups - 1} UPGRADE(S) RESTANTE(S) NA FILA` (Laranja alerta)
- **Badges nos Cards:** `[1]`, `[2]`, `[3]`
- **Tags de Categoria:** `[CONFIGURACAO]`, `[CONSUMIVEL]`
- **Seções dos Cards:** `BENEFICIOS:` (Verde) e `SACRIFICIO:` (Laranja)
- **Prompt dos Cards:** `Pressione [1]`, `Pressione [2]`, `Pressione [3]`
- **Rodapé:** `Pressione [1], [2], [3] no teclado ou clique com o mouse para escolher`
- **Origem no Código:** `src/ui/modal_level_up.py:708-852`

### 9.3 In-Game HUD e Toasts de Coleta
- **Cronômetro:** `{minutos:02d}:{segundos:02d}`
- **Abates:** `Abates: {abates}`
- **Barra de XP:** `NÍVEL {sistema_xp.nivel} (MÁXIMO)` ou `Nv. {nivel} - {xp_atual}/{proximo_custo} XP`
- **Barra de Chefe Elite:** `{nome_elite}` e `{hp_atual}/{hp_max} HP`
- **Slots Inventário:** `[1]` Melee, `[2]` Pistola, `[3]` Especial (Munição em número), `[4]` Drone (`{tempo}s` ou `x{qtd} ({tempo}s)`)
- **Indicador FPS / Engrenagem:** `FPS: {fps}` e `[C]` (752x16px)
- **Toasts Flutuantes:**
  - `+{ev['valor']} XP` (Amarelo)
  - `+{val_cura} HP` (Verde)
  - `{nome_arma} ({mun})` (Dourado)
  - `{nome_drone} (30s)` (Laranja)
- **Origem no Código:** `src/ui/hud.py:27-133`, `src/cenas/gameplay.py:709-747`

### 9.4 Tela de Pausa
- **Título:** `JOGO PAUSADO`
- **Opções:** `[ESC] Continuar Partida`, `[M] Menu Principal`
- **Origem no Código:** `src/cenas/gameplay.py:1270-1284`

### 9.5 Tela de Game Over (Derrota)
- **Título:** `PROTOCOLO FALHOU` (Vermelho)
- **Subtítulo:** `A Batata sucumbiu aos bugs e estagiários.`
- **Métricas:**
  - `Tempo de Sobrevivência: {minutos:02d}:{segundos:02d}`
  - `Total de Abates: {self.abates}`
  - `Dano Total: {self.dano_total_causado:,}`
  - `Pontuação Final: {score_val:,} PTS`
  - `[NOVO RECORDE DE PONTOS!]` (se superado)
- **Prompt:** `Pressione [ENTER] para Jogar Novamente ou [ESC] para o Menu`
- **Origem no Código:** `src/cenas/gameplay.py:1297-1330`

### 9.6 Tela de Vitória (10 Minutos)
- **Título:** `PROTOCOLO EXECUTADO COM SUCESSO` (Dourado)
- **Subtítulo:** `A Batata superou 10 minutos de compilacao sem erros criticos.`
- **Métricas:**
  - `Tempo de Sobrevivencia:` `10:00 (600.0s) [MAXIMO]`
  - `Inimigos Neutralizados (Abates):` `{abates}`
  - `Dano Total Infligido:` `{dano_total:,}`
  - `Configuracoes Desbloqueadas:` `{desbloqueadas} / 20`
  - `Multiplicador de Dificuldade:` `x{mult_dif:.2f}`
  - `PONTUACAO FINAL:` `{score_final:,} PTS`
  - `[NOVO RECORDE HISTORICO!]` (se superado)
- **Prompts:** `[ENTER / ESPACO] Jogar Novamente`, `[ESC / M] Retornar ao Menu Principal`, `[C] Menu de Configuracoes`
- **Origem no Código:** `src/cenas/gameplay.py:1194-1262`

### 9.7 Console de Debug (F1 / ~)
- **Título:** `CONSOLE DEBUG (F1 / ~)`
- **Itens:**
  - `1. Spawn Natural` (LIGADO / DESLIGADO)
  - `2. Congelar Timer` (LIGADO / DESLIGADO)
  - `3. Municao Infinita` (LIGADO / DESLIGADO)
  - `4. Modo Deus (HP Inf)` (LIGADO / DESLIGADO)
  - `5. Spawn Drop` (`< XP (+5) >`, `< XP (+50) >`, `< Cura (+35) >`, `< Caixa de Arma >`, `< Caixa Equipamento >`)
  - `6. Equipar Arma` (`< Minigun >`, `< Shotgun >`, `< Rifle Assalto >`, `< Lanca-Foguetes >`, `< Lanca-Granadas >`, `< Railgun >`)
  - `7. Ativar Drone` (`< Drone Cura >`, `< Drone Combate >`, `< Drone Suporte >`)
  - `8. Spawn Inimigo` (`< Padrao (Estagiario) >`, `< Rapido (Cafeina) >`, `< Phasing (Warranty) >`, `< Blindado >`, `< Ranged (Atirador) >`, `< Tanque (Geladeira) >`, `< Chefe de Elite >`)
  - `9. Curar Vida Max` (`[ENTER PARA CURAR]`)
  - `10. Tomar Dano 1/8` (`[ENTER PARA DANO]`)
  - `11. Level Up (+X)` (`< +1 Nivel >`, `< +3 Nivel >`, `< +5 Nivel >`, `< +10 Nivel >`)
  - `12. Destravar Configs` (`[ENTER DESTRAVA 20]`)
- **Status Toasts:** `VIDA RESTAURADA AO MAXIMO!`, `DANO RECEBIDO: -{dano} HP`, `LEVEL UP (+{qtd}) ATIVADO!`, `TODAS AS 20 CONFIGS DESBLOQUEADAS!`, `DROP SPAWNADO: {nome}`, `ARMA EQUIPADA: {nome}`, `DRONE ATIVADO: {nome}`, `INIMIGO SPAWNADO: {nome}`.
- **Hint:** `SETAS: Navegar | ENTER: Acao | CLIQUE: Spawn`
- **Origem no Código:** `src/ui/menu_debug.py:368-435`

---

# 10. Fórmulas Matemáticas e Mecânicas Centrais

1. **Progressão de Nível e Custo de XP:**
   $$XP_{prox}(level) = 20 + 10 \cdot level + 5 \cdot level^2$$
   *Exemplos:* Nv. 1 -> 35 XP, Nv. 2 -> 60 XP, Nv. 3 -> 95 XP, Nv. 4 -> 140 XP.  
   **Origem no Código:** `src/sistemas/sistema_xp.py:39`

2. **Intervalo de Ondas de Spawn:**
   $$T_{spawn}(t) = \max(0.75\text{s}, 3.00\text{s} - 0.012\text{s} \cdot t)$$
   **Origem no Código:** `src/sistemas/sistema_spawn.py:39`

3. **Tamanho do Lote de Inimigos por Pulso:**
   $$N_{batch}(t) = \min\left(8, 1 + \left\lfloor \frac{t}{25} \right\rfloor\right)$$
   **Origem no Código:** `src/sistemas/sistema_spawn.py:46`

4. **Pontuação Final Consolidada:**
   $$Score = \left(Score_{abates} + 10 \cdot t + 0.5 \cdot Dano_{causado} + Score_{vitoria}\right) \times \left(1.0 + 0.10 \cdot N_{configs\_amaldicoadas}\right)$$
   Onde $Score_{vitoria} = 10.000\text{ pts}$ se $t \ge 600.0\text{s}$.  
   **Origem no Código:** `src/cenas/gameplay.py:1117-1134`

5. **Regra de Coleta Inimiga (Scavenger):**
   Apenas 1 inimigo pode ser eleito Scavenger para disputar um drop com tempo no chão $\ge 10.0\text{s}$. A seleção exclui os 3 inimigos mais próximos ao item e qualquer inimigo a mais de $600.0\text{px}$ de distância.  
   **Origem no Código:** `src/sistemas/sistema_scavenger.py:48-80`
