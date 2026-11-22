"""
Modal de Overclock / BIOS Upgrade — Protocolo: Batata
Exibe a seleção de 3 upgrades especiais de Overclock coletados ao derrotar Mini-Bosses da arena.
"""

import os
import random
import pygame
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA,
    ROXO_ACENTO, ROXO_CLARO, ROXO_ESCURO,
    DOURADO, VERDE_CURA, VERMELHO_DANO, LARANJA_ALERTA, BRANCO, CINZA_TEXTO,
    obter_caminho_asset
)
from src.utils.math_utils import clamp

# Paleta Cyber-Office (Spec §8 aprovada)
_C_BACKDROP = (7, 9, 14)
_C_HUD_PANEL = (11, 14, 23)
_C_CARD = (17, 24, 39)
_C_CARD_HOVER = (24, 28, 50)
_C_ELEVATED = (30, 41, 59)
_C_BORDER = (51, 65, 85)
_C_TEXT_PRIMARY = (241, 245, 249)
_C_TEXT_SECONDARY = (148, 163, 184)
_C_TEXT_MUTED = (100, 116, 139)
_C_PURPLE = (168, 85, 247)
_C_PURPLE_SOFT = (216, 180, 254)
_C_GREEN = (16, 185, 129)
_C_GREEN_SOFT = (110, 231, 183)
_C_GOLD = (251, 191, 36)


_FONT_CACHE: dict[tuple[str, int, bool, bool], pygame.font.Font] = {}


def _carregar_fonte_sans(tamanho: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    px_sz = max(8, int(tamanho))
    chave = ("sans", px_sz, bold, italic)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in ("notosans", "dejavusans", "liberationsans", "arial"):
        f = pygame.font.SysFont(nome, px_sz, bold=bold, italic=italic)
        if f is not None:
            _FONT_CACHE[chave] = f
            return f
    f = pygame.font.SysFont("Arial", px_sz, bold=bold, italic=italic)
    _FONT_CACHE[chave] = f
    return f


def _carregar_fonte_mono(tamanho: int, bold: bool = False) -> pygame.font.Font:
    px_sz = max(8, int(tamanho))
    chave = ("mono", px_sz, bold, False)
    if chave in _FONT_CACHE:
        return _FONT_CACHE[chave]
    for nome in ("jetbrainsmono", "firacode", "consolas", "dejavusansmono"):
        f = pygame.font.SysFont(nome, px_sz, bold=bold)
        if f is not None:
            _FONT_CACHE[chave] = f
            return f
    f = pygame.font.SysFont("Consolas", px_sz, bold=bold)
    _FONT_CACHE[chave] = f
    return f


CATALOGO_OVERCLOCKS = [
    {
        "id": "multithreading",
        "nome": "Multithreading",
        "subtitulo": "NÚCLEOS DE ESCOLTA",
        "buff": "Gera 2 núcleos orbitais que disparam cópias leves e bloqueiam 1 projétil inimigo a cada 4s.",
        "flavor": "Dois núcleos trabalhando para você não levar tiro de graça."
    },
    {
        "id": "refrigeracao",
        "nome": "Refrigeração a Nitrogênio",
        "subtitulo": "CONTROLE TÉRMICO",
        "buff": "+20% de cadência base. Parar de atirar por 1.5s libera uma onda de frio que reduz a velocidade dos inimigos em 50%.",
        "flavor": "Aproveita o resfriamento do cano para congelar quem estiver perto."
    },
    {
        "id": "overvolt",
        "nome": "Overvolt",
        "subtitulo": "DESCARGA ACUMULADA",
        "buff": "+15% de chance de crítico. A cada 25 abates (ou acerto crítico), dispara um arco elétrico em até 4 inimigos.",
        "flavor": "Sobe a tensão na marra até sair faísca nos alvos próximos."
    },
    {
        "id": "bios_modding",
        "nome": "BIOS Modding",
        "subtitulo": "SLOT DUPLO",
        "buff": "Permite equipar duas armas especiais (Botão Esquerdo / Direito) e recupera 15% de munição ao derrotar Mini-Bosses.",
        "flavor": "Destrava o segundo barramento de armas da placa."
    },
    {
        "id": "protecao_surtos",
        "nome": "Proteção contra Surtos",
        "subtitulo": "DISJUNTOR DE EMERGÊNCIA",
        "buff": "+50 de vida máxima. Dano fatal desarma o disjuntor: congela a arena por 4s e recupera 50% da vida (60s de recarga).",
        "flavor": "Quando tudo dá errado, o disjuntor desarma antes de você queimar."
    },
    {
        "id": "upgrade_barramento",
        "nome": "Upgrade de Barramento",
        "subtitulo": "COLETA DE CAMPO",
        "buff": "+15% de velocidade de movimento fixa e puxa automaticamente itens e gemas de XP na arena.",
        "flavor": "Trilhas de cobre limpas para puxar tudo o que cai no chão."
    }
]

MODULOS_OVERCLOCK = CATALOGO_OVERCLOCKS



class ModalOverclock:
    """
    Modal de interface para escolha de módulos de Overclock BIOS.
    """

    def __init__(self, jogador=None, cena=None):
        self.jogador = jogador
        self.cena = cena
        self.ativo = False

        self.cards_sorteados: list[dict] = []
        self.card_rects: list[pygame.Rect] = []
        self.card_hovered = None
        self._ultimo_hover = None
        self._hover_lift: list[float] = [0.0, 0.0, 0.0]
        self._mouse_pressionado_anterior = False

        self.tempo_transicao_entrada = 0.0
        self.tempo_transicao_saida = 0.0

        self._fonte_titulo = None
        self._fonte_sub = None
        self._fonte_card_tit = None
        self._fonte_card_sub = None
        self._fonte_card_badge = None
        self._fonte_card_sec = None
        self._fonte_card_desc = None
        self._fonte_card_flavor = None
        self._fonte_rodape = None

        # Superfícies pré-alocadas para alta performance (zero alocação por frame)
        self._overlay_fundo = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._layer_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._glow_surf = pygame.Surface((280 + 24, 410 + 24), pygame.SRCALPHA)

        self._inicializar_rects()

    def _inicializar_fontes(self):
        if self._fonte_titulo is None:
            self._fonte_titulo = _carregar_fonte_sans(32, bold=True)
            self._fonte_sub = _carregar_fonte_sans(15, bold=False)
            self._fonte_card_tit = _carregar_fonte_sans(18, bold=True)
            self._fonte_card_sub = _carregar_fonte_sans(10, bold=True)
            self._fonte_card_badge = _carregar_fonte_mono(12, bold=True)
            self._fonte_card_sec = _carregar_fonte_sans(10, bold=True)
            self._fonte_card_desc = _carregar_fonte_sans(13, bold=False)
            self._fonte_card_flavor = _carregar_fonte_sans(12, italic=True)
            self._fonte_rodape = _carregar_fonte_mono(12, bold=False)

    def _inicializar_rects(self):
        self.card_rects = []
        card_w = 280
        card_h = 410
        espacamento = 44
        start_x = (LARGURA_TELA - (3 * card_w + 2 * espacamento)) // 2
        start_y = (ALTURA_TELA - card_h) // 2 + 20

        for i in range(3):
            rx = start_x + i * (card_w + espacamento)
            self.card_rects.append(pygame.Rect(rx, start_y, card_w, card_h))

    def _tocar_som(self, chave_som: str):
        """Reproduz efeito sonoro de forma segura sem crash em ambiente headless."""
        try:
            from PPlay.sound import Sound
            caminho = obter_caminho_asset(chave_som)
            if os.path.isfile(caminho):
                sfx = Sound(caminho)
                sfx.play()
        except (KeyError, pygame.error, OSError, ImportError):
            pass

    def abrir(self):
        """Abre o modal sorteando 3 overclocks distintos que o jogador ainda não possui."""
        adquiridos = set()
        if self.jogador is not None and hasattr(self.jogador, "overclocks_adquiridos"):
            adquiridos = set(self.jogador.overclocks_adquiridos)

        pool = [mod for mod in CATALOGO_OVERCLOCKS if mod.get("id") not in adquiridos]
        # Fallback caso já tenha adquirido todos ou quase todos
        if len(pool) < 3:
            faltantes = [mod for mod in CATALOGO_OVERCLOCKS if mod not in pool]
            random.shuffle(faltantes)
            pool.extend(faltantes[:3 - len(pool)])

        random.shuffle(pool)
        self.cards_sorteados = pool[:3]
        self.ativo = True
        self.tempo_transicao_entrada = 0.35
        self.tempo_transicao_saida = 0.0
        self._mouse_pressionado_anterior = True
        self.card_hovered = None
        self._ultimo_hover = None

    def selecionar_card(self, indice: int):
        """Aplica o overclock selecionado ao jogador e fecha o modal."""
        if not self.ativo or indice < 0 or indice >= len(self.cards_sorteados):
            return

        self._tocar_som("sfx_btn_click")

        card = self.cards_sorteados[indice]
        mod_id = card.get("id")

        if self.jogador is not None and hasattr(self.jogador, "aplicar_overclock"):
            self.jogador.aplicar_overclock(mod_id)

        if self.cena and hasattr(self.cena, "aplicar_modificadores"):
            self.cena.aplicar_modificadores()

        self.ativo = False
        self.tempo_transicao_saida = 0.20
        if self.cena and hasattr(self.cena, "pausado"):
            self.cena.pausado = False

    @property
    def opcoes_sorteadas(self) -> list[dict]:
        return self.cards_sorteados

    def selecionar_opcao(self, index: int):
        return self.selecionar_card(index)

    def update(self, dt: float, teclado=None, mouse=None):
        if self.tempo_transicao_saida > 0.0:
            self.tempo_transicao_saida = max(0.0, self.tempo_transicao_saida - dt)
            return

        if not self.ativo:
            return

        if self.tempo_transicao_entrada > 0.0:
            self.tempo_transicao_entrada = max(0.0, self.tempo_transicao_entrada - dt)
            if self.tempo_transicao_entrada > 0.0:
                return

        # Teclas numéricas 1, 2, 3 (e Numpad) usando key_down para seleção por teclado
        k1, k2, k3 = False, False, False

        if teclado is not None:
            # Dá preferência a key_down; se key_down retornar False ou não for usado, checa key_pressed para retrocompatibilidade
            kd1 = hasattr(teclado, "key_down") and (teclado.key_down("1") or teclado.key_down("KP1") or teclado.key_down("KP_1") or teclado.key_down("[1]"))
            kd2 = hasattr(teclado, "key_down") and (teclado.key_down("2") or teclado.key_down("KP2") or teclado.key_down("KP_2") or teclado.key_down("[2]"))
            kd3 = hasattr(teclado, "key_down") and (teclado.key_down("3") or teclado.key_down("KP3") or teclado.key_down("KP_3") or teclado.key_down("[3]"))

            kp1 = hasattr(teclado, "key_pressed") and (teclado.key_pressed("1") or teclado.key_pressed("KP1") or teclado.key_pressed("KP_1") or teclado.key_pressed("[1]"))
            kp2 = hasattr(teclado, "key_pressed") and (teclado.key_pressed("2") or teclado.key_pressed("KP2") or teclado.key_pressed("KP_2") or teclado.key_pressed("[2]"))
            kp3 = hasattr(teclado, "key_pressed") and (teclado.key_pressed("3") or teclado.key_pressed("KP3") or teclado.key_pressed("KP_3") or teclado.key_pressed("[3]"))

            if kd1 or kp1:
                k1 = True
            if kd2 or kp2:
                k2 = True
            if kd3 or kp3:
                k3 = True

        if k1:
            self.selecionar_card(0)
            return
        elif k2:
            self.selecionar_card(1)
            return
        elif k3:
            self.selecionar_card(2)
            return

        # Mouse
        mx, my = (400, 300)
        mouse_clicado = False
        if mouse is not None:
            try:
                mx, my = mouse.get_position()
            except (AttributeError, TypeError):
                pass

        pressionado_agora = pygame.mouse.get_pressed()[0] if pygame.mouse.get_focused() else False
        if pressionado_agora and not self._mouse_pressionado_anterior:
            mouse_clicado = True
        self._mouse_pressionado_anterior = pressionado_agora

        self.card_hovered = None
        for i, rect in enumerate(self.card_rects):
            if i < len(self.cards_sorteados) and rect.collidepoint(mx, my):
                self.card_hovered = i
                if self.card_hovered != self._ultimo_hover:
                    self._tocar_som("sfx_btn_hover")
                    self._ultimo_hover = self.card_hovered

                if mouse_clicado:
                    self.selecionar_card(i)
                    return
        if self.card_hovered is None:
            self._ultimo_hover = None

        taxa = min(1.0, dt * 16.0)
        for i in range(len(self._hover_lift)):
            alvo = -4.0 if self.card_hovered == i else 0.0
            self._hover_lift[i] += (alvo - self._hover_lift[i]) * taxa

    def draw(self, screen: pygame.Surface):
        if (not self.ativo and self.tempo_transicao_saida <= 0.0) or screen is None:
            return

        self._inicializar_fontes()

        # Fator de interpolação da transição (0.0 a 1.0)
        if self.tempo_transicao_saida > 0.0:
            fator_anim = clamp(self.tempo_transicao_saida / 0.20, 0.0, 1.0)
        elif self.tempo_transicao_entrada > 0.0:
            fator_anim = clamp(1.0 - (self.tempo_transicao_entrada / 0.35), 0.0, 1.0)
        else:
            fator_anim = 1.0

        slide_offset_y = int((1.0 - fator_anim) * 20.0)
        alpha_fundo = int(fator_anim * 220)
        alpha_conteudo = int(fator_anim * 255)

        # Projeção Native-DPI
        sw, sh = screen.get_size()
        scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
        vx = (sw - int(round(LARGURA_TELA * scale))) // 2
        vy = (sh - int(round(ALTURA_TELA * scale))) // 2

        def px(val: float) -> int:
            return vx + int(round(val * scale))

        def py(val: float) -> int:
            return vy + int(round(val * scale))

        def ps(val: float) -> int:
            return max(1, int(round(val * scale)))

        # Fontes nativas cacheadas por escala
        fonte_titulo = _carregar_fonte_sans(max(8, int(round(32 * scale))), bold=True)
        fonte_sub = _carregar_fonte_sans(max(8, int(round(15 * scale))), bold=False)
        fonte_card_tit = _carregar_fonte_sans(max(8, int(round(18 * scale))), bold=True)
        fonte_card_sub = _carregar_fonte_sans(max(8, int(round(10 * scale))), bold=True)
        fonte_card_badge = _carregar_fonte_mono(max(8, int(round(12 * scale))), bold=True)
        fonte_card_sec = _carregar_fonte_sans(max(8, int(round(10 * scale))), bold=True)
        fonte_card_desc = _carregar_fonte_sans(max(8, int(round(13 * scale))), bold=False)
        fonte_card_flavor = _carregar_fonte_sans(max(8, int(round(12 * scale))), italic=True)
        fonte_rodape = _carregar_fonte_mono(max(8, int(round(12 * scale))), bold=False)

        # Redimensiona superfícies cacheadas apenas quando resolução muda
        if self._overlay_fundo.get_size() != (sw, sh):
            self._overlay_fundo = pygame.Surface((sw, sh), pygame.SRCALPHA)
        if self._layer_surf.get_size() != (sw, sh):
            self._layer_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        glow_pad = ps(12)
        glow_sz = (ps(280) + glow_pad * 2, ps(410) + glow_pad * 2)
        if self._glow_surf.get_size() != glow_sz:
            self._glow_surf = pygame.Surface(glow_sz, pygame.SRCALPHA)

        # 1. Overlay Escuro Translúcido sobre todo o ecrã nativo (#07090e)
        self._overlay_fundo.fill((*_C_BACKDROP, alpha_fundo))
        screen.blit(self._overlay_fundo, (0, 0))

        # 2. Superfície de Conteúdo com Transparência Global (reutilizada)
        self._layer_surf.fill((0, 0, 0, 0))
        layer_surf = self._layer_surf
        centro_x = px(LARGURA_TELA // 2)

        # Filete superior Roxo / Dourado
        stripe_y = py(26 + slide_offset_y)
        stripe_h = max(2, ps(2))
        pygame.draw.rect(layer_surf, _C_PURPLE, (px(160), stripe_y, ps(LARGURA_TELA // 2 - 160), stripe_h))
        pygame.draw.rect(layer_surf, _C_GOLD, (centro_x, stripe_y, ps(LARGURA_TELA // 2 - 160), stripe_h))

        # Título
        sh_off = max(1, ps(2))
        tit_sombra = fonte_titulo.render("NÚCLEO DE OVERCLOCK OBTIDO!", True, (0, 0, 0))
        tit_surf = fonte_titulo.render("NÚCLEO DE OVERCLOCK OBTIDO!", True, _C_GOLD)
        tit_rect = tit_surf.get_rect(centerx=centro_x, top=py(42 + slide_offset_y))
        layer_surf.blit(tit_sombra, (tit_rect.x + sh_off, tit_rect.y + sh_off))
        layer_surf.blit(tit_surf, tit_rect)

        # Subtítulo
        sub_surf = fonte_sub.render("Selecione um protocolo BIOS para instalar na Batata com [1] [2] [3] ou clique", True, _C_PURPLE_SOFT)
        layer_surf.blit(sub_surf, sub_surf.get_rect(centerx=centro_x, top=py(86 + slide_offset_y)))

        # Cards (Cyber-Office + Hover -4 px + Glow em DPI nativo)
        for i, card in enumerate(self.cards_sorteados):
            if i >= len(self.card_rects):
                break
            base_rect = self.card_rects[i]
            is_hovered = (self.card_hovered == i)
            lift_px = int(round(self._hover_lift[i])) if i < len(self._hover_lift) else 0
            if is_hovered and lift_px == 0:
                lift_px = -4

            rect = pygame.Rect(
                px(base_rect.x),
                py(base_rect.y + slide_offset_y + lift_px),
                ps(base_rect.width),
                ps(base_rect.height),
            )
            accent = _C_GOLD if is_hovered else _C_PURPLE

            # Glow externo no hover
            if is_hovered:
                self._glow_surf.fill((0, 0, 0, 0))
                for camada in range(4, 0, -1):
                    exp = ps(camada * 3)
                    alpha_g = int(48 * (1.0 - (camada - 1) / 4.0))
                    gr = pygame.Rect(glow_pad - exp, glow_pad - exp, rect.width + exp * 2, rect.height + exp * 2)
                    pygame.draw.rect(self._glow_surf, (*_C_PURPLE, alpha_g), gr, width=max(2, ps(3)), border_radius=ps(12) + exp // 2)
                layer_surf.blit(self._glow_surf, (rect.x - glow_pad, rect.y - glow_pad))

            cor_bg = _C_CARD_HOVER if is_hovered else _C_CARD
            cor_borda = _C_GOLD if is_hovered else _C_PURPLE
            borda_w = ps(2) if is_hovered else max(1, ps(1))

            pygame.draw.rect(layer_surf, cor_bg, rect, border_radius=ps(12))
            pygame.draw.rect(layer_surf, cor_borda, rect, width=borda_w, border_radius=ps(12))

            # Barra semântica superior
            pygame.draw.rect(layer_surf, accent, (rect.x + ps(14), rect.y + 1, rect.width - ps(28), max(2, ps(3))), border_radius=max(1, ps(2)))

            # Subtítulo da categoria (pill top-left)
            cat_txt = card.get("subtitulo", "BIOS OVERCLOCK")
            cat_surf = fonte_card_sub.render(cat_txt, True, _C_PURPLE_SOFT)
            cat_pill = pygame.Rect(rect.x + ps(12), rect.y + ps(12), min(rect.width - ps(74), cat_surf.get_width() + ps(14)), cat_surf.get_height() + ps(6))
            pygame.draw.rect(layer_surf, (*_C_PURPLE, 30), cat_pill, border_radius=ps(5))
            pygame.draw.rect(layer_surf, _C_PURPLE, cat_pill, width=max(1, ps(1)), border_radius=ps(5))
            layer_surf.blit(cat_surf, cat_surf.get_rect(center=cat_pill.center))

            # Badge Keycap [1], [2], [3] (monospace top-right)
            badge_fg = _C_BACKDROP if is_hovered else _C_TEXT_PRIMARY
            badge_bg_col = _C_GOLD if is_hovered else _C_ELEVATED
            badge_surf = fonte_card_badge.render(f"[{i + 1}]", True, badge_fg)
            badge_bg = pygame.Rect(0, 0, badge_surf.get_width() + ps(14), badge_surf.get_height() + ps(8))
            badge_bg.topright = (rect.right - ps(12), rect.top + ps(10))
            pygame.draw.rect(layer_surf, badge_bg_col, badge_bg, border_radius=ps(5))
            pygame.draw.rect(layer_surf, cor_borda, badge_bg, width=max(1, ps(1)), border_radius=ps(5))
            layer_surf.blit(badge_surf, badge_surf.get_rect(center=badge_bg.center))

            # Nome do Overclock (wrap seguro)
            nome_val = card.get("nome", "")
            palavras_n = nome_val.split(" ")
            linhas_n, ln_cur = [], ""
            for p in palavras_n:
                teste = f"{ln_cur} {p}".strip()
                if fonte_card_tit.size(teste)[0] <= rect.width - ps(28):
                    ln_cur = teste
                else:
                    if ln_cur:
                        linhas_n.append(ln_cur)
                    ln_cur = p
            if ln_cur:
                linhas_n.append(ln_cur)

            ny = rect.y + ps(48)
            for ln in linhas_n[:2]:
                nome_surf = fonte_card_tit.render(ln, True, _C_GOLD if is_hovered else _C_TEXT_PRIMARY)
                layer_surf.blit(nome_surf, (rect.x + ps(14), ny))
                ny += ps(23)

            # Sub-card de Efeito (Verde Esmeralda #10b981)
            ben_top = max(rect.y + ps(98), ny + ps(8))
            ben_h = ps(178)
            ben_rect = pygame.Rect(rect.x + ps(12), ben_top, rect.width - ps(24), ben_h)
            pygame.draw.rect(layer_surf, (6, 40, 30, 230), ben_rect, border_radius=ps(8))
            pygame.draw.rect(layer_surf, _C_GREEN, ben_rect, width=max(1, ps(1)), border_radius=ps(8))
            pygame.draw.rect(layer_surf, _C_GREEN, (ben_rect.x, ben_rect.y + ps(6), max(2, ps(3)), ben_rect.height - ps(12)), border_radius=max(1, ps(2)))

            hdr_surf = fonte_card_sec.render("+ EFEITO BIOS", True, _C_GREEN_SOFT)
            hdr_pill = pygame.Rect(ben_rect.x + ps(10), ben_rect.y + ps(8), hdr_surf.get_width() + ps(12), hdr_surf.get_height() + ps(4))
            pygame.draw.rect(layer_surf, (16, 185, 129, 40), hdr_pill, border_radius=ps(4))
            layer_surf.blit(hdr_surf, hdr_surf.get_rect(center=hdr_pill.center))

            desc_texto = card.get("buff", "")
            palavras = desc_texto.split(" ")
            linhas = []
            linha_atual = ""
            for p in palavras:
                teste = f"{linha_atual} {p}".strip()
                if fonte_card_desc.size(teste)[0] < ben_rect.width - ps(24):
                    linha_atual = teste
                else:
                    if linha_atual:
                        linhas.append(linha_atual)
                    linha_atual = p
            if linha_atual:
                linhas.append(linha_atual)

            cur_y = hdr_pill.bottom + ps(8)
            for l in linhas[:7]:
                l_surf = fonte_card_desc.render(l, True, _C_TEXT_PRIMARY)
                layer_surf.blit(l_surf, (ben_rect.x + ps(12), cur_y))
                cur_y += ps(18)

            # Flavor text entre o sub-card e o botão CTA
            flavor_val = card.get("flavor", "")
            flavor_texto = f'"{flavor_val}"'
            f_palavras = flavor_texto.split(" ")
            f_linhas = []
            f_linha_atual = ""
            for p in f_palavras:
                teste = f"{f_linha_atual} {p}".strip()
                if fonte_card_flavor.size(teste)[0] < rect.width - ps(28):
                    f_linha_atual = teste
                else:
                    if f_linha_atual:
                        f_linhas.append(f_linha_atual)
                    f_linha_atual = p
            if f_linha_atual:
                f_linhas.append(f_linha_atual)

            f_cur_y = ben_rect.bottom + ps(10)
            for fl in f_linhas[:3]:
                fl_surf = fonte_card_flavor.render(fl, True, _C_TEXT_MUTED)
                layer_surf.blit(fl_surf, (rect.x + ps(14), f_cur_y))
                f_cur_y += ps(16)

            # Barra CTA inferior
            cta_rect = pygame.Rect(rect.x + ps(12), rect.bottom - ps(42), rect.width - ps(24), ps(30))
            pygame.draw.rect(layer_surf, (*cor_borda, 42) if is_hovered else _C_ELEVATED, cta_rect, border_radius=ps(7))
            pygame.draw.rect(layer_surf, cor_borda if is_hovered else _C_BORDER, cta_rect, width=max(1, ps(1)), border_radius=ps(7))
            cta_surf = fonte_card_badge.render(f"INSTALAR [{i + 1}]", True, _C_GOLD if is_hovered else _C_PURPLE_SOFT)
            layer_surf.blit(cta_surf, cta_surf.get_rect(center=cta_rect.center))

        # Rodapé
        rodape_surf = fonte_rodape.render("[1] [2] [3] Instalar pelo teclado   •   [Mouse] Clique no módulo", True, _C_TEXT_MUTED)
        layer_surf.blit(rodape_surf, rodape_surf.get_rect(centerx=centro_x, bottom=py(ALTURA_TELA - 32)))

        # Blit com alpha global
        if alpha_conteudo < 255:
            layer_surf.set_alpha(alpha_conteudo)
        screen.blit(layer_surf, (0, 0))
