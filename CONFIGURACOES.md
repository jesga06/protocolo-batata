# Protocolo: Batata — Catálogo de Configurações do Jogo (SSOT)

> **SSOT (Single Source of Truth)**: Este documento é a **Única Fonte da Verdade** para todas as configurações de jogo, modificadores mecânicos, balanceamento numérico, sacrifícios, benefícios e textos de sabor (*flavor text*) do projeto Protocolo: Batata. Qualquer implementação no código deve seguir estritamente o que está declarado neste arquivo.

---

## Regra Fundamental de Desbloqueio
- **Antes de desbloquear**: A configuração fica travada em seu **valor padrão**, que nunca concede bônus.
- **Ao desbloquear (Level Up)**: O jogador pode alternar livremente entre os valores disponíveis antes ou durante as runs.

---

# 🎮 Configurações de Gameplay (20 Desbloqueáveis)

---

### 1. Limite de Quadros (`fps_cap`)
- **Categoria**: Performance
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: 60 FPS (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **60 FPS** | Nenhum | Nenhum | *"O olho humano não consegue ver além de 30 FPS."* |
| **45 FPS** | Fluidez reduzida a 45 FPS | Dano recebido de inimigos reduzido em **15%** ($\times 0.85$) e micro-congelamentos de esquiva (`fps_stutter_dodge`: congela inimigos por 0.15s e concede **+0.35s** de i-frames aditivos) | **Economia de Energia**<br>*"Menos quadros, menos calor. Dá tempo de respirar."* |
| **30 FPS** | Fluidez reduzida a 30 FPS | Velocidade de movimento dos inimigos reduzida em **10%** ($\times 0.90$) e micro-congelamentos de esquiva (`fps_stutter_dodge`: **+0.35s** de i-frames aditivos) | **Modo Econômico**<br>*"O monitor sofre, mas os inimigos sofrem mais."* |
| **15 FPS** | Experiência quase injogável | Dano de inimigos reduzido em **27.75%** ($\times 0.7225$), velocidade reduzida em **19%** ($\times 0.81$) e micro-congelamentos de esquiva (`fps_stutter_dodge`: **+0.35s** de i-frames aditivos) | **Modo Slideshow**<br>*"Quase uma apresentação de PowerPoint, mas funcional."* |

---

### 2. Qualidade Gráfica (`graficos_qualidade`)
- **Categoria**: Performance
- **Tipo**: Alternador (Toggle)
- **Padrão**: Alta (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Alta** | Nenhum | Nenhum | *"Texturas nítidas e detalhes visuais completos."* |
| **Baixa** | Todos os sprites viram retângulos e formas geométricas coloridas. Partículas simplificadas. | HP dos inimigos **-20%** e cada inimigo abatido **solta 4 estilhaços low-poly perfurantes** | **Gráficos Integrados**<br>*"Sem placa de vídeo dedicada. A carcaça dos inimigos quebra em pedaços."* |

---

### 3. Resolução da Tela (`resolucao`)
- **Categoria**: Performance
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: Nativa (100% da resolução máxima do monitor)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Nativa (100%)** | Nenhum | Nenhum | *"Cada pixel em seu devido lugar."* |
| **75%** | Visão levemente borrada e pixelada | Chance de drop de itens aumentada em **+10%** e área de impacto dos tiros aumentada em **+25%** (hitbox $\times 1.25$) | **Upscaling Básico**<br>*"Resolução menor, renderização mais folgada."* |
| **50%** | Visão consideravelmente pixelada | Chance de drop de itens aumentada em **+25%** e área de impacto dos tiros aumentada em **+50%** (hitbox $\times 1.50$) | **Modo Retro**<br>*"Pixels grandes facilitam achar sucata no chão."* |
| **25%** | Praticamente indecifrável | Chance de drop de itens aumentada em **+50%** e área de impacto dos tiros dobrada (**+100%** / hitbox $\times 2.0$) | **320x240 CRT**<br>*"Na dúvida do que está na tela, qualquer tiro acerta."* |

---

### 4. Sincronização Vertical (`vsync`)
- **Categoria**: Performance
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum | Nenhum | *"Estabilidade garantida sem quebra de quadros."* |
| **Desligado** | Linha de tearing varre a tela | **+10% de velocidade** e projéteis que cruzam o corte de tela **são duplicados** | **Linha de Rasgo**<br>*"Monitor sem sincronia. O corte na imagem divide seus tiros em dois."* |

---

### 5. Tremor de Tela (`screen_shake`)
- **Categoria**: Performance / Visual
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Uma experiência suave."* |
| **Ligado** | A tela treme violentamente a cada disparo pesado, explosão e dano | **+20% de dano explosivo** e impactos de **tiros balísticos, melee e bombas** causam **tropeço (empurrão) e lentidão (50% slow)** nos inimigos atingidos (`screen_shake_stagger`) | **Pico de Vibração**<br>*"Cooler desbalanceado faz o gabinete inteiro tremer."* |

---

### 6. Desfoque de Movimento (`motion_blur`)
- **Categoria**: Performance / Visual
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Uma experiência suave."* |
| **Ligado** | Rastro visual (*ghosting*) borra todos os elementos em movimento rápido | Velocidade de movimento da batata aumentada em **+15%** e o rastro fantasmagórico concede **+0.40s de invulnerabilidade aditiva** sobre os 0.20s base após dano ou dash (`motion_blur_ghosting`) | **Tempo de Resposta Alto**<br>*"Painel VA antigo. O rastro borrado ajuda a cortar caminho."* |

---

### 7. Exibição de Interface (`hud`)
- **Categoria**: Interface
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum | Nenhum | *"Barras de vida, experiência, inventário e cronômetro visíveis."* |
| **Desligado** | Oculta completamente HP, XP, inventário, munição e timer (resta apenas o ícone de pausar/configurar) | **+25% de XP** e **pulso magnético a cada 4s** puxa todos os drops da tela | **Monitor Secundário Queimado**<br>*"Sem HUD. O sensor puxa as sucatas da tela automaticamente."* |

---

### 8. Números de Dano (`damage_numbers`)
- **Categoria**: Interface
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum (acertos críticos são desabilitados) | *"Inimigos sofrem dano em silêncio."* |
| **Ligado** | Poluição visual com centenas de números flutuando sobre hordas de inimigos | **Habilita o sistema de Críticos**: **25% de chance de causar 2× de dano** e impacto empurra inimigos | **Log Verboso**<br>*"Cada número impresso no console tem peso físico e empurra o alvo."* |

---

### 9. Nível de Zoom (`zoom`)
- **Categoria**: Interface
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: 100% (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **75% (Zoom Out)** | Câmera mais distante (**FOV real ampliado para $1067 \times 800$** escalado em tela cheia), sprites menores e mais difíceis de discernir | Tamanho da caixa de colisão (*hitbox*) de todos os projéteis aumentado em **+50%** (com mira do mouse realinhada via transformada inversa) | **Visão Panorâmica**<br>*"Visão ampla do mapa com hitboxes maiores."* |
| **100%** | Nenhum | Nenhum | *"Campo de visão padrão e equilibrado."* |
| **125% (Zoom In)** | Campo de visão periférico reduzido | Dano de todas as armas aumentado em **+10%** | **Foco Fechado**<br>*"Mira fechada para concentrar os tiros."* |
| **150% (Zoom In)** | Visão extremamente restrita do mapa | Dano de todas as armas aumentado em **+20%** | **Zoom Máximo**<br>*"Quase em cima do alvo, garantindo dano concentrado."* |

---

### 10. Movimento pelo Mouse (`movimento_mouse`)
- **Categoria**: Controles
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (controle padrão via teclado) | Nenhum | *"Controle manual com pés firmes nas teclas."* |
| **Ligado** | A batata caminha incessantemente na direção do cursor do mouse. Teclas de movimento desabilitadas. | **+40% de chance de drop** e colisões atropelam inimigos comuns causando dano de impacto | **Cursor Guia**<br>*"Movimentação direta pelo cursor. Atropela inimigos no caminho."* |

---

### 11. Modificadores de Teclas (`keybinds`)
- **Categoria**: Controles
- **Tipo**: Grupo Mutuamente Exclusivo (Presets)
- **Padrão**: Padrão (WASD + Mouse, sem buff)

| Preset | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Padrão** | Nenhum | Nenhum | *"Ergonomia convencional para seres humanos normais."* |
| **Invertido** | Teclas de movimento invertidas (W: baixo, S: cima, A: direita, D: esquerda) | Dano de todas as armas aumentado em **+10%** | **Layout Invertido**<br>*"Teclas de movimento trocadas."* |
| **Arrow Keys** | Movimento transferido para as Setas direcionais | Velocidade de movimento da batata aumentada em **+15%** | **Teclado Compacto**<br>*"Movimento transferido para as setas."* |
| **Uma Mão Só** | Movimentação em `QWER`, **mira e tiro 100% no teclado** (dispara na direção atual do movimento `(dx, dy)` ou **para cima `(0, -1)`** quando parado; tiro via `ESPAÇO`/`F`/`ENTER` ou automático com `auto_fire`, tiro secundário via `SHIFT`/`V`/`TAB`; mouse usado apenas em menus/`[C]`) | Ganho de XP aumentado em **+20%** e reversão brusca de direção dispara **Overdrive Dash** com pulso de choque (`keybinds_overdrive_dash`) | **Uma Mão no Teclado**<br>*"Todos os comandos concentrados em uma mão só."* |
| **Pesadelo** | Movimento em `IJKL` com eixo Y do mouse invertido | Dano de todas as armas aumentado em **+30%** | **Mapeamento Caótico**<br>*"Esquema de controle totalmente fora do padrão."* |

---

### 12. Suavização de Câmera (`suavizacao_camera`)
- **Categoria**: Controles / Câmera
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum (câmera com interpolação suave) | Nenhum | *"Transições suaves para evitar tontura."* |
| **Desligado** | A câmera trava rigidamente no centro do jogador sem suavização | Velocidade de movimento da batata aumentada em **+8%** | **Trava Rígida**<br>*"Câmera fixa direto no centro sem interpolação."* |

---

### 13. Disparo Automático (`auto_fire`)
- **Categoria**: Controles / Combate
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum (armas automáticas disparam continuamente ao segurar o botão) | Nenhum | *"Segure o botão e atire sem parar."* |
| **Desligado** | É necessário **clicar manualmente a cada disparo** | **+15% de dano** e cada clique manual dispara uma **segunda salva instantânea** | **Gatilho Manual**<br>*"Cada clique manual dispara um tiro duplo concentrado."* |

---

### 14. Inimigos à Distância (`inimigos_ranged`)
- **Categoria**: Dificuldade
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (todos os inimigos causam dano apenas por contato corpo a corpo) | Nenhum | *"Inimigos comuns sem ataque de longo alcance."* |
| **Ligado** | Inimigos com disparos à distância (*Ranged*) passam a spawnar no mapa | Inimigos Ranged possuem tabela de loot enriquecida (**alta chance de caixas de armas e equipamentos**) | **Inimigos com Disparo**<br>*"Adiciona inimigos que atiram de longe com melhores drops."* |

---

### 15. Captura de Drops por Inimigos (`coleta_inimiga`)
- **Categoria**: Dificuldade
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (inimigos ignoram completamente todas as caixas e itens no chão) | Nenhum | *"Inimigos ignoram os itens dropados."* |
| **Ligado** | Inimigos tentam roubar drops após 10s de chão (Scavenger) | **Todos os drops coletados pelo jogador valem 2×** (XP, cura, munição e duração de drones) | **Coleta Competitiva**<br>*"Inimigos disputam os drops com você. Coletas valem o dobro."* |

---

### 16. Velocidade dos Inimigos (`velocidade_inimigos`)
- **Categoria**: Dificuldade
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: Normal (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Normal** | Nenhum | Nenhum | *"Inimigos marcham na velocidade normal."* |
| **+25% Velocidade** | Todos os inimigos se movem 25% mais rápido | Ganho de XP por abate aumentado em **+20%** | **Inimigos Acelerados**<br>*"Inimigos mais rápidos, maior ganho de experiência."* |
| **+50% Velocidade** | Todos os inimigos correm em disparada | Ganho de XP por abate aumentado em **+40%** | **Velocidade Máxima**<br>*"Inimigos em corrida constante com bônus alto de XP."* |

---

### 17. Vida dos Inimigos (`vida_inimigos`)
- **Categoria**: Dificuldade
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: Normal (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Normal** | Nenhum | Nenhum | *"Inimigos com vida padrão."* |
| **+50% HP** | Inimigos possuem 50% a mais de vida | Chance de drop de itens aumentada em **+20%** | **Inimigos Reforçados**<br>*"Inimigos com mais vida deixam mais itens ao morrer."* |
| **+100% HP** | Inimigos possuem o dobro de vida | Chance de drop de itens aumentada em **+40%** | **Inimigos Blindados**<br>*"Inimigos com vida dobrada e taxa de drop máxima."* |

---

### 18. Iluminação Dinâmica (`iluminacao`)
- **Categoria**: Experimental / Atmosfera
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (mapa totalmente iluminado e visível) | Nenhum | *"Arena totalmente visível sem escuridão."* |
| **Ligado** | Névoa de escuridão (*fog of war*): campo de visão restrito ao redor da batata | Inimigos fora do cone de visão **causam 50% a menos de dano** | **Lanterna de Bancada**<br>*"Visão restrita ao redor. Inimigos no escuro causam metade do dano."* |

---

### 19. Cores Invertidas (`cores_invertidas`)
- **Categoria**: Experimental / Visual
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Paleta de cores padrão."* |
| **Ligado** | Inversão total de RGB da tela | Dano global de todas as armas aumentado em **+20%** | **Cores Invertidas**<br>*"Inverte todas as cores da tela e concede aumento de dano."* |

---

### 20. Fogo Amigo (`fogo_amigo`)
- **Categoria**: Experimental / Risco Extremo
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Seus tiros e explosões atravessam você inofensivamente."* |
| **Ligado** | Seus próprios projéteis e explosões causam dano à batata e destroem drones | **+25% de dano global** e explosões aplicam **impulso de rocket-jump** | **Curto-Circuito**<br>*"Tiros e explosões acertam você, mas geram impulso de salto."* |

---

# ⚙️ Configurações de Sistema (Sempre Disponíveis — Sem Efeito de Gameplay)

Estas opções existem puramente para acessibilidade e usabilidade do jogador e **não fazem parte da progressão permanente**:

| Configuração | Identificador | Tipo | Valores | Descrição |
|---|---|---|---|---|
| **Volume Geral** | `volume_master` | Slider | 0% a 100% (Padrão: 100%) | Controla o volume geral de toda a aplicação. |
| **Volume da Música** | `volume_musica` | Slider | 0% a 100% (Padrão: 100%) | Controla a trilha sonora 8-bit em loop. |
| **Volume dos Efeitos** | `volume_sfx` | Slider | 0% a 100% (Padrão: 100%) | Controla tiros, explosões, pickups e menus. |
