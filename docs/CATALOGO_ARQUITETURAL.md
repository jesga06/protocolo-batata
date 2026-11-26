# Protocolo: Batata: Catálogo Arquitetural

Este documento descreve os módulos, contratos entre subsistemas, entidades, arsenal, configurações, conquistas, Chips de Firmware, sincronização de música e schema de save da branch `experimento-gameloop`. Ele complementa `docs/GDD_ATUALIZADO.md` e `docs/CONFIGURACOES.md`.

Os valores numéricos listados aqui (HP, dano, cadência, metas, multiplicadores e raios) são referências calibráveis durante playtests. Saves legados não são migrados nesta branch.

## Sumário

1. [Arquitetura modular de cena e Pipeline B+](#1-arquitetura-modular-de-cena-e-pipeline-b)
2. [Inimigos, especialistas, curva progressiva e Mini-Bosses](#2-inimigos-especialistas-curva-progressiva-e-mini-bosses)
3. [Arsenal de armas, separação LMB/RMB e modo contínuo](#3-arsenal-de-armas-separação-lmbrmb-e-modo-contínuo)
4. [Just-Dodge](#4-just-dodge)
5. [Equipamentos orbitais, drops e consumíveis](#5-equipamentos-orbitais-drops-e-consumíveis)
6. [Configurações de gameplay e exclusividade mútua](#6-configurações-de-gameplay-e-exclusividade-mútua)
7. [Sistema de conquistas, Chips de Firmware e schema de save](#7-sistema-de-conquistas-chips-de-firmware-e-schema-de-save)
8. [Módulos de upgrade de BIOS](#8-módulos-de-upgrade-de-bios)
9. [Sincronização bidirecional música-onda](#9-sincronização-bidirecional-música-onda)
10. [Chefe final (Geladeira Tsunami) e vitória](#10-chefe-final-geladeira-tsunami-e-vitória)
11. [Telas, HUD e fórmulas centrais](#11-telas-hud-e-fórmulas-centrais)

---

## 1. Arquitetura modular de cena e Pipeline B+

### 1.1 Divisão de `GameplayScene`

A cena principal foi dividida em três arquivos para separar orquestração, combate e renderização:

| Módulo | Classe ou Mixin | Responsabilidades |
|---|---|---|
| `src/cenas/gameplay.py` | `GameplayScene(GameplayCombateMixin, GameplayRenderMixin)` | Inicialização, estado da partida, modais e pausa, mediação entre `SistemaMusica` e `SistemaSpawn`, ciclo de Mini-Boss e chefe final, `loop()`, pontuação e fim de partida. |
| `src/cenas/gameplay_combate.py` | `GameplayCombateMixin` | Disparo de armas balísticas e contínuas, controle de calor, separação entre LMB e RMB, melee, Quick-Parry com onda defensiva, Duelo de Parry em 3 estágios, railgun, overvolt, colisões de projéteis, abates e execução do `GerenciadorEfeitosCombate`. |
| `src/cenas/gameplay_render.py` | `GameplayRenderMixin` | `draw()`, viewport, zoom e resolução, passes visuais (`vsync` em bandas com refração e deflexão, `iluminacao`, `cores_invertidas`, `motion_blur`, `modo_wireframe`), HUD no mundo, toasts, banners de desbloqueio (`desenhar_banners_desbloqueio`), buffs e telas de pausa, vitória e derrota. |

### 1.2 Pipeline B+ de hooks seletivos (`src/sistemas/efeitos_combate.py`)

O `GerenciadorEfeitosCombate`, mantido em `GameplayScene`, instancia apenas os handlers `EfeitoCombate` correspondentes às configurações não-neutras ativas e aos 1 a 3 Chips de Firmware equipados na run. Os ganchos são executados em ordem determinística por prioridade:

- `ao_tick(ctx, dt)`
- `ao_dash(ctx, origem, destino)`
- `ao_dash_evasao(ctx, evento)` (Just-Dodge)
- `ao_parry(ctx, projeteis_rebatidos)`
- `ao_disparo(ctx, arma, projeteis)`
- `ao_impacto(ctx, alvo, dano, fonte)`
- `ao_abate(ctx, inimigo, fonte)`
- `ao_dano_recebido(ctx, quantidade, fonte)`
- `ao_pos_render_mundo(ctx, superficie, camera=None)`

A entidade auxiliar `EntidadeHolograma` (`src/entidades/holograma.py`) atende dois comportamentos: no modo `"sombra"` (`sombra_espelho`), replica disparos e parries com cerca de 55% do dano sem recursão; no modo `"clone_agro"` (`thread_fantasma`), atrai inimigos próximos e explode ao ser destruída.

### 1.3 Infraestrutura transversal (`src/utils/`)

O loader `src/utils/traducao.py` carrega os arquivos JSON de `assets/locales/<idioma>/` para a memória na inicialização, sem I/O por frame. Ele expõe `t(categoria, chave, **kwargs)`, `obter_entradas()`, `obter_entrada()`, `obter_meta()` e `carregar_idioma()`. Em `pt_BR`, existem 12 categorias: `combate_entidades`, `configs_catalogo`, `conquistas`, `dicas`, `menu_configs`, `menu_conquistas`, `menu_debug`, `menu_principal`, `modal_level_up`, `modal_overclock`, `tutorial` e `ui_geral`.

O módulo `src/utils/fontes.py` mantém um cache compartilhado de fontes Sans-Serif e Monospace (`carregar_fonte_sans`, `carregar_fonte_mono`) usado por cenas, menus e modais. Já `src/utils/janela.py` gerencia a janela nativa de 1280x720 com `SpriteScaleCache`, `delta_time()` (clampado em `DT_CLAMP_MAX = 0.05s`) e `delta_time_real()` (tempo real com clamp de segurança de `0.25s` para áudio e timers independentes de stutter).

---

## 2. Inimigos, especialistas, curva progressiva e Mini-Bosses

### 2.1 Inimigos e limites simultâneos

O limite global de inimigos ativos é `SPAWN_MAX_ATIVOS = 95`. Quando algum limite tático específico é atingido, o spawner gera `InimigoPadrao` ou `InimigoRapido` como fallback.

| Inimigo | Papel e limite | Atributos base | Comportamento |
|---|---|---|---|
| Inimigo Padrão (Gabinete de Firma) | Volume | HP 18, Vel 130 px/s, Dano 10, XP 5 | Perseguição direta. Cai em 2 tiros de Pistola ou 1 golpe melee. |
| Inimigo Rápido (Mouse Óptico) | Volume | HP 10, Vel 234 px/s, Dano 8, XP 8 | Perseguição rápida. Cai em 1 tiro de Pistola ou 1 golpe melee. |
| Inimigo Tanque (Copiadora Xerox) | Especialista (`SPAWN_MAX_TANK = 3`) | HP 120, Vel 65 px/s, Dano 20, XP 25 | Bloqueia passagem e absorve dano alto. |
| Inimigo Phasing (Monitor CRT) | Especialista | HP 35, Vel 117 px/s, Dano 12, XP 12 | Ciclo de 3,0s com 1,2s de intangibilidade e imunidade a dano. |
| Inimigo Blindado (Triturador Blindado) | Especialista | HP 50, Vel 97,5 px/s, Dano 15, XP 15 | Placa frontal reduz dano em 30%. Vulnerável a flanco, dano verdadeiro e `cores_invertidas`. |
| Inimigo Ranged (Projetor Laser) | Especialista (`SPAWN_MAX_RANGED = 4`, dobrado com `inimigos_ranged`) | HP 30, Vel 104 px/s, Dano 10, Standoff 300 px, XP 15 | Mira preditiva com fator 0,50x. Dispara tiro único antes de 75s e rajada tripla após 75s. Com `inimigos_ranged="ligado"`, dispara mísseis teleguiados não-parriáveis e melhora o loot. |
| Impressora Térmica | Especialista (`SPAWN_MAX_IMPRESSORA = 2`, 60s+) | HP 75, Vel 85 px/s, Núcleo 25 dano (240 px/s), XP 22 | Dispara Núcleos de Sobrecarga parriáveis (~28 a 30 px) que geram contra-detonação de 180 px e 4 estilhaços teleguiados. |
| Ninja Corporativo | Especialista raro (`NINJA_MAX_ATIVOS = 2`, CD 20s, 75s+) | HP 165, Vel 195 px/s, Dano 14, XP 28 | Telegrafo de 0,55s, dash rápido, postura de bloqueio e shurikens não-desviáveis. Só recebe dano de `projetil_jogador` direto, `railgun`, `rifle_arco_direto`, `lanca_chamas` e `parry_ninja_proprio`. |
| Cubo Criogênico | Exclusivo do chefe final | HP 45, Vel 155 px/s, Dano 12, XP 10 | Patina e dispara fragmentos de gelo nas fases 2 e 3 da Geladeira Tsunami. |

### 2.2 Tipos de projéteis inimigos e ordem de desenho

Todos os projéteis inimigos são desenhados acima das entidades inimigas para manter visibilidade em hordas densas. Existem quatro tipos:

1. **Comuns:** esfera vermelha de ~12 px sem rastro. Podem ser evitados com Dash ou rebatidos com Quick-Parry.
2. **Não-desviáveis (`nao_desviavel=True`):** exclusivos do Ninja Corporativo. Shuriken roxo-magenta de ~20 px com núcleo branco, halo pulsante e rastro violeta 2x longo. Ignoram os i-frames do Dash e exigem Parry. Ao rebater, iniciam um Duelo de Parry em 3 estágios com velocidades crescentes (380, 470 e 560 px/s) e delay de retorno telegrafado de 0,25s nos estágios 2 e 3.
3. **Não-parriáveis (`nao_parriavel=True`):** exclusivos do Projetor Laser quando `inimigos_ranged="ligado"`. Seta amarelo-preta de ~20 px com aura âmbar, faíscas, rastro tracejado longo e cone de radar anti-retorno (esquivar para trás do míssil desativa a perseguição). Ignoram Parry e exigem Dash ou Just-Dodge.
4. **Núcleos de Sobrecarga Térmica:** exclusivos da Impressora Térmica. Projétil grande (~28 a 30 px) com núcleo laranja-rubro e contorno escuro sem aura dourada. Podem ser rebatidos para gerar contra-detonação.

### 2.3 Curva de dificuldade progressiva

Entre 0:00 e 1:30, a partida inicia com uma rajada inicial leve de inimigos de volume e `escala_hp_tempo = 1.0x`, enquanto o Projetor Laser dispara apenas tiro único. Todos os disparos do jogador têm knockback reduzido em 75% para evitar espalhar a horda sem controle.

Após 90s, `escala_hp_tempo` aumenta o HP dos inimigos comuns e especialistas em ~18% a cada 30s, acelerando após 180s até o teto de ~2,2x a 2,5x, acompanhado de aumento de velocidade e dano.

### 2.4 Mini-Bosses sincronizados por ciclo musical

Os Mini-Bosses entram na transição para `ASSAULT_INTRO`, em dois ciclos por partida (`MINIBOSS_CICLOS_RUN = 2`), com trava para manter no máximo um ativo por vez. Em cada run, `SistemaSpawn.__init__` sorteia 2 arquétipos sem repetição entre 4 opções: `impressora_matricial`, `fonte_generica`, `roteador_corporativo` e `nobreak_chumbado`.

No Ciclo 1, o Mini-Boss nasce com HP normalizado entre 750 e 850, independente do arquétipo. Nos ciclos seguintes, aplica `MINIBOSS_ESCALA_HP_CICLOS = (1.0, 1.35, 1.50)` sobre o HP cheio do arquétipo. Cada Mini-Boss tem 60,0s antes de superaquecer e explodir sem deixar loot, exibindo o aviso de superaquecimento. Derrotá-lo antes de 60s derruba `drop_overclock` (`ModalOverclock`); derrotá-lo antes de 30s concede bônus de abate rápido.

---

## 3. Arsenal de armas, separação LMB/RMB e modo contínuo

### 3.1 Extensão de `ArmaBase` (`src/armas/arma_base.py`)

`ArmaBase` mantém `disparar(...) -> list[Projetil]` para armas balísticas e adiciona suporte a armas contínuas e controle de calor:

- `eh_continua: bool = False` e `atualizar_fluxo(dt, segurando_gatilho, ...)` geram ticks determinísticos que passam pelo mesmo pipeline de dano, crítico, `overvolt` e `GerenciadorEfeitosCombate` sem criar centenas de projéteis.
- Propriedades opcionais `calor_atual`, `superaquecida` e `em_zona_ideal` alimentam a barra de calor desenhada sob o personagem e na HUD.

### 3.2 Separação entre ataque melee e Quick-Parry (`src/armas/melee.py`, `src/armas/bastao_choque.py`)

Com o Slot 1 equipado, o botão esquerdo (LMB) executa apenas `executar_ataque(...)` com alcance largo (~109 px), sem abrir janela de parry e sem punição de erro.

O botão direito (RMB) ou a tecla `E` em qualquer slot executa `iniciar_golpe_parry(...)` para o Quick-Parry:

- **Alcance desacoplado:** usa `parry_alcance_base` (64,0 px na Chave de Cano e 58,0 px no Bastão de Choque), escalado apenas por multiplicadores de configuração como `precisao_parry`.
- **Feedback visual:** exibe arco defensivo e SFX próprio, sem emitir texto de `"PARRY!"` quando acionado no vazio. A contagem para desbloqueio é acompanhada pelas barras de conquistas fixadas na HUD.
- **Filtro de não-parriáveis:** `tentar_parry_projeteis` ignora projéteis com `nao_parriavel=True`, tocando som metálico opaco sem rebater nem conceder i-frames.
- **Duelo de Parry:** ao aparar um projétil de duelo (Ninja ou Chefe), `finalizar_acerto_duelo()` fecha a janela ativa (`parry_janela_restante = 0.0`) para evitar múltiplos parries num único clique e reduz o cooldown para 0,08s apenas entre estágios do duelo.
- **Onda defensiva:** além do projétil refletido explosivo (90 px), gera uma onda ao redor do Cleiton (raio de ~135 px, dano ~20 e knockback radial em inimigos comuns).

### 3.3 Catálogo do arsenal

| Slot | Arma | Origem / Módulo | Características principais |
|---|---|---|---|
| 1 (Loadout) | Chave de Cano | Inicial (`src/armas/melee.py`) | Arco de 120°, `MELEE_DANO = 20`, `MELEE_ALVOS_MAX = 6`, foco em knockback. `parry_alcance_base = 64.0`. |
| 1 (Loadout) | Bastão de Choque | Alternativa (`src/armas/bastao_choque.py`) | Arco de 95°, menor cooldown, `parry_alcance_base = 58.0`. |
| 2 (Loadout) | Pistola Fajuta | Inicial (`src/armas/pistola.py`) | Munição infinita, `PISTOLA_DANO = 12`, 4º disparo sobrecarregado (2,2x perfurante). |
| 2 (Loadout) | SMG Compacta | Desbloqueada com o Dash em 15 parries (`src/armas/smg_compacta.py`) | Munição infinita com barra de calor (0% a 100%). Gera ~2,0 de calor por tiro com delay de resfriamento de 0,24s e resfria 50/s ao soltar o gatilho. Na zona ideal (60% a 92%), dá +25% de cadência e bônus de dano e velocidade. `ventilar_calor()` reduz 25% no Dash ou Parry e 0,5% por abate na zona ideal. Trava por ~1,0s ao chegar em 100%. Compatível com `bios_modding`. |
| 3 (Drop) | Escopeta | Clássica | 9 pellets, 60 cartuchos, empurrão a curta distância. |
| 3 (Drop) | Minigun | Clássica | 300 tiros, spin-up e recuo leve. |
| 3 (Drop) | Fuzil de Assalto | Clássica | 120 tiros, 3º tiro com crítico garantido. |
| 3 (Drop) | Lança-Foguetes | Clássica | 24 ogivas aceleradas (140 a 850 px/s), explosão de 80 px e fogo no chão. |
| 3 (Drop) | Lança-Granadas | Clássica | 32 granadas parabólicas, explosão de 65 px e 3 sub-explosões. |
| 3 (Drop) | Railgun | Clássica | Feixe perfurante de 1400 px/s com trilha de plasma. |
| 3 (Drop) | Rifle de Arco | Desbloqueável (`src/armas/rifle_arco.py`) | Feixe contínuo travado no alvo mais próximo da mira, com ticks rápidos, micro-slow e sinergia com `overvolt`. Drena munição por segundo. |
| 3 (Drop) | Lança-Chamas | Desbloqueável (`src/armas/lanca_chamas.py`) | Jato de partículas em cone (195 px, 55°), 10 de dano por tick de 0,14s (~71,4 DPS) e queimadura DoT (6 de dano a cada 0,5s por 2,5s). Drena munição por segundo. |

---

## 4. Just-Dodge

`Jogador` expõe a flag `em_dash_iframes` (separada da invulnerabilidade pós-dano) e a trava `dash_evasao_disponivel`, resetada para `True` a cada novo Dash e consumida em `consumir_just_dodge()`. Se um projétil inimigo ou hitbox de contato cruzar o jogador durante `em_dash_iframes`, o jogo registra um único evento `just_dodge` por Dash e envia o evento para `SistemaConquistas`.

---

## 5. Equipamentos orbitais, drops e consumíveis

- **Drones orbitais (Slot 4):** duram 30s e evoluem de MK-I a MK-III. `DroneCura` cura periodicamente e gera barreira de sobrevida até 25 pontos; `DroneCombate` faz 1, 2 ou 3 disparos automáticos; `DroneSuporte` dá +15% de velocidade, ímã de drops e zona de estase (50% de slow e +20% de dano recebido pelos inimigos).
- **Drops no chão:** expiram em 60s e tornam-se elegíveis para o Scavenger após 10s. Incluem Gema de XP (100% por abate), Caixa de Cura (+35 HP), Caixa de Arma (consulta `sistema_conquistas.possui_recompensa("arma", id)` para armas desbloqueáveis), Módulo de Drone, Núcleo de Overclock (exclusivo de Mini-Boss abatido em menos de 60s) e pares de Cápsulas de Suprimento em níveis comuns.
- **12 cartas consumíveis:** aplicam efeitos imediatos ou buffs temporários de 15s sempre abaixo dos bônus das configurações: `cura_pequena`, `cura_grande`, `xp_pequeno`, `xp_grande`, `buff_dano_temp`, `buff_vel_temp`, `buff_cadencia_temp`, `buff_resistencia_temp`, `escudo`, `pulso_magnetico`, `caixa_arma` e `caixa_equip`.

---

## 6. Configurações de gameplay e exclusividade mútua

O catálogo detalhado fica em `docs/CONFIGURACOES.md`, implementado em `src/sistemas/config_dados.py`, `src/sistemas/config_efeitos.py`, `src/sistemas/config_sistema.py` e `src/sistemas/efeitos_combate.py`:

- **30 configurações de gameplay:** incluem as 23 opções base (com rework em 8 delas), `postura_riposte` (janela de 0,45s, enraizamento com invulnerabilidade, estocada perfurante de 240 px com stun de 1,5s), `firewall_estatico`, `ventoinha_360`, `mira_oculta` (oculta cursor fora de menus e aplica curvatura teleguiada aos tiros) e `velocidade_jogo` (categoria `Experimental`, 6 opções `50%`/`75%`/`Padrão`/`125%`/`150%`/`200%`, sub-stepping `<= 0,05s` com separação `dt_real` vs `dt_sim`, pulo de `HOLD` na música dinâmica, relógio duplo `JOGO`/`REAL` no HUD e telas finais).
- **2 configurações de Dash** (exigem `habilidade:dash`): `dash_protocolo` (`padrao`, `teleporte_buffer`, `propulsor_instavel`, `sombra_espelho`, `rollback_estado`) e `dash_rastro` (`padrao`, `exaustao_termica`, `vacuo_io` com vórtice de ~95 px por 2,5s, `subprocesso_atrasado`, `thread_fantasma`).
- **3 configurações gerais adicionais:** `garbage_collector`, `latencia_ping` (`exclusiva_conquista=True`, desbloqueada em `sobrevivente_caos` M3, nunca entra no Level-Up; aplica atraso de ~80ms em disparo, melee, Parry e Dash) e `modo_wireframe`.
- **Contratos em `GerenciadorConfiguracoes` (`config_sistema.py`):** valida `requer_desbloqueio`, `exclusiva_conquista` e `desbloqueada_por` em `obter_configs_bloqueadas_level_up()` e `obter_bloqueadas()`, resolve conflitos de `incompativel_com` em `definir_valor_com_conflitos()` retornando os itens revertidos, calcula impacto prévio na cota 2-4-6 via `simular_definir_valor_com_conflitos()` (ordem inversa Slot 3, 2, 1) e gerencia `preferencias_mira` (`cor` e `escala`) via `definir_preferencias_mira()`.
- **3 configurações de sistema (áudio):** `volume_master`, `volume_musica` e `volume_sfx`. A customização visual da mira (`preferencias_mira`) também fica na aba Sistema e não entra na contagem de configurações não-neutras.

---

## 7. Sistema de conquistas, Chips de Firmware e schema de save

Os módulos responsáveis são `src/sistemas/conquistas_dados.py`, `src/sistemas/sistema_conquistas.py` e `src/ui/menu_conquistas.py`.

### 7.1 Chips de Firmware (cota 2-4-6)

Os 8 Chips de Firmware são equipados no Menu Principal (mesmo abaixo da cota, exibindo status `ATIVO` ou `INATIVO`) e ativam na partida conforme `N_configs_nao_neutras`: Slot 1 exige 2+, Slot 2 exige 4+ e Slot 3 exige 6+. Alterar configurações em partida que reduzam a contagem abaixo da cota abre um modal de confirmação listando os chips afetados na ordem inversa (Slot 3, Slot 2, Slot 1) e dispara banners de desativação ou reativação.

1. `gatilho_duplo`: após Dash ou Parry, o próximo disparo sai duplo (2º projétil com ~60% de dano e -0,4s de CD no Dash).
2. `recarga_tatica`: a cada 3 dashes, recupera ~25% de munição e concede 1 pilha de blindagem (-8% de dano, até 3 pilhas por 4s).
3. `adrenalina_overclock`: abater Elite, destruir Totem do Chefe ou fazer 5 abates rápidos dá pico decrescente de +45% de velocidade e +35% de cadência por 3,5s.
4. `canhoes_perimetrais`: 6 setores angulares ao redor do Cleiton com CD individual; atirar na direção de um setor pronto solta uma rajada flamejante extra.
5. `sobrecarga_estrutural`: 3 tiros seguidos no mesmo alvo (ou atingir Blindados, Tanks, Elites e Boss) fragmentam blindagem (+20% de dano recebido por 4s e explosão perfurante escalada pelo HP máximo).
6. `overclock_termico`: dano recebido acumula Carga Residual por 5s (até +30% de cadência), descarregada no próximo Parry ou Tiro Sobrecarregado em onda frontal de dano verdadeiro.
7. `sandbox_isolada`: CD de ~28s; em Parry perfeito cria uma cúpula fixa no chão por 3,5s que bloqueia projéteis externos.
8. `reset_voraz`: abates em até 2s após Dash ou Parry reduzem em 50% o cooldown restante de ambos.

### 7.2 Conquistas contínuas (5)

| ID | Critério | Milestone 1 | Milestone 2 | Milestone Final |
|---|---|---|---|---|
| `mestre_chave_inglesa` | Parries | 15: `habilidade:dash` e `arma:smg_compacta` | 50: `trofeu:reflexo_metalico` | 120: `opcao_config:precisao_parry:postura_riposte` e `slot_firmware:+1` |
| `velocidade_de_clock` | Just-Dodges | 40: `modificador_run:recarga_tatica` | 150: `opcao_config:dash_rastro:thread_fantasma` | 350: `opcao_config:dash_protocolo:sombra_espelho` |
| `depurador_escritorio` | Abates totais | 250: `trofeu:depurador_m1` | 1.500: `modificador_run:adrenalina_overclock` e `slot_firmware:+1` | 5.000: `arma:lanca_chamas` |
| `cacador_hardware` | Mini-Bosses em <60s | 4: `modificador_run:canhoes_perimetrais` | 16: `modificador_run:sobrecarga_estrutural` | 40: `arma:rifle_arco` |
| `sobrevivente_caos` | Vitórias contra Geladeira | 1: `modificador_run:overclock_termico` | 3: `opcao_config:dash_protocolo:rollback_estado` | 7: `configuracao:latencia_ping` e `slot_firmware:+1` (teto 3) |

### 7.3 Conquistas únicas (11)

- **7 troféus colecionáveis:** `monge_tibetano` (2 min contínuos em 15 FPS), `cabo_vga_solto` (vencer com `cores_invertidas` e `vsync:desligado`), `blindado_escritorio` (abater Mini-Boss com `controles_tanque`), `boliche_corporativo` (3 abates por colisão cinética num golpe), `zero_visao_cem_fe` (Nv. 8 com `hud:desligado` e `iluminacao:ligado`), `auto_sabotagem` (abater Mini-Boss com `fogo_amigo`) e `limpeza_de_disco` (apagar 15+ projéteis numa coleta do `garbage_collector`).
- **4 desbloqueios raros:** `primeiro_overclock_sujo` (1 Mini-Boss em <60s com 2+ configs não-neutras, libera `modificador_run:gatilho_duplo` e recebe auto-pin na HUD após M1 de `mestre_chave_inglesa`), `intocavel_rh` (vencer a Geladeira sem dano na Fase 3, libera `modificador_run:sandbox_isolada`), `reset_infinito` (5 parries seguidos em <12s sem errar, libera `modificador_run:reset_voraz`) e `modo_batata_supremo` (vencer com 5+ configs não-neutras ativas, libera `arma:bastao_choque`).

### 7.4 Schema de persistência (`data/save.json`, v2)

`data/save.json` é gravado de forma atômica ao concluir conquista, alterar menu, pausar ou encerrar a partida. Qualquer arquivo sem `schema_version == 2` é reinicializado no formato abaixo:

```json
{
  "schema_version": 2,
  "tutorial_visto": false,
  "preferencias_mira": { "cor": "ciano", "escala": 1.0 },
  "desbloqueadas": [],
  "ativas": {},
  "sistema_configs": { "volume_master": 100, "volume_musica": 100, "volume_sfx": 100 },
  "loadout": { "slot1": "chave_manutencao", "slot2": "pistola" },
  "estatisticas": {
    "high_score": 0,
    "melhor_tempo": 0.0,
    "total_abates": 0,
    "partidas_jogadas": 0,
    "vitorias": 0,
    "historico": [],
    "parries_total": 0,
    "dash_desbloqueado": false
  },
  "progresso_conquistas": {
    "unicas_concluidas": [],
    "continuas": { "mestre_chave_inglesa": { "valor": 0, "milestones_concluidos": [] } },
    "fixadas": ["mestre_chave_inglesa"],
    "recompensas": {
      "habilidade": [],
      "configuracao": [],
      "opcao_config": [],
      "modificador_run": [],
      "arma": [],
      "trofeu": []
    },
    "slots_firmware_max": 1,
    "modificadores_equipados": []
  }
}
```

---

## 8. Módulos de upgrade de BIOS

Obtidos ao coletar `drop_overclock` de Mini-Bosses derrotados em menos de 60s (`ModalOverclock` exibe até 3 opções não adquiridas):

1. **Multithreading (`multithreading`):** 2 núcleos orbitais copiam disparos (eco de 0,08s) e bloqueiam 1 projétil a cada 4s.
2. **Refrigeração a Nitrogênio (`refrigeracao`):** +20% de cadência e onda de frio (50% de slow por 3s) ao pausar disparos por 1,5s.
3. **Overvolt (`overvolt`):** bônus de crítico e arcos elétricos em cadeia (até 4 inimigos) a cada 25 abates ou acerto crítico.
4. **BIOS Modding (`bios_modding`):** libera o Slot 3B (disparo simultâneo no LMB mantendo RMB livre para Quick-Parry) e dá +15% de munição especial ao abater Mini-Bosses.
5. **Proteção contra Surtos (`protecao_surtos`):** +50 HP máximo e disjuntor contra dano fatal que restaura 50% do HP, limpa projéteis e congela a arena por 4s (CD de 60s).
6. **Upgrade de Barramento (`upgrade_barramento`):** +15% de velocidade fixa e vácuo contínuo de drops comuns.

---

## 9. Sincronização bidirecional música-onda

`SistemaMusica` não importa `SistemaSpawn` nem entidades, e `SistemaSpawn` não importa `SistemaMusica` nem `pygame.mixer`. `GameplayScene` faz a mediação entre os dois.

- **Contratos em `SistemaMusica`:** `atualizar(..., trava_assault: bool = False, pausar_transicao: bool = False)` mantém 2 canais reservados em lock-step (limpo e abafado). `consumir_evento_assault_intro() -> bool` sinaliza o início de `ASSAULT_INTRO`. Quando `trava_assault=True` em `ESTADO_ASSAULT`, `_decidir_proximo_estado()` mantém `ESTADO_ASSAULT` antes de `Channel.queue()` sem usar `Channel.stop()`.
- **Concorrência SDL e áudio procedural:** `SistemaMusica.atualizar()` roda mesmo com `hitstop_timer > 0`, usa lookahead de ~0,50s com checagem de `get_queue() is None`, realinha `_inicio_faixa` em `pausar_transicao=True` e usa fallback determinístico por `dt` em ambiente headless (`SDL_AUDIODRIVER=dummy`). Em `src/sistemas/sistema_audio.py`, `GerenciadorAudio` mantém pools pitch-shifted (incluindo `"explosao"`) e sintetiza em NumPy os SFX de Dash (`_sintetizar_dash_whoosh`), Rifle de Arco (`_sintetizar_arco_eletrico`) e 4 variações de Lança-Chamas (`_sintetizar_lanca_chamas`).
- **Contratos em `SistemaSpawn`:** `update(..., fase_onda: str = "calm", gatilho_assault_intro: bool = False, contagens_taticas: dict[str, int] | None = None)` aplica multiplicador ~0,60x em `"calm"` (`ANTICIPATION`/`HOLD`), dispara Rush Wave e o próximo Mini-Boss em `gatilho_assault_intro=True` e aplica multiplicador ~1,30x em `"assault"` respeitando os tetos táticos.

---

## 10. Chefe final (Geladeira Tsunami) e vitória

O encontro com a Geladeira Tsunami começa ao atingir o Nível 12 após 185s ou ao concluir os 2 ciclos de Mini-Boss (fallback em 195s) sem Mini-Boss vivo. Após um período de transição de 10s, `fadeout_para_boss()` inicia a cutscene em 4 fases.

A entidade tem tamanho de 112x156 px, `BOSS_GELADEIRA_HP_BASE = 48000` e velocidade de 268 px/s. Suas 3 fases são sincronizadas aos graves da trilha via `AnalisadorFFTBoss`, alternando pulsos sônicos (1,15s na F1), cubos de gelo (3,0s), dashes duplos (2,0s na F2), totens `CaixaDeSomBoss` (1,8s na F2), ataques em hélice e explosão radial (1,10s na F3), poças de gelo e Núcleos Criogênicos parriáveis.

A horda de apoio durante o chefe tem limite de 24 inimigos com especialistas progressivos por fase (`InimigoNinja`, `InimigoImpressoraTermica`, `InimigoPhasing`, `InimigoBlindado`, `InimigoRanged`), mantendo `pausar_despawn=True`, 0% de XP e 40% de taxa base de drops. A vitória ocorre exclusivamente ao derrotar a Geladeira Tsunami.

---

## 11. Telas, HUD e fórmulas centrais

- **Menu Principal e revelação progressiva:** o seletor de loadout inicial (Slots 1 e 2) fica oculto até desbloquear `smg_compacta` ou `bastao_choque`. O rótulo `CONQUISTAS` só passa a incluir `& FIRMWARE` após o 1º Chip de Firmware. `MenuConfigs` oculta configurações ainda bloqueadas. Quando `tutorial_visto == False`, um modal pergunta se o jogador deseja abrir o tutorial.
- **Mouse, mira e debug:** o jogo usa cursor de hardware `pygame.cursors.Cursor` com customização estética em `preferencias_mira` e suporte completo a mouse em `MenuConquistas` e `MenuConfigs`. O `MenuDebug` (`F1` ou `~`) permite testar as 30 configurações, as 4 novas armas, spawns de Impressora Térmica e Ninja Corporativo e troca direta de fase musical.
- **HUD em 1280x720:** sob o Cleiton ficam as barras de HP/Barreira, Dash (quando desbloqueado) e Munição/Calor da SMG. No topo esquerdo ficam o painel de vitais com HP, Dash e timer de recarga do Quick-Parry (`PARRY PRONTO` / `PARRY X.Xs`), os slots `[1]` a `[4]` / `[3B]` e buffs ativos. No topo central ficam cronômetro, abates, XP e barra de vida de Boss/Mini-Boss. No topo direito ficam de 0 a 3 conquistas fixadas sem truncamento de nome, ocultas quando `hud="desligado"`, além de FPS e botão `[C]`. Desbloqueios disparam banners animados dedicados em `desenhar_banners_desbloqueio`.
- **Protagonista (Cleiton):** 150 HP base, 260,0 px/s, 0,20s de invulnerabilidade pós-dano (somando com `fps_stutter_dodge` e `motion_blur_ghosting`).
- **Pontuação final:**

  $$Score = \left(Score_{abates} + 10 \cdot t + 0,5 \cdot Dano_{causado} + Score_{vitoria}\right) \times \left(1,0 + 0,10 \cdot N_{configs\_nao\_neutras}\right)$$
