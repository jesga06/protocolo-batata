"""
Componente compartilhado de Dicas Rotativas — Protocolo: Batata
Exibe dicas de combate, progressão e sistemas em estética Cyber-Office nas telas de menu e pausa.
"""

import random
import pygame

_C_HUD_BG = (11, 14, 23, 220)
_C_BORDER = (51, 65, 85)
_C_CYAN = (34, 211, 238)
_C_GOLD = (251, 191, 36)
_C_TEXT_PRIMARY = (241, 245, 249)
_C_TEXT_MUTED = (100, 116, 139)

DICAS_JOGO: tuple[str, ...] = (
    "Botão Esquerdo (LMB) ataca com a arma equipada; Botão Direito (RMB) executa Parry Rápido a qualquer momento.",
    "Acumule 15 Parries bem-sucedidos para desbloquear o Dash e a SMG Compacta!",
    "Projéteis Vermelhos são comuns; Shurikens Roxas exigem Parry (ignoram Dash); Setas Amarelas exigem Dash (ignoram Parry).",
    "Atravessar ataques com os i-frames do Dash ativa Just-Dodge, mantém seu Combo e acelera a recarga.",
    "Na Pistola [2], todo 4º disparo sai sobrecarregado (2.2x de dano e perfurante). Na SMG Compacta, mire na zona ideal de calor (60%-92%).",
    "Acompanhe o ritmo Música-Onda: ANTICIPATION (início), HOLD (respiro) e ASSAULT (ataque intenso).",
    "Fixe até 3 Conquistas na HUD e equipe até 3 Chips de Firmware no Menu Principal antes da partida.",
    "São 28 Configurações de Gameplay combinando Benefícios e Sacrifícios; ative várias para desafios extras.",
    "Mini-Bosses surgem a cada minuto (1:00 a 4:00): derrote-os em menos de 60s para ganhar Overclock.",
    "Se um Mini-Boss superaquecer após 60s, ele explode sem deixar recompensas.",
    "Drops no chão por 10s podem ser roubados pelo Scavenger — colete itens valiosos rápido.",
    "Pressione [F] durante a partida para alternar o disparo automático (Auto-Fire).",
    "Níveis normais não pausam o jogo: curam +10 HP, empurram inimigos e soltam 2 Cápsulas.",
    "Trituradores Blindados reduzem 30% do dano frontal — ataque pelos flancos ou costas.",
    "A Geladeira Tsunami aparece no Nível 12 ou após vencer os 4 estágios de Mini-Boss.",
)

_FONT_CACHE: dict[tuple[str, int, bool], pygame.font.Font] = {}


def _obter_fonte(familia: str, tamanho: int, bold: bool = False) -> pygame.font.Font:
    px = max(8, int(tamanho))
    chave = (familia, px, bold)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    nomes = (
        ("jetbrainsmono", "firacode", "consolas", "dejavusansmono")
        if familia == "mono"
        else ("notosans", "dejavusans", "liberationsans", "arial")
    )
    for nome in nomes:
        try:
            f = pygame.font.SysFont(nome, px, bold=bold)
            if f is not None:
                _FONT_CACHE[chave] = f
                return f
        except Exception:
            continue
    f = pygame.font.Font(None, px)
    _FONT_CACHE[chave] = f
    return f


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
    Banner compacto de dicas rotativas reutilizável entre cenas e overlays.
    """

    def __init__(self, intervalo_rotacao: float = 8.0, indice_inicial: int | None = None):
        self.intervalo_rotacao = max(1.0, float(intervalo_rotacao))
        self._timer = 0.0
        self.indice_atual = (
            int(indice_inicial) % len(DICAS_JOGO)
            if indice_inicial is not None
            else random.randrange(len(DICAS_JOGO))
        )
        self._bg_cache: dict[tuple[int, int, int], pygame.Surface] = {}

    @property
    def texto_atual(self) -> str:
        return DICAS_JOGO[self.indice_atual]

    def proxima_dica(self):
        self.indice_atual = (self.indice_atual + 1) % len(DICAS_JOGO)
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

        tag_surf = fonte_tag.render("DICA", True, _C_GOLD)
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
