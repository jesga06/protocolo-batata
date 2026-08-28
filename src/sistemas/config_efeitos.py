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
        if "critico_chance" in mod_dict:
            mods.critico_chance += float(mod_dict["critico_chance"])
        if "critico_mult" in mod_dict:
            mods.critico_mult = float(mod_dict["critico_mult"])

        # 7. Flags booleanas
        if "auto_dano" in mod_dict:
            mods.auto_dano = mods.auto_dano or bool(mod_dict["auto_dano"])
        if "loot_enriquecido" in mod_dict:
            mods.loot_enriquecido = mods.loot_enriquecido or bool(mod_dict["loot_enriquecido"])

    return mods
