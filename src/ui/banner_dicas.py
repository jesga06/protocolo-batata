"""
Componente compartilhado de Dicas Rotativas Condicionais — Protocolo: Batata
Exibe dicas de combate, progressão e sistemas em estética Cyber-Office nas telas de menu e pausa.

Como adicionar uma nova dica em `BANCO_DICAS`:
--------------------------------------------
Use `dica("Seu texto aqui.")` para dicas sempre visíveis, ou passe `quando=`
com uma expressão legível usando `and`, `or`, `not` e parênteses:

    dica("Texto da dica.", quando="dash_desbloqueado")
    dica("Texto da dica.", quando="dash_desbloqueado and not firmware_desbloqueado")
    dica("Texto da dica.", quando="arma('smg_compacta') or arma('bastao_choque')")
    dica("Texto da dica.", quando="min_parries(15)", exceto="ja_venceu_run")

Você também pode usar `min_parries >= 15` ou tuplas como `("arma", "smg_compacta")`.
Todas as condições são validadas automaticamente ao importar o módulo.
"""

import ast
from dataclasses import dataclass
import random
import re
from typing import Any, Callable, Union
import pygame
from src.utils.traducao import obter_entradas, t

_C_HUD_BG = (11, 14, 23, 220)
_C_BORDER = (51, 65, 85)
_C_CYAN = (34, 211, 238)
_C_GOLD = (251, 191, 36)
_C_TEXT_PRIMARY = (241, 245, 249)
_C_TEXT_MUTED = (100, 116, 139)

CondicaoSpec = Union[str, tuple[Any, ...]]


@dataclass(frozen=True)
class DicaItem:
    """Entrada estruturada de dica condicional no catálogo de dicas."""

    texto: str
    quando: CondicaoSpec = "sempre"
    exceto: CondicaoSpec | None = None
    condicoes_todas: tuple[CondicaoSpec, ...] = ()
    condicoes_qualquer: tuple[CondicaoSpec, ...] = ()
    excluir_se: tuple[CondicaoSpec, ...] = ()


def dica(
    texto: str,
    quando: CondicaoSpec = "sempre",
    *,
    exceto: CondicaoSpec | None = None,
) -> DicaItem:
    """Atalho legível para declarar uma dica condicional em `BANCO_DICAS`."""
    return DicaItem(texto=texto, quando=quando, exceto=exceto)


def _obter_conq(cfg: Any) -> Any:
    if cfg is None:
        return None
    return getattr(cfg, "sistema_conquistas", None)


def _possui_recompensa(cfg: Any, tipo: str, rid: str) -> bool:
    conq = _obter_conq(cfg)
    if conq is None:
        return False
    if hasattr(conq, "possui_recompensa"):
        return bool(conq.possui_recompensa(tipo, rid))
    recs = getattr(conq, "recompensas", {}) or {}
    return rid in recs.get(tipo, ())


def _dash_ativo(cfg: Any) -> bool:
    if _possui_recompensa(cfg, "habilidade", "dash"):
        return True
    if cfg is None:
        return False
    est = getattr(cfg, "estatisticas", {}) or {}
    return bool(est.get("dash_desbloqueado", False))


def _contar_desbloqueadas(cfg: Any) -> int:
    if cfg is None:
        return 0
    return len(getattr(cfg, "desbloqueadas", ()) or ())


def _contar_ativas(cfg: Any) -> int:
    if cfg is None:
        return 0
    if hasattr(cfg, "contar_configs_nao_neutras"):
        return int(cfg.contar_configs_nao_neutras())
    return 0


def _valor_continua(cfg: Any, cid: str) -> int:
    conq = _obter_conq(cfg)
    if conq is None:
        return 0
    cont = getattr(conq, "continuas", {}) or {}
    return int((cont.get(cid) or {}).get("valor", 0))


def _stat_int(cfg: Any, chave: str) -> int:
    if cfg is None:
        return 0
    est = getattr(cfg, "estatisticas", {}) or {}
    return int(est.get(chave, 0) or 0)


def _config_esta_ativa(cfg: Any, cid: str) -> bool:
    if cfg is None:
        return False
    if cid not in (getattr(cfg, "desbloqueadas", ()) or ()):
        return False
    from src.sistemas.config_dados import CONFIGURACOES_GAMEPLAY
    conf_def = CONFIGURACOES_GAMEPLAY.get(cid)
    if conf_def is not None and hasattr(cfg, "obter_valor"):
        return str(cfg.obter_valor(cid)) != str(conf_def.valor_padrao)
    return False


# =============================================================================
# CATÁLOGO EXPOSTO DE CONDIÇÕES (NOMEADAS E PARAMETRIZADAS)
# =============================================================================

CONDICOES_DICAS: dict[str, Callable[[Any], bool]] = {
    "sempre": lambda cfg: True,
    "tutorial_nao_visto": lambda cfg: not bool(getattr(cfg, "tutorial_visto", False)),
    "tutorial_visto": lambda cfg: bool(getattr(cfg, "tutorial_visto", False)),
    "dash_desbloqueado": _dash_ativo,
    "dash_bloqueado": lambda cfg: not _dash_ativo(cfg),
    "smg_desbloqueada": lambda cfg: _possui_recompensa(cfg, "arma", "smg_compacta"),
    "bastao_desbloqueado": lambda cfg: _possui_recompensa(cfg, "arma", "bastao_choque"),
    "rifle_arco_desbloqueado": lambda cfg: _possui_recompensa(cfg, "arma", "rifle_arco"),
    "lanca_chamas_desbloqueado": lambda cfg: _possui_recompensa(cfg, "arma", "lanca_chamas"),
    "loadout_desbloqueado": lambda cfg: (
        _possui_recompensa(cfg, "arma", "smg_compacta")
        or _possui_recompensa(cfg, "arma", "bastao_choque")
    ),
    "firmware_desbloqueado": lambda cfg: bool(
        ((getattr(_obter_conq(cfg), "recompensas", {}) or {}).get("modificador_run"))
    ),
    "firmware_bloqueado": lambda cfg: not bool(
        ((getattr(_obter_conq(cfg), "recompensas", {}) or {}).get("modificador_run"))
    ),
    "firmware_equipado": lambda cfg: bool(
        getattr(_obter_conq(cfg), "modificadores_equipados", ())
    ),
    "multiplos_slots_firmware": lambda cfg: int(getattr(_obter_conq(cfg), "slots_firmware_max", 1)) >= 2,
    "todos_slots_firmware": lambda cfg: int(getattr(_obter_conq(cfg), "slots_firmware_max", 1)) >= 3,
    "alguma_config_desbloqueada": lambda cfg: _contar_desbloqueadas(cfg) >= 1,
    "cota_2_configs_possiveis": lambda cfg: _contar_desbloqueadas(cfg) >= 2,
    "cota_4_configs_possiveis": lambda cfg: _contar_desbloqueadas(cfg) >= 4,
    "cota_6_configs_possiveis": lambda cfg: _contar_desbloqueadas(cfg) >= 6,
    "alguma_config_ativa": lambda cfg: _contar_ativas(cfg) >= 1,
    "cota_2_configs_ativas": lambda cfg: _contar_ativas(cfg) >= 2,
    "cota_4_configs_ativas": lambda cfg: _contar_ativas(cfg) >= 4,
    "cota_6_configs_ativas": lambda cfg: _contar_ativas(cfg) >= 6,
    "auto_fire_desbloqueado": lambda cfg: "auto_fire" in (getattr(cfg, "desbloqueadas", ()) or ()),
    "garbage_collector_desbloqueado": lambda cfg: "garbage_collector" in (getattr(cfg, "desbloqueadas", ()) or ()),
    "latencia_ping_desbloqueado": lambda cfg: "latencia_ping" in (getattr(cfg, "desbloqueadas", ()) or ()),
    "modo_wireframe_desbloqueado": lambda cfg: "modo_wireframe" in (getattr(cfg, "desbloqueadas", ()) or ()),
    "mira_oculta_desbloqueada": lambda cfg: "mira_oculta" in (getattr(cfg, "desbloqueadas", ()) or ()),
    "postura_riposte_desbloqueada": lambda cfg: _possui_recompensa(cfg, "opcao_config", "precisao_parry:postura_riposte"),
    "thread_fantasma_desbloqueada": lambda cfg: _possui_recompensa(cfg, "opcao_config", "dash_rastro:thread_fantasma"),
    "sombra_espelho_desbloqueada": lambda cfg: _possui_recompensa(cfg, "opcao_config", "dash_protocolo:sombra_espelho"),
    "rollback_estado_desbloqueado": lambda cfg: _possui_recompensa(cfg, "opcao_config", "dash_protocolo:rollback_estado"),
    "ja_jogou_partida": lambda cfg: _stat_int(cfg, "partidas_jogadas") >= 1,
    "ja_abateu_miniboss": lambda cfg: _valor_continua(cfg, "cacador_hardware") >= 1,
    "primeiro_overclock_concluido": lambda cfg: "primeiro_overclock_sujo" in (getattr(_obter_conq(cfg), "unicas_concluidas", ()) or ()),
    "ja_venceu_run": lambda cfg: _stat_int(cfg, "vitorias") >= 1 or _valor_continua(cfg, "sobrevivente_caos") >= 1,
}

CONDICOES_PARAMETRIZADAS: dict[str, Callable[..., bool]] = {
    "arma": lambda cfg, arma_id: _possui_recompensa(cfg, "arma", str(arma_id)),
    "habilidade": lambda cfg, hab_id: (
        _dash_ativo(cfg) if str(hab_id) == "dash" else _possui_recompensa(cfg, "habilidade", str(hab_id))
    ),
    "firmware": lambda cfg, chip_id: _possui_recompensa(cfg, "modificador_run", str(chip_id)),
    "config_desbloqueada": lambda cfg, cid: str(cid) in (getattr(cfg, "desbloqueadas", ()) or ()),
    "config_ativa": lambda cfg, cid: _config_esta_ativa(cfg, str(cid)),
    "config_valor": lambda cfg, cid, val: (
        cfg is not None and hasattr(cfg, "obter_valor") and cfg.obter_valor(str(cid)) == val
    ),
    "opcao_config": lambda cfg, op: _possui_recompensa(cfg, "opcao_config", str(op)),
    "conquista_unica": lambda cfg, cid: str(cid) in (getattr(_obter_conq(cfg), "unicas_concluidas", ()) or ()),
    "trofeu": lambda cfg, tid: _possui_recompensa(cfg, "trofeu", str(tid)),
    "min_parries": lambda cfg, n: max(_stat_int(cfg, "parries_total"), _valor_continua(cfg, "mestre_chave_inglesa")) >= int(n),
    "min_just_dodges": lambda cfg, n: _valor_continua(cfg, "velocidade_de_clock") >= int(n),
    "min_abates": lambda cfg, n: max(_stat_int(cfg, "total_abates"), _valor_continua(cfg, "depurador_escritorio")) >= int(n),
    "min_miniboss_rapidos": lambda cfg, n: _valor_continua(cfg, "cacador_hardware") >= int(n),
    "min_vitorias": lambda cfg, n: max(_stat_int(cfg, "vitorias"), _valor_continua(cfg, "sobrevivente_caos")) >= int(n),
    "min_partidas": lambda cfg, n: _stat_int(cfg, "partidas_jogadas") >= int(n),
    "min_configs_desbloqueadas": lambda cfg, n: _contar_desbloqueadas(cfg) >= int(n),
    "min_configs_ativas": lambda cfg, n: _contar_ativas(cfg) >= int(n),
    "min_slots_firmware": lambda cfg, n: int(getattr(_obter_conq(cfg), "slots_firmware_max", 1)) >= int(n),
}


_ALIASES_COMPARACAO: dict[str, str] = {
    "parries": "min_parries",
    "just_dodges": "min_just_dodges",
    "abates": "min_abates",
    "miniboss_rapidos": "min_miniboss_rapidos",
    "vitorias": "min_vitorias",
    "partidas": "min_partidas",
    "configs_desbloqueadas": "min_configs_desbloqueadas",
    "configs_ativas": "min_configs_ativas",
    "slots_firmware": "min_slots_firmware",
}


def _validar_ast_condicao(node: ast.AST, origem: str) -> None:
    if isinstance(node, ast.Expression):
        _validar_ast_condicao(node.body, origem)
        return
    if isinstance(node, ast.Name):
        if node.id not in CONDICOES_DICAS:
            raise ValueError(f"Condição de dica desconhecida: {node.id!r}")
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        _validar_ast_condicao(node.operand, origem)
        return
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        for val in node.values:
            _validar_ast_condicao(val, origem)
        return
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        chave = node.func.id
        if chave not in CONDICOES_PARAMETRIZADAS:
            raise ValueError(f"Condição parametrizada de dica desconhecida: {chave!r}")
        if not node.args or not all(isinstance(a, ast.Constant) for a in node.args):
            raise ValueError(f"Argumentos inválidos em condição de dica: {origem!r}")
        return
    if (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.GtE)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and isinstance(node.comparators[0].value, int)
    ):
        chave = _ALIASES_COMPARACAO.get(node.left.id, node.left.id)
        if chave not in CONDICOES_PARAMETRIZADAS:
            raise ValueError(f"Condição de comparação desconhecida: {node.left.id!r}")
        return
    raise ValueError(f"Especificação de condição inválida: {origem!r}")


def _avaliar_ast_condicao(node: ast.AST, cfg: Any) -> bool:
    if isinstance(node, ast.Expression):
        return _avaliar_ast_condicao(node.body, cfg)
    if isinstance(node, ast.Name):
        fn = CONDICOES_DICAS.get(node.id)
        return bool(fn(cfg)) if fn is not None else False
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _avaliar_ast_condicao(node.operand, cfg)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_avaliar_ast_condicao(v, cfg) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(_avaliar_ast_condicao(v, cfg) for v in node.values)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = CONDICOES_PARAMETRIZADAS.get(node.func.id)
        if fn is None:
            return False
        args = [a.value for a in node.args if isinstance(a, ast.Constant)]
        return bool(fn(cfg, *args))
    if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name):
        chave = _ALIASES_COMPARACAO.get(node.left.id, node.left.id)
        fn = CONDICOES_PARAMETRIZADAS.get(chave)
        if fn is None or not node.comparators:
            return False
        comp = node.comparators[0]
        if isinstance(comp, ast.Constant):
            return bool(fn(cfg, comp.value))
    return False


_RE_SHORTHAND_CONDICAO = re.compile(
    r"""(['"][^'"]*['"])|\b([a-zA-Z_][a-zA-Z0-9_]*):([a-zA-Z0-9_:-]+)"""
)


def _normalizar_expressao_condicao(texto: str) -> str:
    return _RE_SHORTHAND_CONDICAO.sub(
        lambda m: m.group(1) if m.group(1) else f"{m.group(2)}({m.group(3)!r})",
        texto.strip(),
    )


def validar_condicao_spec(condicao: CondicaoSpec) -> None:
    """Valida sintaxe e registro de uma condição de dica (falha cedo em erro de digitação)."""
    if isinstance(condicao, str):
        texto = _normalizar_expressao_condicao(condicao)
        try:
            arvore = ast.parse(texto, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Sintaxe inválida na condição de dica {condicao!r}: {exc.msg}") from exc
        _validar_ast_condicao(arvore, condicao)
        return
    if isinstance(condicao, tuple) and len(condicao) >= 2:
        chave = str(condicao[0])
        if chave not in CONDICOES_PARAMETRIZADAS:
            raise ValueError(f"Condição parametrizada de dica desconhecida: {chave!r}")
        return
    raise ValueError(f"Especificação de condição inválida: {condicao!r}")


def avaliar_condicao(condicao: CondicaoSpec, gerenciador_config: Any) -> bool:
    """Avalia uma condição nomeada, expressão booleana ou tupla parametrizada contra `gerenciador_config`."""
    if isinstance(condicao, str):
        texto = condicao.strip()
        if texto in CONDICOES_DICAS:
            return bool(CONDICOES_DICAS[texto](gerenciador_config))
        try:
            arvore = ast.parse(_normalizar_expressao_condicao(texto), mode="eval")
        except SyntaxError:
            return False
        return _avaliar_ast_condicao(arvore, gerenciador_config)
    if isinstance(condicao, tuple) and len(condicao) >= 2:
        fn = CONDICOES_PARAMETRIZADAS.get(str(condicao[0]))
        if fn is None:
            return False
        return bool(fn(gerenciador_config, *condicao[1:]))
    return False


def dica_elegivel(item: DicaItem, gerenciador_config: Any = None) -> bool:
    """Retorna True se a dica deve ser exibida para o estado salvo atual."""
    if gerenciador_config is None:
        return True
    if not avaliar_condicao(item.quando, gerenciador_config):
        return False
    if item.exceto is not None and avaliar_condicao(item.exceto, gerenciador_config):
        return False
    if item.condicoes_todas and not all(avaliar_condicao(c, gerenciador_config) for c in item.condicoes_todas):
        return False
    if item.condicoes_qualquer and not any(avaliar_condicao(c, gerenciador_config) for c in item.condicoes_qualquer):
        return False
    if item.excluir_se and any(avaliar_condicao(c, gerenciador_config) for c in item.excluir_se):
        return False
    return True


# =============================================================================
# BANCO DE DICAS CONDICIONAIS (CARREGADO DE assets/locales/<idioma>/dicas.json)
# =============================================================================

def _carregar_banco_dicas() -> tuple[DicaItem, ...]:
    itens: list[DicaItem] = []
    for entrada in obter_entradas("dicas").values():
        conds = entrada.get("condicoes") or {}
        itens.append(
            DicaItem(
                texto=entrada["texto"],
                quando=conds.get("quando", "sempre"),
                exceto=conds.get("exceto"),
                condicoes_todas=tuple(conds.get("condicoes_todas") or ()),
                condicoes_qualquer=tuple(conds.get("condicoes_qualquer") or ()),
                excluir_se=tuple(conds.get("excluir_se") or ()),
            )
        )
    return tuple(itens)


BANCO_DICAS: tuple[DicaItem, ...] = _carregar_banco_dicas()

for _item_dica in BANCO_DICAS:
    validar_condicao_spec(_item_dica.quando)
    if _item_dica.exceto is not None:
        validar_condicao_spec(_item_dica.exceto)
    for _cond in _item_dica.condicoes_todas + _item_dica.condicoes_qualquer + _item_dica.excluir_se:
        validar_condicao_spec(_cond)

DICAS_JOGO: tuple[str, ...] = tuple(d.texto for d in BANCO_DICAS)


def obter_dicas_elegiveis(gerenciador_config: Any = None) -> tuple[str, ...]:
    """Retorna apenas os textos das dicas elegíveis para o save/estado informado."""
    elegiveis = tuple(d.texto for d in BANCO_DICAS if dica_elegivel(d, gerenciador_config))
    return elegiveis if elegiveis else (BANCO_DICAS[0].texto,)

from src.utils.fontes import carregar_fonte_sans, carregar_fonte_mono


def _obter_fonte(familia: str, tamanho: int, bold: bool = False) -> pygame.font.Font:
    if familia == "mono":
        return carregar_fonte_mono(tamanho, bold=bold)
    return carregar_fonte_sans(tamanho, bold=bold)


def _quebrar_texto_por_largura(texto: str, fonte: pygame.font.Font, max_largura: int) -> list[str]:
    palavras = texto.split()
    if not palavras:
        return [""]
    linhas: list[str] = []
    atual = palavras[0]
    for palavra in palavras[1:]:
        teste = f"{atual} {palavra}"
        if fonte.size(teste)[0] <= max_largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    linhas.append(atual)
    return linhas


class BannerDica:
    """
    Banner compacto de dicas rotativas condicionais reutilizável entre cenas e overlays.
    """

    def __init__(
        self,
        intervalo_rotacao: float = 8.0,
        indice_inicial: int | None = None,
        gerenciador_config: Any = None,
    ):
        self.intervalo_rotacao = max(1.0, float(intervalo_rotacao))
        self.gerenciador_config = gerenciador_config
        self._timer = 0.0
        pool = obter_dicas_elegiveis(gerenciador_config)
        self.indice_atual = (
            int(indice_inicial) % len(pool)
            if indice_inicial is not None
            else random.randrange(len(pool))
        )
        self._bg_cache: dict[tuple[int, int, int], pygame.Surface] = {}

    def definir_gerenciador_config(self, gerenciador_config: Any) -> None:
        self.gerenciador_config = gerenciador_config

    def _obter_pool_atual(self) -> tuple[str, ...]:
        return obter_dicas_elegiveis(self.gerenciador_config)

    @property
    def texto_atual(self) -> str:
        pool = self._obter_pool_atual()
        if self.indice_atual >= len(pool):
            self.indice_atual = 0
        return pool[self.indice_atual]

    def proxima_dica(self):
        pool = self._obter_pool_atual()
        self.indice_atual = (self.indice_atual + 1) % len(pool)
        self._timer = 0.0

    def atualizar(self, dt: float):
        if dt <= 0.0:
            return
        self._timer += float(dt)
        if self._timer >= self.intervalo_rotacao:
            self.proxima_dica()

    def _obter_fundo(self, w: int, h: int, raio: int) -> pygame.Surface:
        chave = (max(1, int(w)), max(1, int(h)), max(0, int(raio)))
        if chave not in self._bg_cache:
            surf = pygame.Surface((chave[0], chave[1]), pygame.SRCALPHA)
            pygame.draw.rect(surf, _C_HUD_BG, (0, 0, chave[0], chave[1]), border_radius=chave[2])
            self._bg_cache[chave] = surf
        return self._bg_cache[chave]

    def desenhar(self, screen, rect: pygame.Rect, scale: float = 1.0):
        if screen is None or rect.width < 40 or rect.height < 20:
            return

        s = max(0.5, float(scale))
        raio = max(3, int(round(6 * s)))
        borda = max(1, int(round(1 * s)))
        pad_x = max(8, int(round(12 * s)))
        pad_y = max(4, int(round(6 * s)))

        bg = self._obter_fundo(rect.width, rect.height, raio)
        screen.blit(bg, (rect.x, rect.y))
        pygame.draw.rect(screen, _C_BORDER, rect, width=borda, border_radius=raio)

        fonte_tag = _obter_fonte("mono", max(9, int(round(10 * s))), bold=True)
        fonte_txt = _obter_fonte("sans", max(10, int(round(12 * s))), bold=False)

        tag_surf = fonte_tag.render(t("ui_geral", "tag_dica"), True, _C_GOLD)
        tag_pad_x = max(5, int(round(7 * s)))
        tag_pad_y = max(2, int(round(3 * s)))
        tag_w = tag_surf.get_width() + tag_pad_x * 2
        tag_h = tag_surf.get_height() + tag_pad_y * 2
        tag_rect = pygame.Rect(rect.x + pad_x, rect.y + (rect.height - tag_h) // 2, tag_w, tag_h)
        pygame.draw.rect(screen, (30, 41, 59), tag_rect, border_radius=max(2, int(round(4 * s))))
        pygame.draw.rect(screen, _C_CYAN, tag_rect, width=borda, border_radius=max(2, int(round(4 * s))))
        screen.blit(tag_surf, tag_surf.get_rect(center=tag_rect.center))

        texto_x = tag_rect.right + max(8, int(round(10 * s)))
        max_w = max(40, rect.right - pad_x - texto_x)
        linhas = _quebrar_texto_por_largura(self.texto_atual, fonte_txt, max_w)[:2]

        line_h = fonte_txt.get_linesize()
        total_h = len(linhas) * line_h
        start_y = rect.y + max(pad_y, (rect.height - total_h) // 2)
        for i, linha in enumerate(linhas):
            surf_l = fonte_txt.render(linha, True, _C_TEXT_PRIMARY)
            screen.blit(surf_l, (texto_x, start_y + i * line_h))
