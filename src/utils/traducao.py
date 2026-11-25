"""
Sistema de Tradução e Localização (i18n) — Protocolo: Batata
Carrega arquivos JSON categorizados de `assets/locales/<idioma>/` em memória
na inicialização (zero I/O por frame), com suporte a contexto, placeholders
documentados e metadados por categoria.
"""

import json
import os
import sys
from typing import Any

if getattr(sys, "frozen", False):
    _PROJECT_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
else:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCALES_DIR = os.path.join(_PROJECT_ROOT, "assets", "locales")
IDIOMA_PADRAO = "pt_BR"

_idioma_atual: str = IDIOMA_PADRAO
_cache_entradas: dict[str, dict[str, dict[str, Any]]] = {}
_cache_meta: dict[str, dict[str, Any]] = {}
_carregado: bool = False


def obter_idioma() -> str:
    """Retorna o código do idioma ativo."""
    return _idioma_atual


def carregar_idioma(idioma: str = IDIOMA_PADRAO) -> None:
    """Carrega todos os arquivos JSON de categoria do idioma especificado para a memória."""
    global _idioma_atual, _carregado
    pasta = os.path.join(LOCALES_DIR, idioma)
    if not os.path.isdir(pasta):
        raise FileNotFoundError(f"Diretório de localização não encontrado: {pasta}")

    novas_entradas: dict[str, dict[str, dict[str, Any]]] = {}
    novos_meta: dict[str, dict[str, Any]] = {}

    for nome_arquivo in sorted(os.listdir(pasta)):
        if not nome_arquivo.endswith(".json"):
            continue
        categoria = nome_arquivo[:-5]
        caminho = os.path.join(pasta, nome_arquivo)
        with open(caminho, "r", encoding="utf-8") as arq:
            dados = json.load(arq)
        novos_meta[categoria] = dados.get("_meta", {})
        novas_entradas[categoria] = dados.get("entradas", {})

    _cache_meta.clear()
    _cache_meta.update(novos_meta)
    _cache_entradas.clear()
    _cache_entradas.update(novas_entradas)
    _idioma_atual = idioma
    _carregado = True


def _garantir_carregado() -> None:
    if not _carregado:
        carregar_idioma(_idioma_atual)


def definir_idioma(idioma: str) -> None:
    """Altera o idioma ativo e recarrega o cache em memória."""
    carregar_idioma(idioma)


def recarregar_traducoes() -> None:
    """Recarrega as traduções do idioma ativo a partir do disco."""
    carregar_idioma(_idioma_atual)


def listar_categorias() -> list[str]:
    """Retorna a lista ordenada de categorias carregadas."""
    _garantir_carregado()
    return sorted(_cache_entradas.keys())


def obter_meta(categoria: str) -> dict[str, Any]:
    """Retorna o bloco `_meta` de uma categoria."""
    _garantir_carregado()
    if categoria not in _cache_meta:
        raise KeyError(f"Categoria de tradução desconhecida: {categoria!r}")
    return _cache_meta[categoria]


def obter_entradas(categoria: str) -> dict[str, dict[str, Any]]:
    """Retorna o dicionário completo de entradas estruturadas de uma categoria."""
    _garantir_carregado()
    if categoria not in _cache_entradas:
        raise KeyError(f"Categoria de tradução desconhecida: {categoria!r}")
    return _cache_entradas[categoria]


def obter_entrada(categoria: str, chave: str) -> dict[str, Any]:
    """Retorna os metadados completos (`texto`, `contexto`, `placeholders`, etc.) de uma chave."""
    entradas = obter_entradas(categoria)
    if chave not in entradas:
        raise KeyError(f"Chave de tradução desconhecida: {categoria!r}.{chave!r}")
    return entradas[chave]


def t(categoria: str, chave: str, /, **kwargs: Any) -> str:
    """Retorna o texto traduzido e formatado com `kwargs` para `categoria` e `chave`."""
    entrada = obter_entrada(categoria, chave)
    texto = entrada["texto"]
    if kwargs:
        try:
            return texto.format(**kwargs)
        except KeyError as exc:
            raise ValueError(
                f"Placeholder ausente ao formatar {categoria!r}.{chave!r}: {exc}"
            ) from exc
    return texto
