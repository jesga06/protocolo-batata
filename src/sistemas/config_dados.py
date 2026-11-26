"""
Catálogo e Definições de Dados do Sistema de Configurações — Protocolo: Batata
SSOT: CONFIGURACOES.md
Define todas as 30 configurações de gameplay desbloqueáveis e as 3 configurações de sistema (33 no total).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from src.utils.traducao import t


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
# CATÁLOGO DE CONFIGURAÇÕES DE GAMEPLAY (29 ITENS DESBLOQUEÁVEIS)
# =============================================================================

CONFIGURACOES_GAMEPLAY: dict[str, ConfiguracaoDef] = {
    # 1. Limite de Quadros (Performance)
    "fps_cap": ConfiguracaoDef(
        id="fps_cap",
        nome=t("configs_catalogo", "fps_cap__nome"),
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="ilimitado",
        ordem=1,
        opcoes={
            "ilimitado": OpcaoConfig(
                id="ilimitado",
                label=t("configs_catalogo", "fps_cap__opt_ilimitado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "fps_cap__opt_ilimitado__flavor"),
                nerf_text=t("configs_catalogo", "fps_cap__opt_ilimitado__nerf"),
                buff_text=t("configs_catalogo", "fps_cap__opt_ilimitado__buff")
            ),
            "45": OpcaoConfig(
                id="45",
                label=t("configs_catalogo", "fps_cap__opt_45__label"),
                modificadores={"dano_inimigos_mult": 0.85, "fps_stutter_dodge": True},
                flavor_text=t("configs_catalogo", "fps_cap__opt_45__flavor"),
                nerf_text=t("configs_catalogo", "fps_cap__opt_45__nerf"),
                buff_text=t("configs_catalogo", "fps_cap__opt_45__buff")
            ),
            "30": OpcaoConfig(
                id="30",
                label=t("configs_catalogo", "fps_cap__opt_30__label"),
                modificadores={"vel_inimigos_mult": 0.90, "fps_stutter_dodge": True},
                flavor_text=t("configs_catalogo", "fps_cap__opt_30__flavor"),
                nerf_text=t("configs_catalogo", "fps_cap__opt_30__nerf"),
                buff_text=t("configs_catalogo", "fps_cap__opt_30__buff")
            ),
            "15": OpcaoConfig(
                id="15",
                label=t("configs_catalogo", "fps_cap__opt_15__label"),
                modificadores={"dano_inimigos_mult": 0.7225, "vel_inimigos_mult": 0.81, "fps_stutter_dodge": True},
                flavor_text=t("configs_catalogo", "fps_cap__opt_15__flavor"),
                nerf_text=t("configs_catalogo", "fps_cap__opt_15__nerf"),
                buff_text=t("configs_catalogo", "fps_cap__opt_15__buff")
            ),
        }
    ),

    # 2. Qualidade Gráfica (Performance)
    "graficos_qualidade": ConfiguracaoDef(
        id="graficos_qualidade",
        nome=t("configs_catalogo", "graficos_qualidade__nome"),
                categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="alta",
        ordem=2,
        opcoes={
            "alta": OpcaoConfig(
                id="alta",
                label=t("configs_catalogo", "graficos_qualidade__opt_alta__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "graficos_qualidade__opt_alta__flavor"),
                nerf_text=t("configs_catalogo", "graficos_qualidade__opt_alta__nerf"),
                buff_text=t("configs_catalogo", "graficos_qualidade__opt_alta__buff")
            ),
            "baixa": OpcaoConfig(
                id="baixa",
                label=t("configs_catalogo", "graficos_qualidade__opt_baixa__label"),
                modificadores={"hp_inimigos_mult": 0.80, "graficos_shrapnel": True},
                flavor_text=t("configs_catalogo", "graficos_qualidade__opt_baixa__flavor"),
                nerf_text=t("configs_catalogo", "graficos_qualidade__opt_baixa__nerf"),
                buff_text=t("configs_catalogo", "graficos_qualidade__opt_baixa__buff"),
                incompativel_com=[("modo_wireframe", "ligado")],
            ),
        }
    ),

    # 3. Resolução da Tela (Performance)
    "resolucao": ConfiguracaoDef(
        id="resolucao",
        nome=t("configs_catalogo", "resolucao__nome"),
                categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="100%",
        ordem=3,
        opcoes={
            "100%": OpcaoConfig(
                id="100%",
                label=t("configs_catalogo", "resolucao__opt_100%__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "resolucao__opt_100%__flavor"),
                nerf_text=t("configs_catalogo", "resolucao__opt_100%__nerf"),
                buff_text=t("configs_catalogo", "resolucao__opt_100%__buff")
            ),
            "75%": OpcaoConfig(
                id="75%",
                label=t("configs_catalogo", "resolucao__opt_75%__label"),
                modificadores={"drop_chance_bonus": 0.10, "resolucao_chunky_hitbox": 1.25},
                flavor_text=t("configs_catalogo", "resolucao__opt_75%__flavor"),
                nerf_text=t("configs_catalogo", "resolucao__opt_75%__nerf"),
                buff_text=t("configs_catalogo", "resolucao__opt_75%__buff")            ),
            "50%": OpcaoConfig(
                id="50%",
                label=t("configs_catalogo", "resolucao__opt_50%__label"),
                modificadores={"drop_chance_bonus": 0.25, "resolucao_chunky_hitbox": 1.50},
                flavor_text=t("configs_catalogo", "resolucao__opt_50%__flavor"),
                nerf_text=t("configs_catalogo", "resolucao__opt_50%__nerf"),
                buff_text=t("configs_catalogo", "resolucao__opt_50%__buff")            ),
            "25%": OpcaoConfig(
                id="25%",
                label=t("configs_catalogo", "resolucao__opt_25%__label"),
                modificadores={"drop_chance_bonus": 0.50, "resolucao_chunky_hitbox": 2.00},
                flavor_text=t("configs_catalogo", "resolucao__opt_25%__flavor"),
                nerf_text=t("configs_catalogo", "resolucao__opt_25%__nerf"),
                buff_text=t("configs_catalogo", "resolucao__opt_25%__buff")            ),
        }
    ),

    # 4. Sincronização Vertical (Performance)
    "vsync": ConfiguracaoDef(
        id="vsync",
        nome=t("configs_catalogo", "vsync__nome"),
                categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=4,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "vsync__opt_ligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "vsync__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "vsync__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "vsync__opt_ligado__buff")
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "vsync__opt_desligado__label"),
                modificadores={"vsync_tear_refraction": True, "vsync_cadencia_contra_varredura": 1.15},
                flavor_text=t("configs_catalogo", "vsync__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "vsync__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "vsync__opt_desligado__buff")            ),
        }
    ),

    # 5. Tremor de Tela (Performance / Visual)
    "screen_shake": ConfiguracaoDef(
        id="screen_shake",
        nome=t("configs_catalogo", "screen_shake__nome"),
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=5,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "screen_shake__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "screen_shake__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "screen_shake__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "screen_shake__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "screen_shake__opt_ligado__label"),
                modificadores={"dano_explosivos_mult": 1.20, "screen_shake_stagger": True},
                flavor_text=t("configs_catalogo", "screen_shake__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "screen_shake__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "screen_shake__opt_ligado__buff")
            ),
        }
    ),

    # 6. Desfoque de Movimento (Performance / Visual)
    "motion_blur": ConfiguracaoDef(
        id="motion_blur",
        nome=t("configs_catalogo", "motion_blur__nome"),
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=6,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "motion_blur__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "motion_blur__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "motion_blur__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "motion_blur__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "motion_blur__opt_ligado__label"),
                modificadores={"vel_jogador_mult": 1.15, "motion_blur_ghosting": True},
                flavor_text=t("configs_catalogo", "motion_blur__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "motion_blur__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "motion_blur__opt_ligado__buff")            ),
        }
    ),

    # 7. Exibição de Interface (Interface)
    "hud": ConfiguracaoDef(
        id="hud",
        nome=t("configs_catalogo", "hud__nome"),
                categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=7,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "hud__opt_ligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "hud__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "hud__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "hud__opt_ligado__buff")
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "hud__opt_desligado__label"),
                modificadores={"xp_ganho_mult": 1.25, "hud_pulse_magnet": True},
                flavor_text=t("configs_catalogo", "hud__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "hud__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "hud__opt_desligado__buff")          ),
        }
    ),

    # 8. Números de Dano (Interface)
    "damage_numbers": ConfiguracaoDef(
        id="damage_numbers",
        nome=t("configs_catalogo", "damage_numbers__nome"),
                categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=8,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "damage_numbers__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "damage_numbers__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "damage_numbers__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "damage_numbers__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "damage_numbers__opt_ligado__label"),
                modificadores={"critico_chance": 0.25, "critico_mult": 2.0, "damage_numbers_knockback": True},
                flavor_text=t("configs_catalogo", "damage_numbers__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "damage_numbers__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "damage_numbers__opt_ligado__buff")          ),
        }
    ),

    # 9. Nível de Zoom (Interface)
    "zoom": ConfiguracaoDef(
        id="zoom",
        nome=t("configs_catalogo", "zoom__nome"),
                categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="100%",
        ordem=9,
        opcoes={
            "75%": OpcaoConfig(
                id="75%",
                label=t("configs_catalogo", "zoom__opt_75%__label"),
                modificadores={"zoom_balistica_longa": True, "zoom_queima_roupa_mult": 0.85},
                flavor_text=t("configs_catalogo", "zoom__opt_75%__flavor"),
                nerf_text=t("configs_catalogo", "zoom__opt_75%__nerf"),
                buff_text=t("configs_catalogo", "zoom__opt_75%__buff")      ),
            "100%": OpcaoConfig(
                id="100%",
                label=t("configs_catalogo", "zoom__opt_100%__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "zoom__opt_100%__flavor"),
                nerf_text=t("configs_catalogo", "zoom__opt_100%__nerf"),
                buff_text=t("configs_catalogo", "zoom__opt_100%__buff")
            ),
            "125%": OpcaoConfig(
                id="125%",
                label=t("configs_catalogo", "zoom__opt_125%__label"),
                modificadores={"zoom_execucao_cd_red": 0.5},
                flavor_text=t("configs_catalogo", "zoom__opt_125%__flavor"),
                nerf_text=t("configs_catalogo", "zoom__opt_125%__nerf"),
                buff_text=t("configs_catalogo", "zoom__opt_125%__buff")          ),
            "150%": OpcaoConfig(
                id="150%",
                label=t("configs_catalogo", "zoom__opt_150%__label"),
                modificadores={"zoom_execucao_cd_red": 1.0, "zoom_execucao_limiar_hp": 0.20},
                flavor_text=t("configs_catalogo", "zoom__opt_150%__flavor"),
                nerf_text=t("configs_catalogo", "zoom__opt_150%__nerf"),
                buff_text=t("configs_catalogo", "zoom__opt_150%__buff")         ),
        }
    ),

    # 10. Movimento pelo Mouse (Controles)
    "movimento_mouse": ConfiguracaoDef(
        id="movimento_mouse",
        nome=t("configs_catalogo", "movimento_mouse__nome"),
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=10,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "movimento_mouse__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "movimento_mouse__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "movimento_mouse__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "movimento_mouse__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "movimento_mouse__opt_ligado__label"),
                modificadores={"drop_chance_mult": 1.40, "movimento_ram_collision": True},
                flavor_text=t("configs_catalogo", "movimento_mouse__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "movimento_mouse__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "movimento_mouse__opt_ligado__buff"),
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
        nome=t("configs_catalogo", "keybinds__nome"),
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="padrao",
        ordem=11,
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label=t("configs_catalogo", "keybinds__opt_padrao__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "keybinds__opt_padrao__flavor"),
                nerf_text=t("configs_catalogo", "keybinds__opt_padrao__nerf"),
                buff_text=t("configs_catalogo", "keybinds__opt_padrao__buff")
            ),
            "invertido": OpcaoConfig(
                id="invertido",
                label=t("configs_catalogo", "keybinds__opt_invertido__label"),
                modificadores={"dano_armas_mult": 1.10, "keybinds_overdrive_dash": True},
                flavor_text=t("configs_catalogo", "keybinds__opt_invertido__flavor"),
                nerf_text=t("configs_catalogo", "keybinds__opt_invertido__nerf"),
                buff_text=t("configs_catalogo", "keybinds__opt_invertido__buff")            ),
            "arrow_keys": OpcaoConfig(
                id="arrow_keys",
                label=t("configs_catalogo", "keybinds__opt_arrow_keys__label"),
                modificadores={"vel_jogador_mult": 1.15, "keybinds_overdrive_dash": True},
                flavor_text=t("configs_catalogo", "keybinds__opt_arrow_keys__flavor"),
                nerf_text=t("configs_catalogo", "keybinds__opt_arrow_keys__nerf"),
                buff_text=t("configs_catalogo", "keybinds__opt_arrow_keys__buff")            ),
            "uma_mao": OpcaoConfig(
                id="uma_mao",
                label=t("configs_catalogo", "keybinds__opt_uma_mao__label"),
                modificadores={"xp_ganho_mult": 1.20, "keybinds_overdrive_dash": True},
                flavor_text=t("configs_catalogo", "keybinds__opt_uma_mao__flavor"),
                nerf_text=t("configs_catalogo", "keybinds__opt_uma_mao__nerf"),
                buff_text=t("configs_catalogo", "keybinds__opt_uma_mao__buff"),
                incompativel_com=[
                    ("movimento_mouse", "ligado"),
                    ("controles_tanque", "ligado"),
                    ("mira_oculta", "ligado"),
                ],
            ),
            "pesadelo": OpcaoConfig(
                id="pesadelo",
                label=t("configs_catalogo", "keybinds__opt_pesadelo__label"),
                modificadores={"dano_armas_mult": 1.30, "keybinds_overdrive_dash": True},
                flavor_text=t("configs_catalogo", "keybinds__opt_pesadelo__flavor"),
                nerf_text=t("configs_catalogo", "keybinds__opt_pesadelo__nerf"),
                buff_text=t("configs_catalogo", "keybinds__opt_pesadelo__buff"),
                incompativel_com=[
                    ("movimento_mouse", "ligado"),
                ],
            ),
        }
    ),

    # 12. Suavização de Câmera (Controles / Câmera)
    "suavizacao_camera": ConfiguracaoDef(
        id="suavizacao_camera",
        nome=t("configs_catalogo", "suavizacao_camera__nome"),
                categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=12,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "suavizacao_camera__opt_ligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "suavizacao_camera__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "suavizacao_camera__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "suavizacao_camera__opt_ligado__buff")
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "suavizacao_camera__opt_desligado__label"),
                modificadores={"camera_hard_kick": True, "flick_shot_ativo": True},
                flavor_text=t("configs_catalogo", "suavizacao_camera__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "suavizacao_camera__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "suavizacao_camera__opt_desligado__buff")      ),
        }
    ),

    # 13. Disparo Automático (Controles / Combate)
    "auto_fire": ConfiguracaoDef(
        id="auto_fire",
        nome=t("configs_catalogo", "auto_fire__nome"),
                categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="ligado",
        ordem=13,
        opcoes={
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "auto_fire__opt_ligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "auto_fire__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "auto_fire__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "auto_fire__opt_ligado__buff")
            ),
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "auto_fire__opt_desligado__label"),
                modificadores={"dano_armas_mult": 1.15, "auto_fire_burst": True},
                flavor_text=t("configs_catalogo", "auto_fire__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "auto_fire__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "auto_fire__opt_desligado__buff")            ),
        }
    ),

    # 14. Inimigos à Distância (Dificuldade)
    "inimigos_ranged": ConfiguracaoDef(
        id="inimigos_ranged",
        nome=t("configs_catalogo", "inimigos_ranged__nome"),
                categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=14,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "inimigos_ranged__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "inimigos_ranged__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "inimigos_ranged__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "inimigos_ranged__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "inimigos_ranged__opt_ligado__label"),
                modificadores={"loot_enriquecido": True, "inimigos_ranged_bullet_hell": True},
                flavor_text=t("configs_catalogo", "inimigos_ranged__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "inimigos_ranged__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "inimigos_ranged__opt_ligado__buff")           ),
        }
    ),

    # 15. Captura de Drops por Inimigos (Dificuldade)
    "coleta_inimiga": ConfiguracaoDef(
        id="coleta_inimiga",
        nome=t("configs_catalogo", "coleta_inimiga__nome"),
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=15,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "coleta_inimiga__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "coleta_inimiga__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "coleta_inimiga__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "coleta_inimiga__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "coleta_inimiga__opt_ligado__label"),
                modificadores={"drops_valor_mult": 2.0, "coleta_inimiga": True},
                flavor_text=t("configs_catalogo", "coleta_inimiga__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "coleta_inimiga__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "coleta_inimiga__opt_ligado__buff")            ),
        }
    ),

    # 16. Velocidade dos Inimigos (Dificuldade)
    "velocidade_inimigos": ConfiguracaoDef(
        id="velocidade_inimigos",
        nome=t("configs_catalogo", "velocidade_inimigos__nome"),
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="normal",
        ordem=16,
        opcoes={
            "normal": OpcaoConfig(
                id="normal",
                label=t("configs_catalogo", "velocidade_inimigos__opt_normal__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "velocidade_inimigos__opt_normal__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_inimigos__opt_normal__nerf"),
                buff_text=t("configs_catalogo", "velocidade_inimigos__opt_normal__buff")
            ),
            "+25%": OpcaoConfig(
                id="+25%",
                label=t("configs_catalogo", "velocidade_inimigos__opt_+25%__label"),
                modificadores={"vel_inimigos_mult": 1.25, "xp_ganho_mult": 1.15, "inercia_cinetica_nivel": 1},
                flavor_text=t("configs_catalogo", "velocidade_inimigos__opt_+25%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_inimigos__opt_+25%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_inimigos__opt_+25%__buff")           ),
            "+50%": OpcaoConfig(
                id="+50%",
                label=t("configs_catalogo", "velocidade_inimigos__opt_+50%__label"),
                modificadores={"vel_inimigos_mult": 1.50, "xp_ganho_mult": 1.30, "inercia_cinetica_nivel": 2},
                flavor_text=t("configs_catalogo", "velocidade_inimigos__opt_+50%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_inimigos__opt_+50%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_inimigos__opt_+50%__buff")         ),
        }
    ),

    # 17. Vida dos Inimigos (Dificuldade)
    "vida_inimigos": ConfiguracaoDef(
        id="vida_inimigos",
        nome=t("configs_catalogo", "vida_inimigos__nome"),
        categoria=CategoriaConfig.DIFICULDADE,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="normal",
        ordem=17,
        opcoes={
            "normal": OpcaoConfig(
                id="normal",
                label=t("configs_catalogo", "vida_inimigos__opt_normal__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "vida_inimigos__opt_normal__flavor"),
                nerf_text=t("configs_catalogo", "vida_inimigos__opt_normal__nerf"),
                buff_text=t("configs_catalogo", "vida_inimigos__opt_normal__buff")
            ),
            "+50%": OpcaoConfig(
                id="+50%",
                label=t("configs_catalogo", "vida_inimigos__opt_+50%__label"),
                modificadores={"hp_inimigos_mult": 1.50, "pinhata_hardware_nivel": 1},
                flavor_text=t("configs_catalogo", "vida_inimigos__opt_+50%__flavor"),
                nerf_text=t("configs_catalogo", "vida_inimigos__opt_+50%__nerf"),
                buff_text=t("configs_catalogo", "vida_inimigos__opt_+50%__buff")           ),
            "+100%": OpcaoConfig(
                id="+100%",
                label=t("configs_catalogo", "vida_inimigos__opt_+100%__label"),
                modificadores={"hp_inimigos_mult": 2.00, "pinhata_hardware_nivel": 2, "drop_chance_bonus": 0.15},
                flavor_text=t("configs_catalogo", "vida_inimigos__opt_+100%__flavor"),
                nerf_text=t("configs_catalogo", "vida_inimigos__opt_+100%__nerf"),
                buff_text=t("configs_catalogo", "vida_inimigos__opt_+100%__buff")            ),
        }
    ),

    # 18. Iluminação Dinâmica (Experimental / Atmosfera)
    "iluminacao": ConfiguracaoDef(
        id="iluminacao",
        nome=t("configs_catalogo", "iluminacao__nome"),
                categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=18,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "iluminacao__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "iluminacao__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "iluminacao__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "iluminacao__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "iluminacao__opt_ligado__label"),
                modificadores={"clarao_fotossensivel": True},
                flavor_text=t("configs_catalogo", "iluminacao__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "iluminacao__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "iluminacao__opt_ligado__buff")         ),
        }
    ),

    # 19. Cores Invertidas (Experimental / Visual)
    "cores_invertidas": ConfiguracaoDef(
        id="cores_invertidas",
        nome=t("configs_catalogo", "cores_invertidas__nome"),
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=19,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "cores_invertidas__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "cores_invertidas__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "cores_invertidas__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "cores_invertidas__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "cores_invertidas__opt_ligado__label"),
                modificadores={"polaridade_invertida": True},
                flavor_text=t("configs_catalogo", "cores_invertidas__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "cores_invertidas__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "cores_invertidas__opt_ligado__buff")
            ),
        }
    ),

    # 20. Fogo Amigo (Experimental / Risco Extremo)
    "fogo_amigo": ConfiguracaoDef(
        id="fogo_amigo",
        nome=t("configs_catalogo", "fogo_amigo__nome"),
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=20,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "fogo_amigo__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "fogo_amigo__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "fogo_amigo__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "fogo_amigo__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "fogo_amigo__opt_ligado__label"),
                modificadores={"dano_armas_mult": 1.25, "auto_dano": True, "fogo_amigo_rocket_jump": True},
                flavor_text=t("configs_catalogo", "fogo_amigo__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "fogo_amigo__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "fogo_amigo__opt_ligado__buff")            ),
        }
    ),

    # 21. Calibragem de Parry (Precisão vs Poder)
    "precisao_parry": ConfiguracaoDef(
        id="precisao_parry",
        nome=t("configs_catalogo", "precisao_parry__nome"),
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=21,
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label=t("configs_catalogo", "precisao_parry__opt_padrao__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "precisao_parry__opt_padrao__flavor"),
                nerf_text=t("configs_catalogo", "precisao_parry__opt_padrao__nerf"),
                buff_text=t("configs_catalogo", "precisao_parry__opt_padrao__buff")
            ),
            "cirurgico": OpcaoConfig(
                id="cirurgico",
                label=t("configs_catalogo", "precisao_parry__opt_cirurgico__label"),
                modificadores={"parry_precisao": "cirurgico"},
                flavor_text=t("configs_catalogo", "precisao_parry__opt_cirurgico__flavor"),
                nerf_text=t("configs_catalogo", "precisao_parry__opt_cirurgico__nerf"),
                buff_text=t("configs_catalogo", "precisao_parry__opt_cirurgico__buff")            ),
            "amplificado": OpcaoConfig(
                id="amplificado",
                label=t("configs_catalogo", "precisao_parry__opt_amplificado__label"),
                modificadores={"parry_precisao": "amplificado"},
                flavor_text=t("configs_catalogo", "precisao_parry__opt_amplificado__flavor"),
                nerf_text=t("configs_catalogo", "precisao_parry__opt_amplificado__nerf"),
                buff_text=t("configs_catalogo", "precisao_parry__opt_amplificado__buff")            ),
            "postura_riposte": OpcaoConfig(
                id="postura_riposte",
                label=t("configs_catalogo", "precisao_parry__opt_postura_riposte__label"),
                modificadores={"parry_precisao": "postura_riposte"},
                flavor_text=t("configs_catalogo", "precisao_parry__opt_postura_riposte__flavor"),
                nerf_text=t("configs_catalogo", "precisao_parry__opt_postura_riposte__nerf"),
                buff_text=t("configs_catalogo", "precisao_parry__opt_postura_riposte__buff"),
                desbloqueada_por="opcao_config:precisao_parry:postura_riposte",
            ),
        }
    ),

    # 22. Protocolo de Reflexão (Efeito do Parry)
    "efeito_parry": ConfiguracaoDef(
        id="efeito_parry",
        nome=t("configs_catalogo", "efeito_parry__nome"),
                categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=22,
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label=t("configs_catalogo", "efeito_parry__opt_padrao__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "efeito_parry__opt_padrao__flavor"),
                nerf_text=t("configs_catalogo", "efeito_parry__opt_padrao__nerf"),
                buff_text=t("configs_catalogo", "efeito_parry__opt_padrao__buff")
            ),
            "estilhaco": OpcaoConfig(
                id="estilhaco",
                label=t("configs_catalogo", "efeito_parry__opt_estilhaco__label"),
                modificadores={"parry_efeito": "estilhaco"},
                flavor_text=t("configs_catalogo", "efeito_parry__opt_estilhaco__flavor"),
                nerf_text=t("configs_catalogo", "efeito_parry__opt_estilhaco__nerf"),
                buff_text=t("configs_catalogo", "efeito_parry__opt_estilhaco__buff")            ),
            "pulso_emp": OpcaoConfig(
                id="pulso_emp",
                label=t("configs_catalogo", "efeito_parry__opt_pulso_emp__label"),
                modificadores={"parry_efeito": "pulso_emp"},
                flavor_text=t("configs_catalogo", "efeito_parry__opt_pulso_emp__flavor"),
                nerf_text=t("configs_catalogo", "efeito_parry__opt_pulso_emp__nerf"),
                buff_text=t("configs_catalogo", "efeito_parry__opt_pulso_emp__buff")            ),
            "firewall_estatico": OpcaoConfig(
                id="firewall_estatico",
                label=t("configs_catalogo", "efeito_parry__opt_firewall_estatico__label"),
                modificadores={"parry_efeito": "firewall_estatico"},
                flavor_text=t("configs_catalogo", "efeito_parry__opt_firewall_estatico__flavor"),
                nerf_text=t("configs_catalogo", "efeito_parry__opt_firewall_estatico__nerf"),
                buff_text=t("configs_catalogo", "efeito_parry__opt_firewall_estatico__buff")           ),
            "ventoinha_360": OpcaoConfig(
                id="ventoinha_360",
                label=t("configs_catalogo", "efeito_parry__opt_ventoinha_360__label"),
                modificadores={"parry_efeito": "ventoinha_360"},
                flavor_text=t("configs_catalogo", "efeito_parry__opt_ventoinha_360__flavor"),
                nerf_text=t("configs_catalogo", "efeito_parry__opt_ventoinha_360__nerf"),
                buff_text=t("configs_catalogo", "efeito_parry__opt_ventoinha_360__buff")           ),
        }
    ),

    # 23. Controles de Tanque (Blindagem & Artilharia)
    "controles_tanque": ConfiguracaoDef(
        id="controles_tanque",
        nome=t("configs_catalogo", "controles_tanque__nome"),
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=23,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "controles_tanque__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "controles_tanque__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "controles_tanque__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "controles_tanque__opt_desligado__buff")
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "controles_tanque__opt_ligado__label"),
                modificadores={"controles_tanque": True, "dano_armas_mult": 1.35, "dano_recebido_mult": 0.80},
                flavor_text=t("configs_catalogo", "controles_tanque__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "controles_tanque__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "controles_tanque__opt_ligado__buff"),
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
        nome=t("configs_catalogo", "dash_protocolo__nome"),
        categoria=CategoriaConfig.CONTROLES,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=24,
        requer_desbloqueio=("habilidade", "dash"),
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label=t("configs_catalogo", "dash_protocolo__opt_padrao__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "dash_protocolo__opt_padrao__flavor"),
                nerf_text=t("configs_catalogo", "dash_protocolo__opt_padrao__nerf"),
                buff_text=t("configs_catalogo", "dash_protocolo__opt_padrao__buff"),
            ),
            "teleporte_buffer": OpcaoConfig(
                id="teleporte_buffer",
                label=t("configs_catalogo", "dash_protocolo__opt_teleporte_buffer__label"),
                modificadores={"dash_protocolo": "teleporte_buffer"},
                flavor_text=t("configs_catalogo", "dash_protocolo__opt_teleporte_buffer__flavor"),
                nerf_text=t("configs_catalogo", "dash_protocolo__opt_teleporte_buffer__nerf"),
                buff_text=t("configs_catalogo", "dash_protocolo__opt_teleporte_buffer__buff")            ),
            "propulsor_instavel": OpcaoConfig(
                id="propulsor_instavel",
                label=t("configs_catalogo", "dash_protocolo__opt_propulsor_instavel__label"),
                modificadores={"dash_protocolo": "propulsor_instavel"},
                flavor_text=t("configs_catalogo", "dash_protocolo__opt_propulsor_instavel__flavor"),
                nerf_text=t("configs_catalogo", "dash_protocolo__opt_propulsor_instavel__nerf"),
                buff_text=t("configs_catalogo", "dash_protocolo__opt_propulsor_instavel__buff")
            ),
            "sombra_espelho": OpcaoConfig(
                id="sombra_espelho",
                label=t("configs_catalogo", "dash_protocolo__opt_sombra_espelho__label"),
                modificadores={"dash_protocolo": "sombra_espelho"},
                flavor_text=t("configs_catalogo", "dash_protocolo__opt_sombra_espelho__flavor"),
                nerf_text=t("configs_catalogo", "dash_protocolo__opt_sombra_espelho__nerf"),
                buff_text=t("configs_catalogo", "dash_protocolo__opt_sombra_espelho__buff"),
                desbloqueada_por="opcao_config:dash_protocolo:sombra_espelho",
            ),
            "rollback_estado": OpcaoConfig(
                id="rollback_estado",
                label=t("configs_catalogo", "dash_protocolo__opt_rollback_estado__label"),
                modificadores={"dash_protocolo": "rollback_estado"},
                flavor_text=t("configs_catalogo", "dash_protocolo__opt_rollback_estado__flavor"),
                nerf_text=t("configs_catalogo", "dash_protocolo__opt_rollback_estado__nerf"),
                buff_text=t("configs_catalogo", "dash_protocolo__opt_rollback_estado__buff"),
                desbloqueada_por="opcao_config:dash_protocolo:rollback_estado",
            ),
        },
    ),

    # 25. Rastro de Dash (Experimental — Requer habilidade:dash)
    "dash_rastro": ConfiguracaoDef(
        id="dash_rastro",
        nome=t("configs_catalogo", "dash_rastro__nome"),
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.SELETOR,
        valor_padrao="padrao",
        ordem=25,
        requer_desbloqueio=("habilidade", "dash"),
        opcoes={
            "padrao": OpcaoConfig(
                id="padrao",
                label=t("configs_catalogo", "dash_rastro__opt_padrao__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "dash_rastro__opt_padrao__flavor"),
                nerf_text=t("configs_catalogo", "dash_rastro__opt_padrao__nerf"),
                buff_text=t("configs_catalogo", "dash_rastro__opt_padrao__buff"),
            ),
            "exaustao_termica": OpcaoConfig(
                id="exaustao_termica",
                label=t("configs_catalogo", "dash_rastro__opt_exaustao_termica__label"),
                modificadores={"dash_rastro": "exaustao_termica"},
                flavor_text=t("configs_catalogo", "dash_rastro__opt_exaustao_termica__flavor"),
                nerf_text=t("configs_catalogo", "dash_rastro__opt_exaustao_termica__nerf"),
                buff_text=t("configs_catalogo", "dash_rastro__opt_exaustao_termica__buff"),
            ),
            "vacuo_io": OpcaoConfig(
                id="vacuo_io",
                label=t("configs_catalogo", "dash_rastro__opt_vacuo_io__label"),
                modificadores={"dash_rastro": "vacuo_io"},
                flavor_text=t("configs_catalogo", "dash_rastro__opt_vacuo_io__flavor"),
                nerf_text=t("configs_catalogo", "dash_rastro__opt_vacuo_io__nerf"),
                buff_text=t("configs_catalogo", "dash_rastro__opt_vacuo_io__buff")
            ),
            "subprocesso_atrasado": OpcaoConfig(
                id="subprocesso_atrasado",
                label=t("configs_catalogo", "dash_rastro__opt_subprocesso_atrasado__label"),
                modificadores={"dash_rastro": "subprocesso_atrasado"},
                flavor_text=t("configs_catalogo", "dash_rastro__opt_subprocesso_atrasado__flavor"),
                nerf_text=t("configs_catalogo", "dash_rastro__opt_subprocesso_atrasado__nerf"),
                buff_text=t("configs_catalogo", "dash_rastro__opt_subprocesso_atrasado__buff")
            ),
            "thread_fantasma": OpcaoConfig(
                id="thread_fantasma",
                label=t("configs_catalogo", "dash_rastro__opt_thread_fantasma__label"),
                modificadores={"dash_rastro": "thread_fantasma"},
                flavor_text=t("configs_catalogo", "dash_rastro__opt_thread_fantasma__flavor"),
                nerf_text=t("configs_catalogo", "dash_rastro__opt_thread_fantasma__nerf"),
                buff_text=t("configs_catalogo", "dash_rastro__opt_thread_fantasma__buff"),
                desbloqueada_por="opcao_config:dash_rastro:thread_fantasma",
            ),
        },
    ),

    # 26. Garbage Collector (Performance)
    "garbage_collector": ConfiguracaoDef(
        id="garbage_collector",
        nome=t("configs_catalogo", "garbage_collector__nome"),
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=26,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "garbage_collector__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "garbage_collector__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "garbage_collector__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "garbage_collector__opt_desligado__buff"),
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "garbage_collector__opt_ligado__label"),
                modificadores={"garbage_collector": True},
                flavor_text=t("configs_catalogo", "garbage_collector__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "garbage_collector__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "garbage_collector__opt_ligado__buff")         ),
        },
    ),

    # 27. Latência Simulada (Experimental — Exclusiva de Conquista)
    "latencia_ping": ConfiguracaoDef(
        id="latencia_ping",
        nome=t("configs_catalogo", "latencia_ping__nome"),
                categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=27,
        exclusiva_conquista=True,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "latencia_ping__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "latencia_ping__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "latencia_ping__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "latencia_ping__opt_desligado__buff"),
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "latencia_ping__opt_ligado__label"),
                modificadores={"latencia_ping": True},
                flavor_text=t("configs_catalogo", "latencia_ping__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "latencia_ping__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "latencia_ping__opt_ligado__buff")
            ),
        },
    ),

    # 28. Modo Wireframe (Performance)
    "modo_wireframe": ConfiguracaoDef(
        id="modo_wireframe",
        nome=t("configs_catalogo", "modo_wireframe__nome"),
        categoria=CategoriaConfig.PERFORMANCE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=28,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "modo_wireframe__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "modo_wireframe__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "modo_wireframe__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "modo_wireframe__opt_desligado__buff"),
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "modo_wireframe__opt_ligado__label"),
                modificadores={"modo_wireframe": True},
                flavor_text=t("configs_catalogo", "modo_wireframe__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "modo_wireframe__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "modo_wireframe__opt_ligado__buff"),
                incompativel_com=[("graficos_qualidade", "baixa")],
            ),
        },
    ),

    # 29. Cursor Desabilitado / Mira Oculta (Interface)
    "mira_oculta": ConfiguracaoDef(
        id="mira_oculta",
        nome=t("configs_catalogo", "mira_oculta__nome"),
        categoria=CategoriaConfig.INTERFACE,
        tipo=TipoControleConfig.TOGGLE,
        valor_padrao="desligado",
        ordem=29,
        opcoes={
            "desligado": OpcaoConfig(
                id="desligado",
                label=t("configs_catalogo", "mira_oculta__opt_desligado__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "mira_oculta__opt_desligado__flavor"),
                nerf_text=t("configs_catalogo", "mira_oculta__opt_desligado__nerf"),
                buff_text=t("configs_catalogo", "mira_oculta__opt_desligado__buff"),
            ),
            "ligado": OpcaoConfig(
                id="ligado",
                label=t("configs_catalogo", "mira_oculta__opt_ligado__label"),
                modificadores={"mira_oculta_homing": True},
                flavor_text=t("configs_catalogo", "mira_oculta__opt_ligado__flavor"),
                nerf_text=t("configs_catalogo", "mira_oculta__opt_ligado__nerf"),
                buff_text=t("configs_catalogo", "mira_oculta__opt_ligado__buff"),
                incompativel_com=[("keybinds", "uma_mao")],
            ),
        },
    ),

    # 30. Velocidade do Jogo (Experimental)
    "velocidade_jogo": ConfiguracaoDef(
        id="velocidade_jogo",
        nome=t("configs_catalogo", "velocidade_jogo__nome"),
        categoria=CategoriaConfig.EXPERIMENTAL,
        tipo=TipoControleConfig.GRUPO,
        valor_padrao="100%",
        ordem=30,
        opcoes={
            "50%": OpcaoConfig(
                id="50%",
                label=t("configs_catalogo", "velocidade_jogo__opt_50%__label"),
                modificadores={
                    "velocidade_jogo_mult": 0.50,
                    "xp_ganho_mult": 0.80,
                    "drops_despawn_real_mult": 1.50,
                    "dash_cooldown_mult": 1.30,
                },
                flavor_text=t("configs_catalogo", "velocidade_jogo__opt_50%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_jogo__opt_50%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_jogo__opt_50%__buff"),
            ),
            "75%": OpcaoConfig(
                id="75%",
                label=t("configs_catalogo", "velocidade_jogo__opt_75%__label"),
                modificadores={
                    "velocidade_jogo_mult": 0.75,
                    "xp_ganho_mult": 0.90,
                    "drops_despawn_real_mult": 1.25,
                },
                flavor_text=t("configs_catalogo", "velocidade_jogo__opt_75%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_jogo__opt_75%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_jogo__opt_75%__buff"),
            ),
            "100%": OpcaoConfig(
                id="100%",
                label=t("configs_catalogo", "velocidade_jogo__opt_100%__label"),
                modificadores={},
                flavor_text=t("configs_catalogo", "velocidade_jogo__opt_100%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_jogo__opt_100%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_jogo__opt_100%__buff"),
            ),
            "125%": OpcaoConfig(
                id="125%",
                label=t("configs_catalogo", "velocidade_jogo__opt_125%__label"),
                modificadores={
                    "velocidade_jogo_mult": 1.25,
                    "xp_ganho_mult": 1.15,
                    "cadencia_movimento_continuo_mult": 1.15,
                },
                flavor_text=t("configs_catalogo", "velocidade_jogo__opt_125%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_jogo__opt_125%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_jogo__opt_125%__buff"),
            ),
            "150%": OpcaoConfig(
                id="150%",
                label=t("configs_catalogo", "velocidade_jogo__opt_150%__label"),
                modificadores={
                    "velocidade_jogo_mult": 1.50,
                    "xp_ganho_mult": 1.25,
                    "abate_reducao_cd_dash_parry": 0.20,
                },
                flavor_text=t("configs_catalogo", "velocidade_jogo__opt_150%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_jogo__opt_150%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_jogo__opt_150%__buff"),
            ),
            "200%": OpcaoConfig(
                id="200%",
                label=t("configs_catalogo", "velocidade_jogo__opt_200%__label"),
                modificadores={
                    "velocidade_jogo_mult": 2.00,
                    "xp_ganho_mult": 1.40,
                    "abate_reducao_cd_dash_parry": 0.35,
                    "parry_nightcore_ativo": True,
                },
                flavor_text=t("configs_catalogo", "velocidade_jogo__opt_200%__flavor"),
                nerf_text=t("configs_catalogo", "velocidade_jogo__opt_200%__nerf"),
                buff_text=t("configs_catalogo", "velocidade_jogo__opt_200%__buff"),
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
        nome=t("configs_catalogo", "volume_master__nome"),
        categoria=CategoriaConfig.SISTEMA,
        tipo=TipoControleConfig.SLIDER,
        valor_padrao=100,
        is_gameplay=False,
        ordem=101,
        descricao_sistema=t("configs_catalogo", "volume_master__descricao_sistema")   ),

    # S2. Volume da Música
    "volume_musica": ConfiguracaoDef(
        id="volume_musica",
        nome=t("configs_catalogo", "volume_musica__nome"),
                categoria=CategoriaConfig.SISTEMA,
        tipo=TipoControleConfig.SLIDER,
        valor_padrao=100,
        is_gameplay=False,
        ordem=102,
        descricao_sistema=t("configs_catalogo", "volume_musica__descricao_sistema")
    ),

    # S3. Volume dos Efeitos
    "volume_sfx": ConfiguracaoDef(
        id="volume_sfx",
        nome=t("configs_catalogo", "volume_sfx__nome"),
        categoria=CategoriaConfig.SISTEMA,
        tipo=TipoControleConfig.SLIDER,
        valor_padrao=100,
        is_gameplay=False,
        ordem=103,
        descricao_sistema=t("configs_catalogo", "volume_sfx__descricao_sistema")    ),
}

# Dicionário consolidado com as configurações (32 no total: 29 gameplay + 3 sistema)
TODAS_CONFIGURACOES: dict[str, ConfiguracaoDef] = {
    **CONFIGURACOES_GAMEPLAY,
    **CONFIGURACOES_SISTEMA
}
