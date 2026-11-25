"""
Catálogo SSOT de Conquistas (Contínuas e Únicas) e Chips de Firmware — Protocolo: Batata
Zero imports de src/armas/ ou src/cenas/.
"""

from dataclasses import dataclass, field

from src.utils.traducao import t


@dataclass(frozen=True)
class ChipFirmwareDef:
    """Definição de um Chip de Firmware equipável pré-run (1..3 slots)."""
    id: str
    nome: str
    descricao: str
    categoria: str
    icone_cor: tuple[int, int, int] = (180, 120, 255)


@dataclass(frozen=True)
class MilestoneConquista:
    """Marco progressivo de uma conquista contínua."""
    meta: int
    titulo: str
    recompensas: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ConquistaContinuaDef:
    """Conquista cumulativa com 3 milestones progressivos."""
    id: str
    nome: str
    descricao: str
    evento: str
    milestones: list[MilestoneConquista] = field(default_factory=list)


@dataclass(frozen=True)
class ConquistaUnicaDef:
    """Conquista única de feito específico (Troféu ou Desbloqueio Raro)."""
    id: str
    nome: str
    descricao: str
    recompensas: list[tuple[str, str]] = field(default_factory=list)
    categoria: str = "trofeu"


# =============================================================================
# 8 CHIPS DE FIRMWARE (MODIFICADORES DE RUN)
# =============================================================================

CHIPS_FIRMWARE: dict[str, ChipFirmwareDef] = {
    "gatilho_duplo": ChipFirmwareDef(
        id="gatilho_duplo",
        nome=t("conquistas", "firmware_gatilho_duplo__nome"),
        descricao=t("conquistas", "firmware_gatilho_duplo__descricao"),
                categoria="Ofensivo",
        icone_cor=(255, 160, 60),
    ),
    "recarga_tatica": ChipFirmwareDef(
        id="recarga_tatica",
        nome=t("conquistas", "firmware_recarga_tatica__nome"),
                descricao=t("conquistas", "firmware_recarga_tatica__descricao"),
                categoria="Tático",
        icone_cor=(80, 210, 255),
    ),
    "adrenalina_overclock": ChipFirmwareDef(
        id="adrenalina_overclock",
        nome=t("conquistas", "firmware_adrenalina_overclock__nome"),
        descricao=t("conquistas", "firmware_adrenalina_overclock__descricao"),
                categoria="Mobilidade",
        icone_cor=(255, 90, 140),
    ),
    "canhoes_perimetrais": ChipFirmwareDef(
        id="canhoes_perimetrais",
        nome=t("conquistas", "firmware_canhoes_perimetrais__nome"),
                descricao=t("conquistas", "firmware_canhoes_perimetrais__descricao"),
                categoria="Ofensivo",
        icone_cor=(255, 120, 40),
    ),
    "sobrecarga_estrutural": ChipFirmwareDef(
        id="sobrecarga_estrutural",
        nome=t("conquistas", "firmware_sobrecarga_estrutural__nome"),
        descricao=t("conquistas", "firmware_sobrecarga_estrutural__descricao"),
                categoria="Ofensivo",
        icone_cor=(220, 80, 255),
    ),
    "overclock_termico": ChipFirmwareDef(
        id="overclock_termico",
        nome=t("conquistas", "firmware_overclock_termico__nome"),
                descricao=t("conquistas", "firmware_overclock_termico__descricao"),
                categoria="Reativo",
        icone_cor=(255, 200, 60),
    ),
    "sandbox_isolada": ChipFirmwareDef(
        id="sandbox_isolada",
        nome=t("conquistas", "firmware_sandbox_isolada__nome"),
        descricao=t("conquistas", "firmware_sandbox_isolada__descricao"),
                categoria="Defensivo",
        icone_cor=(90, 255, 180),
    ),
    "reset_voraz": ChipFirmwareDef(
        id="reset_voraz",
        nome=t("conquistas", "firmware_reset_voraz__nome"),
        descricao=t("conquistas", "firmware_reset_voraz__descricao"),
                categoria="Tático",
        icone_cor=(120, 240, 100),
    ),
}


# =============================================================================
# 5 CONQUISTAS CONTÍNUAS
# =============================================================================

CONQUISTAS_CONTINUAS: dict[str, ConquistaContinuaDef] = {
    "mestre_chave_inglesa": ConquistaContinuaDef(
        id="mestre_chave_inglesa",
        nome=t("conquistas", "continua_mestre_chave_inglesa__nome"),
        descricao=t("conquistas", "continua_mestre_chave_inglesa__descricao"),
                evento="parry",
        milestones=[
            MilestoneConquista(
                meta=15,
                titulo=t("conquistas", "continua_mestre_chave_inglesa__ms_0_titulo"),
                recompensas=[("habilidade", "dash"), ("arma", "smg_compacta")],
            ),
            MilestoneConquista(
                meta=50,
                titulo=t("conquistas", "continua_mestre_chave_inglesa__ms_1_titulo"),
                recompensas=[("trofeu", "reflexo_metalico")],
            ),
            MilestoneConquista(
                meta=120,
                titulo=t("conquistas", "continua_mestre_chave_inglesa__ms_2_titulo"),
                recompensas=[("opcao_config", "precisao_parry:postura_riposte"), ("slot_firmware", "+1")],
            ),
        ],
    ),
    "velocidade_de_clock": ConquistaContinuaDef(
        id="velocidade_de_clock",
        nome=t("conquistas", "continua_velocidade_de_clock__nome"),
        descricao=t("conquistas", "continua_velocidade_de_clock__descricao"),
                evento="just_dodge",
        milestones=[
            MilestoneConquista(
                meta=40,
                titulo=t("conquistas", "continua_velocidade_de_clock__ms_0_titulo"),
                recompensas=[("modificador_run", "recarga_tatica")],
            ),
            MilestoneConquista(
                meta=150,
                titulo=t("conquistas", "continua_velocidade_de_clock__ms_1_titulo"),
                recompensas=[("opcao_config", "dash_rastro:thread_fantasma")],
            ),
            MilestoneConquista(
                meta=350,
                titulo=t("conquistas", "continua_velocidade_de_clock__ms_2_titulo"),
                recompensas=[("opcao_config", "dash_protocolo:sombra_espelho")],
            ),
        ],
    ),
    "depurador_escritorio": ConquistaContinuaDef(
        id="depurador_escritorio",
        nome=t("conquistas", "continua_depurador_escritorio__nome"),
                descricao=t("conquistas", "continua_depurador_escritorio__descricao"),
        evento="abate",
        milestones=[
            MilestoneConquista(
                meta=250,
                titulo=t("conquistas", "continua_depurador_escritorio__ms_0_titulo"),
                recompensas=[("trofeu", "depurador_m1")],
            ),
            MilestoneConquista(
                meta=1500,
                titulo=t("conquistas", "continua_depurador_escritorio__ms_1_titulo"),
                recompensas=[("modificador_run", "adrenalina_overclock"), ("slot_firmware", "+1")],
            ),
            MilestoneConquista(
                meta=5000,
                titulo=t("conquistas", "continua_depurador_escritorio__ms_2_titulo"),
                recompensas=[("arma", "lanca_chamas")],
            ),
        ],
    ),
    "cacador_hardware": ConquistaContinuaDef(
        id="cacador_hardware",
        nome=t("conquistas", "continua_cacador_hardware__nome"),
                descricao=t("conquistas", "continua_cacador_hardware__descricao"),
        evento="miniboss_rapido",
        milestones=[
            MilestoneConquista(
                meta=4,
                titulo=t("conquistas", "continua_cacador_hardware__ms_0_titulo"),
                recompensas=[("modificador_run", "canhoes_perimetrais")],
            ),
            MilestoneConquista(
                meta=16,
                titulo=t("conquistas", "continua_cacador_hardware__ms_1_titulo"),
                recompensas=[("modificador_run", "sobrecarga_estrutural")],
            ),
            MilestoneConquista(
                meta=40,
                titulo=t("conquistas", "continua_cacador_hardware__ms_2_titulo"),
                recompensas=[("arma", "rifle_arco")],
            ),
        ],
    ),
    "sobrevivente_caos": ConquistaContinuaDef(
        id="sobrevivente_caos",
        nome=t("conquistas", "continua_sobrevivente_caos__nome"),
        descricao=t("conquistas", "continua_sobrevivente_caos__descricao"),
        evento="vitoria_boss",
        milestones=[
            MilestoneConquista(
                meta=1,
                titulo=t("conquistas", "continua_sobrevivente_caos__ms_0_titulo"),
                recompensas=[("modificador_run", "overclock_termico")],
            ),
            MilestoneConquista(
                meta=3,
                titulo=t("conquistas", "continua_sobrevivente_caos__ms_1_titulo"),
                recompensas=[("opcao_config", "dash_protocolo:rollback_estado")],
            ),
            MilestoneConquista(
                meta=7,
                titulo=t("conquistas", "continua_sobrevivente_caos__ms_2_titulo"),
                recompensas=[("configuracao", "latencia_ping"), ("slot_firmware", "+1")],
            ),
        ],
    ),
}


# =============================================================================
# 11 CONQUISTAS ÚNICAS (7 TROFÉUS + 4 RARAS COM DESBLOQUEIO)
# =============================================================================

CONQUISTAS_UNICAS: dict[str, ConquistaUnicaDef] = {
    "monge_tibetano": ConquistaUnicaDef(
        id="monge_tibetano",
        nome=t("conquistas", "unica_monge_tibetano__nome"),
        descricao=t("conquistas", "unica_monge_tibetano__descricao"),
                recompensas=[("trofeu", "monge_tibetano")],
        categoria="trofeu",
    ),
    "cabo_vga_solto": ConquistaUnicaDef(
        id="cabo_vga_solto",
        nome=t("conquistas", "unica_cabo_vga_solto__nome"),
        descricao=t("conquistas", "unica_cabo_vga_solto__descricao"),
                recompensas=[("trofeu", "cabo_vga_solto")],
        categoria="trofeu",
    ),
    "blindado_escritorio": ConquistaUnicaDef(
        id="blindado_escritorio",
        nome=t("conquistas", "unica_blindado_escritorio__nome"),
                descricao=t("conquistas", "unica_blindado_escritorio__descricao"),
        recompensas=[("trofeu", "blindado_escritorio")],
        categoria="trofeu",
    ),
    "boliche_corporativo": ConquistaUnicaDef(
        id="boliche_corporativo",
        nome=t("conquistas", "unica_boliche_corporativo__nome"),
        descricao=t("conquistas", "unica_boliche_corporativo__descricao"),
                recompensas=[("trofeu", "boliche_corporativo")],
        categoria="trofeu",
    ),
    "zero_visao_cem_fe": ConquistaUnicaDef(
        id="zero_visao_cem_fe",
        nome=t("conquistas", "unica_zero_visao_cem_fe__nome"),
                descricao=t("conquistas", "unica_zero_visao_cem_fe__descricao"),
                recompensas=[("trofeu", "zero_visao_cem_fe")],
        categoria="trofeu",
    ),
    "auto_sabotagem": ConquistaUnicaDef(
        id="auto_sabotagem",
        nome=t("conquistas", "unica_auto_sabotagem__nome"),
        descricao=t("conquistas", "unica_auto_sabotagem__descricao"),
        recompensas=[("trofeu", "auto_sabotagem")],
        categoria="trofeu",
    ),
    "limpeza_de_disco": ConquistaUnicaDef(
        id="limpeza_de_disco",
        nome=t("conquistas", "unica_limpeza_de_disco__nome"),
        descricao=t("conquistas", "unica_limpeza_de_disco__descricao"),
                recompensas=[("trofeu", "limpeza_de_disco")],
        categoria="trofeu",
    ),
    "intocavel_rh": ConquistaUnicaDef(
        id="intocavel_rh",
        nome=t("conquistas", "unica_intocavel_rh__nome"),
                descricao=t("conquistas", "unica_intocavel_rh__descricao"),
                recompensas=[("modificador_run", "sandbox_isolada")],
        categoria="desbloqueio",
    ),
    "reset_infinito": ConquistaUnicaDef(
        id="reset_infinito",
        nome=t("conquistas", "unica_reset_infinito__nome"),
        descricao=t("conquistas", "unica_reset_infinito__descricao"),
        recompensas=[("modificador_run", "reset_voraz")],
        categoria="desbloqueio",
    ),
    "modo_batata_supremo": ConquistaUnicaDef(
        id="modo_batata_supremo",
        nome=t("conquistas", "unica_modo_batata_supremo__nome"),
        descricao=t("conquistas", "unica_modo_batata_supremo__descricao"),
                recompensas=[("arma", "bastao_choque")],
        categoria="desbloqueio",
    ),
    "primeiro_overclock_sujo": ConquistaUnicaDef(
        id="primeiro_overclock_sujo",
        nome=t("conquistas", "unica_primeiro_overclock_sujo__nome"),
        descricao=t("conquistas", "unica_primeiro_overclock_sujo__descricao"),
                recompensas=[("modificador_run", "gatilho_duplo")],
        categoria="desbloqueio",
    ),
}
