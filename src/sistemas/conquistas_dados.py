"""
Catálogo SSOT de Conquistas (Contínuas e Únicas) e Chips de Firmware — Protocolo: Batata
Zero imports de src/armas/ ou src/cenas/.
"""

from dataclasses import dataclass, field


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
# 9 CHIPS DE FIRMWARE (MODIFICADORES DE RUN)
# =============================================================================

CHIPS_FIRMWARE: dict[str, ChipFirmwareDef] = {
    "gatilho_duplo": ChipFirmwareDef(
        id="gatilho_duplo",
        nome="Gatilho Duplo",
        descricao="Após Dash ou Parry, próximo disparo sai duplo (2º projétil ~60% dano e -0,4s CD no Dash).",
        categoria="Ofensivo",
        icone_cor=(255, 160, 60),
    ),
    "recarga_tatica": ChipFirmwareDef(
        id="recarga_tatica",
        nome="Recarga Tática",
        descricao="A cada 3 dashes, recupera ~25% de munição (Slot 3/pente) + 1 pilha de blindagem (-8% dano, máx. 3 por 4s).",
        categoria="Tático",
        icone_cor=(80, 210, 255),
    ),
    "adrenalina_overclock": ChipFirmwareDef(
        id="adrenalina_overclock",
        nome="Adrenalina Overclock",
        descricao="Abater Elite, destruir Totem ou 5 abates rápidos concede pico decrescente de +45% vel. e +35% cadência por 3,5s.",
        categoria="Mobilidade",
        icone_cor=(255, 90, 140),
    ),
    "canhoes_perimetrais": ChipFirmwareDef(
        id="canhoes_perimetrais",
        nome="Canhões Perimetrais",
        descricao="6 setores angulares ao redor de Cleiton com CD individual; atirar na direção de um setor pronto dispara rajada flamejante extra.",
        categoria="Ofensivo",
        icone_cor=(255, 120, 40),
    ),
    "sobrecarga_estrutural": ChipFirmwareDef(
        id="sobrecarga_estrutural",
        nome="Sobrecarga Estrutural",
        descricao="3 tiros consecutivos no mesmo alvo fragmentam blindagem (+20% dano recebido 4s + explosão perfurante).",
        categoria="Ofensivo",
        icone_cor=(220, 80, 255),
    ),
    "overclock_termico": ChipFirmwareDef(
        id="overclock_termico",
        nome="Overclock Térmico",
        descricao="Dano recebido acumula Carga Residual (5s, até +30% cadência) descarregada no próximo Parry ou Tiro Sobrecarregado.",
        categoria="Reativo",
        icone_cor=(255, 200, 60),
    ),
    "sandbox_isolada": ChipFirmwareDef(
        id="sandbox_isolada",
        nome="Sandbox Isolada",
        descricao="CD ~28s; em Parry perfeito cria cúpula fixa no chão (3,5s) que bloqueia projéteis externos.",
        categoria="Defensivo",
        icone_cor=(90, 255, 180),
    ),
    "reset_voraz": ChipFirmwareDef(
        id="reset_voraz",
        nome="Reset Voraz",
        descricao="Abates dentro de 2s após Dash ou Parry reduzem em 50% o cooldown restante de ambos.",
        categoria="Tático",
        icone_cor=(120, 240, 100),
    ),
    "medidor_estilo": ChipFirmwareDef(
        id="medidor_estilo",
        nome="Medidor de Estilo",
        descricao="Ativa Ranks D → C → B → A → S e pulso Overdrive no SistemaCombo universal (drones excluídos).",
        categoria="Estilo",
        icone_cor=(255, 220, 70),
    ),
}


# =============================================================================
# 5 CONQUISTAS CONTÍNUAS
# =============================================================================

CONQUISTAS_CONTINUAS: dict[str, ConquistaContinuaDef] = {
    "mestre_chave_inglesa": ConquistaContinuaDef(
        id="mestre_chave_inglesa",
        nome="Mestre da Chave Inglesa",
        descricao="Execute parries bem-sucedidos contra projéteis inimigos.",
        evento="parry",
        milestones=[
            MilestoneConquista(
                meta=15,
                titulo="Aprendiz do Parry",
                recompensas=[("habilidade", "dash"), ("arma", "smg_compacta")],
            ),
            MilestoneConquista(
                meta=50,
                titulo="Reflexo Metálico",
                recompensas=[("modificador_run", "gatilho_duplo")],
            ),
            MilestoneConquista(
                meta=120,
                titulo="Mestre da Chave Inglesa",
                recompensas=[("opcao_config", "precisao_parry:postura_riposte"), ("slot_firmware", "+1")],
            ),
        ],
    ),
    "velocidade_de_clock": ConquistaContinuaDef(
        id="velocidade_de_clock",
        nome="Velocidade de Clock",
        descricao="Execute Just-Dodges atravessando ameaças com os i-frames do Dash.",
        evento="just_dodge",
        milestones=[
            MilestoneConquista(
                meta=40,
                titulo="Desvio Sincronizado",
                recompensas=[("modificador_run", "recarga_tatica")],
            ),
            MilestoneConquista(
                meta=150,
                titulo="Thread Fantasma",
                recompensas=[("opcao_config", "dash_rastro:thread_fantasma")],
            ),
            MilestoneConquista(
                meta=350,
                titulo="Velocidade de Clock",
                recompensas=[("opcao_config", "dash_protocolo:sombra_espelho")],
            ),
        ],
    ),
    "depurador_escritorio": ConquistaContinuaDef(
        id="depurador_escritorio",
        nome="Depurador do Escritório",
        descricao="Acumule abates de inimigos corporativos.",
        evento="abate",
        milestones=[
            MilestoneConquista(
                meta=250,
                titulo="Faxina Inicial",
                recompensas=[("trofeu", "depurador_m1"), ("slot_firmware", "+1")],
            ),
            MilestoneConquista(
                meta=1500,
                titulo="Controle de Pragas",
                recompensas=[("modificador_run", "adrenalina_overclock")],
            ),
            MilestoneConquista(
                meta=5000,
                titulo="Depurador Supremo",
                recompensas=[("arma", "lanca_chamas")],
            ),
        ],
    ),
    "cacador_hardware": ConquistaContinuaDef(
        id="cacador_hardware",
        nome="Caçador de Hardware",
        descricao="Derrote Mini-Bosses em menos de 60 segundos.",
        evento="miniboss_rapido",
        milestones=[
            MilestoneConquista(
                meta=4,
                titulo="Desmontador",
                recompensas=[("modificador_run", "canhoes_perimetrais")],
            ),
            MilestoneConquista(
                meta=16,
                titulo="Serralheiro Tático",
                recompensas=[("modificador_run", "sobrecarga_estrutural")],
            ),
            MilestoneConquista(
                meta=40,
                titulo="Caçador de Hardware",
                recompensas=[("arma", "rifle_arco")],
            ),
        ],
    ),
    "sobrevivente_caos": ConquistaContinuaDef(
        id="sobrevivente_caos",
        nome="Sobrevivente do Caos",
        descricao="Derrote a Geladeira Tsunami ao final da partida.",
        evento="vitoria_boss",
        milestones=[
            MilestoneConquista(
                meta=1,
                titulo="Primeiro Degelo",
                recompensas=[("modificador_run", "overclock_termico")],
            ),
            MilestoneConquista(
                meta=3,
                titulo="Controle de Versão",
                recompensas=[("opcao_config", "dash_protocolo:rollback_estado")],
            ),
            MilestoneConquista(
                meta=7,
                titulo="Sobrevivente do Caos",
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
        nome="Monge Tibetano",
        descricao="Sobreviva 2 minutos contínuos jogando em 15 FPS.",
        recompensas=[("trofeu", "monge_tibetano")],
        categoria="trofeu",
    ),
    "cabo_vga_solto": ConquistaUnicaDef(
        id="cabo_vga_solto",
        nome="Cabo VGA Solto",
        descricao="Vença a partida com Cores Invertidas e VSync Desligado ativos.",
        recompensas=[("trofeu", "cabo_vga_solto")],
        categoria="trofeu",
    ),
    "blindado_escritorio": ConquistaUnicaDef(
        id="blindado_escritorio",
        nome="Blindado de Escritório",
        descricao="Derrote um Mini-Boss usando Controles de Tanque.",
        recompensas=[("trofeu", "blindado_escritorio")],
        categoria="trofeu",
    ),
    "boliche_corporativo": ConquistaUnicaDef(
        id="boliche_corporativo",
        nome="Boliche Corporativo",
        descricao="Abata 3 inimigos por colisão cinética em um único golpe.",
        recompensas=[("trofeu", "boliche_corporativo")],
        categoria="trofeu",
    ),
    "zero_visao_cem_fe": ConquistaUnicaDef(
        id="zero_visao_cem_fe",
        nome="Zero Visão, Cem Fé",
        descricao="Alcance o Nível 8 com HUD Desligado e Iluminação Dinâmica Ligada.",
        recompensas=[("trofeu", "zero_visao_cem_fe")],
        categoria="trofeu",
    ),
    "auto_sabotagem": ConquistaUnicaDef(
        id="auto_sabotagem",
        nome="Auto-Sabotagem",
        descricao="Derrote um Mini-Boss com Fogo Amigo ativado.",
        recompensas=[("trofeu", "auto_sabotagem")],
        categoria="trofeu",
    ),
    "limpeza_de_disco": ConquistaUnicaDef(
        id="limpeza_de_disco",
        nome="Limpeza de Disco",
        descricao="Apague 15 ou mais projéteis inimigos em uma única coleta do Garbage Collector.",
        recompensas=[("trofeu", "limpeza_de_disco")],
        categoria="trofeu",
    ),
    "estilo_corporativo_s": ConquistaUnicaDef(
        id="estilo_corporativo_s",
        nome="Estilo Corporativo S",
        descricao="Mantenha combo ativo por >= 45s ou alcance >= 50x.",
        recompensas=[("modificador_run", "medidor_estilo")],
        categoria="desbloqueio",
    ),
    "intocavel_rh": ConquistaUnicaDef(
        id="intocavel_rh",
        nome="Intocável pelo RH",
        descricao="Vença a Geladeira Tsunami sem sofrer dano na Fase 3.",
        recompensas=[("modificador_run", "sandbox_isolada")],
        categoria="desbloqueio",
    ),
    "reset_infinito": ConquistaUnicaDef(
        id="reset_infinito",
        nome="Reset Infinito",
        descricao="Execute 5 parries consecutivos em menos de 12 segundos sem errar.",
        recompensas=[("modificador_run", "reset_voraz")],
        categoria="desbloqueio",
    ),
    "modo_batata_supremo": ConquistaUnicaDef(
        id="modo_batata_supremo",
        nome="Modo Batata Supremo",
        descricao="Vença a partida com 5 ou mais configurações não-neutras ativas.",
        recompensas=[("arma", "bastao_choque")],
        categoria="desbloqueio",
    ),
}
