# Protocolo: Batata

# Seção 1 - Overview

## 1.1 - High Concept

**Protocolo: Batata** é um arena survival shooter 2D em visão top-down, inspirado em jogos como *Vampire Survivors*, que faz uma única pergunta ao jogador: 

> **"O quão desconfortável você está disposto a ficar para se tornar mais forte?"**

Diferentemente de jogos do gênero, a principal forma de progressão de longo prazo do jogador não vem de desbloquear armas mais fortes ou upgrades passivos, mas sim de desbloquear **configurações do jogo**.

Quase todas as configurações esperadas em um jogo que afetam a gameplay estão bloqueadas por padrão.

Durante a gameplay, o jogador pode permanentemente desbloquear novas opções de configuração. Essas configurações podem ser habilitadas ou desabilitadas antes ou durante qualquer run futura.

A filosofia central de design é que **configurações menos confortáveis fornecem vantagens na gameplay**.

Exemplos incluem:
* Limitar FPS
* Desabilitar HUD
* Habilitar movimento apenas com o mouse
* Reduzir a qualidade gráfica
* Usar binds intencionalmente inconvenientes

Em vez de tratar o menu de opções como algo fora do jogo, **Protocolo: Batata** o transforma em um dos principais sistemas de progressão da experiência.

## 1.2 - Loop de Gameplay

O loop padrão de uma run segue a estrutura abaixo:

1. Iniciar uma run com o equipamento padrão e configurações escolhidas.
3. Derrotar inimigos.
4. Coletar XP.
5. Subir de nível.
6. Desbloquear permanentemente uma nova configuração de gameplay (escolhendo 1 entre 3 apresentadas).
7. Continuar sobrevivendo contra hordas de inimigos progressivamente mais difíceis.
8. Coletar armas e equipamentos temporários.
9. Sobreviver até a morte (or derrotar o chefe, se implementado).

Após o término da run:
* Configurações desbloqueadas permanecem disponíveis para sempre;
* Armas temporárias desaparecem;
* Equipamentos temporários desaparecem;
* O jogador pode alterar quais configurações estão ativas antes da próxima run.

## 1.3 - Progressão do Jogador

O jogo contém **dois sistemas de progressão completamente distintos**:

### Progressão Permanente
A progressão permanente existe fora da run. O jogador desbloqueia configurações de gameplay que permanecem disponíveis para sempre.
Exemplos:
* Opções de limite de FPS
* Qualidade gráfica
* Alternância de HUD
* Modificadores de movimento
* Modificadores de inimigos
* Desbloqueio de futuras configurações

A progressão permanente é salva localmente.

### Progressão Temporária
A progressão temporária existe apenas durante a run atual.
Exemplos:
* Níveis de XP
* Armas temporárias
* Equipamentos temporários
* Cura
* Buffs

Tudo nesta categoria é perdido quando a run acaba.

## 1.4 - Estrutura do Jogo

O jogo consiste em uma única arena.
* Não há fases.
* Não há campanhas.
* Não há progressão de história.

A dificuldade aumenta naturalmente com o tempo através do spawn de inimigos. Versões futuras podem introduzir encontros com chefes após um determinado tempo de sobrevivência.

## 1.5 - Identidade Visual e Tom

O jogo abraça uma relação intencionalmente exagerada entre opções de desempenho e mecânicas de jogo. Os jogadores devem perceber imediatamente que o menu de Opções não é apenas utilitário, mas uma das mecânicas centrais do jogo.

O humor vem de tratar opções de gráficos ou controles comuns como se fossem itens lendários de um RPG.

Exemplos de *Flavor Text*:

> **Gráfico: Baixo/Alto**
> *"Texturas são um luxo."*

> **Limite de FPS: 15/30/45/60**
> *"O olho humano não consegue ver além de 24 FPS."*

> **HUD: Ativado/Desativado**
> *"Olha mãe, sem olhar!."*

> **Remapeamento**
> *"Cuidado pra não desenvolver túnel de carpo."*

## 1.6 - Escopo

Este projeto prioriza intencionalmente a originalidade em detrimento da complexidade.

Funcionalidades como IAs sofisticadas, mundos procedurais, multiplayer online, sistemas de diálogo ou progressão narrativa estão fora do escopo do projeto.

A experiência pretendida é:
* Fácil de entender;
* Fácil de jogar novamente (fator replay);
* Mecanicamente sólida e consistente;
* Bem-humorada;
* Altamente configurável.

A característica marcante do projeto é a transformação do menu de Configurações tradicional no sistema de progressão permanente do jogador.

## Observações:

### 1. Toda Configuração É uma Decisão
Alterar uma configuração nunca deve parecer algo puramente cosmético. Sempre que possível, uma configuração deve ter:
* Uma consequência imediata na gameplay;
* Um trade-off claro;
* Um impacto visível.

Os jogadores devem se perguntar frequentemente: *"Vale a pena ativar isso?"*, em vez de *"Qual configuração aumenta mais o meu número?"*.

### 2. Engraçado Sem Virar Piada Pronta
O jogo deve manter um tom comédico. Descrições de configurações, desbloqueios e textos de sabor (flavor text) são encorajados a ser bem-humorados. No entanto, a gameplay deve permanecer consistente e mecanicamente sólida. A piada é a premissa; a jogabilidade ainda precisa ser satisfatória.

# Seção 2 - Core Gameplay

## 2.1 - Visão Geral da Gameplay

O jogador controla uma batata dentro de uma arena vista de cima (top-down).

O objetivo é sobreviver pelo maior tempo possível enquanto se torna progressivamente mais forte através de equipamentos temporários e expande permanentemente as configurações de jogo disponíveis.

A arena não possui um objetivo pré-definido além da sobrevivência. A pressão dos inimigos aumenta continuamente até que o jogador morra ou, em versões futuras, derrote um chefe.

## 2.2 - Fluxo da Partida

Toda partida segue a mesma estrutura de alto nível:

```
Iniciar Run
    │
Spawnar Jogador
    │
Lutar contra Inimigos
    │
Coletar XP
    │
Subir de Nível
    │
Desbloquear Configuração
    │
Ativar Configurações (opcional)
    │
Coletar Armas / Equipamentos
    │
Inimigos Ficam Mais Fortes
    │
Repetir
    │
Jogador Morre
    │
Fim da Run
```

Apenas as configurações permanentes persistem entre as runs.

## 2.3 - O Jogador

O jogador controla uma batata.

A batata não possui diálogos, história ou personalidade que afetem a gameplay. Seu único propósito é servir como o avatar do jogador.

O design visual deve comunicar:
* Simplicidade
* Maquinário
* Durabilidade
* Aparente toque comédico

## 2.4 - Câmera

Perspectiva da câmera:
* Top-down (visão superior)
* A câmera segue o jogador
* Efeito suave de suavização/atraso (smoothing/lag) em vez de travar rigidamente na posição do jogador

Propósito:
* Fazer a movimentação parecer menos rígida
* Proporcionar um movimento mais dinâmico
* Evitar a sensação de câmera "colada" no jogador

## 2.5 - Movimentação

Existem dois modos de movimentação:

### Movimentação Padrão
A movimentação utiliza teclas remapeáveis.

Padrão:
* W (Cima)
* A (Esquerda)
* S (Baixo)
* D (Direita)

Movimentação omnidirecional, sendo permitida movimentação na diagonal.

### Modo de Movimentação pelo Mouse
Desbloqueado posteriormente como uma configuração de gameplay.

Quando ativado:
* O robô anda continuamente em direção ao cursor do mouse
* Movimentação pelo teclado é desabilitada
* A movimentação nunca para, a menos que o cursor esteja diretamente sobre o jogador

Recompensa:
* +40% de chance multiplicativa de drop

Flavor Text:
> **Piloto Automático**
> *"Pensar custa caro."*

## 2.6 - Vida (HP)

HP Base: **150**

O HP máximo pode aumentar através de configurações de gameplay.

O HP **não** se regenera naturalmente.

Formas de cura ocorrem exclusivamente por:
* Drops de cura
* Equipamentos temporários
* Itens futuros

### Morte
O jogador morre imediatamente quando o HP chega a zero.
* A run atual termina.
* O progresso temporário é perdido.
* As configurações desbloqueadas permanecem salvas.

## 2.7 - Dano

Os inimigos causam dano ao tocar no jogador.

Cada inimigo mantém seu próprio tempo de recarga (cooldown) de dano.

Exemplo:
1. Inimigo A toca no jogador -> Cooldown de 400 ms começa.
2. Inimigo B toca no jogador -> Inimigo B usa seu próprio cooldown independentemente.

Esse valor **não** é global. Cada arquétipo de inimigo define:
* Dano
* Cooldown
* Velocidade de movimento

Exemplo:
* **Inimigo Rápido**: Dano 8 | Cooldown 250 ms
* **Tank**: Dano 20 | Cooldown 700 ms

Isso faz com que os inimigos pareçam mecanicamente diferentes sem a necessidade de uma IA complexa.

## 2.8 - Combate

O combate é intencionalmente direto.

O jogador possui duas armas permanentes. Armas temporárias adicionais podem ser coletadas durante a run.

## 2.9 - Armas Iniciais

### Ataque Melee (Corpo a Corpo)
Características:
* Curto alcance
* Dano baixo
* Ataca em área
* Empurra até dois inimigos mais próximos (knockback)

Propósito:
* Controle de grupo de emergência
* Escapar de situações onde o jogador esteja encurralado

O knockback deve ser perceptível, mas não excessivo.

Flavor Text:
> **Chave de Manutenção**
> *"Manutenção percussiva resolve a maioria dos problemas."*

### Pistola
Características:
* Munição infinita
* Dano baixo
* Velocidade de projétil lenta
* Alvo único
* Longo alcance

Propósito:
* Arma padrão confiável.
* Nunca desaparece.

Flavor Text:
> **Padrão de Fábrica**
> *"Tecnicamente qualifica como 'armado'."*

## 2.10 - Slots de Armas

O inventário do jogador contém quatro slots:

* **Slot 1:** Arma melee permanente (não pode ser substituída).
* **Slot 2:** Pistola permanente (não pode ser substituída).
* **Slot 3:** Arma especial temporária (suporta exatamente uma arma; pegar outra substitui a atual).
* **Slot 4:** Equipamento temporário (reservado para gadgets de suporte; apenas um por vez).

## 2.11 - Armas Especiais

Armas especiais são obtidas através de drops de armas.

Ficam ativas imediatamente ao serem coletadas.

O jogador usa o mesmo botão de tiro para todas as armas:
* Armas automáticas atiram continuamente enquanto o botão for mantido pressionado.
* Armas de disparo único exigem cliques repetidos.

Armas planejadas:

### Minigun
* Alta taxa de disparo
* DPS elevado
* Grande dispersão
* Munição limitada

### Espingarda (Shotgun)
* Dano por explosão (burst) muito alto
* Ampla dispersão de projéteis
* Curto alcance efetivo

### Fuzil de Assalto (Assault Rifle)
* Automático
* Dano balanceado
* Dispersão média
* Arma de uso geral

### Lança-Foguetes (Rocket Launcher)
* Dano explosivo em área (AoE)
* Munição muito limitada
* Projéteis lentos

### Lança-Granadas (Grenade Launcher)
* Dano explosivo
* Mais munição que o lança-foguetes
* Arco de projétil pode ser introduzido em versões futuras

Outras armas podem ser introduzidas seguindo a mesma filosofia.

## 2.12 - Munição

Armas especiais utilizam munição limitada.

Quando a munição chega a zero:
* A arma desaparece
* O Slot 3 fica vazio

Armas permanentes **nunca** consomem munição.

## 2.13 - Equipamentos

Equipamentos ocupam o Slot 4 e são temporários.

* **Duração:** 30 segundos.
* Pegar outro equipamento substitui imediatamente o atual.
* Obtidos exclusivamente por drops.

Exemplos atuais:
* **Drone de Cura:** Cura o jogador periodicamente.
* **Drone de Combate:** Ataca automaticamente inimigos próximos.
* **Drone de Suporte:** Fornece buffs temporários.

## 2.14 - Experiência (XP)

Inimigos concedem XP ao serem derrotados.

Diferentes arquétipos de inimigos concedem quantidades variadas de XP.

A XP coletada preenche a barra de experiência do jogador, representada por uma barra amarela abaixo do robô.

## 2.15 - Subir de Nível (Level Up)

Quando XP suficiente é coletada:
1. O jogo pausa.
2. O menu de level up abre.
3. O jogador recebe 3 configurações bloqueadas aleatórias (se restarem menos de 3, exibe apenas as restantes).
4. O jogador escolhe exatamente uma.
5. A configuração selecionada torna-se permanentemente desbloqueada.
6. O jogo despausa e retoma a ação.

Configurações desbloqueadas **nunca** aparecem novamente nas escolhas.

## 2.16 - Nível Máximo

Não há um nível máximo fixo no código.

O nível máximo é determinado pela quantidade de configurações de gameplay bloqueadas restantes.

Quando todas as configurações forem desbloqueadas:
* Novos level ups tornam-se impossíveis.
* O sistema calcula isso automaticamente.

Isso permite adicionar novas configurações no futuro sem precisar modificar o código central da gameplay.

## 2.17 - Progressão na Run

A intensidade dos inimigos aumenta continuamente através de:
* Ondas maiores
* Mais inimigos simultâneos
* Arquétipos mais fortes

O objetivo é criar uma pressão crescente e contínua em vez de picos bruscos de dificuldade.

## 2.18 - Vitória

A versão atual não possui uma condição obrigatória de vitória.

O loop pretendido é a sobrevivência até a morte.

Versões futuras podem introduzir:
* Encontros com chefes
* Marcos de tempo de sobrevivência
* Objetivos opcionais de conclusão

Essas adições não devem alterar o foco principal no ciclo de sobrevivência.

## 2.19 - Princípios Core de Design da Gameplay

A gameplay deve permanecer legível em todos os momentos.

A complexidade deve vir de:
* Escolher configurações;
* Decidir quando substituir armas;
* Adaptar-se aos arquétipos de inimigos.

A complexidade **NÃO** deve vir de:
* Controles difíceis;
* Combos de armas complicados;
* IA de inimigos intrincada.

A atenção do jogador deve estar focada em movimentação, posicionamento, coleta de recursos e escolha de configurações. Mecânicas simples interagindo entre si devem criar o desafio.