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
| **45 FPS** | Fluidez reduzida a 45 FPS | Dano recebido de inimigos reduzido em **15%** ($\times 0.85$) | **Modo Performance**<br>*"Os inimigos também estão perdendo frames."* |
| **30 FPS** | Fluidez reduzida a 30 FPS | Velocidade de movimento dos inimigos reduzida em **10%** ($\times 0.90$) | **Modo Slow Motion**<br>*"Só é lag se você estiver perdendo."* |
| **15 FPS** | Experiência quase injogável | Dano de inimigos reduzido em **27.75%** ($\times 0.7225$) e velocidade reduzida em **19%** ($\times 0.81$) | **Experiência Cinematográfica**<br>*"Cada frame foi desenhado à mão por monges tibetanos."* |

---

### 2. Qualidade Gráfica (`graficos_qualidade`)
- **Categoria**: Performance
- **Tipo**: Alternador (Toggle)
- **Padrão**: Alta (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Alta** | Nenhum | Nenhum | *"Sprites nítidos para quem aprecia os pequenos detalhes."* |
| **Baixa** | Todos os sprites viram retângulos e formas geométricas coloridas. Partículas simplificadas. | Vida máxima (HP) de todos os inimigos reduzida em **20%** | **Cortes no Orçamento**<br>*"Texturas são um luxo que o departamento financeiro cortou."* |

---

### 3. Resolução da Tela (`resolucao`)
- **Categoria**: Performance
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: Nativa (100% da resolução máxima do monitor)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Nativa (100%)** | Nenhum | Nenhum | *"Cada pixel em seu devido lugar."* |
| **75%** | Visão levemente borrada e pixelada | Chance de drop de itens aumentada em **+10%** | **Anti-Aliasing Reverso**<br>*"Menos pixels na tela, mais caixas no chão."* |
| **50%** | Visão consideravelmente pixelada | Chance de drop de itens aumentada em **+25%** | **Nostalgia Forçada**<br>*"Lembranças de uma época de monitores CRT."* |
| **25%** | Praticamente indecifrável | Chance de drop de itens aumentada em **+50%** | **Arqueologia de Pixels**<br>*"Se você consegue contar os pixels nos dedos, está economizando processamento."* |

---

### 4. Sincronização Vertical (`vsync`)
- **Categoria**: Performance
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum | Nenhum | *"Estabilidade garantida para monitores sensíveis."* |
| **Desligado** | Possível quebra de linha visual (*screen tearing*) | Velocidade de movimento da batata aumentada em **+10%** | **Morte por Mil Cortes**<br>*"Espero que seu monitor tenha FreeSync."* |

---

### 5. Tremor de Tela (`screen_shake`)
- **Categoria**: Performance / Visual
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Uma experiência suave."* |
| **Ligado** | A tela treme violentamente a cada disparo pesado, explosão e dano | Dano das armas explosivas (Lança-Foguetes e Lança-Granadas) aumentado em **+20%** | **Protocolo: Terremoto**<br>*"A tela treme. A sua mira também."* |

---

### 6. Desfoque de Movimento (`motion_blur`)
- **Categoria**: Performance / Visual
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Uma experiência suave."* |
| **Ligado** | Rastro visual (*ghosting*) borra todos os elementos em movimento rápido | Velocidade de movimento da batata aumentada em **+15%** | **Fantasmagórico**<br>*"Você se move tão rápido que até seus pixels ficaram para trás."* |

---

### 7. Exibição de Interface (`hud`)
- **Categoria**: Interface
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum | Nenhum | *"Barras de vida, experiência, inventário e cronômetro visíveis."* |
| **Desligado** | Oculta completamente HP, XP, inventário, munição e timer (resta apenas o ícone de pausar/configurar) | Ganho de experiência (XP) por inimigo derrotado aumentado em **+25%** | **"Trust Me Bro"**<br>*"Com certeza você ainda tem vida sobrando. Provavelmente."* |

---

### 8. Números de Dano (`damage_numbers`)
- **Categoria**: Interface
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum (acertos críticos são desabilitados) | *"Inimigos sofrem dano em silêncio."* |
| **Ligado** | Poluição visual com centenas de números flutuando sobre hordas de inimigos | **Habilita o sistema de Críticos**: **15%** de chance em cada projétil de causar **2× de dano** | **Aula de Matemática**<br>*"Finalmente uma aplicação prática para aritmética básica."* |

---

### 9. Nível de Zoom (`zoom`)
- **Categoria**: Interface
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: 100% (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **75% (Zoom Out)** | Câmera mais distante, sprites menores e mais difíceis de discernir | Tamanho da caixa de colisão (*hitbox*) de todos os projéteis aumentado em **+50%** | **Visão de Satélite**<br>*"Aquilo é uma batata ou uma formiga armada?"* |
| **100%** | Nenhum | Nenhum | *"Campo de visão padrão e equilibrado."* |
| **125% (Zoom In)** | Campo de visão periférico reduzido | Dano de todas as armas aumentado em **+10%** | **Lupa**<br>*"Foco total no que está na sua cara."* |
| **150% (Zoom In)** | Visão extremamente restrita do mapa | Dano de todas as armas aumentado em **+20%** | **Modo Microscópio**<br>*"Você consegue ver de perto os inimigos."* |

---

### 10. Movimento pelo Mouse (`movimento_mouse`)
- **Categoria**: Controles
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (controle padrão via teclado) | Nenhum | *"Controle manual com pés firmes nas teclas."* |
| **Ligado** | A batata caminha incessantemente na direção do cursor do mouse. Teclas de movimento desabilitadas. A batata nunca para a menos que o mouse esteja em cima dela. | Chance de drop multiplicativa aumentada em **+40%** | **Piloto Automático**<br>*"Para que servem as pernas quando o destino tem um cursor?"* |

---

### 11. Modificadores de Teclas (`keybinds`)
- **Categoria**: Controles
- **Tipo**: Grupo Mutuamente Exclusivo (Presets)
- **Padrão**: Padrão (WASD + Mouse, sem buff)

| Preset | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Padrão** | Nenhum | Nenhum | *"Ergonomia convencional para seres humanos normais."* |
| **Invertido** | Teclas de movimento invertidas (W: baixo, S: cima, A: direita, D: esquerda) | Dano de todas as armas aumentado em **+10%** | **Horizontes Invertidos**<br>*"Para cima é o novo para baixo."* |
| **Arrow Keys** | Movimento transferido para as Setas direcionais | Velocidade de movimento da batata aumentada em **+15%** | **Nostalgia**<br>*"Lembranças dolorosas de jogar no teclado de 1998."* |
| **Uma Mão Só** | Movimentação em `QWER`, ações apenas no teclado. Mouse não tem uso além de trocar configurações | Ganho de XP aumentado em **+20%** | **Uma Mão Só**<br>*"Uma mão no volante, a outra no carinho."* |
| **Pesadelo** | Movimento em `IJKL` com eixo Y do mouse invertido | Dano de todas as armas aumentado em **+30%** | **Anarquia das Teclas**<br>*"Sua memória muscular acabou de pedir demissão."* |

---

### 12. Suavização de Câmera (`suavizacao_camera`)
- **Categoria**: Controles / Câmera
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum (câmera com interpolação suave) | Nenhum | *"Transições suaves para evitar tontura."* |
| **Desligado** | A câmera trava rigidamente no centro do jogador sem suavização | Velocidade de movimento da batata aumentada em **+8%** | **Raw Footage**<br>*"Estabilização de imagem é cobrada à parte."* |

---

### 13. Disparo Automático (`auto_fire`)
- **Categoria**: Controles / Combate
- **Tipo**: Alternador (Toggle)
- **Padrão**: Ligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Ligado** | Nenhum (armas automáticas disparam continuamente ao segurar o botão) | Nenhum | *"Segure o botão e reze."* |
| **Desligado** | É necessário **clicar manualmente a cada disparo** para todas as armas (inclusive Minigun e Rifle) | Dano de todas as armas aumentado em **+15%** | **Trigger Discipline**<br>*"Cada projétil disparado é uma decisão de vida ou morte."* |

---

### 14. Inimigos à Distância (`inimigos_ranged`)
- **Categoria**: Dificuldade
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (todos os inimigos causam dano apenas por contato corpo a corpo) | Nenhum | *"Inimigos civilizados."* |
| **Ligado** | Inimigos com disparos à distância (*Ranged*) passam a spawnar no mapa | Inimigos Ranged possuem tabela de loot enriquecida (**alta chance de caixas de armas e equipamentos**) | **Evolução Tecnológica**<br>*"Eles finalmente descobriram a tecnologia dos projéteis balísticos."* |

---

### 15. Captura de Drops por Inimigos (`coleta_inimiga`)
- **Categoria**: Dificuldade
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (inimigos ignoram completamente todas as caixas e itens no chão) | Nenhum | *"Raposo, não pegue."* |
| **Ligado** | **Ativa a Coleta Inimiga (Scavenger)**: Após 1s de vida de um drop (tempo total de 10s no chão), 1 inimigo na tela tenta ativamente devorar o drop antes de você (selecionado pseudo-aleatoriamente, excluindo inimigos muito distantes e os 2–3 mais próximos). | **Todos os drops coletados pelo jogador valem 2×** (XP em dobro, cura em dobro, munição dobrada e dobro de duração/usos de equipamentos) | **Modo Raciocínio**<br>*"Os inimigos se sentiram inspirados pelo Gemini 3.7 Flash."* |

---

### 16. Velocidade dos Inimigos (`velocidade_inimigos`)
- **Categoria**: Dificuldade
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: Normal (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Normal** | Nenhum | Nenhum | *"Inimigos marcham normalmente."* |
| **+25% Velocidade** | Todos os inimigos se movem 25% mais rápido | Ganho de XP por abate aumentado em **+20%** | **Overclock**<br>*"Eles encontraram o botão turbo."* |
| **+50% Velocidade** | Todos os inimigos correm em disparada | Ganho de XP por abate aumentado em **+40%** | **Surto**<br>*"Injetaram energético na corrente de dados."* |

---

### 17. Vida dos Inimigos (`vida_inimigos`)
- **Categoria**: Dificuldade
- **Tipo**: Grupo Mutuamente Exclusivo
- **Padrão**: Normal (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Normal** | Nenhum | Nenhum | *"Inimigos com vida padrão."* |
| **+50% HP** | Inimigos possuem 50% a mais de vida | Chance de drop de itens aumentada em **+20%** | **Blindados**<br>*"Blindagem adicional direto da fábrica."* |
| **+100% HP** | Inimigos possuem o dobro de vida | Chance de drop de itens aumentada em **+40%** | **Pesados**<br>*"Eles estão mais densos."* |

---

### 18. Iluminação Dinâmica (`iluminacao`)
- **Categoria**: Experimental / Atmosfera
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum (mapa totalmente iluminado e visível) | Nenhum | *"Luz do dia perpétua sobre o campo de batalha."* |
| **Ligado** | Névoa de escuridão (*fog of war*): campo de visão restrito ao redor da batata | Inimigos fora do cone de visão **causam 50% a menos de dano** | **Modo Escuridão**<br>*"Eles estão com dificuldade de te enxergar."* |

---

### 19. Cores Invertidas (`cores_invertidas`)
- **Categoria**: Experimental / Visual
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Paleta de cores original e aconchegante."* |
| **Ligado** | Inversão total de RGB da tela (estética de negativo fotográfico) | Dano global de todas as armas aumentado em **+20%** | **Espaço Negativo**<br>*"Seus olhos registraram uma reclamação no Procon."* |

---

### 20. Fogo Amigo (`fogo_amigo`)
- **Categoria**: Experimental / Risco Extremo
- **Tipo**: Alternador (Toggle)
- **Padrão**: Desligado (sem buff)

| Valor | Sacrifício (Nerf) | Benefício (Buff) | Flavor Text |
|---|---|---|---|
| **Desligado** | Nenhum | Nenhum | *"Seus tiros e explosões atravessam você inofensivamente."* |
| **Ligado** | Seus próprios projéteis e explosões causam dano à batata. Drones/equipamentos têm 1 HP e são destruídos instantaneamente por fogo amigo. | Dano global de todas as armas aumentado em **+25%** | **Collateral Damage**<br>*"Aparentemente, estilhaços de granada não leem crachá de identificação."* |

---

# ⚙️ Configurações de Sistema (Sempre Disponíveis — Sem Efeito de Gameplay)

Estas opções existem puramente para acessibilidade e usabilidade do jogador e **não fazem parte da progressão permanente**:

| Configuração | Identificador | Tipo | Valores | Descrição |
|---|---|---|---|---|
| **Volume Geral** | `volume_master` | Slider | 0% a 100% (Padrão: 100%) | Controla o volume geral de toda a aplicação. |
| **Volume da Música** | `volume_musica` | Slider | 0% a 100% (Padrão: 100%) | Controla a trilha sonora 8-bit em loop. |
| **Volume dos Efeitos** | `volume_sfx` | Slider | 0% a 100% (Padrão: 100%) | Controla tiros, explosões, pickups e menus. |
