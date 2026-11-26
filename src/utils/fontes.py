"""
Cache compartilhado de fontes Sans e Monospace — Protocolo: Batata
Carrega prioritariamente as fontes TrueType embutidas em assets/fonts/
(OPPO Sans 4.0 e JetBrains Mono NL) para garantir paridade visual 1:1 entre
Linux, Windows, macOS e Wine, com fallback seguro por match_font() caso
algum arquivo esteja ausente.
"""

import os
import pygame
from src.utils.constantes import ASSETS_DIR

_FONT_CACHE: dict[tuple[str, int, bool, bool], pygame.font.Font] = {}

FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
ARQUIVO_FONTE_SANS = os.path.join(FONTS_DIR, "OPPO_Sans_4.0.ttf")
ARQUIVO_FONTE_MONO_REGULAR = os.path.join(FONTS_DIR, "JetBrainsMonoNL-Regular.ttf")
ARQUIVO_FONTE_MONO_BOLD = os.path.join(FONTS_DIR, "JetBrainsMonoNL-Bold.ttf")

_FAMILIAS_SANS = ("opposans", "notosans", "dejavusans", "liberationsans", "segoeui", "arial")
_FAMILIAS_MONO = ("jetbrainsmononl", "jetbrainsmono", "firacode", "consolas", "dejavusansmono", "couriernew")


def limpar_cache_fontes() -> None:
    """Limpa o cache em memória de fontes (útil para testes automatizados)."""
    _FONT_CACHE.clear()


def _carregar_ttf(caminho: str, px_sz: int, bold: bool = False, italic: bool = False) -> pygame.font.Font | None:
    """Carrega um arquivo TTF local se existir e aplica estilo sintético quando solicitado."""
    if not caminho or not os.path.isfile(caminho):
        return None
    try:
        fonte = pygame.font.Font(caminho, px_sz)
        if bold:
            fonte.set_bold(True)
        if italic:
            fonte.set_italic(True)
        return fonte
    except (pygame.error, OSError):
        return None


def _carregar_sysfont_fallback(
    familias: tuple[str, ...],
    px_sz: int,
    bold: bool = False,
    italic: bool = False,
) -> pygame.font.Font:
    """
    Fallback seguro de fontes do sistema: verifica match_font() antes de instanciar SysFont
    para impedir que uma fonte ausente encerre o loop na freesansbold.ttf minúscula do Pygame.
    """
    for nome in familias:
        try:
            if pygame.font.match_font(nome, bold=bold, italic=italic):
                return pygame.font.SysFont(nome, px_sz, bold=bold, italic=italic)
        except pygame.error:
            continue
    return pygame.font.Font(None, px_sz)


def carregar_fonte_sans(tamanho: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Carrega e cacheia fonte Sans-Serif (OPPO Sans 4.0 embutida com fallback seguro)."""
    px_sz = max(8, int(tamanho))
    chave = ("sans", px_sz, bool(bold), bool(italic))
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]

    fonte = _carregar_ttf(ARQUIVO_FONTE_SANS, px_sz, bold=bool(bold), italic=bool(italic))
    if fonte is None:
        fonte = _carregar_sysfont_fallback(_FAMILIAS_SANS, px_sz, bold=bool(bold), italic=bool(italic))

    _FONT_CACHE[chave] = fonte
    return fonte


def carregar_fonte_mono(tamanho: int, bold: bool = False) -> pygame.font.Font:
    """Carrega e cacheia fonte Monospace (JetBrains Mono NL embutida com fallback seguro)."""
    px_sz = max(8, int(tamanho))
    chave = ("mono", px_sz, bool(bold), False)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]

    fonte: pygame.font.Font | None = None
    if bold:
        fonte = _carregar_ttf(ARQUIVO_FONTE_MONO_BOLD, px_sz, bold=False, italic=False)
        if fonte is None:
            fonte = _carregar_ttf(ARQUIVO_FONTE_MONO_REGULAR, px_sz, bold=True, italic=False)
    else:
        fonte = _carregar_ttf(ARQUIVO_FONTE_MONO_REGULAR, px_sz, bold=False, italic=False)

    if fonte is None:
        fonte = _carregar_sysfont_fallback(_FAMILIAS_MONO, px_sz, bold=bool(bold), italic=False)

    _FONT_CACHE[chave] = fonte
    return fonte
