"""
Catálogo e Definições de Dados do Sistema de Configurações — Protocolo: Batata
SSOT: CONFIGURACOES.md
Define todas as 20 configurações de gameplay desbloqueáveis e as 3 configurações de sistema (23 no total).
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


# =============================================================================
# CATÁLOGO DE CONFIGURAÇÕES DE GAMEPLAY (20 ITENS DESBLOQUEÁVEIS)
# =============================================================================

CONFIGURACOES_GAMEPLAY: dict[str, ConfiguracaoDef] = {
    # 1. Limite de Quadros (Performance)
    "fps_cap": ConfiguracaoDef(
        id="fps_cap",
        nome="Limite de Quadros",
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="60",
        ordem=1,
        opcoes={
            "60": OpcaoConfig(
                id="60",
                label="60 FPS",
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
                flavor_text="Sprites nítidos para quem aprecia os pequenos detalhes.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "baixa": OpcaoConfig(
                id="baixa",
                label="Baixa",
                modificadores={"hp_inimigos_mult": 0.80, "graficos_shrapnel": True},
                flavor_text="Texturas são um luxo que o departamento financeiro cortou.",
                nerf_text="Sprites e partículas simplificados.",
                buff_text="HP de inimigos -20% e inimigos mortos estilhaçam em polígonos que furam outros alvos"
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
                flavor_text="Estabilidade garantida para monitores sensíveis.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label="Desligado",
                modificadores={"vel_jogador_mult": 1.10, "vsync_tear_refraction": True},
                flavor_text="Espero que seu monitor tenha FreeSync.",
                nerf_text="Possível quebra de linha visual (screen tearing)",
                buff_text="Velocidade +10% e projéteis que cruzam a linha de rasgo se duplicam em dois"
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
                flavor_text="Uma experiência suave.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"dano_explosivos_mult": 1.20, "screen_shake_stagger": True},
                flavor_text="A tela treme. A sua mira também.",
                nerf_text="A tela treme violentamente a cada disparo pesado, explosão e dano",
                buff_text="Dano explosivo +20% e ondas de choque de tiros e bombas causam tropeço e lentidão em área"
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
                flavor_text="Uma experiência suave.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"vel_jogador_mult": 1.15, "motion_blur_ghosting": True},
                flavor_text="Você se move tão rápido que até seus pixels ficaram para trás.",
                nerf_text="Rastro visual (ghosting) borra elementos em movimento",
                buff_text="Velocidade de movimento aumentada em +15% (x1.15) e rastro fantasmagórico concede +0.40s de i-frames"
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
                modificadores={"hitbox_projeteis_mult": 1.50},
                flavor_text="Aquilo é uma batata ou uma formiga armada?",
                nerf_text="Câmera mais distante, sprites menores",
                buff_text="Tamanho da hitbox de todos os projéteis aumentado em +50% (x1.50)"
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
                modificadores={"dano_armas_mult": 1.10},
                flavor_text="Foco total no que está na sua cara.",
                nerf_text="Campo de visão periférico reduzido",
                buff_text="Dano de todas as armas aumentado em +10% (x1.10)"
            ),
            "150%": OpcaoConfig(
                id="150%",
                label="150% (Zoom In)",
                modificadores={"dano_armas_mult": 1.20},
                flavor_text="Você consegue ver de perto os inimigos.",
                nerf_text="Visão extremamente restrita do mapa",
                buff_text="Dano de todas as armas aumentado em +20% (x1.20)"
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
                buff_text="Drop de itens +40% e andar continuamente te faz atropelar e empurrar inimigos"
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
                buff_text="Ganho de XP +20% e manobras repentinas geram pulso de empurrão"
            ),
            "pesadelo": OpcaoConfig(
                id="pesadelo",
                label="Pesadelo",
                modificadores={"dano_armas_mult": 1.30, "keybinds_overdrive_dash": True},
                flavor_text="Sua memória muscular acabou de pedir demissão.",
                nerf_text="Movimento em IJKL com eixo Y do mouse invertido",
                buff_text="Dano de armas +30% e pulso forte de empurrão ao desviar"
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
                modificadores={"vel_jogador_mult": 1.08},
                flavor_text="Estabilização de imagem é cobrada à parte.",
                nerf_text="Câmera trava rigidamente no centro do jogador",
                buff_text="Velocidade de movimento da batata aumentada em +8% (x1.08)"
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
                flavor_text="Inimigos civilizados.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"loot_enriquecido": True},
                flavor_text="Eles finalmente descobriram a tecnologia dos projéteis balísticos.",
                nerf_text="Inimigos com disparos à distância passam a spawnar",
                buff_text="Inimigos Ranged possuem alta chance de caixas de armas"
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
                flavor_text="Os inimigos se sentiram inspirados pelo Gemini 3.7 Flash.",
                nerf_text="Ativa Scavenger: inimigos tentam devorar drops após 10s",
                buff_text="Todos os drops coletados pelo jogador valem 2x (XP e cura em dobro)"
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
                flavor_text="Inimigos marcham normalmente.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "+25%": OpcaoConfig(
                id="+25%",
                label="+25% Velocidade",
                modificadores={"vel_inimigos_mult": 1.25, "xp_ganho_mult": 1.20},
                flavor_text="Eles encontraram o botão turbo.",
                nerf_text="Todos os inimigos se movem 25% mais rápido",
                buff_text="Ganho de XP por abate aumentado em +20% (x1.20)"
            ),
            "+50%": OpcaoConfig(
                id="+50%",
                label="+50% Velocidade",
                modificadores={"vel_inimigos_mult": 1.50, "xp_ganho_mult": 1.40},
                flavor_text="Injetaram energético na corrente de dados.",
                nerf_text="Todos os inimigos correm em disparada (+50%)",
                buff_text="Ganho de XP por abate aumentado em +40% (x1.40)"
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
                flavor_text="Inimigos com vida padrão.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "+50%": OpcaoConfig(
                id="+50%",
                label="+50% HP",
                modificadores={"hp_inimigos_mult": 1.50, "drop_chance_bonus": 0.20},
                flavor_text="Blindagem adicional direto da fábrica.",
                nerf_text="Inimigos possuem 50% a mais de vida",
                buff_text="Chance de drop de itens aumentada em +20%"
            ),
            "+100%": OpcaoConfig(
                id="+100%",
                label="+100% HP",
                modificadores={"hp_inimigos_mult": 2.00, "drop_chance_bonus": 0.40},
                flavor_text="Eles estão mais densos.",
                nerf_text="Inimigos possuem o dobro de vida (+100%)",
                buff_text="Chance de drop de itens aumentada em +40%"
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
                flavor_text="Luz do dia perpétua sobre o campo de batalha.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"dano_fora_visao_mult": 0.50},
                flavor_text="Eles estão com dificuldade de te enxergar.",
                nerf_text="Névoa de escuridão: campo de visão restrito ao redor da batata",
                buff_text="Inimigos fora do cone de visão causam 50% a menos de dano (x0.50)"
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
                flavor_text="Paleta de cores original e aconchegante.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"dano_armas_mult": 1.20},
                flavor_text="Seus olhos registraram uma reclamação no Procon.",
                nerf_text="Inversão total de RGB da tela (estética de negativo)",
                buff_text="Dano global de todas as armas aumentado em +20% (x1.20)"
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
                flavor_text="Seus tiros e explosões atravessam você inofensivamente.",
                nerf_text="Nenhum",
                buff_text="Nenhum"
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label="Ligado",
                modificadores={"dano_armas_mult": 1.25, "auto_dano": True, "fogo_amigo_rocket_jump": True},
                flavor_text="Aparentemente, estilhaços de granada não leem crachá de identificação.",
                nerf_text="Seus próprios tiros e explosões causam dano à batata",
                buff_text="Dano +25% e explosões te arremessam longe, permitindo rocket-jump"
            ),
        }
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

# Dicionário consolidado com as configurações (23 no total)
TODAS_CONFIGURACOES: dict[str, ConfiguracaoDef] = {
    **CONFIGURACOES_GAMEPLAY,
    **CONFIGURACOES_SISTEMA
}
