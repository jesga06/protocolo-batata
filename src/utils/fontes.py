"""
Cache compartilhado de fontes Sans e Monospace — Protocolo: Batata
Centraliza o carregamento e cacheamento de pygame.font.SysFont entre cenas, menus e modais.
"""

import pygame

_FONT_CACHE: dict[tuple[str, int, bool, bool], pygame.font.Font] = {}

_FAMILIAS_SANS = ("notosans", "dejavusans", "liberationsans", "arial")
_FAMILIAS_MONO = ("jetbrainsmono", "firacode", "consolas", "dejavusansmono")


def carregar_fonte_sans(tamanho: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Carrega e cacheia fonte Sans-Serif com fallback seguro para Arial / fonte padrão."""
    px_sz = max(8, int(tamanho))
    chave = ("sans", px_sz, bool(bold), bool(italic))
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in _FAMILIAS_SANS:
        try:
            f = pygame.font.SysFont(nome, px_sz, bold=bold, italic=italic)
            if f is not None:
                _FONT_CACHE[chave] = f
                return f
        except pygame.error:
            continue
    try:
        f = pygame.font.SysFont("Arial", px_sz, bold=bold, italic=italic)
    except pygame.error:
        f = pygame.font.Font(None, px_sz)
    _FONT_CACHE[chave] = f
    return f


def carregar_fonte_mono(tamanho: int, bold: bool = False) -> pygame.font.Font:
    """Carrega e cacheia fonte Monospace com fallback seguro para Consolas / fonte padrão."""
    px_sz = max(8, int(tamanho))
    chave = ("mono", px_sz, bool(bold), False)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in _FAMILIAS_MONO:
        try:
            f = pygame.font.SysFont(nome, px_sz, bold=bold)
            if f is not None:
                _FONT_CACHE[chave] = f
                return f
        except pygame.error:
            continue
    try:
        f = pygame.font.SysFont("Consolas", px_sz, bold=bold)
    except pygame.error:
        f = pygame.font.Font(None, px_sz)
    _FONT_CACHE[chave] = f
    return f
