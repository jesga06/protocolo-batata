"""
Constantes Globais — Protocolo: Batata
Single Source of Truth no código para dimensões, cores, valores baselines,
caminhos de assets e catálogo de configurações (alinhado com CONFIGURACOES.md).
"""

import os

# =============================================================================
# 1. DIRETÓRIOS E CAMINHOS
# =============================================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SAVE_FILE_PATH = os.path.join(DATA_DIR, "save.json")

# =============================================================================
# 2. JANELA E VIRTUAL BUFFER
# =============================================================================

LARGURA_TELA = 800
ALTURA_TELA = 600
LARGURA_ARENA = 1600
ALTURA_ARENA = 1200
TITULO_JOGO = "Protocolo: Batata"
FPS_PADRAO = 60

# =============================================================================
# 3. PALETA DE CORES (RGB / RGBA)
# =============================================================================

BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
CINZA_FUNDO = (22, 25, 32)
CINZA_PAINEL = (30, 35, 45)
CINZA_BORDA = (60, 75, 95)
CINZA_TEXTO = (180, 190, 205)

VERMELHO_HP = (235, 45, 55)
VERMELHO_DANO = (255, 80, 80)
AMARELO_XP = (255, 215, 0)
VERDE_CURA = (40, 210, 85)
AZUL_CIANO = (0, 220, 255)
ROXO_DROPS = (160, 50, 220)
LARANJA_ALERTA = (255, 140, 0)
DOURADO = (255, 215, 0)

# =============================================================================
# 4. JOGADOR (BATATA) — BASELINES
# =============================================================================

JOGADOR_HP_MAX_PADRAO = 150
JOGADOR_VELOCIDADE_PADRAO = 200.0  # pixels por segundo
JOGADOR_LARGURA = 32
JOGADOR_ALTURA = 32
JOGADOR_COOLDOWN_DANO_FLASH = 0.15  # segundos de flash vermelho
JOGADOR_INVULNERABILIDADE_TEMPO = 0.2  # segundos mínimos entre frames de dano

# =============================================================================
# 5. INIMIGOS — BASELINES
# =============================================================================

# Inimigo Padrão (Estagiário)
INIMIGO_PADRAO_HP = 50
INIMIGO_PADRAO_VELOCIDADE = 100.0
INIMIGO_PADRAO_DANO = 10
INIMIGO_PADRAO_COOLDOWN_ATAQUE = 0.4
INIMIGO_PADRAO_XP = 5

# Inimigo Tanque (Geladeira Industrial - 120 HP)
INIMIGO_TANK_HP = 120
INIMIGO_TANK_VELOCIDADE = 50.0
INIMIGO_TANK_DANO = 20
INIMIGO_TANK_COOLDOWN_ATAQUE = 0.7
INIMIGO_TANK_XP = 25

# Inimigo Rápido (Viciado em Cafeína - 12 HP)
INIMIGO_RAPIDO_HP = 12
INIMIGO_RAPIDO_VELOCIDADE = 180.0
INIMIGO_RAPIDO_DANO = 8
INIMIGO_RAPIDO_COOLDOWN_ATAQUE = 0.25
INIMIGO_RAPIDO_XP = 8

# Inimigo Phasing (Warranty Void - 35 HP)
INIMIGO_PHASING_HP = 35
INIMIGO_PHASING_VELOCIDADE = 90.0
INIMIGO_PHASING_DANO = 12
INIMIGO_PHASING_COOLDOWN_ATAQUE = 0.4
INIMIGO_PHASING_XP = 12
INIMIGO_PHASING_CICLO = 3.0  # a cada 3s entra em fase por 1.2s

# Inimigo Blindado (Ballistic Enthusiast - 50 HP)
INIMIGO_BLINDADO_HP = 50
INIMIGO_BLINDADO_VELOCIDADE = 75.0
INIMIGO_BLINDADO_DANO = 15
INIMIGO_BLINDADO_COOLDOWN_ATAQUE = 0.5
INIMIGO_BLINDADO_XP = 15

# Inimigo Ranged (Atirador Blaster - 30 HP)
INIMIGO_RANGED_HP = 30
INIMIGO_RANGED_VELOCIDADE = 80.0
INIMIGO_RANGED_DANO = 10
INIMIGO_RANGED_COOLDOWN_ATAQUE = 1.2
INIMIGO_RANGED_XP = 15
INIMIGO_RANGED_DISTANCIA_TIRO = 280.0

# =============================================================================
# 6. SISTEMA DE SPAWN
# =============================================================================

SPAWN_INTERVALO_INICIAL = 1.8
SPAWN_INTERVALO_MINIMO = 0.4
SPAWN_DECAIMENTO_TAXA = 0.02
SPAWN_DISTANCIA_OFFSET = 60  # pixels fora da tela visível
LIMITE_INIMIGOS_VIVOS = 120

# =============================================================================
# 7. ARMAS E PROJÉTEIS — BASELINES
# =============================================================================

# Slot 1: Melee (Chave de Manutenção)
MELEE_DANO = 10
MELEE_COOLDOWN = 0.6
MELEE_ALCANCE = 84.0
MELEE_KNOCKBACK = 360.0
MELEE_ALVOS_MAX = 2
MELEE_ARCO_GRAUS = 45.0

# Slot 2: Pistola (Padrão de Fábrica)
PISTOLA_DANO = 17
PISTOLA_COOLDOWN = 0.35
PISTOLA_VELOCIDADE_PROJETIL = 450.0
PISTOLA_ALCANCE_MAX = 800.0

# Slot 3: Armas Especiais Temporárias
MINIGUN_DANO = 6
MINIGUN_COOLDOWN = 0.08
MINIGUN_VELOCIDADE_PROJETIL = 550.0
MINIGUN_MUNICIAO_MAX = 150

SHOTGUN_DANO = 10
SHOTGUN_COOLDOWN = 0.70
SHOTGUN_VELOCIDADE_PROJETIL = 400.0
SHOTGUN_PELLETS = 5
SHOTGUN_SPREAD_ANGULO = 0.35
SHOTGUN_MUNICIAO_MAX = 30

RIFLE_DANO = 18
RIFLE_COOLDOWN = 0.18
RIFLE_VELOCIDADE_PROJETIL = 650.0
RIFLE_MUNICIAO_MAX = 60

FOGUETES_DANO = 60
FOGUETES_COOLDOWN = 1.20
FOGUETES_VELOCIDADE_PROJETIL = 300.0
FOGUETES_RAIO_EXPLOSAO = 80.0
FOGUETES_MUNICIAO_MAX = 12

GRANADAS_DANO = 45
GRANADAS_COOLDOWN = 0.90
GRANADAS_VELOCIDADE_PROJETIL = 280.0
GRANADAS_RAIO_EXPLOSAO = 65.0
GRANADAS_MUNICIAO_MAX = 16

# =============================================================================
# 8. EQUIPAMENTOS (DRONES) — BASELINES
# =============================================================================

DRONE_CURA_VALOR = 15
DRONE_CURA_INTERVALO = 5.0
DRONE_COMBATE_DANO = 8
DRONE_COMBATE_COOLDOWN = 0.5
DRONE_COMBATE_ALCANCE = 250.0
DRONE_SUPORTE_ESCUDO_MAX = 40
DRONE_SUPORTE_REGEN_INTERVALO = 8.0

# =============================================================================
# 9. DROPS E PROGRESSÃO TEMPORÁRIA
# =============================================================================

DROP_XP_VALOR_BASE = 5
DROP_CURA_VALOR_BASE = 35
DROP_TEMPO_DESAPARECER = 25.0
DROP_TEMPO_SCAVENGER_ATIVAR = 1.0
DROP_LARGURA = 42
DROP_ALTURA = 42

# =============================================================================
# 10. CATÁLOGO COMPLETO DE CONFIGURAÇÕES (SSOT: CONFIGURACOES.MD)
# =============================================================================

TOTAL_CONFIGS_GAMEPLAY = 20

CONFIGURACOES_CATALOGO = {
    # 1. Limite de Quadros (Performance)
    "fps_cap": {
        "id": "fps_cap",
        "nome": "Limite de Quadros",
        "categoria": "Performance",
        "tipo": "grupo",
        "padrao": "60",
        "opcoes": ["60", "45", "30", "15"],
        "icone": "ui/icones_configs/icon_fps_cap.png",
        "flavor_text": {
            "60": "O olho humano não consegue ver além de 30 FPS.",
            "45": "Modo Performance: Os inimigos também estão perdendo frames.",
            "30": "Modo Slow Motion: Só é lag se você estiver perdendo.",
            "15": "Experiência Cinematográfica: Cada frame foi desenhado à mão por monges tibetanos."
        },
        "buffs": {
            "60": {},
            "45": {"dano_inimigos_mult": 0.85},
            "30": {"vel_inimigos_mult": 0.90},
            "15": {"dano_inimigos_mult": 0.7225, "vel_inimigos_mult": 0.81}
        }
    },

    # 2. Qualidade Gráfica (Performance)
    "graficos_qualidade": {
        "id": "graficos_qualidade",
        "nome": "Qualidade Gráfica",
        "categoria": "Performance",
        "tipo": "toggle",
        "padrao": "alta",
        "opcoes": ["alta", "baixa"],
        "icone": "ui/icones_configs/icon_graficos_qualidade.png",
        "flavor_text": {
            "alta": "Sprites nítidos para quem aprecia os pequenos detalhes.",
            "baixa": "Cortes no Orçamento: Texturas são um luxo que o departamento financeiro cortou."
        },
        "buffs": {
            "alta": {},
            "baixa": {"hp_inimigos_mult": 0.80}
        }
    },

    # 3. Resolução da Tela (Performance)
    "resolucao": {
        "id": "resolucao",
        "nome": "Resolução da Tela",
        "categoria": "Performance",
        "tipo": "grupo",
        "padrao": "100%",
        "opcoes": ["100%", "75%", "50%", "25%"],
        "icone": "ui/icones_configs/icon_resolucao.png",
        "flavor_text": {
            "100%": "Cada pixel em seu devido lugar.",
            "75%": "Anti-Aliasing Reverso: Menos pixels na tela, mais caixas no chão.",
            "50%": "Nostalgia Forçada: Lembranças de uma época de monitores CRT.",
            "25%": "Arqueologia de Pixels: Se você consegue contar os pixels nos dedos, está economizando processamento."
        },
        "buffs": {
            "100%": {},
            "75%": {"drop_chance_bonus": 0.10},
            "50%": {"drop_chance_bonus": 0.25},
            "25%": {"drop_chance_bonus": 0.50}
        }
    },

    # 4. Sincronização Vertical (Performance)
    "vsync": {
        "id": "vsync",
        "nome": "Sincronização Vertical",
        "categoria": "Performance",
        "tipo": "toggle",
        "padrao": "ligado",
        "opcoes": ["ligado", "desligado"],
        "icone": "ui/icones_configs/icon_vsync.png",
        "flavor_text": {
            "ligado": "Estabilidade garantida para monitores sensíveis.",
            "desligado": "Morte por Mil Cortes: Espero que seu monitor tenha FreeSync."
        },
        "buffs": {
            "ligado": {},
            "desligado": {"vel_jogador_mult": 1.10}
        }
    },

    # 5. Tremor de Tela (Performance / Visual)
    "screen_shake": {
        "id": "screen_shake",
        "nome": "Tremor de Tela",
        "categoria": "Performance / Visual",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_screen_shake.png",
        "flavor_text": {
            "desligado": "Uma experiência suave.",
            "ligado": "Protocolo: Terremoto: A tela treme. A sua mira também."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"dano_explosivos_mult": 1.20}
        }
    },

    # 6. Desfoque de Movimento (Performance / Visual)
    "motion_blur": {
        "id": "motion_blur",
        "nome": "Desfoque de Movimento",
        "categoria": "Performance / Visual",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_motion_blur.png",
        "flavor_text": {
            "desligado": "Uma experiência suave.",
            "ligado": "Fantasmagórico: Você se move tão rápido que até seus pixels ficaram para trás."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"vel_jogador_mult": 1.15}
        }
    },

    # 7. Exibição de Interface (Interface)
    "hud": {
        "id": "hud",
        "nome": "Exibição de Interface",
        "categoria": "Interface",
        "tipo": "toggle",
        "padrao": "ligado",
        "opcoes": ["ligado", "desligado"],
        "icone": "ui/icones_configs/icon_hud.png",
        "flavor_text": {
            "ligado": "Barras de vida, experiência, inventário e cronômetro visíveis.",
            "desligado": "Trust Me Bro: Com certeza você ainda tem vida sobrando. Provavelmente."
        },
        "buffs": {
            "ligado": {},
            "desligado": {"xp_ganho_mult": 1.25}
        }
    },

    # 8. Números de Dano (Interface)
    "damage_numbers": {
        "id": "damage_numbers",
        "nome": "Números de Dano",
        "categoria": "Interface",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_damage_numbers.png",
        "flavor_text": {
            "desligado": "Inimigos sofrem dano em silêncio.",
            "ligado": "Aula de Matemática: Finalmente uma aplicação prática para aritmética básica."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"critico_chance": 0.15, "critico_mult": 2.0}
        }
    },

    # 9. Nível de Zoom (Interface)
    "zoom": {
        "id": "zoom",
        "nome": "Nível de Zoom",
        "categoria": "Interface",
        "tipo": "grupo",
        "padrao": "100%",
        "opcoes": ["75%", "100%", "125%", "150%"],
        "icone": "ui/icones_configs/icon_zoom.png",
        "flavor_text": {
            "75%": "Visão de Satélite: Aquilo é uma batata ou uma formiga armada?",
            "100%": "Campo de visão padrão e equilibrado.",
            "125%": "Lupa: Foco total no que está na sua cara.",
            "150%": "Modo Microscópio: Você consegue ver de perto os inimigos."
        },
        "buffs": {
            "75%": {"hitbox_projeteis_mult": 1.50},
            "100%": {},
            "125%": {"dano_armas_mult": 1.10},
            "150%": {"dano_armas_mult": 1.20}
        }
    },

    # 10. Movimento pelo Mouse (Controles)
    "movimento_mouse": {
        "id": "movimento_mouse",
        "nome": "Movimento pelo Mouse",
        "categoria": "Controles",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_movimento_mouse.png",
        "flavor_text": {
            "desligado": "Controle manual com pés firmes nas teclas.",
            "ligado": "Piloto Automático: Para que servem as pernas quando o destino tem um cursor?"
        },
        "buffs": {
            "desligado": {},
            "ligado": {"drop_chance_mult": 1.40}
        }
    },

    # 11. Modificadores de Teclas (Controles)
    "keybinds": {
        "id": "keybinds",
        "nome": "Modificadores de Teclas",
        "categoria": "Controles",
        "tipo": "grupo",
        "padrao": "padrao",
        "opcoes": ["padrao", "invertido", "arrow_keys", "uma_mao", "pesadelo"],
        "icone": "ui/icones_configs/icon_keybinds.png",
        "flavor_text": {
            "padrao": "Ergonomia convencional para seres humanos normais.",
            "invertido": "Horizontes Invertidos: Para cima é o novo para baixo.",
            "arrow_keys": "Nostalgia: Lembranças dolorosas de jogar no teclado de 1998.",
            "uma_mao": "Uma Mão Só: Uma mão no volante, a outra no carinho.",
            "pesadelo": "Anarquia das Teclas: Sua memória muscular acabou de pedir demissão."
        },
        "buffs": {
            "padrao": {},
            "invertido": {"dano_armas_mult": 1.10},
            "arrow_keys": {"vel_jogador_mult": 1.15},
            "uma_mao": {"xp_ganho_mult": 1.20},
            "pesadelo": {"dano_armas_mult": 1.30}
        }
    },

    # 12. Suavização de Câmera (Controles / Câmera)
    "suavizacao_camera": {
        "id": "suavizacao_camera",
        "nome": "Suavização de Câmera",
        "categoria": "Controles / Câmera",
        "tipo": "toggle",
        "padrao": "ligado",
        "opcoes": ["ligado", "desligado"],
        "icone": "ui/icones_configs/icon_suavizacao_camera.png",
        "flavor_text": {
            "ligado": "Transições suaves para evitar tontura.",
            "desligado": "Raw Footage: Estabilização de imagem é cobrada à parte."
        },
        "buffs": {
            "ligado": {},
            "desligado": {"vel_jogador_mult": 1.08}
        }
    },

    # 13. Disparo Automático (Controles / Combate)
    "auto_fire": {
        "id": "auto_fire",
        "nome": "Disparo Automático",
        "categoria": "Controles / Combate",
        "tipo": "toggle",
        "padrao": "ligado",
        "opcoes": ["ligado", "desligado"],
        "icone": "ui/icones_configs/icon_auto_fire.png",
        "flavor_text": {
            "ligado": "Segure o botão e reze.",
            "desligado": "Trigger Discipline: Cada projétil disparado é uma decisão de vida ou morte."
        },
        "buffs": {
            "ligado": {},
            "desligado": {"dano_armas_mult": 1.15}
        }
    },

    # 14. Inimigos à Distância (Dificuldade)
    "inimigos_ranged": {
        "id": "inimigos_ranged",
        "nome": "Inimigos à Distância",
        "categoria": "Dificuldade",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_inimigos_ranged.png",
        "flavor_text": {
            "desligado": "Inimigos civilizados.",
            "ligado": "Evolução Tecnológica: Eles finalmente descobriram a tecnologia dos projéteis balísticos."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"loot_enriquecido": True}
        }
    },

    # 15. Captura de Drops por Inimigos (Dificuldade)
    "coleta_inimiga": {
        "id": "coleta_inimiga",
        "nome": "Captura de Drops por Inimigos",
        "categoria": "Dificuldade",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_coleta_inimiga.png",
        "flavor_text": {
            "desligado": "Raposo, não pegue.",
            "ligado": "Modo Raciocínio: Os inimigos se sentiram inspirados pelo Gemini 3.7 Flash."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"drops_valor_mult": 2.0}
        }
    },

    # 16. Velocidade dos Inimigos (Dificuldade)
    "velocidade_inimigos": {
        "id": "velocidade_inimigos",
        "nome": "Velocidade dos Inimigos",
        "categoria": "Dificuldade",
        "tipo": "grupo",
        "padrao": "normal",
        "opcoes": ["normal", "+25%", "+50%"],
        "icone": "ui/icones_configs/icon_velocidade_inimigos.png",
        "flavor_text": {
            "normal": "Inimigos marcham normalmente.",
            "+25%": "Overclock: Eles encontraram o botão turbo.",
            "+50%": "Surto: Injetaram energético na corrente de dados."
        },
        "buffs": {
            "normal": {},
            "+25%": {"xp_ganho_mult": 1.20, "vel_inimigos_mult": 1.25},
            "+50%": {"xp_ganho_mult": 1.40, "vel_inimigos_mult": 1.50}
        }
    },

    # 17. Vida dos Inimigos (Dificuldade)
    "vida_inimigos": {
        "id": "vida_inimigos",
        "nome": "Vida dos Inimigos",
        "categoria": "Dificuldade",
        "tipo": "grupo",
        "padrao": "normal",
        "opcoes": ["normal", "+50%", "+100%"],
        "icone": "ui/icones_configs/icon_vida_inimigos.png",
        "flavor_text": {
            "normal": "Inimigos com vida padrão.",
            "+50%": "Blindados: Blindagem adicional direto da fábrica.",
            "+100%": "Pesados: Eles estão mais densos."
        },
        "buffs": {
            "normal": {},
            "+50%": {"drop_chance_bonus": 0.20, "hp_inimigos_mult": 1.50},
            "+100%": {"drop_chance_bonus": 0.40, "hp_inimigos_mult": 2.00}
        }
    },

    # 18. Iluminação Dinâmica (Experimental / Atmosfera)
    "iluminacao": {
        "id": "iluminacao",
        "nome": "Iluminação Dinâmica",
        "categoria": "Experimental / Atmosfera",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_iluminacao.png",
        "flavor_text": {
            "desligado": "Luz do dia perpétua sobre o campo de batalha.",
            "ligado": "Modo Escuridão: Eles estão com dificuldade de te enxergar."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"dano_fora_visao_mult": 0.50}
        }
    },

    # 19. Cores Invertidas (Experimental / Visual)
    "cores_invertidas": {
        "id": "cores_invertidas",
        "nome": "Cores Invertidas",
        "categoria": "Experimental / Visual",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_cores_invertidas.png",
        "flavor_text": {
            "desligado": "Paleta de cores original e aconchegante.",
            "ligado": "Espaço Negativo: Seus olhos registraram uma reclamação no Procon."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"dano_armas_mult": 1.20}
        }
    },

    # 20. Fogo Amigo (Experimental / Risco Extremo)
    "fogo_amigo": {
        "id": "fogo_amigo",
        "nome": "Fogo Amigo",
        "categoria": "Experimental / Risco Extremo",
        "tipo": "toggle",
        "padrao": "desligado",
        "opcoes": ["desligado", "ligado"],
        "icone": "ui/icones_configs/icon_fogo_amigo.png",
        "flavor_text": {
            "desligado": "Seus tiros e explosões atravessam você inofensivamente.",
            "ligado": "Collateral Damage: Aparentemente, estilhaços de granada não leem crachá de identificação."
        },
        "buffs": {
            "desligado": {},
            "ligado": {"dano_armas_mult": 1.25, "auto_dano": True}
        }
    }
}

# =============================================================================
# 11. CONFIGURAÇÕES DE SISTEMA (SEM IMPACTO NO GAMEPLAY)
# =============================================================================

CONFIGURACOES_SISTEMA = {
    "volume_master": {
        "id": "volume_master",
        "nome": "Volume Geral",
        "tipo": "slider",
        "padrao": 100,
        "min": 0,
        "max": 100,
        "icone": "ui/icones_configs/icon_volume_master.png",
        "descricao": "Controla o volume geral de toda a aplicação."
    },
    "volume_musica": {
        "id": "volume_musica",
        "nome": "Volume da Música",
        "tipo": "slider",
        "padrao": 100,
        "min": 0,
        "max": 100,
        "icone": "ui/icones_configs/icon_volume_musica.png",
        "descricao": "Controla a trilha sonora 8-bit em loop."
    },
    "volume_sfx": {
        "id": "volume_sfx",
        "nome": "Volume dos Efeitos",
        "tipo": "slider",
        "padrao": 100,
        "min": 0,
        "max": 100,
        "icone": "ui/icones_configs/icon_volume_sfx.png",
        "descricao": "Controla tiros, explosões, pickups e menus."
    }
}

# =============================================================================
# 12. MAPA DE ARQUIVOS DE ASSETS
# =============================================================================

ASSET_PATHS = {
    # Jogador
    "jogador_idle": "sprites/jogador/batata_idle.png",
    "jogador_walk": "sprites/jogador/batata_walk_sheet.png",
    "jogador_dano": "sprites/jogador/batata_dano.png",

    # Inimigos
    "inimigo_padrao": "sprites/inimigos/inimigo_padrao.png",
    "inimigo_tank": "sprites/inimigos/inimigo_tank.png",
    "inimigo_rapido": "sprites/inimigos/inimigo_rapido.png",
    "inimigo_phasing": "sprites/inimigos/inimigo_phasing.png",
    "inimigo_blindado": "sprites/inimigos/inimigo_blindado.png",
    "inimigo_ranged": "sprites/inimigos/inimigo_ranged.png",

    # Armas
    "arma_melee": "sprites/armas/arma_melee.png",
    "arma_pistola": "sprites/armas/arma_pistola.png",
    "arma_minigun": "sprites/armas/arma_minigun.png",
    "arma_shotgun": "sprites/armas/arma_shotgun.png",
    "arma_rifle": "sprites/armas/arma_rifle.png",
    "arma_foguetes": "sprites/armas/arma_foguetes.png",
    "arma_granadas": "sprites/armas/arma_granadas.png",

    # Projéteis
    "projetil_pistola": "sprites/projeteis/projetil_pistola.png",
    "projetil_minigun": "sprites/projeteis/projetil_minigun.png",
    "projetil_shotgun": "sprites/projeteis/projetil_shotgun.png",
    "projetil_rifle": "sprites/projeteis/projetil_rifle.png",
    "projetil_foguete": "sprites/projeteis/projetil_foguete.png",
    "projetil_granada": "sprites/projeteis/projetil_granada.png",
    "projetil_inimigo": "sprites/projeteis/projetil_inimigo.png",

    # Equipamentos
    "drone_cura": "sprites/equipamentos/drone_cura.png",
    "drone_combate": "sprites/equipamentos/drone_combate.png",
    "drone_suporte": "sprites/equipamentos/drone_suporte.png",

    # Drops
    "drop_xp": "sprites/drops/drop_xp.png",
    "drop_cura": "sprites/drops/drop_cura.png",
    "drop_arma": "sprites/drops/drop_arma.png",
    "drop_equipamento": "sprites/drops/drop_equipamento.png",
    "drop_config": "sprites/drops/drop_config.png",

    # Tiles
    "tile_piso": "tiles/tile_piso.png",
    "tile_piso_alt": "tiles/tile_piso_alt.png",
    "tile_parede": "tiles/tile_parede.png",
    "obstaculo_caixa": "tiles/obstaculo_caixa.png",

    # UI
    "btn_gear": "ui/btn_gear.png",
    "card_upgrade_bg": "ui/card_upgrade_bg.png",
    "slot_inventario": "ui/slot_inventario.png",
    "btn_bg_normal": "ui/btn_bg_normal.png",
    "btn_bg_hover": "ui/btn_bg_hover.png",
    "mira_crosshair": "ui/mira_crosshair.png",

    # Áudio SFX
    "sfx_tiro_pistola": "audio/sfx/tiro_pistola.wav",
    "sfx_tiro_minigun": "audio/sfx/tiro_minigun.wav",
    "sfx_tiro_shotgun": "audio/sfx/tiro_shotgun.wav",
    "sfx_tiro_rifle": "audio/sfx/tiro_rifle.wav",
    "sfx_tiro_foguete": "audio/sfx/tiro_foguete.wav",
    "sfx_tiro_granada": "audio/sfx/tiro_granada.wav",
    "sfx_ataque_melee": "audio/sfx/ataque_melee.wav",
    "sfx_explosao": "audio/sfx/explosao.wav",
    "sfx_dano_jogador": "audio/sfx/dano_jogador.wav",
    "sfx_morte_jogador": "audio/sfx/morte_jogador.wav",
    "sfx_morte_inimigo": "audio/sfx/morte_inimigo.wav",
    "sfx_pickup_xp": "audio/sfx/pickup_xp.wav",
    "sfx_pickup_cura": "audio/sfx/pickup_cura.wav",
    "sfx_pickup_arma": "audio/sfx/pickup_arma.wav",
    "sfx_pickup_equipamento": "audio/sfx/pickup_equipamento.wav",
    "sfx_levelup": "audio/sfx/levelup.wav",
    "sfx_btn_hover": "audio/sfx/btn_hover.wav",
    "sfx_btn_click": "audio/sfx/btn_click.wav",

    # Música
    "musica_fase": "audio/musica/musica_fase.wav"
}


def obter_caminho_asset(chave: str) -> str:
    """Retorna o caminho absoluto do asset a partir da chave registrada."""
    if chave in ASSET_PATHS:
        return os.path.join(ASSETS_DIR, ASSET_PATHS[chave])
    raise KeyError(f"Asset '{chave}' não encontrado no catálogo de caminhos.")
