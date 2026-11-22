"""
Constantes Globais — Protocolo: Batata
Single Source of Truth no código para dimensões, cores, valores baselines,
caminhos de assets e catálogo de configurações (alinhado com CONFIGURACOES.md).
"""

import os
import sys

# =============================================================================
# 1. DIRETÓRIOS E CAMINHOS
# =============================================================================


def _obter_data_dir(project_root: str) -> str:
    """Retorna diretório gravável para saves, suportando execução normal e empacotada (PyInstaller)."""
    if not getattr(sys, "frozen", False):
        return os.path.join(project_root, "data")

    app_name = "ProtocoloBatata"
    exec_dir = os.path.dirname(os.path.abspath(sys.executable))

    # No macOS, bundles .app podem ser somente leitura (App Translocation)
    if sys.platform != "darwin":
        portable_dir = os.path.join(exec_dir, "data")
        try:
            os.makedirs(portable_dir, exist_ok=True)
            if os.access(portable_dir, os.W_OK):
                return portable_dir
        except OSError:
            pass

    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, app_name)
    if sys.platform == "darwin":
        return os.path.expanduser(f"~/Library/Application Support/{app_name}")
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, app_name)


if getattr(sys, "frozen", False):
    PROJECT_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRC_DIR = os.path.join(PROJECT_ROOT, "src")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
DATA_DIR = _obter_data_dir(PROJECT_ROOT)
SAVE_FILE_PATH = os.path.join(DATA_DIR, "save.json")

# =============================================================================
# 2. JANELA E VIRTUAL BUFFER
# =============================================================================

LARGURA_TELA = 1280
ALTURA_TELA = 720
LARGURA_ARENA = 2240
ALTURA_ARENA = 1560
TITULO_JOGO = "Protocolo: Batata"
FPS_PADRAO = 0  # 0 = Ilimitado (sem cap de FPS)
CAMERA_DAMPING_K = 0.115
DT_CLAMP_MAX = 0.05

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
ROXO_ACENTO = (175, 75, 255)
ROXO_CLARO = (215, 140, 255)
ROXO_ESCURO = (70, 20, 110)
AZUL_CIANO = ROXO_ACENTO  # Aliasing para compatibilidade retroativa com novo tema roxo
ROXO_DROPS = (175, 75, 255)
LARANJA_ALERTA = (255, 140, 0)
DOURADO = (255, 215, 0)

# =============================================================================
# 4. JOGADOR (BATATA) — BASELINES
# =============================================================================

JOGADOR_HP_MAX_PADRAO = 150
JOGADOR_VELOCIDADE_PADRAO = 260.0  # pixels por segundo (+30%)
JOGADOR_LARGURA = 32
JOGADOR_ALTURA = 32
JOGADOR_COOLDOWN_DANO_FLASH = 0.15  # segundos de flash vermelho
JOGADOR_INVULNERABILIDADE_TEMPO = 0.2  # segundos mínimos entre frames de dano

# Dash Direcional (Desbloqueável Permanente)
DASH_DURACAO = 0.22
DASH_MULT_VEL = 2.6
DASH_IFRAMES_BASE = 0.35
DASH_COOLDOWN = 1.8
DASH_PARRY_META = 100

# =============================================================================
# 5. INIMIGOS — BASELINES
# =============================================================================

# Inimigo Padrão (Estagiário - 40 HP, 4 tiros de pistola ou 4 golpes melee)
INIMIGO_PADRAO_HP = 40
INIMIGO_PADRAO_VELOCIDADE = 130.0
INIMIGO_PADRAO_DANO = 10
INIMIGO_PADRAO_COOLDOWN_ATAQUE = 0.4
INIMIGO_PADRAO_XP = 5

# Inimigo Tanque (Geladeira Industrial - 120 HP)
INIMIGO_TANK_HP = 120
INIMIGO_TANK_VELOCIDADE = 65.0
INIMIGO_TANK_DANO = 20
INIMIGO_TANK_COOLDOWN_ATAQUE = 0.7
INIMIGO_TANK_XP = 25

# Inimigo Rápido (Viciado em Cafeína - 20 HP, 2 tiros de pistola ou 2 golpes melee)
INIMIGO_RAPIDO_HP = 20
INIMIGO_RAPIDO_VELOCIDADE = 234.0
INIMIGO_RAPIDO_DANO = 8
INIMIGO_RAPIDO_COOLDOWN_ATAQUE = 0.25
INIMIGO_RAPIDO_XP = 8

# Inimigo Phasing (Warranty Void - 35 HP)
INIMIGO_PHASING_HP = 35
INIMIGO_PHASING_VELOCIDADE = 117.0
INIMIGO_PHASING_DANO = 12
INIMIGO_PHASING_COOLDOWN_ATAQUE = 0.4
INIMIGO_PHASING_XP = 12
INIMIGO_PHASING_CICLO = 3.0  # a cada 3s entra em fase por 1.2s

# Inimigo Blindado (Ballistic Enthusiast - 50 HP)
INIMIGO_BLINDADO_HP = 50
INIMIGO_BLINDADO_VELOCIDADE = 97.5
INIMIGO_BLINDADO_DANO = 15
INIMIGO_BLINDADO_COOLDOWN_ATAQUE = 0.5
INIMIGO_BLINDADO_XP = 15

# Inimigo Ranged (Atirador Blaster - 30 HP)
INIMIGO_RANGED_HP = 30
INIMIGO_RANGED_VELOCIDADE = 104.0
INIMIGO_RANGED_DANO = 10
INIMIGO_RANGED_COOLDOWN_ATAQUE = 1.2
INIMIGO_RANGED_XP = 15
INIMIGO_RANGED_DISTANCIA_TIRO = 280.0

# Inimigo Impressora Térmica (Artilharia Pesada - 75 HP)
INIMIGO_IMPRESSORA_HP = 75
INIMIGO_IMPRESSORA_VELOCIDADE = 85.0
INIMIGO_IMPRESSORA_DANO = 12
INIMIGO_IMPRESSORA_XP = 22

# Inimigo Ninja (Assassino de TI - Dash + Parry, máx 2 ativos, 20s spawn CD)
INIMIGO_NINJA_HP = 55
INIMIGO_NINJA_VELOCIDADE = 195.0
INIMIGO_NINJA_DANO = 14
INIMIGO_NINJA_XP = 28
NINJA_MAX_ATIVOS = 2
NINJA_COOLDOWN_SPAWN = 20.0

# Cubo Criogênico (Goon de Gelo do Boss)
INIMIGO_CUBO_CRIOGENICO_HP = 45
INIMIGO_CUBO_CRIOGENICO_VELOCIDADE = 155.0
INIMIGO_CUBO_CRIOGENICO_DANO = 12
INIMIGO_CUBO_CRIOGENICO_XP = 10

# Mini-Boss e Chefe Final (Geladeira Tsunami)
MINIBOSS_TEMPO_SOBREAQUECIMENTO = 60.0
BOSS_GELADEIRA_LARGURA = 112
BOSS_GELADEIRA_ALTURA = 156
BOSS_GELADEIRA_HP_BASE = 50000
BOSS_GELADEIRA_DANO_CONTATO = 30
BOSS_GELADEIRA_VELOCIDADE = 268.0
BOSS_GELADEIRA_NOME = "GELADEIRA TSUNAMI"
BOSS_GELADEIRA_FLAVOR = "The Perfect Sound™"

GELADEIRA_TSUNAMI_LARGURA = 112
GELADEIRA_TSUNAMI_ALTURA = 156
GELADEIRA_TSUNAMI_HP = 50000
GELADEIRA_TSUNAMI_DANO = 30
GELADEIRA_TSUNAMI_VELOCIDADE = 268.0
GELADEIRA_TSUNAMI_NOME = "GELADEIRA TSUNAMI"
GELADEIRA_TSUNAMI_FLAVOR = "The Perfect Sound™"

# =============================================================================
# 6. SPAWN DE INIMIGOS — CONFIGURAÇÃO (+50% INTERVALO ENTRE WAVES)
# =============================================================================

SPAWN_INTERVALO_INICIAL = 1.75
SPAWN_INTERVALO_MINIMO = 0.45
SPAWN_DISTANCIA_OFFSET = 80.0
SPAWN_MAX_ATIVOS = 400
TEMPO_VITORIA = 600.0  # Constante legada mantida para compatibilidade de testes (vitória agora requer derrotar Geladeira Tsunami)


# =============================================================================
# 7. ARMAS E PROJÉTEIS — BASELINES
# =============================================================================

# Slot 1: Melee (Chave de Manutenção)
MELEE_DANO = 10
MELEE_COOLDOWN = 0.6
MELEE_ALCANCE = 109.0  # +25px de alcance base
MELEE_KNOCKBACK = 360.0
MELEE_ALVOS_MAX = 2
MELEE_ARCO_GRAUS = 90.0  # Abertura de cone exigindo precisão no parry (90º)

# Slot 2: Pistola (Padrão de Fábrica - 10 Dano)
PISTOLA_DANO = 10
PISTOLA_COOLDOWN = 0.33
PISTOLA_VELOCIDADE_PROJETIL = 420.0
PISTOLA_ALCANCE_MAX = 800.0

# Slot 3: Armas Especiais Temporárias (+50% de Munição)
MINIGUN_DANO = 6
MINIGUN_COOLDOWN = 0.08
MINIGUN_VELOCIDADE_PROJETIL = 550.0
MINIGUN_MUNICIAO_MAX = 300

SHOTGUN_DANO = 10
SHOTGUN_COOLDOWN = 0.70
SHOTGUN_VELOCIDADE_PROJETIL = 420.0
SHOTGUN_PELLETS = 9
SHOTGUN_SPREAD_ANGULO = 0.45
SHOTGUN_MUNICIAO_MAX = 60

RIFLE_DANO = 18
RIFLE_COOLDOWN = 0.18
RIFLE_VELOCIDADE_PROJETIL = 650.0
RIFLE_MUNICIAO_MAX = 120

FOGUETES_DANO = 60
FOGUETES_COOLDOWN = 1.20
FOGUETES_VELOCIDADE_PROJETIL = 140.0
FOGUETES_RAIO_EXPLOSAO = 80.0
FOGUETES_MUNICIAO_MAX = 24

GRANADAS_DANO = 45
GRANADAS_COOLDOWN = 0.90
GRANADAS_VELOCIDADE_PROJETIL = 280.0
GRANADAS_RAIO_EXPLOSAO = 65.0
GRANADAS_MUNICIAO_MAX = 32

RAILGUN_DANO = 165
RAILGUN_COOLDOWN = 0.95
RAILGUN_CHARGE_TIME = 0.0
RAILGUN_VELOCIDADE_PROJETIL = 1400.0
RAILGUN_MUNICIAO_MAX = 10

# =============================================================================
# 8. EQUIPAMENTOS (DRONES) — BASELINES
# =============================================================================

DRONE_DURACAO = 30.0  # Duração de 30 segundos em órbita
DRONE_ORBITA_RAIO = 48.0
DRONE_ORBITA_VELOCIDADE = 2.5
DRONE_CURA_VALOR = 5
DRONE_CURA_INTERVALO = 3.0
DRONE_COMBATE_DANO = 8
DRONE_COMBATE_INTERVALO = 1.0
DRONE_COMBATE_ALCANCE = 350.0

# =============================================================================
# 9. DROPS E PROGRESSÃO TEMPORÁRIA
# =============================================================================

DROP_XP_VALOR_BASE = 5
DROP_CURA_VALOR_BASE = 35
DROP_TEMPO_DESAPARECER = 60.0
DROP_TEMPO_SCAVENGER_ATIVAR = 10.0
DROP_LARGURA = 42
DROP_ALTURA = 42

# =============================================================================
# 10. CATÁLOGO COMPLETO DE CONFIGURAÇÕES (SSOT: src.sistemas.config_dados)
# =============================================================================

TOTAL_CONFIGS_GAMEPLAY = 23

# Re-export de CONFIGURACOES_GAMEPLAY, CONFIGURACOES_CATALOGO e CONFIGURACOES_SISTEMA
# localizado ao final do módulo para evitar importação circular de pacotes.

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
    "inimigo_ninja": "sprites/inimigos/inimigo_ninja.png",
    "boss_geladeira_tsunami": "sprites/inimigos/geladeira_tsunami.png",

    # Armas
    "arma_melee": "sprites/armas/arma_melee.png",
    "arma_pistola": "sprites/armas/arma_pistola.png",
    "arma_minigun": "sprites/armas/arma_minigun.png",
    "arma_shotgun": "sprites/armas/arma_shotgun.png",
    "arma_rifle": "sprites/armas/arma_rifle.png",
    "arma_foguetes": "sprites/armas/arma_foguetes.png",
    "arma_granadas": "sprites/armas/arma_granadas.png",
    "arma_railgun": "sprites/armas/arma_railgun.png",

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
    "drop_overclock": "sprites/drops/drop_config.png",

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

    # UI - Ícones de Configurações
    "icon_auto_fire": "ui/icones_configs/icon_auto_fire.png",
    "icon_coleta_inimiga": "ui/icones_configs/icon_coleta_inimiga.png",
    "icon_controles_tanque": "ui/icones_configs/icon_controles_tanque.png",
    "icon_cores_invertidas": "ui/icones_configs/icon_cores_invertidas.png",
    "icon_damage_numbers": "ui/icones_configs/icon_damage_numbers.png",
    "icon_efeito_parry": "ui/icones_configs/icon_efeito_parry.png",
    "icon_fogo_amigo": "ui/icones_configs/icon_fogo_amigo.png",
    "icon_fps_cap": "ui/icones_configs/icon_fps_cap.png",
    "icon_graficos_qualidade": "ui/icones_configs/icon_graficos_qualidade.png",
    "icon_hud": "ui/icones_configs/icon_hud.png",
    "icon_iluminacao": "ui/icones_configs/icon_iluminacao.png",
    "icon_inimigos_ranged": "ui/icones_configs/icon_inimigos_ranged.png",
    "icon_keybinds": "ui/icones_configs/icon_keybinds.png",
    "icon_motion_blur": "ui/icones_configs/icon_motion_blur.png",
    "icon_movimento_mouse": "ui/icones_configs/icon_movimento_mouse.png",
    "icon_precisao_parry": "ui/icones_configs/icon_precisao_parry.png",
    "icon_resolucao": "ui/icones_configs/icon_resolucao.png",
    "icon_screen_shake": "ui/icones_configs/icon_screen_shake.png",
    "icon_suavizacao_camera": "ui/icones_configs/icon_suavizacao_camera.png",
    "icon_velocidade_inimigos": "ui/icones_configs/icon_velocidade_inimigos.png",
    "icon_vida_inimigos": "ui/icones_configs/icon_vida_inimigos.png",
    "icon_volume_master": "ui/icones_configs/icon_volume_master.png",
    "icon_volume_musica": "ui/icones_configs/icon_volume_musica.png",
    "icon_volume_sfx": "ui/icones_configs/icon_volume_sfx.png",
    "icon_vsync": "ui/icones_configs/icon_vsync.png",
    "icon_zoom": "ui/icones_configs/icon_zoom.png",

    # Áudio SFX
    "sfx_tiro_pistola": "audio/sfx/tiro_pistola.wav",
    "sfx_tiro_minigun": "audio/sfx/tiro_minigun.wav",
    "sfx_tiro_shotgun": "audio/sfx/tiro_shotgun.wav",
    "sfx_tiro_rifle": "audio/sfx/tiro_rifle.wav",
    "sfx_tiro_foguete": "audio/sfx/tiro_foguete.wav",
    "sfx_tiro_granada": "audio/sfx/tiro_granada.wav",
    "sfx_tiro_railgun": "audio/sfx/tiro_railgun.wav",
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
    "musica_fase": "audio/musica/heavy is the bit.wav",
    "musica_boss": "audio/musica/geladeira tsunami.wav",
    "musica_menu": "audio/musica/8bits-control.wav",
    "musica_anticipation": "audio/musica/8bits-anticipation.wav",
    "musica_anticipation_muffled": "audio/musica/8bits-anticipation-muffled.wav",
    "musica_hold": "audio/musica/8bits-hold.wav",
    "musica_hold_muffled": "audio/musica/8bits-hold-muffled.wav",
    "musica_assault_intro": "audio/musica/8bits-assault-intro.wav",
    "musica_assault_intro_muffled": "audio/musica/8bits-assault-intro-muffled.wav",
    "musica_assault": "audio/musica/8bits-assault.wav",
    "musica_assault_muffled": "audio/musica/8bits-assault-muffled.wav",
}

# =============================================================================
# SISTEMA DE MÚSICA DINÂMICA
# =============================================================================
MUSICA_VOLUME_BASE = 0.4
MUSICA_TEMPO_ASSAULT = 50.0
MUSICA_LOOKAHEAD_SEGUNDOS = 0.35
MUSICA_TRANSICAO_ABAFADO_SEGUNDOS = 0.06


def obter_caminho_asset(chave: str) -> str:
    """Retorna o caminho absoluto do asset a partir da chave registrada."""
    if chave in ASSET_PATHS:
        return os.path.join(ASSETS_DIR, ASSET_PATHS[chave])
    raise KeyError(f"Asset '{chave}' não encontrado no catálogo de caminhos.")


# Re-export e aliases SSOT a partir de src.sistemas.config_dados
from src.sistemas.config_dados import (
    CONFIGURACOES_GAMEPLAY,
    CONFIGURACOES_GAMEPLAY as CONFIGURACOES_CATALOGO,
    CONFIGURACOES_SISTEMA,
)
