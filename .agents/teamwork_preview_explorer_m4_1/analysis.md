# Protocolo: Batata — Relatório de Mineração de Especificação: Sistema de Configurações

**Documento**: Análise Completa de Especificação (Spec Miner)  
**Autor**: Explorer 1 (Spec Miner)  
**Data**: 2026-08-28  
**Autoridade Primária (SSOT)**: `CONFIGURACOES.md`  
**Autoridades Complementares**: `PLANO_DE_IMPLEMENTACAO.md`, `GDD.md`, `.agents/architecture_cache.md`, `src/utils/constantes.py`  

---

## 1. Sumário Executivo & Premissa Central

Em **Protocolo: Batata**, o menu de configurações não é apenas uma ferramenta utilitária de opções, mas sim o **mecanismo central de progressão permanente** do jogo.

A premissa central é o sacrifício intencional de conforto audiovisual, ergonomia de controles e facilidade mecânica em troca de bônus diretos de poder (*buffs*).

### Regra Fundamental de Desbloqueio e Baseline
1. **Estado Bloqueado (Locked State)**: Antes de ser desbloqueada pelo jogador (via Level Up), qualquer configuração de gameplay é **estritamente travada em seu valor padrão (Baseline)**. O valor padrão **nunca concede qualquer buff** (multiplicador neutro $\times 1.0$, $0\%$ de bônus, comportamento padrão do jogo).
2. **Desbloqueio Permanente (Level Up)**: Ao subir de nível em uma run, o jogador escolhe 1 configuração entre até 3 opções bloqueadas restantes. A configuração escolhida é desbloqueada de forma permanente (persistida em `data/save.json`).
3. **Seleção Pós-Desbloqueio**: Uma vez desbloqueada, o jogador pode alternar livremente entre qualquer uma de suas opções no Menu Principal ou Menu de Pausa.
4. **Nível Máximo do Jogador**: Exatamente **20**, correspondendo ao total de 20 configurações de gameplay desbloqueáveis. Quando todas as 20 estão desbloqueadas, o sistema bloqueia novos level ups.

---

## 2. Tabela Mestra: As 20 Configurações de Gameplay Desbloqueáveis

| # | ID / Chave | Nome | Categoria | Tipo | Valor Padrão (Baseline) | Valores Selecionáveis | Resumo de Buffs / Nerfs |
|---|---|---|---|---|---|---|---|
| **1** | `fps_cap` | Limite de Quadros | Performance | Grupo Mutuamente Exclusivo | `60` (60 FPS) | `60`, `45`, `30`, `15` | **45**: Dano inimigos $\times 0.85$<br>**30**: Vel inimigos $\times 0.90$<br>**15**: Dano $\times 0.7225$, Vel $\times 0.81$ |
| **2** | `graficos_qualidade` | Qualidade Gráfica | Performance | Alternador (Toggle) | `alta` (Alta) | `alta`, `baixa` | **baixa**: Sprites viram retângulos coloridos; HP dos inimigos $-20\%$ ($\times 0.80$) |
| **3** | `resolucao` | Resolução da Tela | Performance | Grupo Mutuamente Exclusivo | `100%` (Nativa) | `100%`, `75%`, `50%`, `25%` | **75%**: Chance drop $+10\%$<br>**50%**: Chance drop $+25\%$<br>**25%**: Chance drop $+50\%$ |
| **4** | `vsync` | Sincronização Vertical | Performance | Alternador (Toggle) | `ligado` (Ligado) | `ligado`, `desligado` | **desligado**: Risco de screen tearing; Velocidade da batata $+10\%$ ($\times 1.10$) |
| **5** | `screen_shake` | Tremor de Tela | Performance / Visual | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Tela treme fortemente; Dano explosivo (foguetes/granadas) $+20\%$ ($\times 1.20$) |
| **6** | `motion_blur` | Desfoque de Movimento | Performance / Visual | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Ghosting visual intenso; Velocidade da batata $+15\%$ ($\times 1.15$) |
| **7** | `hud` | Exibição de Interface | Interface | Alternador (Toggle) | `ligado` (Ligado) | `ligado`, `desligado` | **desligado**: Oculta HP, XP, inventário, timer; Ganho de XP $+25\%$ ($\times 1.25$) |
| **8** | `damage_numbers` | Números de Dano | Interface | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Poluição visual de números; Habilita Críticos ($15\%$ chance de causar $2\times$ dano) |
| **9** | `zoom` | Nível de Zoom | Interface | Grupo Mutuamente Exclusivo | `100%` (100%) | `75%`, `100%`, `125%`, `150%` | **75%**: Hitbox projéteis $+50\%$<br>**125%**: Dano armas $+10\%$<br>**150%**: Dano armas $+20\%$ |
| **10** | `movimento_mouse` | Movimento pelo Mouse | Controles | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Batata segue cursor sem parar, teclado off; Chance de drop $\times 1.40$ ($+40\%$ mult) |
| **11** | `keybinds` | Modificadores de Teclas | Controles | Grupo Mutuamente Exclusivo (Presets) | `padrao` (WASD + Mouse) | `padrao`, `invertido`, `arrow_keys`, `uma_mao`, `pesadelo` | **invertido**: Dano $+10\%$<br>**arrow_keys**: Vel $+15\%$<br>**uma_mao**: XP $+20\%$<br>**pesadelo**: Dano $+30\%$ |
| **12** | `suavizacao_camera` | Suavização de Câmera | Controles / Câmera | Alternador (Toggle) | `ligado` (Ligado) | `ligado`, `desligado` | **desligado**: Câmera rígida sem interpolação; Velocidade da batata $+8\%$ ($\times 1.08$) |
| **13** | `auto_fire` | Disparo Automático | Controles / Combate | Alternador (Toggle) | `ligado` (Ligado) | `ligado`, `desligado` | **desligado**: Clique manual obrigatório por tiro; Dano de todas as armas $+15\%$ ($\times 1.15$) |
| **14** | `inimigos_ranged` | Inimigos à Distância | Dificuldade | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Spawna inimigos que atiram projéteis; Loot enriquecido (altas chances de caixas de armas/drones) |
| **15** | `coleta_inimiga` | Captura de Drops | Dificuldade | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Ativa Scavenger Enemy (1s delay, 1 alvo global); Todos os drops coletados valem $2\times$ |
| **16** | `velocidade_inimigos` | Velocidade dos Inimigos | Dificuldade | Grupo Mutuamente Exclusivo | `normal` (Normal) | `normal`, `+25%`, `+50%` | **+25%**: Inimigos $+25\%$ vel, XP $+20\%$<br>**+50%**: Inimigos $+50\%$ vel, XP $+40\%$ |
| **17** | `vida_inimigos` | Vida dos Inimigos | Dificuldade | Grupo Mutuamente Exclusivo | `normal` (Normal) | `normal`, `+50%`, `+100%` | **+50%**: Inimigos $+50\%$ HP, Drop $+20\%$<br>**+100%**: Inimigos $+100\%$ HP, Drop $+40\%$ |
| **18** | `iluminacao` | Iluminação Dinâmica | Experimental / Atmosfera | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Névoa de escuridão (*fog of war*); Inimigos fora do cone de visão causam $-50\%$ dano ($\times 0.50$) |
| **19** | `cores_invertidas` | Cores Invertidas | Experimental / Visual | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Inversão total RGB (negativo fotográfico); Dano global de todas as armas $+20\%$ ($\times 1.20$) |
| **20** | `fogo_amigo` | Fogo Amigo | Experimental / Risco Extremo | Alternador (Toggle Invertido) | `desligado` (Desligado) | `desligado`, `ligado` | **ligado**: Tiros/explosões ferem batata, Drones têm 1 HP; Dano global de todas as armas $+25\%$ ($\times 1.25$) |

---

## 3. Catálogo Detalhado Item por Item (#1 ao #20)

### 1. Limite de Quadros (`fps_cap`)
- **Categoria**: Performance
- **Tipo**: Grupo Mutuamente Exclusivo (4 opções)
- **Valor Padrão (Locked Baseline)**: `"60"`
- **Opções Registradas**:
  1. `"60"`:
     - Nerf: Nenhum. Jogo roda a 60 FPS estáveis.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"O olho humano não consegue ver além de 30 FPS."*
  2. `"45"`:
     - Nerf: Fluidez visual reduzida para 45 FPS.
     - Buff: Dano recebido de inimigos reduzido em 15% ($\times 0.85$).
     - Modificadores: `{"dano_inimigos_mult": 0.85}`
     - Título / Flavor Text: **Modo Performance** — *"Os inimigos também estão perdendo frames."*
  3. `"30"`:
     - Nerf: Fluidez visual reduzida para 30 FPS.
     - Buff: Velocidade de movimento dos inimigos reduzida em 10% ($\times 0.90$).
     - Modificadores: `{"vel_inimigos_mult": 0.90}`
     - Título / Flavor Text: **Modo Slow Motion** — *"Só é lag se você estiver perdendo."*
  4. `"15"`:
     - Nerf: Experiência quase injogável a 15 FPS.
     - Buff: Dano de inimigos reduzido em 27.75% ($\times 0.7225 = 0.85^2$) **E** velocidade de movimento dos inimigos reduzida em 19% ($\times 0.81 = 0.90^2$).
     - Modificadores: `{"dano_inimigos_mult": 0.7225, "vel_inimigos_mult": 0.81}`
     - Título / Flavor Text: **Experiência Cinematográfica** — *"Cada frame foi desenhado à mão por monges tibetanos."*

---

### 2. Qualidade Gráfica (`graficos_qualidade`)
- **Categoria**: Performance
- **Tipo**: Alternador (Toggle)
- **Valor Padrão (Locked Baseline)**: `"alta"`
- **Opções Registradas**:
  1. `"alta"`:
     - Nerf: Nenhum. Sprites nítidos e detalhados.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Sprites nítidos para quem aprecia os pequenos detalhes."*
  2. `"baixa"`:
     - Nerf: Todos os sprites de personagens, inimigos e armas são substituídos por retângulos e formas geométricas simples com cores sólidas. Partículas são simplificadas.
     - Buff: Vida máxima (HP) de todos os inimigos reduzida em 20% ($\times 0.80$).
     - Modificadores: `{"hp_inimigos_mult": 0.80}`
     - Título / Flavor Text: **Cortes no Orçamento** — *"Texturas são um luxo que o departamento financeiro cortou."*

---

### 3. Resolução da Tela (`resolucao`)
- **Categoria**: Performance
- **Tipo**: Grupo Mutuamente Exclusivo (4 opções)
- **Valor Padrão (Locked Baseline)**: `"100%"`
- **Opções Registradas**:
  1. `"100%"` (Nativa):
     - Nerf: Nenhum. Renderização em resolução nativa da janela.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Cada pixel em seu devido lugar."*
  2. `"75%"`:
     - Nerf: Visão levemente borrada e pixelada (downscale).
     - Buff: Chance de drop de itens aumentada em +10% ($+0.10$ bônus aditivo à chance base).
     - Modificadores: `{"drop_chance_bonus": 0.10}`
     - Título / Flavor Text: **Anti-Aliasing Reverso** — *"Menos pixels na tela, mais caixas no chão."*
  3. `"50%"`:
     - Nerf: Visão consideravelmente pixelada.
     - Buff: Chance de drop de itens aumentada em +25% ($+0.25$ bônus aditivo à chance base).
     - Modificadores: `{"drop_chance_bonus": 0.25}`
     - Título / Flavor Text: **Nostalgia Forçada** — *"Lembranças de uma época de monitores CRT."*
  4. `"25%"`:
     - Nerf: Resolução extrema baixa (praticamente indecifrável).
     - Buff: Chance de drop de itens aumentada em +50% ($+0.50$ bônus aditivo à chance base).
     - Modificadores: `{"drop_chance_bonus": 0.50}`
     - Título / Flavor Text: **Arqueologia de Pixels** — *"Se você consegue contar os pixels nos dedos, está economizando processamento."*

---

### 4. Sincronização Vertical (`vsync`)
- **Categoria**: Performance
- **Tipo**: Alternador (Toggle)
- **Valor Padrão (Locked Baseline)**: `"ligado"`
- **Opções Registradas**:
  1. `"ligado"`:
     - Nerf: Nenhum.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Estabilidade garantida para monitores sensíveis."*
  2. `"desligado"`:
     - Nerf: Possível quebra de linha visual (*screen tearing* simulado ou real).
     - Buff: Velocidade de movimento da batata aumentada em +10% ($\times 1.10$).
     - Modificadores: `{"vel_jogador_mult": 1.10}`
     - Título / Flavor Text: **Morte por Mil Cortes** — *"Espero que seu monitor tenha FreeSync."*

---

### 5. Tremor de Tela (`screen_shake`)
- **Categoria**: Performance / Visual
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum. Câmera estável sem tremores.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Uma experiência suave."*
  2. `"ligado"`:
     - Nerf: A tela treme violentamente a cada disparo pesado, explosão ou dano sofrido.
     - Buff: Dano de armas explosivas (Lança-Foguetes e Lança-Granadas) aumentado em +20% ($\times 1.20$).
     - Modificadores: `{"dano_explosivos_mult": 1.20}`
     - Título / Flavor Text: **Protocolo: Terremoto** — *"A tela treme. A sua mira também."*

---

### 6. Desfoque de Movimento (`motion_blur`)
- **Categoria**: Performance / Visual
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Uma experiência suave."*
  2. `"ligado"`:
     - Nerf: Rastro visual (*ghosting*) borra todos os elementos e sprites em movimento rápido.
     - Buff: Velocidade de movimento da batata aumentada em +15% ($\times 1.15$).
     - Modificadores: `{"vel_jogador_mult": 1.15}`
     - Título / Flavor Text: **Fantasmagórico** — *"Você se move tão rápido que até seus pixels ficaram para trás."*

---

### 7. Exibição de Interface (`hud`)
- **Categoria**: Interface
- **Tipo**: Alternador (Toggle)
- **Valor Padrão (Locked Baseline)**: `"ligado"`
- **Opções Registradas**:
  1. `"ligado"`:
     - Nerf: Nenhum. Todas as barras de HP, XP, inventário, munição e cronômetro visíveis.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Barras de vida, experiência, inventário e cronômetro visíveis."*
  2. `"desligado"`:
     - Nerf: Oculta completamente HP, XP, inventário, munição e timer (visível apenas o botão/ícone de configurações/pausa).
     - Buff: Ganho de experiência (XP) por inimigo derrotado aumentado em +25% ($\times 1.25$).
     - Modificadores: `{"xp_ganho_mult": 1.25}`
     - Título / Flavor Text: **"Trust Me Bro"** — *"Com certeza você ainda tem vida sobrando. Provavelmente."*

---

### 8. Números de Dano (`damage_numbers`)
- **Categoria**: Interface
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum (acertos críticos são desabilitados).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Inimigos sofrem dano em silêncio."*
  2. `"ligado"`:
     - Nerf: Poluição visual intensa com centenas de números flutuando na tela.
     - Buff: **Habilita o Sistema de Críticos**: 15% de chance em cada projétil de causar $2.0\times$ de dano.
     - Modificadores: `{"critico_chance": 0.15, "critico_mult": 2.0}`
     - Título / Flavor Text: **Aula de Matemática** — *"Finalmente uma aplicação prática para aritmética básica."*

---

### 9. Nível de Zoom (`zoom`)
- **Categoria**: Interface
- **Tipo**: Grupo Mutuamente Exclusivo (4 opções)
- **Valor Padrão (Locked Baseline)**: `"100%"`
- **Opções Registradas**:
  1. `"75%"` (Zoom Out):
     - Nerf: Câmera mais distante, sprites menores e mais difíceis de discernir.
     - Buff: Tamanho da caixa de colisão (*hitbox*) de todos os projéteis aumentado em +50% ($\times 1.50$).
     - Modificadores: `{"hitbox_projeteis_mult": 1.50}`
     - Título / Flavor Text: **Visão de Satélite** — *"Aquilo é uma batata ou uma formiga armada?"*
  2. `"100%"` (Padrão):
     - Nerf: Nenhum. Campo de visão padrão e equilibrado.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Campo de visão padrão e equilibrado."*
  3. `"125%"` (Zoom In):
     - Nerf: Campo de visão periférico reduzido.
     - Buff: Dano de todas as armas aumentado em +10% ($\times 1.10$).
     - Modificadores: `{"dano_armas_mult": 1.10}`
     - Título / Flavor Text: **Lupa** — *"Foco total no que está na sua cara."*
  4. `"150%"` (Zoom In Extremo):
     - Nerf: Visão extremamente restrita da arena.
     - Buff: Dano de todas as armas aumentado em +20% ($\times 1.20$).
     - Modificadores: `{"dano_armas_mult": 1.20}`
     - Título / Flavor Text: **Modo Microscópio** — *"Você consegue ver de perto os inimigos."*

---

### 10. Movimento pelo Mouse (`movimento_mouse`)
- **Categoria**: Controles
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum (movimento convencional via teclado).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Controle manual com pés firmes nas teclas."*
  2. `"ligado"`:
     - Nerf: A batata move-se incessantemente em direção ao cursor do mouse. Teclas de movimento desabilitadas. A batata nunca para, exceto quando o cursor estiver exatamente sobre ela.
     - Buff: Chance de drop de itens aumentada multiplicativamente em +40% ($\times 1.40$).
     - Modificadores: `{"drop_chance_mult": 1.40}`
     - Título / Flavor Text: **Piloto Automático** — *"Para que servem as pernas quando o destino tem um cursor?"*

---

### 11. Modificadores de Teclas (`keybinds`)
- **Categoria**: Controles
- **Tipo**: Grupo Mutuamente Exclusivo (5 Presets)
- **Valor Padrão (Locked Baseline)**: `"padrao"`
- **Opções Registradas**:
  1. `"padrao"`:
     - Nerf: Nenhum (WASD para mover + Mouse para mirar/atirar).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Ergonomia convencional para seres humanos normais."*
  2. `"invertido"`:
     - Nerf: Teclas de movimento invertidas (W = Baixo, S = Cima, A = Direita, D = Esquerda).
     - Buff: Dano de todas as armas aumentado em +10% ($\times 1.10$).
     - Modificadores: `{"dano_armas_mult": 1.10}`
     - Título / Flavor Text: **Horizontes Invertidos** — *"Para cima é o novo para baixo."*
  3. `"arrow_keys"`:
     - Nerf: Movimentação transferida para as Setas do teclado.
     - Buff: Velocidade de movimento da batata aumentada em +15% ($\times 1.15$).
     - Modificadores: `{"vel_jogador_mult": 1.15}`
     - Título / Flavor Text: **Nostalgia** — *"Lembranças dolorosas de jogar no teclado de 1998."*
  4. `"uma_mao"`:
     - Nerf: Movimentação em `QWER`, todas as ações no teclado. Mouse serve apenas para menus.
     - Buff: Ganho de XP aumentado em +20% ($\times 1.20$).
     - Modificadores: `{"xp_ganho_mult": 1.20}`
     - Título / Flavor Text: **Uma Mão Só** — *"Uma mão no volante, a outra no carinho."*
  5. `"pesadelo"`:
     - Nerf: Movimentação em `IJKL` com o eixo Y do mouse invertido.
     - Buff: Dano de todas as armas aumentado em +30% ($\times 1.30$).
     - Modificadores: `{"dano_armas_mult": 1.30}`
     - Título / Flavor Text: **Anarquia das Teclas** — *"Sua memória muscular acabou de pedir demissão."*

---

### 12. Suavização de Câmera (`suavizacao_camera`)
- **Categoria**: Controles / Câmera
- **Tipo**: Alternador (Toggle)
- **Valor Padrão (Locked Baseline)**: `"ligado"`
- **Opções Registradas**:
  1. `"ligado"`:
     - Nerf: Nenhum (câmera com interpolação e atraso suave).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Transições suaves para evitar tontura."*
  2. `"desligado"`:
     - Nerf: A câmera trava rigidamente no centro do jogador sem qualquer suavização (snap seco).
     - Buff: Velocidade de movimento da batata aumentada em +8% ($\times 1.08$).
     - Modificadores: `{"vel_jogador_mult": 1.08}`
     - Título / Flavor Text: **Raw Footage** — *"Estabilização de imagem é cobrada à parte."*

---

### 13. Disparo Automático (`auto_fire`)
- **Categoria**: Controles / Combate
- **Tipo**: Alternador (Toggle)
- **Valor Padrão (Locked Baseline)**: `"ligado"`
- **Opções Registradas**:
  1. `"ligado"`:
     - Nerf: Nenhum (armas automáticas disparam continuamente ao segurar o botão).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Segure o botão e reze."*
  2. `"desligado"`:
     - Nerf: É obrigatório clicar manualmente para cada tiro disparado em todas as armas (inclusive Minigun e Rifle).
     - Buff: Dano de todas as armas aumentado em +15% ($\times 1.15$).
     - Modificadores: `{"dano_armas_mult": 1.15}`
     - Título / Flavor Text: **Trigger Discipline** — *"Cada projétil disparado é uma decisão de vida ou morte."*

---

### 14. Inimigos à Distância (`inimigos_ranged`)
- **Categoria**: Dificuldade
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum (inimigos atacam exclusivamente corpo a corpo por contato).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Inimigos civilizados."*
  2. `"ligado"`:
     - Nerf: O arquétipo de inimigo `InimigoRanged` passa a spawnar na arena, atirando projéteis balísticos em direção à batata.
     - Buff: Inimigos à distância utilizam tabela de loot enriquecida (alta probabilidade de dropar caixas de armas especiais e equipamentos).
     - Modificadores: `{"loot_enriquecido": True}`
     - Título / Flavor Text: **Evolução Tecnológica** — *"Eles finalmente descobriram a tecnologia dos projéteis balísticos."*

---

### 15. Captura de Drops por Inimigos (`coleta_inimiga`)
- **Categoria**: Dificuldade
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum (inimigos ignoram completamente todos os drops no chão).
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Raposo, não pegue."*
  2. `"ligado"`:
     - Nerf: **Ativa o Sistema Scavenger**: Drops no chão possuem tempo de vida de 10s. Após 1.0s de existência, 1 inimigo global na arena é designado pseudo-aleatoriamente (excluindo os 2–3 mais próximos e inimigos fora do alcance máximo) para desviar e devorar o drop.
     - Buff: **Todos os drops coletados pelo jogador valem o dobro ($2\times$)**: XP dobrada, cura dobrada, munição de armas dobrada e dobro de usos/duração de equipamentos.
     - Modificadores: `{"drops_valor_mult": 2.0}`
     - Título / Flavor Text: **Modo Raciocínio** — *"Os inimigos se sentiram inspirados pelo Gemini 3.7 Flash."*

---

### 16. Velocidade dos Inimigos (`velocidade_inimigos`)
- **Categoria**: Dificuldade
- **Tipo**: Grupo Mutuamente Exclusivo (3 opções)
- **Valor Padrão (Locked Baseline)**: `"normal"`
- **Opções Registradas**:
  1. `"normal"`:
     - Nerf: Nenhum.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Inimigos marcham normalmente."*
  2. `"+25%"`:
     - Nerf: Todos os inimigos se movem 25% mais rápido ($\times 1.25$).
     - Buff: Ganho de XP por abate aumentado em +20% ($\times 1.20$).
     - Modificadores: `{"vel_inimigos_mult": 1.25, "xp_ganho_mult": 1.20}`
     - Título / Flavor Text: **Overclock** — *"Eles encontraram o botão turbo."*
  3. `"+50%"`:
     - Nerf: Todos os inimigos correm em disparada (+50% velocidade, $\times 1.50$).
     - Buff: Ganho de XP por abate aumentado em +40% ($\times 1.40$).
     - Modificadores: `{"vel_inimigos_mult": 1.50, "xp_ganho_mult": 1.40}`
     - Título / Flavor Text: **Surto** — *"Injetaram energético na corrente de dados."*

---

### 17. Vida dos Inimigos (`vida_inimigos`)
- **Categoria**: Dificuldade
- **Tipo**: Grupo Mutuamente Exclusivo (3 opções)
- **Valor Padrão (Locked Baseline)**: `"normal"`
- **Opções Registradas**:
  1. `"normal"`:
     - Nerf: Nenhum. Inimigos possuem HP baseline.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Inimigos com vida padrão."*
  2. `"+50%"`:
     - Nerf: Inimigos nascem com 50% a mais de HP ($\times 1.50$).
     - Buff: Chance de drop de itens aumentada em +20% ($+0.20$ bônus aditivo à chance base).
     - Modificadores: `{"hp_inimigos_mult": 1.50, "drop_chance_bonus": 0.20}`
     - Título / Flavor Text: **Blindados** — *"Blindagem adicional direto da fábrica."*
  3. `"+100%"`:
     - Nerf: Inimigos possuem o dobro de HP ($\times 2.00$).
     - Buff: Chance de drop de itens aumentada em +40% ($+0.40$ bônus aditivo à chance base).
     - Modificadores: `{"hp_inimigos_mult": 2.00, "drop_chance_bonus": 0.40}`
     - Título / Flavor Text: **Pesados** — *"Eles estão mais densos."*

---

### 18. Iluminação Dinâmica (`iluminacao`)
- **Categoria**: Experimental / Atmosfera
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum. Campo de visão 100% aberto e iluminado.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Luz do dia perpétua sobre o campo de batalha."*
  2. `"ligado"`:
     - Nerf: Névoa de escuridão (*fog of war*): campo de visão estritamente restrito ao redor da batata.
     - Buff: Inimigos fora do cone/círculo de visão do jogador causam **50% a menos de dano** ($\times 0.50$).
     - Modificadores: `{"dano_fora_visao_mult": 0.50}`
     - Título / Flavor Text: **Modo Escuridão** — *"Eles estão com dificuldade de te enxergar."*

---

### 19. Cores Invertidas (`cores_invertidas`)
- **Categoria**: Experimental / Visual
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum. Paleta de cores normal.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Paleta de cores original e aconchegante."*
  2. `"ligado"`:
     - Nerf: Inversão total de RGB da tela inteira (estética de negativo fotográfico).
     - Buff: Dano global de todas as armas aumentado em +20% ($\times 1.20$).
     - Modificadores: `{"dano_armas_mult": 1.20}`
     - Título / Flavor Text: **Espaço Negativo** — *"Seus olhos registraram uma reclamação no Procon."*

---

### 20. Fogo Amigo (`fogo_amigo`)
- **Categoria**: Experimental / Risco Extremo
- **Tipo**: Alternador (Toggle Invertido — Ativar é o sacrifício)
- **Valor Padrão (Locked Baseline)**: `"desligado"`
- **Opções Registradas**:
  1. `"desligado"`:
     - Nerf: Nenhum. Projéteis e explosões não atingem a batata ou drones.
     - Buff: Nenhum.
     - Modificadores: `{}`
     - Flavor Text: *"Seus tiros e explosões atravessam você inofensivamente."*
  2. `"ligado"`:
     - Nerf: Projéteis e explosões do jogador causam dano ao próprio jogador. Drones e equipamentos ativos possuem 1 HP e são destruídos instantaneamente caso atingidos por fogo amigo.
     - Buff: Dano global de todas as armas aumentado em +25% ($\times 1.25$).
     - Modificadores: `{"dano_armas_mult": 1.25, "auto_dano": True, "drone_1hp": True}`
     - Título / Flavor Text: **Collateral Damage** — *"Aparentemente, estilhaços de granada não leem crachá de identificação."*

---

## 4. Configurações de Sistema (Sempre Disponíveis, Sem Efeito de Gameplay)

Estas configurações não entram na progressão de Level Up e estão sempre desbloqueadas para acessibilidade do usuário:

| ID | Nome | Tipo | Escala / Valores | Padrão | Descrição |
|---|---|---|---|---|---|
| `volume_master` | Volume Geral | Slider | 0 a 100 (%) | 100 | Controla o volume geral do mixer de áudio da aplicação. |
| `volume_musica` | Volume da Música | Slider | 0 a 100 (%) | 100 | Controla o ganho da faixa musical em loop. |
| `volume_sfx` | Volume dos Efeitos | Slider | 0 a 100 (%) | 100 | Controla o ganho de tiros, explosões, pickups e cliques de UI. |
| `filtro_daltonico` | Filtro Daltônico | Seletor | `desligado`, `protanopia`, `deuteranopia`, `tritanopia` | `desligado` | Filtro de pós-processamento para acessibilidade de visão em cores. |

---

## 5. Modelo Matemático de Stacking e Aplicação de Modificadores

Todas as configurações calculam modificadores com base no catálogo SSOT. A seguir estão as fórmulas canônicas:

### 5.1 Dano do Jogador (Armas Gerais e Especiais)
- Multiplicadores Ativos:
  - `auto_fire == 'desligado'`: $\times 1.15$
  - `keybinds == 'invertido'`: $\times 1.10$
  - `keybinds == 'pesadelo'`: $\times 1.30$
  - `cores_invertidas == 'ligado'`: $\times 1.20$
  - `fogo_amigo == 'ligado'`: $\times 1.25$
  - `zoom == '125%'`: $\times 1.10$
  - `zoom == '150%'`: $\times 1.20$
- Multiplicador Exclusivo para Armas Explosivas (Lança-Foguetes e Lança-Granadas):
  - `screen_shake == 'ligado'`: $\times 1.20$
- **Fórmula de Dano**:
  $$\text{DanoArma} = \text{DanoBaseArma} \times \prod M_{\text{dano\_armas}} \times (M_{\text{explosivo}} \text{ se arma for explosiva})$$
- **Exemplo Máximo de Stacking**:
  Se o jogador ativar Pesadelo ($1.30$), Inverted Colors ($1.20$), Friendly Fire ($1.25$), Auto-Fire Off ($1.15$) e Zoom 150% ($1.20$):
  $$\text{MultTotal} = 1.30 \times 1.20 \times 1.25 \times 1.15 \times 1.20 = 2.691 \times \text{ Dano Base}$$

### 5.2 Velocidade do Jogador (Batata)
- Multiplicadores:
  - `vsync == 'desligado'`: $\times 1.10$
  - `motion_blur == 'ligado'`: $\times 1.15$
  - `suavizacao_camera == 'desligado'`: $\times 1.08$
  - `keybinds == 'arrow_keys'`: $\times 1.15$
- **Fórmula de Velocidade**:
  $$\text{VelJogador} = \text{VelBase} \times \prod M_{\text{vel\_jogador}}$$
- **Exemplo de Stacking Completo**:
  $$\text{MultVelMax} = 1.10 \times 1.15 \times 1.08 \times 1.15 \approx 1.571 \times \text{ Vel Base}$$

### 5.3 Ganho de Experiência (XP por Inimigo)
- Multiplicadores:
  - `hud == 'desligado'`: $\times 1.25$
  - `keybinds == 'uma_mao'`: $\times 1.20$
  - `velocidade_inimigos == '+25%'`: $\times 1.20$
  - `velocidade_inimigos == '+50%'`: $\times 1.40$
- **Fórmula de XP**:
  $$\text{XPGanho} = \text{XPBaseInimigo} \times \prod M_{\text{xp}}$$

### 5.4 Chance de Drop de Itens
- Bônus Aditivos de Base:
  - `resolucao`: $+0.10$ (75%), $+0.25$ (50%), $+0.50$ (25%)
  - `vida_inimigos`: $+0.20$ (+50%), $+0.40$ (+100%)
- Modificador Multiplicativo:
  - `movimento_mouse == 'ligado'`: $\times 1.40$
- **Fórmula de Chance de Drop**:
  $$\text{ChanceDropEfetiva} = \min\left(1.0, \left(\text{ChanceBase} + \sum \text{BonusAditivos}\right) \times M_{\text{mouse}}\right)$$

### 5.5 Vida Máxima dos Inimigos (Spawn)
- Modificadores:
  - `graficos_qualidade == 'baixa'`: $\times 0.80$
  - `vida_inimigos == '+50%'`: $\times 1.50$
  - `vida_inimigos == '+100%'`: $\times 2.00$
- **Fórmula**:
  $$\text{HPMaxInimigo} = \text{HPBase} \times M_{\text{graficos}} \times M_{\text{vida\_inimigos}}$$

### 5.6 Velocidade dos Inimigos
- Modificadores:
  - `fps_cap == '30'`: $\times 0.90$
  - `fps_cap == '15'`: $\times 0.81$
  - `velocidade_inimigos == '+25%'`: $\times 1.25$
  - `velocidade_inimigos == '+50%'`: $\times 1.50$
- **Fórmula**:
  $$\text{VelInimigo} = \text{VelBase} \times M_{\text{fps\_vel}} \times M_{\text{vel\_inimigos}}$$

### 5.7 Dano dos Inimigos Sofrido pelo Jogador
- Modificadores:
  - `fps_cap == '45'`: $\times 0.85$
  - `fps_cap == '15'`: $\times 0.7225$
  - `iluminacao == 'ligado'` (quando inimigo está fora do raio de luz): $\times 0.50$
- **Fórmula**:
  $$\text{DanoSofrido} = \text{DanoBaseInimigo} \times M_{\text{fps\_dano}} \times (0.50 \text{ se fora da visão})$$

### 5.8 Sistema de Críticos
- Habilitado exclusivamente quando `damage_numbers == 'ligado'`:
  - `critico_chance = 0.15` (15%)
  - `critico_mult = 2.0` ($2\times$ dano ao acertar crítico)
  - Quando `damage_numbers == 'desligado'`: `critico_chance = 0.0` (sem críticos).

---

## 6. Mecânica de Desbloqueio e Persistência

### 6.1 Estrutura do Estado (State Representation)
O sistema opera com duas estruturas de dados essenciais:
1. `unlocked_configs: set[str]` — IDs das configurações desbloqueadas pelo jogador.
2. `active_configs: dict[str, str]` — Mapeamento do ID para o valor atualmente ativo.

### 6.2 Regras de Transição de Estado
1. **Inicialização / New Game**:
   - `unlocked_configs = []` (Vazio).
   - Para qualquer `cfg_id`: se `cfg_id not in unlocked_configs`, `get_active_value(cfg_id)` **retorna obrigatoriamente seu valor padrão (baseline)**, independentemente do que constar no dicionário ativo.
2. **Level Up Pool**:
   - `locked_pool = [cfg for cfg in ALL_CONFIGS if cfg.id not in unlocked_configs]`
   - Se `len(locked_pool) > 0`: seleciona até 3 aleatoriamente e apresenta na tela de Level Up.
   - Ao clicar no card, `unlocked_configs.add(chosen_id)` é persistido.
3. **Limite de Nível**:
   - O jogador atinge o nível máximo quando `len(unlocked_configs) == 20`. A partir deste momento, nenhum level up é disparado.

---

## 7. Casos de Borda e Verificações Especiais

| # | Configuração | Caso de Borda / Condição Limite | Comportamento Esperado |
|---|---|---|---|
| 1 | `damage_numbers` | Configuração desligada vs projétil com flag de crit | Crítico nunca deve disparar se `damage_numbers` estiver desligado (`crit_chance = 0.0`). |
| 2 | `coleta_inimiga` | Menos de 3 inimigos na tela ao spawnar drop | O seletor de scavenger não deve quebrar caso a lista de candidatos filtrados fique vazia. Simplesmente nenhum inimigo é alocado até que um candidato válido surja. |
| 3 | `fogo_amigo` | Jogador atira com shotgun de perto contra parede ou inimigo | Projéteis do jogador que colidirem com o hitbox do jogador devem infligir dano e consumir o projétil. Drones ativos morrem com 1 hit. |
| 4 | `movimento_mouse` | Mouse posicionado exatamente no centro do jogador ($dist \approx 0$) | Velocidade de movimento deve ser zerada para evitar jitter de rotação ou movimento espasmódico. |
| 5 | `fps_cap` | Stacking de FPS cap a 15 com outros multiplicadores de dano/velocidade | Multiplicador de $0.7225$ para dano e $0.81$ para velocidade são aplicados cumulativamente com `velocidade_inimigos`. |
| 6 | `hud` | Jogador sobe de nível ou morre com HUD desligado | O menu de pause, menu de level up e game over continuam funcionando normalmente. Apenas a barra in-game e inventário ficam ocultos. |

---

## 8. Conclusão & Próximos Passos
O catálogo de 20 configurações de gameplay de `CONFIGURACOES.md` está 100% mapeado com todas as opções, baselines, fórmulas matemáticas de stacking e flavor texts.
Os agentes de implementação backend (`config_sistema.py`, `config_dados.py`, `config_efeitos.py`) podem instanciar diretamente as constantes e o registry a partir desta especificação canônica.
