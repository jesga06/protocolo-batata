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
        self._mouse_pressionado_anterior = False

        self.tempo_transicao_entrada = 0.0
        self.tempo_transicao_saida = 0.0

        self._fonte_titulo = None
        self._fonte_sub = None
        self._fonte_card_tit = None
        self._fonte_card_sub = None
        self._fonte_card_desc = None
        self._fonte_card_flavor = None

        # Surface de overlay escurecido pré-alocada para alta performance
        self._overlay_fundo = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._overlay_fundo.fill((12, 8, 22, 220))

        self._inicializar_rects()

    def _inicializar_fontes(self):
        if self._fonte_titulo is None:
            self._fonte_titulo = pygame.font.SysFont("Arial", 32, bold=True)
            self._fonte_sub = pygame.font.SysFont("Arial", 16, bold=True)
            self._fonte_card_tit = pygame.font.SysFont("Arial", 18, bold=True)
            self._fonte_card_sub = pygame.font.SysFont("Arial", 13, bold=True)
            self._fonte_card_desc = pygame.font.SysFont("Arial", 14, bold=False)
            self._fonte_card_flavor = pygame.font.SysFont("Arial", 12, italic=True)

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

        # 1. Overlay Escuro Translúcido sobre o Gameplay
        dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        dark_surf.fill((12, 8, 22, alpha_fundo))
        screen.blit(dark_surf, (0, 0))

        # 2. Superfície de Conteúdo com Transparência Global
        layer_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)

        # Título
        tit_sombra = self._fonte_titulo.render("NÚCLEO DE OVERCLOCK OBTIDO!", True, (0, 0, 0))
        layer_surf.blit(tit_sombra, (LARGURA_TELA // 2 - tit_sombra.get_width() // 2 + 2, 47 + slide_offset_y))
        tit_surf = self._fonte_titulo.render("NÚCLEO DE OVERCLOCK OBTIDO!", True, DOURADO)
        layer_surf.blit(tit_surf, (LARGURA_TELA // 2 - tit_surf.get_width() // 2, 45 + slide_offset_y))

        # Subtítulo
        sub_surf = self._fonte_sub.render("SELECIONE UM PROTOCOLO DE OVERCLOCK PARA INSTALAR NA BATATA", True, ROXO_CLARO)
        layer_surf.blit(sub_surf, (LARGURA_TELA // 2 - sub_surf.get_width() // 2, 85 + slide_offset_y))

        # Cards
        for i, card in enumerate(self.cards_sorteados):
            if i >= len(self.card_rects):
                break
            base_rect = self.card_rects[i]
            rect = pygame.Rect(base_rect.x, base_rect.y + slide_offset_y, base_rect.width, base_rect.height)
            is_hovered = (self.card_hovered == i)

            cor_bg = (38, 24, 54) if not is_hovered else (58, 36, 82)
            cor_borda = DOURADO if is_hovered else ROXO_ACENTO
            borda_w = 3 if is_hovered else 2

            pygame.draw.rect(layer_surf, cor_bg, rect, border_radius=8)
            pygame.draw.rect(layer_surf, cor_borda, rect, width=borda_w, border_radius=8)

            # Badge [1], [2], [3]
            badge_surf = self._fonte_card_sub.render(f"[{i + 1}]", True, DOURADO)
            layer_surf.blit(badge_surf, (rect.x + 12, rect.y + 12))

            # Subtítulo da categoria
            cat_surf = self._fonte_card_sub.render(card.get("subtitulo", "OVERCLOCK"), True, ROXO_CLARO)
            layer_surf.blit(cat_surf, (rect.x + 36, rect.y + 12))

            # Nome
            nome_surf = self._fonte_card_tit.render(card.get("nome", ""), True, BRANCO)
            layer_surf.blit(nome_surf, (rect.x + 12, rect.y + 40))

            # Linha divisória
            pygame.draw.line(layer_surf, (75, 50, 105), (rect.x + 12, rect.y + 68), (rect.right - 12, rect.y + 68), 1)

            # Buff Description
            desc_texto = card.get("buff", "")
            palavras = desc_texto.split(" ")
            linhas = []
            linha_atual = ""
            for p in palavras:
                teste = f"{linha_atual} {p}".strip()
                if self._fonte_card_desc.size(teste)[0] < rect.width - 24:
                    linha_atual = teste
                else:
                    linhas.append(linha_atual)
                    linha_atual = p
            if linha_atual:
                linhas.append(linha_atual)

            cur_y = rect.y + 82
            for l in linhas:
                l_surf = self._fonte_card_desc.render(l, True, VERDE_CURA)
                layer_surf.blit(l_surf, (rect.x + 12, cur_y))
                cur_y += 18

            # Flavor text no rodapé do card
            flavor_val = card.get("flavor", "")
            flavor_texto = f'"{flavor_val}"'
            f_palavras = flavor_texto.split(" ")
            f_linhas = []
            f_linha_atual = ""
            for p in f_palavras:
                teste = f"{f_linha_atual} {p}".strip()
                if self._fonte_card_flavor.size(teste)[0] < rect.width - 24:
                    f_linha_atual = teste
                else:
                    f_linhas.append(f_linha_atual)
                    f_linha_atual = p
            if f_linha_atual:
                f_linhas.append(f_linha_atual)

            f_cur_y = rect.bottom - (len(f_linhas) * 14 + 16)
            for fl in f_linhas:
                fl_surf = self._fonte_card_flavor.render(fl, True, (160, 150, 180))
                layer_surf.blit(fl_surf, (rect.x + 12, f_cur_y))
                f_cur_y += 14

        # Blit com alpha global
        if alpha_conteudo < 255:
            layer_surf.set_alpha(alpha_conteudo)
        screen.blit(layer_surf, (0, 0))
