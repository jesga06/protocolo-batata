"""
Calculadora de Efeitos e Modificadores de Gameplay — Protocolo: Batata
SSOT: CONFIGURACOES.md
Calcula o empilhamento multiplicativo puro de modificadores com base nas configurações
desbloqueadas e ativas. Configurações não desbloqueadas são estritamente forçadas para
o valor padrão neutro (sem nenhum buff).
"""

from dataclasses import dataclass
from typing import Union, Iterable
from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY


@dataclass
class ModificadoresGameplay:
    """Estrutura com todos os modificadores de gameplay consolidados."""
    dano_armas_mult: float = 1.0
    dano_explosivos_mult: float = 1.0
    vel_jogador_mult: float = 1.0
    xp_ganho_mult: float = 1.0
    drop_chance_bonus: float = 0.0
    drop_chance_mult: float = 1.0
    drops_valor_mult: float = 1.0
    hp_inimigos_mult: float = 1.0
    vel_inimigos_mult: float = 1.0
    dano_inimigos_mult: float = 1.0
    dano_fora_visao_mult: float = 1.0
    hitbox_projeteis_mult: float = 1.0
    critico_chance: float = 0.0
    critico_mult: float = 1.0
    auto_dano: bool = False
    loot_enriquecido: bool = False

    # Modificadores Mecânicos / Sistêmicos (The Juice)
    auto_fire_burst: bool = False
    vsync_tear_refraction: bool = False
    graficos_shrapnel: bool = False
    screen_shake_stagger: bool = False
    resolucao_chunky_hitbox: float = 1.0
    fps_stutter_dodge: bool = False
    hud_pulse_magnet: bool = False
    damage_numbers_knockback: bool = False
    fogo_amigo_rocket_jump: bool = False
    movimento_ram_collision: bool = False
    keybinds_overdrive_dash: bool = False
    motion_blur_ghosting: bool = False
    coleta_inimiga: bool = False
    parry_precisao: str = "padrao"
    parry_efeito: str = "padrao"
    controles_tanque: bool = False
    dano_recebido_mult: float = 1.0


def calcular_modificadores(
    configs_desbloqueadas: Union[set, list, tuple],
    configs_ativas: dict
) -> ModificadoresGameplay:
    """
    Calcula os modificadores consolidados de gameplay.
    Regra Fundamental:
    - Se a configuração NÃO estiver em configs_desbloqueadas, seu valor é travado
      no valor padrão (neutro, sem efeitos).
    - Se a configuração estiver desbloqueada, aplica os multiplicadores da opção ativa.
    """
    desbloqueadas_set = set(configs_desbloqueadas) if configs_desbloqueadas else set()
    mods = ModificadoresGameplay()

    for config_id, conf_def in CONFIGURACOES_GAMEPLAY.items():
        # Se a config não foi desbloqueada, usa o valor neutro padrão
        if config_id not in desbloqueadas_set:
            valor_ativo = conf_def.valor_padrao
        else:
            valor_ativo = configs_ativas.get(config_id, conf_def.valor_padrao)

        # Obtém os modificadores da opção selecionada
        chave_opcao = str(valor_ativo)
        if chave_opcao not in conf_def.opcoes:
            chave_opcao = str(conf_def.valor_padrao)

        opcao = conf_def.opcoes.get(chave_opcao)
        if not opcao or not opcao.modificadores:
            continue

        mod_dict = opcao.modificadores

        # 1. Multiplicadores de Dano
        if "dano_armas_mult" in mod_dict:
            mods.dano_armas_mult *= float(mod_dict["dano_armas_mult"])
        if "dano_explosivos_mult" in mod_dict:
            mods.dano_explosivos_mult *= float(mod_dict["dano_explosivos_mult"])

        # 2. Multiplicador de Velocidade do Jogador
        if "vel_jogador_mult" in mod_dict:
            mods.vel_jogador_mult *= float(mod_dict["vel_jogador_mult"])

        # 3. Multiplicador de Ganho de XP
        if "xp_ganho_mult" in mod_dict:
            mods.xp_ganho_mult *= float(mod_dict["xp_ganho_mult"])

        # 4. Modificadores de Drops e Coleta
        if "drop_chance_bonus" in mod_dict:
            mods.drop_chance_bonus += float(mod_dict["drop_chance_bonus"])
        if "drop_chance_mult" in mod_dict:
            mods.drop_chance_mult *= float(mod_dict["drop_chance_mult"])
        if "drops_valor_mult" in mod_dict:
            mods.drops_valor_mult *= float(mod_dict["drops_valor_mult"])

        # 5. Modificadores de Inimigos (HP, Velocidade, Dano)
        if "hp_inimigos_mult" in mod_dict:
            mods.hp_inimigos_mult *= float(mod_dict["hp_inimigos_mult"])
        if "vel_inimigos_mult" in mod_dict:
            mods.vel_inimigos_mult *= float(mod_dict["vel_inimigos_mult"])
        if "dano_inimigos_mult" in mod_dict:
            mods.dano_inimigos_mult *= float(mod_dict["dano_inimigos_mult"])
        if "dano_fora_visao_mult" in mod_dict:
            mods.dano_fora_visao_mult *= float(mod_dict["dano_fora_visao_mult"])

        # 6. Projéteis e Críticos
        if "hitbox_projeteis_mult" in mod_dict:
            mods.hitbox_projeteis_mult *= float(mod_dict["hitbox_projeteis_mult"])
        if "resolucao_chunky_hitbox" in mod_dict:
            mods.resolucao_chunky_hitbox *= float(mod_dict["resolucao_chunky_hitbox"])
        if "critico_chance" in mod_dict:
            mods.critico_chance += float(mod_dict["critico_chance"])
        if "critico_mult" in mod_dict:
            mods.critico_mult *= float(mod_dict["critico_mult"])

        # 7. Flags booleanas e mecânicas
        if "auto_dano" in mod_dict:
            mods.auto_dano = mods.auto_dano or bool(mod_dict["auto_dano"])
        if "loot_enriquecido" in mod_dict:
            mods.loot_enriquecido = mods.loot_enriquecido or bool(mod_dict["loot_enriquecido"])
        if "auto_fire_burst" in mod_dict:
            mods.auto_fire_burst = mods.auto_fire_burst or bool(mod_dict["auto_fire_burst"])
        if "vsync_tear_refraction" in mod_dict:
            mods.vsync_tear_refraction = mods.vsync_tear_refraction or bool(mod_dict["vsync_tear_refraction"])
        if "graficos_shrapnel" in mod_dict:
            mods.graficos_shrapnel = mods.graficos_shrapnel or bool(mod_dict["graficos_shrapnel"])
        if "screen_shake_stagger" in mod_dict:
            mods.screen_shake_stagger = mods.screen_shake_stagger or bool(mod_dict["screen_shake_stagger"])
        if "fps_stutter_dodge" in mod_dict:
            mods.fps_stutter_dodge = mods.fps_stutter_dodge or bool(mod_dict["fps_stutter_dodge"])
        if "hud_pulse_magnet" in mod_dict:
            mods.hud_pulse_magnet = mods.hud_pulse_magnet or bool(mod_dict["hud_pulse_magnet"])
        if "damage_numbers_knockback" in mod_dict:
            mods.damage_numbers_knockback = mods.damage_numbers_knockback or bool(mod_dict["damage_numbers_knockback"])
        if "fogo_amigo_rocket_jump" in mod_dict:
            mods.fogo_amigo_rocket_jump = mods.fogo_amigo_rocket_jump or bool(mod_dict["fogo_amigo_rocket_jump"])
        if "movimento_ram_collision" in mod_dict:
            mods.movimento_ram_collision = mods.movimento_ram_collision or bool(mod_dict["movimento_ram_collision"])
        if "keybinds_overdrive_dash" in mod_dict:
            mods.keybinds_overdrive_dash = mods.keybinds_overdrive_dash or bool(mod_dict["keybinds_overdrive_dash"])
        if "motion_blur_ghosting" in mod_dict:
            mods.motion_blur_ghosting = mods.motion_blur_ghosting or bool(mod_dict["motion_blur_ghosting"])
        if "coleta_inimiga" in mod_dict:
            mods.coleta_inimiga = mods.coleta_inimiga or bool(mod_dict["coleta_inimiga"])
        if "parry_precisao" in mod_dict:
            mods.parry_precisao = str(mod_dict["parry_precisao"])
        if "parry_efeito" in mod_dict:
            mods.parry_efeito = str(mod_dict["parry_efeito"])
        if "controles_tanque" in mod_dict:
            mods.controles_tanque = mods.controles_tanque or bool(mod_dict["controles_tanque"])
        if "dano_recebido_mult" in mod_dict:
            mods.dano_recebido_mult *= float(mod_dict["dano_recebido_mult"])

    return mods
