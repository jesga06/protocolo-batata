# Protocolo: Batata — Plano de Implementação (v4 Status Real)

## 📊 Status Atual do Projeto

| Fase | Descrição | Status | Detalhes & Entregas |
|---|---|:---:|---|
| **Fase 0** | Bootstrap & Assets Procedurais | ✅ **CONCLUÍDO** | 64 sprites pixel-art (+30% escala), 19 áudios procedurais WAV, estrutura de pastas e integração com PPlay 2.0. |
| **Fase 1** | Core Loop de Combate | ✅ **CONCLUÍDO** | Movimento WASD com normalização diagonal, mira no mouse, câmera 2D suave com letterbox, ciclo de vida de entidades e destruição. |
| **Fase 1.5** | Polimento de UI & Controles | ✅ **CONCLUÍDO** | Textos perfeitamente centralizados (Pygame nativo), disparo contínuo ao segurar botão, buffer de entrada (150ms), troca de armas (1, 2, 3) e **ataque Melee em cone direcional de 45°** (~84px alcance, 10 dano, 360 px/s knockback). Pistola calibrada para 17 dano (3 hits). |
| **Fase 2** | Drops & Sistema de XP | ✅ **CONCLUÍDO** | Gemas de XP e caixas com 25s de vida útil e escala 42px (tamanho da batata), progressão quadrática desafiadora ($XP = 20 + 10 \cdot lvl + 5 \cdot lvl^2$), barra de XP dinâmica no HUD e **todos os 6 arquétipos de inimigos** com arte e spawner progressivo. |
| **Fase 3** | Motor das 20 Configurações | ✅ **CONCLUÍDO** | Backend matemático (`config_dados.py`, `config_efeitos.py`, `config_sistema.py`) com as 20 configs de gameplay e 5 de sistema, calculando stacking multiplicativo. |
| **Fase 4** | UI de Level Up & Menu de Ajustes | ⏳ **A SEGUIR** | Tela modal de Level Up (3 cards aleatórios), seleção via clique/teclado, desbloqueio em tempo real e Menu de Configurações in-game (engrenagem/ESC). |
| **Fase 5** | Armas Especiais, Drones & Scavenger | ⏳ **PENDENTE** | 5 armas especiais de munição limitada no Slot 3, 3 drones orbitais no Slot 4, mecânica de Coleta Inimiga (Scavenger) e projéteis do Inimigo Ranged. |
| **Fase 6** | Efeitos de Tela, Áudio & Persistência | ⏳ **PENDENTE** | Shaders/efeitos de pós-processamento (Screen Shake, Cores Invertidas, Iluminação Dinâmica/Fog, Motion Blur), loop de música ambiente e salvamento em `data/save.json`. |

---

## ⚙️ Regras do Jogo e SSOT

- **SSOT**: O arquivo [`CONFIGURACOES.md`](file:///c:/Users/jesse/Documents/Computaria/visual%20studio/protocolo-batata/CONFIGURACOES.md) é a Única Fonte da Verdade para as 20 configurações de gameplay e 5 de sistema.
- **Regra de Defaults**: Configurações travadas antes do desbloqueio operam sempre na opção padrão que **não concede bônus/buffs**.
- **Combate Calibrado**:
  - **Inimigo Comum (Estagiário)**: 50 HP (cede 5 XP).
  - **Pistola (Slot 2)**: 17 Dano $\to$ Exatamente 3 disparos para eliminar o inimigo comum.
  - **Chave de Manutenção (Slot 1)**: 10 Dano, Cone de 45°, Alcance ~84px (2 batatas), Knockback 360 px/s $\to$ Exatamente 5 golpes para eliminar.
  - **Inimigos Variados**: Rápido (8 XP), Phasing (12 XP), Blindado (15 XP), Ranged (15 XP), Tanque (25 XP).

---

## 🎯 Detalhamento do que Falta Implementar

### 📌 FASE 4 — Interface de Level Up & Menu de Configurações (Imediata)
1. **Modal de Level Up (`src/cenas/level_up.py` ou overlay em `gameplay.py`)**:
   - Pausa automática do gameplay ao atingir a meta de XP.
   - Sorteio determinístico de 3 configurações ainda bloqueadas na run.
   - Exibição de 3 Cards visuais (`card_upgrade_bg.png`, ícone da config, título, descrição de sacrifício/benefício e flavor text).
   - Seleção interativa via clique do mouse ou teclas `1`, `2` e `3`.
   - Aplicação instantânea dos novos multiplicadores ao retornar ao jogo.
2. **Menu de Configurações In-Game (`src/cenas/menu_configs.py`)**:
   - Acesso a qualquer momento clicando no botão de engrenagem no topo direito ou pressionando `ESC`.
   - Permite ao jogador ligar/desligar as configurações que ele **já desbloqueou**, permitindo ajustar a dificuldade e os bônus durante a partida.
   - Aba de Configurações de Sistema (Volume Master/Música/SFX, Filtro Daltônico S4 e Escala Global S5).

---

### 📌 FASE 5 — Armas Especiais, Drones e Mecânicas Avançadas
1. **Armas Especiais Temporárias (Slot 3)**:
   - **Minigun**: 150 munições, taxa altíssima de disparos com dispersão leve.
   - **Shotgun**: 30 munições, 5 projéteis em leque por disparo.
   - **Rifle de Assalto**: 60 munições, disparos rápidos de precisão perfurante.
   - **Lança-Foguetes**: 12 munições, projétil lento com explosão em área de 80px.
   - **Lança-Granadas**: 16 munições, projétil balístico com detonação após ricochete/tempo.
   - *Comportamento de Munição*: Ao esgotar as balas, a arma é descartada automaticamente e o jogador volta para o Slot 2/1.
2. **Equipamentos de Apoio — Drones Orbitais (Slot 4)**:
   - **Drone de Cura**: Regenera 5 HP do jogador a cada 3.0s.
   - **Drone de Combate**: Dispara lasers no inimigo mais próximo a cada 1.0s.
   - **Drone de Suporte**: Concede +15% de velocidade de movimento e raio de coleta magnética de XP.
   - *Duração*: 30 segundos em órbita do jogador.
   - *Fogo Amigo*: Se a Config 19 (`fogo_amigo`) estiver ativa, drones possuem 1 HP e podem ser destruídos acidentalmente por tiros do jogador.
3. **Mecânica de Coleta Inimiga (Scavenger - Config 15)**:
   - Quando ativada, se um drop ficar no chão por mais de 1.0s, exatamente 1 inimigo elegível (excluindo os 3 mais próximos) desvia sua rota e corre para devorar o drop, impedindo a coleta pelo jogador.

---

### 📌 FASE 6 — Efeitos de Tela, Áudio & Persistência Final
1. **Efeitos Visuais de Configurações**:
   - **Screen Shake (Config 5)**: Tremor de câmera em explosões e dano.
   - **Cores Invertidas (Config 17)**: Pass de inversão RGB em tela cheia via Surface shader.
   - **Iluminação Dinâmica / Fog of War (Config 18)**: Máscara escura circular ao redor da batata; inimigos revelados ao entrar no campo de visão perdem 50% do HP imediatamente.
   - **Motion Blur (Config 8)**: Rastro translúcido dos frames anteriores.
2. **Sistema de Persistência (`src/sistemas/sistema_save.py`)**:
   - Salvar em `data/save.json`: histórico de pontuações, tempo recorde de sobrevivência e catálogo de configurações desbloqueadas globalmente.
3. **Gerenciador de Áudio**:
   - Loop contínuo da trilha sonora 8-bit `musica_fase.wav`.
   - Ajuste em tempo real de canais de áudio baseado nas configs de volume.

---

## 🔍 Checklist de Detalhes Críticos Identificados

- [x] **SSOT Respeitada**: Dano da pistola em 17 (3 hits) e melee em 10 (5 hits).
- [x] **Geometria de Cone**: Melee utiliza cone direcional estrito de 45° no ângulo do mouse.
- [x] **Curva de XP**: Progressão quadrática desafiadora implementada ($XP = 20 + 10\cdot lvl + 5\cdot lvl^2$).
- [x] **Variedade Visual de Inimigos**: 6 sprites e 6 classes instanciadas progressivamente pelo spawner.
- [ ] **Descarte de Arma Esgotada**: Garantir que o Slot 3 limpa a arma ao atingir 0 munições e retorna o slot ativo para o Slot 2 (Pistola).
- [ ] **Regra do Fogo Amigo com Drones**: Drones duram 30s normalmente, mas morrem com 1 hit de projétil se `fogo_amigo` estiver ligado.
- [ ] **Config 18 (Holofote de Dano)**: Marcar a flag `ja_revelado = True` no inimigo ao entrar no cone de luz para que ele não sofra a perda de 50% de HP repetidamente no mesmo frame.
- [ ] **Fallback de Level Up Nível 20**: Caso o jogador atinja o nível máximo (20) ou desbloqueie todas as configs, o card deve oferecer Cura Completa (+100 HP) ou Aumento de HP Máximo (+20 HP).

---

## 🧪 Verificação Automatizada
- Testes unitários contínuos: `python -m unittest discover -s tests` (**146 testes atualmente passando**).
- Zero testes mockados / hardcoded — validações matemáticas de produto escalar e simulação física real.
