"""
Catálogo e Definições de Dados do Sistema de Configurações — Protocolo: Batata
SSOT: CONFIGURACOES.md
Define todas as 28 configurações de gameplay desbloqueáveis e as 3 configurações de sistema (31 no total).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class CategoriaConfig(str, Enum):
    PERFORMANCE = "Performance"
    INTERFACE = "Interface"
    CONTROLES = "Controles"
    DIFICULDADE = "Dificuldade"
    EXPERIMENTAL = "Experimental"
    SISTEMA = "Sistema"


class TipoControleConfig(str, Enum):
    TOGGLE = "Toggle"
    GRUPO = "Grupo"
    SLIDER = "Slider"
    SELETOR = "Seletor"


@dataclass
class OpcaoConfig:
    """Representa uma opção selecionável dentro de uma configuração."""
    id: str
    label: str
    modificadores: dict[str, Any] = field(default_factory=dict)
    flavor_text: str = ""
    nerf_text: str = "Nenhum"
    buff_text: str = "Nenhum"
    desbloqueada_por: Optional[str] = None
    incompativel_com: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class ConfiguracaoDef:
    """Definição completa de uma configuração do jogo."""
    id: str
    nome: str
    categoria: CategoriaConfig
    tipo: TipoControleConfig
    valor_padrao: Any
    opcoes: dict[str, OpcaoConfig] = field(default_factory=dict)
    is_gameplay: bool = True
    ordem: int = 1
    descricao_sistema: str = ""
    requer_desbloqueio: Optional[tuple[str, str]] = None
    exclusiva_conquista: bool = False


# =============================================================================
# CATÁLOGO DE CONFIGURAÇÕES DE GAMEPLAY (28 ITENS DESBLOQUEÁVEIS)
# =============================================================================

CONFIGURACOES_GAMEPLAY: dict[str, ConfiguracaoDef] = {
    # 1. Limite de Quadros (Performance)
    "fps_cap": ConfiguracaoDef(
        id="fps_cap",
        nome="Limite de Quadros",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="ilimitado",
        ordem=1,
        opcoes={
            "ilimitado": OpcaoConfig(
                id="ilimitado",
                label="Ilimitado",
                modificadores={},
                flavor_text="O olho humano não consegue ver além de 30 FPS.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "45": OpcaoConfig(
                id="45",
                label="45 FPS",
                modificadores={"dano_inimigos_mult": 0.85, "fps_stutter_dodge": True},
                flavor_text="Os inimigos também estão perdendo frames.",
                nerf_text="Fluidez reduzida a 45 FPS",
                buff_text="Dano recebido de inimigos reduzido em 15% (x0.85) e micro-congelamentos de esquiva (stutter dodge)"
            ),
            "30": OpcaoConfig(
                id="30",
                label="30 FPS",
                modificadores={"vel_inimigos_mult": 0.90, "fps_stutter_dodge": True},
                flavor_text="Só é lag se você estiver perdendo.",
                nerf_text="Fluidez reduzida a 30 FPS",
                buff_text="Velocidade dos inimigos -10% e micro-congelamentos de esquiva (stutter dodge)"
            ),
            "15": OpcaoConfig(
                id="15",
                label="15 FPS",
                modificadores={"dano_inimigos_mult": 0.7225, "vel_inimigos_mult": 0.81, "fps_stutter_dodge": True},
                flavor_text="Cada frame foi desenhado à mão por monges tibetanos.",
                nerf_text="Experiência quase injogável",
                buff_text="Dano de inimigos -27.75% (x0.7225), velocidade -19% (x0.81) e micro-congelamentos de esquiva (stutter dodge)"
            ),
        }
    ),

    # 2. Qualidade Gráfica (Performance)
    "graficos_qualidade": ConfiguracaoDef(
        id="graficos_qualidade",
        nome="Qualidade Gráfica",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="alta",
        ordem=2,
        opcoes={
            "alta": OpcaoConfig(
                id="alta",
                label="Alta",
                modificadores={},
                flavor_text="Tudo bonito enquanto a placa aguenta.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "baixa": OpcaoConfig(
                id="baixa",
                label="Baixa",
                modificadores={"hp_inimigos_mult": 0.80, "graficos_shrapnel": True},
                flavor_text="O verdadeiro modo batata.",
                nerf_text="Cenário e partículas simplificados",
                buff_text="-20% de vida nos inimigos e estilhaços perfurantes ao abatê-los",
                incompativel_com=[("modo_wireframe", "ligado")],
            ),
        }
    ),

    # 3. Resolução da Tela (Performance)
    "resolucao": ConfiguracaoDef(
        id="resolucao",
        nome="Resolução da Tela",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="100%",
        ordem=3,
        opcoes={
            "100%": OpcaoConfig(
                id="100%",
                label="1280x720 (100%)",
                modificadores={},
                flavor_text="Cada pixel em seu devido lugar.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "75%": OpcaoConfig(
                id="75%",
                label="960x540 (75%)",
                modificadores={"drop_chance_bonus": 0.10, "resolucao_chunky_hitbox": 1.25},
                flavor_text="Menos pixels na tela, mais caixas no chão.",
                nerf_text="Visão levemente pixelada",
                buff_text="Drop de itens +10% e área de impacto dos tiros aumentada em +25%"
            ),
            "50%": OpcaoConfig(
                id="50%",
                label="640x360 (50%)",
                modificadores={"drop_chance_bonus": 0.25, "resolucao_chunky_hitbox": 1.50},
                flavor_text="Lembranças de uma época de monitores CRT.",
                nerf_text="Visão consideravelmente pixelada",
                buff_text="Drop de itens +25% e área de impacto dos tiros aumentada em +50%"
            ),
            "25%": OpcaoConfig(
                id="25%",
                label="320x180 (25%)",
                modificadores={"drop_chance_bonus": 0.50, "resolucao_chunky_hitbox": 2.00},
                flavor_text="Se você consegue contar os pixels nos dedos, está economizando processamento.",
                nerf_text="Praticamente indecifrável",
                buff_text="Drop de itens +50% e área de impacto dos tiros dobrada (x2.0)"
            ),
        }
    ),

    # 4. Sincronização Vertical (Performance)
    "vsync": ConfiguracaoDef(
        id="vsync",
        nome="Sincronização Vertical",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=4,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={},
                flavor_text="Sem cortes na tela.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={"vsync_tear_refraction": True, "vsync_cadencia_contra_varredura": 1.15},
                flavor_text="Monitor sem sincronia. A imagem rasga, e as trajetórias rasgam junto.",
                nerf_text="Rasgo de quadro real em bandas horizontais distorcendo mira e projéteis",
                buff_text="Seus tiros que cruzam o rasgo dividem-se em 2; tiros inimigos sofrem desvio; +15% cadência contra a varredura"
            ),
        }
    ),

    # 5. Tremor de Tela (Performance / Visual)
    "screen_shake": ConfiguracaoDef(
        id="screen_shake",
        nome="Tremor de Tela",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=5,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Câmera firme no tripé.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"dano_explosivos_mult": 1.20, "screen_shake_stagger": True},
                flavor_text="A tela treme. A sua mira também.",
                nerf_text="A tela treme em disparos pesados, explosões e dano",
                buff_text="+20% de dano explosivo e impactos de tiros e bombas empurram e desaceleram inimigos"
            ),
        }
    ),

    # 6. Desfoque de Movimento (Performance / Visual)
    "motion_blur": ConfiguracaoDef(
        id="motion_blur",
        nome="Desfoque de Movimento",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=6,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Imagem limpa em movimento.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"vel_jogador_mult": 1.15, "motion_blur_ghosting": True},
                flavor_text="Parece que passaram vaselina na lente.",
                nerf_text="Rastro visual borra a tela em movimento",
                buff_text="+15% de velocidade e +0.40s de i-frames após sofrer dano"
            ),
        }
    ),

    # 7. Exibição de Interface (Interface)
    "hud": ConfiguracaoDef(
        id="hud",
        nome="Exibição de Interface",
        categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=7,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={},
                flavor_text="Barras de vida, experiência, inventário e cronômetro visíveis.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={"xp_ganho_mult": 1.25, "hud_pulse_magnet": True},
                flavor_text="Com certeza você ainda tem vida sobrando. Provavelmente.",
                nerf_text="Oculta completamente HP, XP, inventário e timer",
                buff_text="XP +25% e pulso magnético a cada 4s que puxa todos os drops do mapa até você"
            ),
        }
    ),

    # 8. Números de Dano (Interface)
    "damage_numbers": ConfiguracaoDef(
        id="damage_numbers",
        nome="Números de Dano",
        categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=8,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Inimigos sofrem dano em silêncio.",
                nerf_text="Nenhum (acertos críticos desabilitados)",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"critico_chance": 0.25, "critico_mult": 2.0, "damage_numbers_knockback": True},
                flavor_text="Finalmente uma aplicação prática para aritmética básica.",
                nerf_text="Poluição visual com números flutuando",
                buff_text="Habilita Críticos (+25% chance) e os números flutuantes empurram os inimigos para trás"
            ),
        }
    ),

    # 9. Nível de Zoom (Interface)
    "zoom": ConfiguracaoDef(
        id="zoom",
        nome="Nível de Zoom",
        categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="100%",
        ordem=9,
        opcoes={
            "75%": OpcaoConfig(
                id="75%",
                label="75% (Zoom Out)",
                modificadores={"zoom_balistica_longa": True, "zoom_queima_roupa_mult": 0.85},
                flavor_text="Mire de longe; tiros à queima-roupa perdem força.",
                nerf_text="FOV ampliado, sprites menores, inimigos detectam de longe e -15% de dano à queima-roupa",
                buff_text="Balística Longa: projéteis escalam dano pela distância (até +45%) e ganham +1 perfuração em longa distância"
            ),
            "100%": OpcaoConfig(
                id="100%",
                label="100%",
                modificadores={},
                flavor_text="Campo de visão padrão e equilibrado.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "125%": OpcaoConfig(
                id="125%",
                label="125% (Zoom In)",
                modificadores={"zoom_execucao_cd_red": 0.5},
                flavor_text="Olho no olho. Cada abate encurta sua próxima esquiva.",
                nerf_text="Campo periférico severamente reduzido (flancos cegos)",
                buff_text="Execução Próxima: abates reduzem cooldown de Dash/Parry em -0,5s"
            ),
            "150%": OpcaoConfig(
                id="150%",
                label="150% (Zoom In)",
                modificadores={"zoom_execucao_cd_red": 1.0, "zoom_execucao_limiar_hp": 0.20},
                flavor_text="Quem entra no seu foco não sai inteiro.",
                nerf_text="Visão extremamente restrita do mapa",
                buff_text="Execução Próxima Máxima: abates reduzem cooldown de Dash/Parry em -1,0s e executam comuns abaixo de 20% HP"
            ),
        }
    ),

    # 10. Movimento pelo Mouse (Controles)
    "movimento_mouse": ConfiguracaoDef(
        id="movimento_mouse",
        nome="Movimento pelo Mouse",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=10,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Controle manual com pés firmes nas teclas.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"drop_chance_mult": 1.40, "movimento_ram_collision": True},
                flavor_text="Para que servem as pernas quando o destino tem um cursor?",
                nerf_text="A batata caminha incessantemente na direção do cursor",
                buff_text="Drop de itens +40% e andar continuamente te faz atropelar e empurrar inimigos",
                incompativel_com=[
                    ("controles_tanque", "ligado"),
                    ("keybinds", "uma_mao"),
                    ("keybinds", "pesadelo"),
                ],
            ),
        }
    ),

    # 11. Modificadores de Teclas (Controles)
    "keybinds": ConfiguracaoDef(
        id="keybinds",
        nome="Modificadores de Teclas",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="padrao",
        ordem=11,
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label="Padrão",
                modificadores={},
                flavor_text="Ergonomia convencional para seres humanos normais.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "invertido": OpcaoConfig(
                id="invertido",
                label="Invertido",
                modificadores={"dano_armas_mult": 1.10, "keybinds_overdrive_dash": True},
                flavor_text="Para cima é o novo para baixo.",
                nerf_text="Teclas de movimento invertidas (W: baixo, S: cima, etc.)",
                buff_text="Dano de armas +10% e manobras repentinas geram pulso de empurrão"
            ),
            "arrow_keys": OpcaoConfig(
                id="arrow_keys",
                label="Arrow Keys",
                modificadores={"vel_jogador_mult": 1.15, "keybinds_overdrive_dash": True},
                flavor_text="Lembranças dolorosas de jogar no teclado de 1998.",
                nerf_text="Movimento transferido exclusivamente para as setas direcionais",
                buff_text="Velocidade da batata +15% e manobras repentinas geram pulso de empurrão"
            ),
            "uma_mao": OpcaoConfig(
                id="uma_mao",
                label="Uma Mão Só",
                modificadores={"xp_ganho_mult": 1.20, "keybinds_overdrive_dash": True},
                flavor_text="Uma mão no volante, a outra no carinho.",
                nerf_text="Movimentação em QWER, ações 100% no teclado (sem mouse)",
                buff_text="Ganho de XP +20% e manobras repentinas geram pulso de empurrão",
                incompativel_com=[
                    ("movimento_mouse", "ligado"),
                    ("controles_tanque", "ligado"),
                ],
            ),
            "pesadelo": OpcaoConfig(
                id="pesadelo",
                label="Pesadelo",
                modificadores={"dano_armas_mult": 1.30, "keybinds_overdrive_dash": True},
                flavor_text="Sua memória muscular acabou de pedir demissão.",
                nerf_text="Movimento em IJKL com eixo Y do mouse invertido",
                buff_text="Dano de armas +30% e pulso forte de empurrão ao desviar",
                incompativel_com=[
                    ("movimento_mouse", "ligado"),
                ],
            ),
        }
    ),

    # 12. Suavização de Câmera (Controles / Câmera)
    "suavizacao_camera": ConfiguracaoDef(
        id="suavizacao_camera",
        nome="Suavização de Câmera",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=12,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={},
                flavor_text="Transições suaves para evitar tontura.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={"camera_hard_kick": True, "flick_shot_ativo": True},
                flavor_text="Sem amortecedor. Giros secos viram disparos cirúrgicos.",
                nerf_text="Tranco Seco (Hard Kick): câmera sem amortecimento aplica coice a cada tiro, dash ou impacto",
                buff_text="Flick-Shot de Precisão: após giro rápido (>45°) ou parada, próximo tiro sai 2x vel., +1 perfuração e +35% dano"
            ),
        }
    ),

    # 13. Disparo Automático (Controles / Combate)
    "auto_fire": ConfiguracaoDef(
        id="auto_fire",
        nome="Disparo Automático",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=13,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={},
                flavor_text="Segure o botão e reze.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={"dano_armas_mult": 1.15, "auto_fire_burst": True},
                flavor_text="Cada clique do mouse foi pago com o suor do seu dedo indicador.",
                nerf_text="Necessário clicar manualmente a cada disparo",
                buff_text="Dano +15% e cada clique manual dispara rajada dupla (2 tiros rápidos)"
            ),
        }
    ),

    # 14. Inimigos à Distância (Dificuldade)
    "inimigos_ranged": ConfiguracaoDef(
        id="inimigos_ranged",
        nome="Inimigos à Distância",
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=14,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Por enquanto eles só sabem correr atrás de você.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"loot_enriquecido": True, "inimigos_ranged_bullet_hell": True},
                flavor_text="Mais projéteis teleguiados vindo na sua cara significam mais combustível para contra-atacar.",
                nerf_text="Dobro de Projetores Laser disparando projéteis teleguiados não-parriáveis",
                buff_text="Combustível de Bullet-Hell: loot enriquecido e Parry/Just-Dodge reduz CD e sobrecarrega o próximo tiro"
            ),
        }
    ),

    # 15. Captura de Drops por Inimigos (Dificuldade)
    "coleta_inimiga": ConfiguracaoDef(
        id="coleta_inimiga",
        nome="Captura de Drops por Inimigos",
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=15,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Raposo, não pegue.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"drops_valor_mult": 2.0, "coleta_inimiga": True},
                flavor_text="Achado não é roubado.",
                nerf_text="Inimigos roubam itens que ficarem mais de 10s no chão",
                buff_text="Todos os drops coletados por você valem o dobro (2x XP e cura)"
            ),
        }
    ),

    # 16. Velocidade dos Inimigos (Dificuldade)
    "velocidade_inimigos": ConfiguracaoDef(
        id="velocidade_inimigos",
        nome="Velocidade dos Inimigos",
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="normal",
        ordem=16,
        opcoes={
            "normal": OpcaoConfig(
                id="normal",
                label="Normal",
                modificadores={},
                flavor_text="Ritmo normal de segunda-feira.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "+25%": OpcaoConfig(
                id="+25%",
                label="+25% Velocidade",
                modificadores={"vel_inimigos_mult": 1.25, "xp_ganho_mult": 1.15, "inercia_cinetica_nivel": 1},
                flavor_text="Mais rápidos para correr, mais pesados para bater nos colegas.",
                nerf_text="Inimigos +25% mais rápidos",
                buff_text="Inércia Cinética: +15% XP e inimigos empurrados derrapam e colidem entre si"
            ),
            "+50%": OpcaoConfig(
                id="+50%",
                label="+50% Velocidade",
                modificadores={"vel_inimigos_mult": 1.50, "xp_ganho_mult": 1.30, "inercia_cinetica_nivel": 2},
                flavor_text="Um único empurrão transforma a horda em strike.",
                nerf_text="Inimigos +50% mais rápidos",
                buff_text="Inércia Cinética Máxima: +30% XP e colisões em cadeia de pinos com maior alcance e impacto"
            ),
        }
    ),

    # 17. Vida dos Inimigos (Dificuldade)
    "vida_inimigos": ConfiguracaoDef(
        id="vida_inimigos",
        nome="Vida dos Inimigos",
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="normal",
        ordem=17,
        opcoes={
            "normal": OpcaoConfig(
                id="normal",
                label="Normal",
                modificadores={},
                flavor_text="Carcaça padrão de plástico.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "+50%": OpcaoConfig(
                id="+50%",
                label="+50% HP",
                modificadores={"hp_inimigos_mult": 1.50, "pinhata_hardware_nivel": 1},
                flavor_text="Carcaça grossa demais, mas solta peças úteis a cada pancada.",
                nerf_text="Inimigos com +50% de vida",
                buff_text="Pinhata de Hardware: a cada 33% de HP perdido libera micro-sucata (munição Slot 3, carga ou XP)"
            ),
            "+100%": OpcaoConfig(
                id="+100%",
                label="+100% HP",
                modificadores={"hp_inimigos_mult": 2.00, "pinhata_hardware_nivel": 2, "drop_chance_bonus": 0.15},
                flavor_text="Quanto mais apanham, mais munição derrubam no chão.",
                nerf_text="Inimigos com o dobro de vida (+100%)",
                buff_text="Pinhata de Hardware Pesada: micro-sucata dobrada a cada 33% de HP perdido + 15% bônus de drop"
            ),
        }
    ),

    # 18. Iluminação Dinâmica (Experimental / Atmosfera)
    "iluminacao": ConfiguracaoDef(
        id="iluminacao",
        nome="Iluminação Dinâmica",
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=18,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Luz acesa o tempo todo.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"clarao_fotossensivel": True},
                flavor_text="No breu total, o primeiro clarão cega quem saiu das sombras.",
                nerf_text="Escuridão densa fora do halo/cone de luz da batata",
                buff_text="Clarão Fotossensível: inimigos revelados da escuridão sofrem Crítico Garantido + micro-atordoamento (0,35s)"
            ),
        }
    ),

    # 19. Cores Invertidas (Experimental / Visual)
    "cores_invertidas": ConfiguracaoDef(
        id="cores_invertidas",
        nome="Cores Invertidas",
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=19,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Cores normais de fábrica.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"polaridade_invertida": True},
                flavor_text="O que antes bloqueava tiros agora atrai o estrago.",
                nerf_text="Inversão total de RGB da tela",
                buff_text="Polaridade Invertida: +40% dano em blindados e surto de velocidade/dano por 2s ao sofrer slow ou graze"
            ),
        }
    ),

    # 20. Fogo Amigo (Experimental / Risco Extremo)
    "fogo_amigo": ConfiguracaoDef(
        id="fogo_amigo",
        nome="Fogo Amigo",
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=20,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Seus tiros sabem quem é o dono.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"dano_armas_mult": 1.25, "auto_dano": True, "fogo_amigo_rocket_jump": True},
                flavor_text="A boa notícia é que dá o dobro de dano. A má é que você também apanha dos seus tiros.",
                nerf_text="Seus tiros e explosões causam dano a você e aos seus drones",
                buff_text="+25% de dano e explosões impulsionam a batata (rocket-jump)"
            ),
        }
    ),

    # 21. Calibragem de Parry (Precisão vs Poder)
    "precisao_parry": ConfiguracaoDef(
        id="precisao_parry",
        nome="Calibragem de Parry",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=21,
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label="Padrão",
                modificadores={},
                flavor_text="Chave de manutenção calibrada de fábrica.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "cirurgico": OpcaoConfig(
                id="cirurgico",
                label="Cirúrgico",
                modificadores={"parry_precisao": "cirurgico"},
                flavor_text="Janela minúscula, impacto absurdo.",
                nerf_text="Arco 65°, janela 0.09s e alcance 0.85x",
                buff_text="+75% dano refletido e explosão de 140px"
            ),
            "amplificado": OpcaoConfig(
                id="amplificado",
                label="Amplificado",
                modificadores={"parry_precisao": "amplificado"},
                flavor_text="Mais fácil de acertar, menos letal.",
                nerf_text="-30% dano refletido e +0.25s cooldown melee",
                buff_text="Arco 135°, janela 0.17s e alcance 1.25x"
            ),
            "postura_riposte": OpcaoConfig(
                id="postura_riposte",
                label="Postura Riposte",
                modificadores={"parry_precisao": "postura_riposte"},
                flavor_text="Fique firme; se algo te tocar, devolva atravessando tudo.",
                nerf_text="Enraíza Cleiton no lugar por 0,45s",
                buff_text="Invulnerabilidade total na postura + estocada perfurante que atordoa por 1,5s ao aparar",
                desbloqueada_por="opcao_config:precisao_parry:postura_riposte",
            ),
        }
    ),

    # 22. Protocolo de Reflexão (Efeito do Parry)
    "efeito_parry": ConfiguracaoDef(
        id="efeito_parry",
        nome="Protocolo de Reflexão",
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=22,
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label="Padrão",
                modificadores={},
                flavor_text="Reflexão explosiva padrão.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "estilhaco": OpcaoConfig(
                id="estilhaco",
                label="Estilhaço",
                modificadores={"parry_efeito": "estilhaco"},
                flavor_text="Estilhaça projéteis rebatidos em 3 dardos perfurantes.",
                nerf_text="-25% dano por fragmento e sem explosão AoE",
                buff_text="Projéteis refletidos dividem-se em 3 tiros perfurantes"
            ),
            "pulso_emp": OpcaoConfig(
                id="pulso_emp",
                label="Pulso EMP",
                modificadores={"parry_efeito": "pulso_emp"},
                flavor_text="O parry libera um pulso eletromagnético atordoante.",
                nerf_text="Errar o parry aumenta Exposto para +45% de dano recebido",
                buff_text="Parry bem-sucedido atordoa inimigos próximos por 1.2s"
            ),
            "firewall_estatico": OpcaoConfig(
                id="firewall_estatico",
                label="Firewall Estático",
                modificadores={"parry_efeito": "firewall_estatico"},
                flavor_text="Nada devolvido, nada passa.",
                nerf_text="Não reflete projéteis e cooldown alto (~5,0s-6,0s)",
                buff_text="Ergue parede energética fixa por 2,5s destruindo projéteis inimigos"
            ),
            "ventoinha_360": OpcaoConfig(
                id="ventoinha_360",
                label="Ventoinha 360°",
                modificadores={"parry_efeito": "ventoinha_360"},
                flavor_text="Cooler em rotação máxima fatiando tudo ao redor.",
                nerf_text="Alcance 0,75x e cooldown bem alto (~6,0s-8,0s)",
                buff_text="Giro 360° por 0,6s pulverizando projéteis e aplicando dois cortes circulares"
            ),
        }
    ),

    # 23. Controles de Tanque (Blindagem & Artilharia)
    "controles_tanque": ConfiguracaoDef(
        id="controles_tanque",
        nome="Controles de Tanque",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=23,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Movimento omnidirecional padrão.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"controles_tanque": True, "dano_armas_mult": 1.35, "dano_recebido_mult": 0.80},
                flavor_text="A/D rotacionam a seta; W/S aceleram ou dão ré.",
                nerf_text="Sem strafe lateral (direção controlada por rotação)",
                buff_text="250 HP máx, -20% dano recebido, +35% dano, +1 perfuração, +20% cadência parado e atropelamento frontal",
                incompativel_com=[
                    ("movimento_mouse", "ligado"),
                    ("keybinds", "uma_mao"),
                ],
            ),
        }
    ),

    # 24. Protocolo de Dash (Controles — Requer habilidade:dash)
    "dash_protocolo": ConfiguracaoDef(
        id="dash_protocolo",
        nome="Protocolo de Dash",
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=24,
        requer_desbloqueio=("habilidade", "dash"),
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label="Padrão",
                modificadores={},
                flavor_text="Propulsão direcional calibrada.",
                nerf_text="Nenhum",
                buff_text="Nenhum",
            ),
            "teleporte_buffer": OpcaoConfig(
                id="teleporte_buffer",
                label="Blink de Memória",
                modificadores={"dash_protocolo": "teleporte_buffer"},
                flavor_text="Pula os frames do trajeto e frita quem ficou no meio.",
                nerf_text="+0,6s cooldown, sem controle fino no trajeto e micro-stumble na borda",
                buff_text="Teleporte instantâneo deixando linha elétrica que corta inimigos",
            ),
            "propulsor_instavel": OpcaoConfig(
                id="propulsor_instavel",
                label="Propulsor Sem Escudo",
                modificadores={"dash_protocolo": "propulsor_instavel"},
                flavor_text="Sem proteção, mas com o dobro de fôlego.",
                nerf_text="Remove totalmente os i-frames de invulnerabilidade do Dash",
                buff_text="2 cargas de Dash com recarga 35% mais rápida",
            ),
            "sombra_espelho": OpcaoConfig(
                id="sombra_espelho",
                label="Sombra Espelho",
                modificadores={"dash_protocolo": "sombra_espelho"},
                flavor_text="Um processo espelho atacando do outro ângulo.",
                nerf_text="No 1º toque Cleiton não se move; projeta sombra por 3,5s (2º toque troca posição)",
                buff_text="Sombra replica disparos e parries (~55% dano) na direção da mira",
                desbloqueada_por="opcao_config:dash_protocolo:sombra_espelho",
            ),
            "rollback_estado": OpcaoConfig(
                id="rollback_estado",
                label="Rollback de Estado",
                modificadores={"dash_protocolo": "rollback_estado"},
                flavor_text="Ctrl+Z no próprio corpo.",
                nerf_text="Direção fixa para o passado + cooldown alto",
                buff_text="Teleporta ao snapshot de 3s atrás, recupera parte do HP perdido e detona onda de choque",
                desbloqueada_por="opcao_config:dash_protocolo:rollback_estado",
            ),
        },
    ),

    # 25. Rastro de Dash (Experimental — Requer habilidade:dash)
    "dash_rastro": ConfiguracaoDef(
        id="dash_rastro",
        nome="Rastro de Dash",
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=25,
        requer_desbloqueio=("habilidade", "dash"),
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label="Padrão",
                modificadores={},
                flavor_text="Rastro padrão sem efeitos colaterais.",
                nerf_text="Nenhum",
                buff_text="Nenhum",
            ),
            "exaustao_termica": OpcaoConfig(
                id="exaustao_termica",
                label="Exaustão Térmica",
                modificadores={"dash_rastro": "exaustao_termica"},
                flavor_text="Escape quente demais que cozinha quem persegue.",
                nerf_text="Arma superaquece após o Dash (-25% cadência por 1,2s)",
                buff_text="Deixa trilha incandescente por 3,5s que queima e aplica +25% vulnerabilidade",
            ),
            "vacuo_io": OpcaoConfig(
                id="vacuo_io",
                label="Vácuo de I/O",
                modificadores={"dash_rastro": "vacuo_io"},
                flavor_text="Curto no alcance, mas junta toda a horda num ponto só.",
                nerf_text="Alcance do Dash reduzido em -25%",
                buff_text="Cria vórtice no ponto final que puxa drops e agrupa inimigos",
            ),
            "subprocesso_atrasado": OpcaoConfig(
                id="subprocesso_atrasado",
                label="Subprocesso Atrasado",
                modificadores={"dash_rastro": "subprocesso_atrasado"},
                flavor_text="O processo pai atravessa atrasado paralisando a fila.",
                nerf_text="Alcance -15% e cooldown +0,4s",
                buff_text="Fantasma dispara após 0,75s causando dano e atordoamento (1,1s) na linha",
            ),
            "thread_fantasma": OpcaoConfig(
                id="thread_fantasma",
                label="Thread Fantasma",
                modificadores={"dash_rastro": "thread_fantasma"},
                flavor_text="Isca de hardware pronta para estourar.",
                nerf_text="Cooldown do Dash +40%",
                buff_text="Deixa Clone Holográfico por 2,5s que atrai agro e explode ao ser destruído",
                desbloqueada_por="opcao_config:dash_rastro:thread_fantasma",
            ),
        },
    ),

    # 26. Garbage Collector (Performance)
    "garbage_collector": ConfiguracaoDef(
        id="garbage_collector",
        nome="Garbage Collector",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=26,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Memória gerenciada de forma contínua.",
                nerf_text="Nenhum",
                buff_text="Nenhum",
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"garbage_collector": True},
                flavor_text="Stop-the-World — O coletor trava sua arma, mas limpa o lixo balístico da sala.",
                nerf_text="Barra de RAM enche em ~12s e trava disparos por ~0,8s",
                buff_text="Apaga projéteis inimigos próximos e concede +40% cadência por 4s + munição Slot 3",
            ),
        },
    ),

    # 27. Latência Simulada (Experimental — Exclusiva de Conquista)
    "latencia_ping": ConfiguracaoDef(
        id="latencia_ping",
        nome="Latência Simulada",
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=27,
        exclusiva_conquista=True,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Conexão local 0 ms.",
                nerf_text="Nenhum",
                buff_text="Nenhum",
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"latencia_ping": True},
                flavor_text="Ping 80ms — Você já saiu daqui no servidor, e seu tiro chegou duas vezes.",
                nerf_text="Atraso real de input de ~80ms aplicado a todas as ações (disparo, melee, Parry e Dash)",
                buff_text="Dessincronia de hitbox e eco de pacote (+30% dano após 0,3s ignorando blindagem)",
            ),
        },
    ),

    # 28. Modo Wireframe (Performance)
    "modo_wireframe": ConfiguracaoDef(
        id="modo_wireframe",
        nome="Modo Wireframe",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=28,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={},
                flavor_text="Renderização completa com sprites.",
                nerf_text="Nenhum",
                buff_text="Nenhum",
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"modo_wireframe": True},
                flavor_text="Sem texturas, só geometria e pontos de ruptura.",
                nerf_text="Renderização em contornos técnicos minimalistas + grade de debug",
                buff_text="Nós Vulneráveis: acertar o ângulo exposto causa dano verdadeiro e espalha vulnerabilidade",
                incompativel_com=[("graficos_qualidade", "baixa")],
            ),
        },
    ),
}


# =============================================================================
# CATÁLOGO DE CONFIGURAÇÕES DE SISTEMA (3 ITENS SEMPRE DISPONÍVEIS — SEM BUFFS)
# =============================================================================

# S1-S3: 3 Configurações canônicas de Sistema (SSOT: CONFIGURACOES.md)
CONFIGURACOES_SISTEMA: dict[str, ConfiguracaoDef] = {
    # S1. Volume Geral
    "volume_master": ConfiguracaoDef(
        id="volume_master",
        nome="Volume Geral",
        categoria=CategoriaConfig.SISTEMA,
        tipo=TipoControleConfig.SLIDER,
        valor_padrao=100,
        is_gameplay=False,
        ordem=101,
        descricao_sistema="Controla o volume geral de toda a aplicação (0% a 100%)."
    ),

    # S2. Volume da Música
    "volume_musica": ConfiguracaoDef(
        id="volume_musica",
        nome="Volume da Música",
        categoria=CategoriaConfig.SISTEMA,
        tipo=TipoControleConfig.SLIDER,
        valor_padrao=100,
        is_gameplay=False,
        ordem=102,
        descricao_sistema="Controla a trilha sonora 8-bit em loop (0% a 100%)."
    ),

    # S3. Volume dos Efeitos
    "volume_sfx": ConfiguracaoDef(
        id="volume_sfx",
        nome="Volume dos Efeitos",
        categoria=CategoriaConfig.SISTEMA,
        tipo=TipoControleConfig.SLIDER,
        valor_padrao=100,
        is_gameplay=False,
        ordem=103,
        descricao_sistema="Controla tiros, explosões, pickups e menus (0% a 100%)."
    ),
}

# Dicionário consolidado com as configurações (31 no total: 28 gameplay + 3 sistema)
TODAS_CONFIGURACOES: dict[str, ConfiguracaoDef] = {
    **CONFIGURACOES_GAMEPLAY,
    **CONFIGURACOES_SISTEMA
}
