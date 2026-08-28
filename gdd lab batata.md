## Nome do Projeto
**Protocolo: Batata**

## Highconcept

O jogo é um arena shooter 2D top-down de sobrevivência, inspirado em títulos como *Vampire Survivors*. Sua mecânica principal é o sistema de progressão: Ela não acontece por meio de melhorias tradicionais como aumento de dano, cura, ou alcance, mas sim pelo desbloqueio de novas opções no menu de configurações do jogo. Cada configuração afeta um aspecto mecânico diferente do jogo. O jogador deve sacrificar a conveniência e o próprio conforto (como diminuir o FPS, abaixar os gráficos ou usar keybinds menos-que-confortáveis) em troca de vantagens mecânicas durante a partida.

## Gameplay e Enredo

O jogador controla uma batata dentro de uma arena com o simples objetivo de sobreviver o máximo de tempo possível contra ondas contínuas de inimigos. Não há campanha, progressão de história ou diálogos. Derrotar inimigos ocasionalmente pode criar caixas que podem conter experiência, cura, armas ou equipamentos. O jogador coleta o item ao andar por cima da caixa.

Há um inventário com quatro slots: o primeiro contém um ataque corpo-a-corpo que empurra inimigos próximos; o segundo possui uma pistola permanente com munição infinita; o terceiro é reservado para armas especiais de munição finita (como escopetas e lança-foguetes); e o quarto serve para equipamentos de suporte, como drones.

Ao derrotar inimigos e coletar pontos de experiência o suficiente, o jogador sobe de nível e tem a chance de escolher uma entre três novas configurações de jogo para desbloquear permanentemente. Essas opções poderão ser ativadas ou desativadas em um arquivo de texto empacotado junto ao jogo, surtindo efeitos em partidas futuras. Quanto maior o nível do jogador, mais experiência será necessária para atingir o próximo nível.

## Interface de usuário

O HUD padrão contém:
- Uma barra vermelha de HP abaixo do personagem do jogador.
- Uma barra amarela de experiência logo abaixo da barra de HP.
- Inventário no canto superior esquerdo. (Haverão números abaixo do segundo e terceiro slots, indicando a munição restante. No quarto, haverá o cooldown restante do equipamento.)
- Timer de partida no canto superior direito da tela.

A interface pode ser desativada pelo próprio jogador após o desbloqueio dessa configuração, removendo completamente as barras de vida, experiência, inventário e tempo em troca de recompensas mecânicas.

Ao ganhar um nível, o jogo pausa, a tela é escurecida lentamente, e três configurações bloqueadas são apresentadas em um formato semelhante a cartas colecionáveis, mostrando um ícone, o nome da configuração e uma breve descrição do seu efeito.

## Audio e música

A música da partida é composta por uma única faixa 8-bits em loop contínuo.

O jogo possui feedback sonoro para cada ação, com efeitos distintos para os diferentes tipos de disparos, dano sofrido, interações nos menus e coleta de itens. As configurações de áudio (volume geral, música e efeitos) são as únicas que servem estritamente para usabilidade e não geram impactos no gameplay.

## Arte Conceito e referências

O visual adota o formato pixel art com uma paleta de cores variada. O personagem do jogador tem visual inspirado na Noz de PvZ. O terreno será composto de algumas variações de texturas de grama, e os inimigos e seus projéteis terão contornos vermelhos para facilitar a visualização.

Os itens deixados pelos inimigos caem como caixas de madeira, utilizando cores vivas para diferenciação rápida: amarelo para experiência, vermelho e branco para cura, marrom escuro para armas e cinza para equipamentos.

Existe uma configuração de "Gráficos Baixos" que transforma todos os inimigos e o jogador em formas geométricas coloridas simples.

> Nota: ainda não tive tempo de montar as artes