# Relatório de Investigação Técnica — Explorer 3 (Persistência de Metaprogressão e Sistema de Partículas / Screen Shake)

> **Módulo**: Protocolo: Batata — Fase 6 (Persistência, Metaprogressão, Feedback Visual & Screen Shake)  
> **Data / Timestamp**: 2026-08-29T05:36:15Z  
> **Status**: Hard Handoff — Investigação Concluída com Propostas Arquiteturais Completas  

---

## 1. Observation (Observações Verificadas e Mapeamento de Código)

### 1.1 Persistência e Estrutura Atual de `data/save.json`
- **[Observed] Arquivo `data/save.json`**: Atualmente armazena apenas as chaves `"desbloqueadas"` (lista), `"ativas"` (dicionário de configs de gameplay) e `"sistema_configs"` (volumes, filtro daltonico, escala global). Não possui campos para `high_score`, `melhor_tempo`, `total_abates` ou `historico`.
- **[Observed] `src/sistemas/config_sistema.py:100-154`**:
  - `to_dict()` serializa estritamente:
    ```python
    {
        "desbloqueadas": sorted(list(self.desbloqueadas)),
        "ativas": {k: v for k, v in self.ativas.items()},
        "sistema_configs": {k: v for k, v in self.sistema_configs.items()}
    }
    ```
  - `from_dict(dados)` restaura apenas `desbloqueadas`, `ativas` e `sistema_configs`.
  - **[Verified] Risco Crítico de Sobrescrita**: Qualquer chamada a `salvar_arquivo()` vinda de `menu_configs.py:157` ou `modal_level_up.py:534` sobrescreve `data/save.json` com `self.to_dict()`. Se `estatisticas` forem salvas fora desse pipeline ou se `to_dict()` não as incluir, qualquer fechamento do menu de configurações ou seleção de level-up apagará os recordes e histórico do jogador.
- **[Observed] `src/cenas/menu_principal.py:89-138`**: O método `draw()` desenha o título (`top=110`), as 4 opções de navegação (`inicio_y=260`) e o rodapé (`bottom=ALTURA_TELA-25`), sem nenhuma exibição de Recorde de Pontuação ou Melhor Tempo de Sobrevivência.
- **[Observed] `src/cenas/gameplay.py:910-942`**: Ao morrer (`game_over == True`), `_desenhar_overlay_game_over()` exibe tempo, abates e pontuação final, porém não persiste o resultado em `data/save.json` nem verifica se houve quebra de recorde anterior.

### 1.2 Feedback Visual de Combate e Partículas
- **[Observed] `src/cenas/gameplay.py:85-86, 90`**:
  - `self.shake_intensidade = 0.0` e `self.shake_timer = 0.0` foram declarados na inicialização, mas não são lidos nem atualizados em nenhum outro ponto de `gameplay.py`.
  - Atualmente apenas `self.efeitos_melee` (`gameplay.py:90, 316-324, 336-340, 631-659`) é utilizado para desenhar arcos de 45° do golpe melee.
- **[Observed] `src/entidades/projetil.py:81-152`**:
  - Projéteis explosivos (`Lança-Foguetes` e `Lança-Granadas`) executam `explodir(...)`, calculam dano radial AoE e reproduzem SFX (`sfx_explosao`), mas não geram nenhuma onda de choque visual nem partículas de explosão.
- **[Observed] `src/cenas/gameplay.py:442-476`**:
  - Colisões de projéteis com inimigos aplicam dano e desativam o projétil, sem gerar faíscas balísticas de impacto.
- **[Observed] `src/cenas/gameplay.py:497-539`**:
  - Coleta de drops gera toasts flutuantes de texto (`+5 XP`, `+35 HP`), mas não emite partículas visuais cintilantes (bursts de ouro/verde).
- **[Observed] `src/utils/constantes.py:293-309` & `CONFIGURACOES.md:69-78`**:
  - Configuração 5 (`screen_shake`): Tipo alternador (toggle), Padrão `desligado`.
  - Quando `ligado`: Concede `dano_explosivos_mult: 1.20` (+20% de dano explosivo).
  - Comportamento visual exigido: tremor de tela dinâmico ativado apenas quando a opção estiver `ligado`.

### 1.3 Suíte de Testes e Infraestrutura
- **[Verified] Execução da Suíte de Testes**:
  - Comando executado: `.venv\Scripts\python.exe -m unittest discover -s tests`
  - Resultado: `Ran 139 tests in 0.832s - OK` (100% de aprovação em todos os módulos).
  - Padrão do projeto: Inicialização de Pygame em modo headless com `SDL_VIDEODRIVER="dummy"` e `SDL_AUDIODRIVER="dummy"`.

---

## 2. Logic Chain (Cadeia de Raciocínio Lógico)

1. **Unificação da Persistência em `GerenciadorConfiguracoes`**:
   - *Premissa*: `GerenciadorConfiguracoes` é o repositório central de dados do `data/save.json`, instanciado no Menu Principal, Gameplay, Modal de Level Up e Menu de Configs.
   - *Dedução*: Expandir `GerenciadorConfiguracoes` para gerenciar a chave `"estatisticas"` garante que:
     a) `from_dict()` carregue recordes (`high_score`, `melhor_tempo`, `total_abates`, `partidas_jogadas`, `historico`).
     b) `to_dict()` serialize as estatísticas junto com configurações ativas e desbloqueadas.
     c) Nenhuma operação de salvar configurações em runtime apagará os recordes.
     d) O método `registrar_partida(tempo, abates, pontos, vitoria)` seja uma chamada atômica simples e reutilizável em qualquer encerramento de partida (Game Over ou Vitória).

2. **Exibição Elegante no Menu Principal (`menu_principal.py`)**:
   - *Premissa*: O Menu Principal possui espaço vertical disponível entre o título (`y=110-150`) e as opções (`y=260-410`).
   - *Dedução*: Adicionar um card/banner centralizado (`top=175` a `220`) exibindo `RECORDE: {high_score:,} PTS | MELHOR TEMPO: {min:02d}:{sec:02d}` com cores temáticas `DOURADO` e `AZUL_CIANO` atende perfeitamente ao requisito R3 sem poluir a interface.

3. **Arquitetura Desacoplada e de Alta Performance para Partículas (`sistema_particulas.py`)**:
   - *Premissa*: Protocolo: Batata suporta até 400 inimigos simultâneos na arena. A criação e destruição excessiva de `pygame.Surface` per-frame causaria pausas de coleta de lixo (GC spikes) e queda de FPS.
   - *Dedução*: O `SistemaParticulas` deve operar com:
     a) Listas enxutas de partículas com tempo de vida curto (0.10s a 0.40s).
     b) Teto global máximo de partículas (ex: `MAX_PARTICULAS = 250`).
     c) Desenho direto na tela principal ou usando superfícies reutilizáveis de choque.
     d) Suporte à configuração `graficos_qualidade`: em modo `"baixa"`, reduz a contagem de partículas em 50% e usa formas geométricas simples, garantindo compatibilidade total com o SSOT.

4. **Integração do Screen Shake com a Câmera e Config 5**:
   - *Premissa*: A classe `Camera` do PowerPPlay 2.0 calcula `transform_x` e `transform_y` a partir de `self.x` e `self.y`.
   - *Dedução*:
     a) `GameplayScene.aplicar_screen_shake(intensidade, duracao)` só ativa o temporizador se `gerenciador_config.obter_valor("screen_shake") == "ligado"`.
     b) Durante o método `draw()`, um deslocamento pseudo-aleatório `(offset_x, offset_y)` decrescente é aplicado ao rendering do mundo, sem alterar a posição física permanente da câmera.
     c) Isso garante que em `"desligado"` a tela permaneça 100% estática e em `"ligado"` reaja a tiros explosivos, dano recebido e chefes.

---

## 3. Caveats (Ressalvas e Suposições)

1. **[Observed] Trilha Sonora Headless**: Em ambientes de teste de CI / headless, o mixer de áudio opera em modo dummy. Todas as chamadas a SFX/música devem continuar envolvidas em blocos `try/except Exception: pass`.
2. **[Inferred] Compatibilidade de Saves Antigos**: Caso o usuário execute o jogo com um arquivo `data/save.json` legado que não contenha a chave `"estatisticas"`, o carregador deve inicializar valores padrões (`high_score: 0`, `melhor_tempo: 0.0`, `historico: []`) de forma transparente e resiliente.
3. **[Inferred] Câmera Clamping & Screen Shake**: O tremor de tela deve ser aplicado exclusivamente como offset na renderização ou na visualização, para não causar desvios cumulativos que empurrem a câmera além dos limites da arena (`0` a `1600x1200`).

---

## 4. Conclusion (Proposta de Implementação e Especificações Técnicas)

### 4.1 Extensão do Esquema de Dados em `data/save.json`
```json
{
  "desbloqueadas": [],
  "ativas": {
    "fps_cap": "60",
    "graficos_qualidade": "alta",
    "resolucao": "100%",
    "vsync": "ligado",
    "screen_shake": "desligado",
    "motion_blur": "desligado",
    "hud": "ligado",
    "damage_numbers": "desligado",
    "zoom": "100%",
    "movimento_mouse": "desligado",
    "keybinds": "padrao",
    "suavizacao_camera": "ligado",
    "auto_fire": "ligado",
    "inimigos_ranged": "desligado",
    "coleta_inimiga": "desligado",
    "velocidade_inimigos": "normal",
    "vida_inimigos": "normal",
    "iluminacao": "desligado",
    "cores_invertidas": "desligado",
    "fogo_amigo": "desligado"
  },
  "sistema_configs": {
    "volume_master": 100,
    "volume_musica": 100,
    "volume_sfx": 100,
    "filtro_daltonico": "desligado",
    "escala_global": "100%"
  },
  "estatisticas": {
    "high_score": 0,
    "melhor_tempo": 0.0,
    "total_abates": 0,
    "partidas_jogadas": 0,
    "vitorias": 0,
    "historico": []
  }
}
```

### 4.2 Métodos a Adicionar em `src/sistemas/config_sistema.py`
- `obter_estatisticas() -> dict`: Retorna o dicionário de estatísticas atual.
- `registrar_partida(tempo: float, abates: int, pontos: int, vitoria: bool = False, configs_desbloqueadas: int = 0) -> dict`:
  - Atualiza `total_abates += abates`, `partidas_jogadas += 1`, `vitorias += (1 if vitoria else 0)`.
  - Verifica se `pontos > high_score` e `tempo > melhor_tempo`.
  - Adiciona entrada ao `historico` (mantendo os últimos 20 registros).
  - Executa `salvar_arquivo()` para persistência imediata.
  - Retorna `{ "novo_recorde_pontos": bool, "novo_recorde_tempo": bool }`.

### 4.3 Novo Módulo: `src/sistemas/sistema_particulas.py`
- **Classe `SistemaParticulas`**:
  - `sparks`: Faíscas balísticas emitidas ao atingir inimigos (linhas/pontos amarelos/brancos com dispersão angular e velocidade).
  - `bursts`: Brilhos de coleta de drop (partículas douradas para XP, verdes para cura, laranjas para armas, subindo suavemente e piscando).
  - `shockwaves`: Círculos concêntricos expansivos laranjas/amarelos com fading de transparência para foguetes e granadas.
  - `debris`: Fragmentos de explosão com desaceleração.
  - `MAX_PARTICULAS = 300`: Descarte automático de partículas mais antigas caso o teto seja atingido.

### 4.4 Hook de Screen Shake em `src/cenas/gameplay.py`
- Método `aplicar_shake(intensidade: float, duracao: float)`:
  - Verifica se `self.gerenciador_config.obter_valor("screen_shake") == "ligado"`.
  - Se ligado, inicializa `self.shake_intensidade` e `self.shake_timer`.
- No disparo de explosivos (`proj.explodir`): `self.aplicar_shake(10.0, 0.25)`.
- No dano recebido pelo jogador: `self.aplicar_shake(5.0, 0.15)`.
- Na derrota de chefes / mini-boss: `self.aplicar_shake(14.0, 0.35)`.

---

## 5. Verification Method (Método de Verificação Independente)

### 5.1 Comandos de Teste
Executar no terminal a suíte de testes com o interpretador Python do ambiente virtual:
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

### 5.2 Novos Testes a Criar na Implementação
1. `tests/test_persistence.py`:
   - Validação de carregamento padrão e migração de `save.json` sem a chave `estatisticas`.
   - Validação de atualização de recorde de pontos e melhor tempo via `registrar_partida`.
   - Validação de não-sobrescrita de estatísticas ao salvar via menu de configurações ou modal de level up.
2. `tests/test_particles_screenshake.py`:
   - Emissão e atualização de partículas (faíscas, bursts de XP/cura, ondas de choque).
   - Validação do limite máximo de partículas (`MAX_PARTICULAS`).
   - Validação do comportamento de `screen_shake`: inativo em `"desligado"`, ativo em `"ligado"`.
