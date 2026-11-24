"""
Menu de Configurações do Jogo (In-Game e Menu Principal) — Protocolo: Batata
SSOT: CONFIGURACOES.md, s5.md
Permite ao jogador:
- Aba 1: Visualizar e ajustar em tempo real as 20 configurações de gameplay desbloqueadas (bloqueadas ficam desabilitadas/grayed out).
- Aba 2: Ajustar volumes (Master, Música, SFX).
- Pausar o gameplay durante a execução e persistir alterações em save.json.
"""

import os
import pygame
from typing import Optional, Any
from src.sistemas.config_dados import (
    CONFIGURACOES_GAMEPLAY, CONFIGURACOES_SISTEMA,
    ConfiguracaoDef, CategoriaConfig, TipoControleConfig
)
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.ui.banner_dicas import BannerDica
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, BRANCO, PRETO, DOURADO,
    AZUL_CIANO, AMARELO_XP, VERDE_CURA, VERMELHO_HP, LARANJA_ALERTA,
    CINZA_BORDA, CINZA_PAINEL, CINZA_FUNDO, CINZA_TEXTO,
    obter_caminho_asset, SAVE_FILE_PATH
)

# Paleta Cyber-Office (Spec §8 aprovada)
_C_BACKDROP = (7, 9, 14)
_C_HUD_PANEL = (11, 14, 23)
_C_CARD = (17, 24, 39)
_C_CARD_HOVER = (22, 30, 48)
_C_ELEVATED = (30, 41, 59)
_C_BORDER = (51, 65, 85)
_C_TEXT_PRIMARY = (241, 245, 249)
_C_TEXT_SECONDARY = (148, 163, 184)
_C_TEXT_MUTED = (100, 116, 139)
_C_CYAN = (34, 211, 238)
_C_PURPLE = (168, 85, 247)
_C_GREEN = (16, 185, 129)
_C_GREEN_SOFT = (110, 231, 183)
_C_GOLD = (251, 191, 36)
_C_AMBER = (245, 158, 11)
_C_CRIMSON = (239, 68, 68)
_C_CRIMSON_SOFT = (252, 165, 165)


_FONT_CACHE: dict[tuple[str, int, bool, bool], pygame.font.Font] = {}
_ICON_SCALE_CACHE: dict[tuple[str, bool, int, int], pygame.Surface] = {}


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


def _formatar_texto_wrap(texto: str, max_chars_por_linha: int = 26) -> list[str]:
    """Divide texto em linhas respeitando palavras completas."""
    if not texto:
        return []
    palavras = texto.split()
    linhas = []
    linha_atual = []
    tamanho_atual = 0

    for p in palavras:
        if tamanho_atual + len(p) + len(linha_atual) <= max_chars_por_linha:
            linha_atual.append(p)
            tamanho_atual += len(p)
        else:
            if linha_atual:
                linhas.append(" ".join(linha_atual))
            linha_atual = [p]
            tamanho_atual = len(p)

    if linha_atual:
        linhas.append(" ".join(linha_atual))
    return linhas


class MenuConfigs:
    """
    Controlador e interface gráfica do Menu de Configurações com 2 abas (Gameplay e Sistema).
    """
    _icones_cache: dict[str, pygame.Surface] = {}
    _icones_dark_cache: dict[str, pygame.Surface] = {}

    def __init__(
        self,
        gerenciador_config: GerenciadorConfiguracoes,
        em_jogo: bool = True,
        cena=None
    ):
        self.gerenciador_config = gerenciador_config
        self.em_jogo = em_jogo
        self.cena = cena

        self.ativo: bool = False
        self.aba_atual: int = 0  # 0 = Gameplay, 1 = Sistema
        self.banner_dicas = BannerDica()

        # Filtro de categoria na Aba de Gameplay
        self.categoria_filtro: str = "Performance"
        self.categorias_lista = [
            "Performance",
            "Interface",
            "Controles",
            "Dificuldade",
            "Experimental"
        ]

        # Controle de rolagem da lista de gameplay
        self.scroll_y: float = 0.0
        self.max_scroll_y: float = 0.0
        self.config_selecionada_id: str = "fps_cap"

        # Dimensões da tela e painéis com offsets dinâmicos para centralização em 1280x720
        self.offset_x = (LARGURA_TELA - 800) // 2
        self.offset_y = (ALTURA_TELA - 600) // 2
        self.painel_rect = pygame.Rect(self.offset_x + 30, self.offset_y + 20, 740, 560)
        self.lista_rect = pygame.Rect(self.offset_x + 45, self.offset_y + 110, 435, 410)
        self.detalhes_rect = pygame.Rect(self.offset_x + 495, self.offset_y + 110, 260, 410)

        # Superfície de overlay escuro pré-alocada (#07090e)
        self._dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._dark_surf.fill((*_C_BACKDROP, 232))

        # Estado de interação do mouse e teclado
        self._mouse_pressionado_anterior: bool = False
        self._slider_arrastando: Optional[str] = None
        self.cooldown_input: float = 0.0

        # Fontes de texto (cacheadas — zero alocação por frame)
        self._fonte_titulo = None
        self._fonte_sub = None
        self._fonte_aba = None
        self._fonte_cat = None
        self._fonte_item_tit = None
        self._fonte_item_desc = None
        self._fonte_btn = None
        self._fonte_det_tit = None
        self._fonte_det_corpo = None
        self._fonte_det_flavor = None
        self._fonte_rodape = None
        self._toast_conflito: str = ""
        self._toast_conflito_timer: float = 0.0

        self.aplicar_volumes_atuais()

    def _obter_icone(self, chave_icone: str) -> Optional[pygame.Surface]:
        """Recupera ou carrega um ícone 32x32 para a configuração."""
        if chave_icone in self._icones_cache:
            return self._icones_cache[chave_icone]

        img = None
        try:
            caminho = obter_caminho_asset(chave_icone)
            if os.path.isfile(caminho):
                img = pygame.image.load(caminho).convert_alpha()
        except Exception:
            try:
                from src.utils.constantes import ASSETS_DIR
                direto = os.path.join(ASSETS_DIR, "ui", "icones_configs", f"icon_{chave_icone}.png")
                if os.path.isfile(direto):
                    img = pygame.image.load(direto).convert_alpha()
            except Exception:
                img = None

        if img is None:
            try:
                from src.utils.pixel_art_sprites import obter_icone_config
                img = obter_icone_config(chave_icone, 32)
            except Exception:
                img = None

        if img is not None:
            self._icones_cache[chave_icone] = img
        return img

    def _obter_icone_bloqueado(self, chave_icone: str) -> Optional[pygame.Surface]:
        """Recupera ou gera ícone escurecido cacheado para item bloqueado."""
        if chave_icone in self._icones_dark_cache:
            return self._icones_dark_cache[chave_icone]

        img_base = self._obter_icone(chave_icone)
        if img_base is not None:
            icone_dark = img_base.copy()
            icone_dark.fill((100, 100, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._icones_dark_cache[chave_icone] = icone_dark
            return icone_dark
        return None

    def _inicializar_fontes(self):
        """Inicializa as fontes do Pygame sob demanda (Sans-Serif + Monospace)."""
        if self._fonte_titulo is None:
            self._fonte_titulo = _carregar_fonte_sans(22, bold=True)
            self._fonte_sub = _carregar_fonte_sans(11, bold=False)
            self._fonte_aba = _carregar_fonte_sans(12, bold=True)
            self._fonte_cat = _carregar_fonte_sans(9, bold=True)
            self._fonte_item_tit = _carregar_fonte_sans(12, bold=True)
            self._fonte_item_desc = _carregar_fonte_sans(10, bold=False)
            self._fonte_btn = _carregar_fonte_mono(11, bold=True)
            self._fonte_det_tit = _carregar_fonte_sans(15, bold=True)
            self._fonte_det_corpo = _carregar_fonte_sans(11, bold=False)
            self._fonte_det_flavor = _carregar_fonte_sans(10, italic=True)
            self._fonte_rodape = _carregar_fonte_mono(11, bold=False)

    def abrir(self):
        """Abre o menu de configurações com cooldown de proteção contra duplo disparo."""
        self.ativo = True
        self.scroll_y = 0.0
        self.cooldown_input = 0.25
        if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
            self.banner_dicas.proxima_dica()
        self._tocar_som("sfx_btn_click")

    def _obter_rects_barra_topo(self) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, Optional[pygame.Rect]]:
        """Retorna os retângulos das abas, botão Fechar e botão Menu Principal (quando em jogo)."""
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)
        aba0_rect = pygame.Rect(ox + 50, oy + 68, 200, 32)
        aba1_rect = pygame.Rect(ox + 260, oy + 68, 200, 32)
        btn_fechar_rect = pygame.Rect(ox + 650, oy + 68, 105, 32)
        btn_menu_rect = pygame.Rect(ox + 495, oy + 68, 145, 32) if self.em_jogo else None
        return aba0_rect, aba1_rect, btn_fechar_rect, btn_menu_rect

    def sair_para_menu(self):
        """Salva configurações, fecha o menu e retorna ao Menu Principal durante uma partida."""
        if not self.em_jogo:
            return
        self.fechar()
        if self.cena and hasattr(self.cena, "_voltar_menu"):
            self.cena._voltar_menu()

    def fechar(self):
        """Fecha o menu de configurações e persiste as alterações em disco."""
        self.ativo = False
        self._slider_arrastando = None
        self._tocar_som("sfx_btn_click")

        # Salva o estado atualizado em save.json
        self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)

        # Atualiza a cena se estiver vinculada
        if self.cena and hasattr(self.cena, "aplicar_modificadores"):
            self.cena.aplicar_modificadores()

    def alternar_aba(self, nova_aba: int):
        """Troca a aba ativa (0 = Gameplay, 1 = Sistema)."""
        if nova_aba in (0, 1) and nova_aba != self.aba_atual:
            self.aba_atual = nova_aba
            self.scroll_y = 0.0
            self._tocar_som("sfx_btn_click")

    def alterar_valor_gameplay(self, config_id: str, novo_valor: Any) -> bool:
        """Altera o valor de uma configuração de gameplay desbloqueada, tratando conflitos mútuos."""
        if hasattr(self.gerenciador_config, "definir_valor_com_conflitos"):
            sucesso, conflitos = self.gerenciador_config.definir_valor_com_conflitos(config_id, novo_valor)
        else:
            sucesso = self.gerenciador_config.definir_valor(config_id, novo_valor)
            conflitos = []

        if sucesso:
            if conflitos:
                pares = ", ".join(f"{cid} -> {val}" for cid, val in conflitos)
                self._toast_conflito = f"CONFLITO REVERTIDO: {pares}"
                self._toast_conflito_timer = 3.2
            self._tocar_som("sfx_btn_click")
            if self.cena and hasattr(self.cena, "aplicar_modificadores"):
                self.cena.aplicar_modificadores()
        return sucesso

    def ciclar_opcao_gameplay(self, config_id: str, direcao: int = 1) -> bool:
        """Cicla para a próxima opção disponível (e desbloqueada) de uma configuração de gameplay."""
        if not self.gerenciador_config.is_desbloqueada(config_id):
            return False

        cdef = CONFIGURACOES_GAMEPLAY.get(config_id)
        if not cdef or not cdef.opcoes:
            return False

        sys_conq = getattr(self.gerenciador_config, "sistema_conquistas", None)
        chaves_opcoes = []
        for k, opt in cdef.opcoes.items():
            req_opt = getattr(opt, "desbloqueada_por", None)
            if req_opt and sys_conq is not None and not sys_conq.possui_recompensa("opcao_config", f"{config_id}:{k}"):
                continue
            chaves_opcoes.append(k)
        if not chaves_opcoes:
            return False

        valor_atual = str(self.gerenciador_config.obter_valor(config_id))
        try:
            idx_atual = chaves_opcoes.index(valor_atual)
        except ValueError:
            idx_atual = 0

        novo_idx = (idx_atual + direcao) % len(chaves_opcoes)
        novo_valor = chaves_opcoes[novo_idx]
        return self.alterar_valor_gameplay(config_id, novo_valor)

    def aplicar_volumes_atuais(self):
        """Aplica os volumes atuais salvos no mixer do Pygame e no SoundManager."""
        try:
            vol_master = self.gerenciador_config.obter_valor("volume_master")
            vol_musica = self.gerenciador_config.obter_valor("volume_musica")
            vol_sfx = self.gerenciador_config.obter_valor("volume_sfx")

            vol_master = 100 if vol_master is None else int(vol_master)
            vol_musica = 100 if vol_musica is None else int(vol_musica)
            vol_sfx = 100 if vol_sfx is None else int(vol_sfx)

            try:
                from PPlay.sound import SoundManager
                SoundManager.set_sfx_volume(int(round(vol_sfx * (vol_master / 100.0))))
            except Exception:
                pass

            try:
                from src.sistemas.sistema_musica import obter_sistema_musica
                obter_sistema_musica().atualizar_volume(vol_master, vol_musica)
            except Exception:
                pass

            try:
                pygame.mixer.music.set_volume((vol_musica / 100.0) * (vol_master / 100.0) * 0.4)
            except Exception:
                pass
        except Exception:
            pass

    def definir_volume_sistema(self, config_id: str, valor: int):
        """Define o valor de volume no sistema (0 a 100) e atualiza o mixer do Pygame e SoundManager."""
        valor_clamp = max(0, min(100, int(valor)))
        self.gerenciador_config.definir_valor(config_id, valor_clamp)
        self.aplicar_volumes_atuais()

    def update(self, dt: float, teclado=None, mouse=None):
        """Processa interações de teclado, mouse, cliques, sliders e navegação."""
        if not self.ativo:
            return

        # Decrementa o cooldown de input inicial para prevenir fechamento no mesmo frame
        if self.cooldown_input > 0.0:
            self.cooldown_input = max(0.0, self.cooldown_input - dt)
        if self._toast_conflito_timer > 0.0:
            self._toast_conflito_timer = max(0.0, self._toast_conflito_timer - dt)

        # 1. Inputs de Teclado
        if teclado is not None:
            # ESC ou C para fechar o menu (respeitando cooldown de abertura)
            if self.cooldown_input <= 0.0:
                fechar_acionado = False
                if hasattr(teclado, "key_down"):
                    fechar_acionado = teclado.key_down("ESC") or teclado.key_down("c") or teclado.key_down("C")
                elif hasattr(teclado, "key_pressed"):
                    fechar_acionado = teclado.key_pressed("ESC") or teclado.key_pressed("c") or teclado.key_pressed("C")

                if fechar_acionado:
                    self.fechar()
                    return

            # TAB para alternar abas
            tab_acionado = False
            if hasattr(teclado, "key_down"):
                tab_acionado = teclado.key_down("TAB")
            elif hasattr(teclado, "key_pressed"):
                tab_acionado = teclado.key_pressed("TAB")

            if tab_acionado:
                self.alternar_aba((self.aba_atual + 1) % 2)
                return

        # 2. Inputs de Mouse
        mx, my = (400, 300)
        mouse_clicado = False

        if mouse is not None:
            try:
                mx, my = mouse.get_position()
            except Exception:
                mx, my = (400, 300)

            try:
                if hasattr(mouse, "button_down") and mouse.button_down(1):
                    mouse_clicado = True
            except Exception:
                pass

        pressionado_agora = pygame.mouse.get_pressed()[0] if pygame.mouse.get_focused() else False
        if pressionado_agora and not self._mouse_pressionado_anterior:
            mouse_clicado = True
        self._mouse_pressionado_anterior = pressionado_agora

        # 3. Processamento dos Cliques nas Abas, Menu Principal (em jogo) e Botão Fechar
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)
        aba0_rect, aba1_rect, btn_fechar_rect, btn_menu_rect = self._obter_rects_barra_topo()

        if mouse_clicado:
            if aba0_rect.collidepoint(mx, my):
                self.alternar_aba(0)
                return
            elif aba1_rect.collidepoint(mx, my):
                self.alternar_aba(1)
                return
            elif btn_menu_rect is not None and btn_menu_rect.collidepoint(mx, my):
                self.sair_para_menu()
                return
            elif btn_fechar_rect.collidepoint(mx, my):
                self.fechar()
                return

        # 4. Interações da Aba 1: Gameplay
        if self.aba_atual == 0:
            # Categorias Filtro (topo da lista)
            larguras_cats = {
                "Performance": 82,
                "Interface": 68,
                "Controles": 72,
                "Dificuldade": 76,
                "Experimental": 84
            }
            cat_x = ox + 48
            for cat_nome in self.categorias_lista:
                largura_pill = larguras_cats.get(cat_nome, 76)
                cat_btn_rect = pygame.Rect(cat_x, oy + 108, largura_pill, 22)
                if mouse_clicado and cat_btn_rect.collidepoint(mx, my):
                    self.categoria_filtro = None if cat_nome == "TODAS" else cat_nome
                    self.scroll_y = 0.0
                    self._tocar_som("sfx_btn_click")
                    return
                cat_x += largura_pill + 5

            # Lista de itens de gameplay filtrados
            configs_filtradas = [
                cdef for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
                if self.categoria_filtro is None or
                   (cdef.categoria.value if hasattr(cdef.categoria, "value") else str(cdef.categoria)) == self.categoria_filtro
            ]

            item_h = 52
            espaco_total = len(configs_filtradas) * item_h
            area_visivel_h = 370
            self.max_scroll_y = max(0.0, float(espaco_total - area_visivel_h))

            # Botoes de scroll para cima e para baixo
            btn_up_rect = pygame.Rect(ox + 455, oy + 140, 20, 24)
            btn_down_rect = pygame.Rect(ox + 455, oy + 480, 20, 24)

            # Suporte a MOUSEWHEEL via eventos do pygame
            try:
                for ev in pygame.event.get(pygame.MOUSEWHEEL):
                    if ev.y > 0:
                        self.scroll_y = max(0.0, self.scroll_y - item_h * 2)
                    elif ev.y < 0:
                        self.scroll_y = min(self.max_scroll_y, self.scroll_y + item_h * 2)
            except Exception:
                pass

            if mouse_clicado:
                if btn_up_rect.collidepoint(mx, my):
                    self.scroll_y = max(0.0, self.scroll_y - item_h * 2)
                    return
                elif btn_down_rect.collidepoint(mx, my):
                    self.scroll_y = min(self.max_scroll_y, self.scroll_y + item_h * 2)
                    return

            # Itens da lista
            start_y = oy + 136
            for i, cdef in enumerate(configs_filtradas):
                item_y = start_y + i * item_h - self.scroll_y
                if item_y + item_h < oy + 135 or item_y > oy + 515:
                    continue  # Fora da área de visualização

                item_rect = pygame.Rect(ox + 50, item_y, 400, 48)
                is_desbloqueada = self.gerenciador_config.is_desbloqueada(cdef.id)

                # Se o mouse passou por cima, seleciona para visualização no inspetor
                if item_rect.collidepoint(mx, my):
                    self.config_selecionada_id = cdef.id

                # Controles interativos dentro do item
                if is_desbloqueada:
                    # Botão de Toggle ou Ciclo
                    ctrl_rect = pygame.Rect(ox + 320, item_y + 10, 120, 28)
                    btn_prev_rect = pygame.Rect(ox + 320, item_y + 10, 24, 28)
                    btn_next_rect = pygame.Rect(ox + 420, item_y + 10, 24, 28)

                    if mouse_clicado:
                        if cdef.tipo == TipoControleConfig.TOGGLE:
                            if ctrl_rect.collidepoint(mx, my):
                                self.ciclar_opcao_gameplay(cdef.id, 1)
                                return
                        else:
                            if btn_prev_rect.collidepoint(mx, my):
                                self.ciclar_opcao_gameplay(cdef.id, -1)
                                return
                            elif btn_next_rect.collidepoint(mx, my):
                                self.ciclar_opcao_gameplay(cdef.id, 1)
                                return

        # 5. Interações da Aba 2: Sistema
        elif self.aba_atual == 1:
            # Sliders de Volume (Master, Música, SFX)
            sliders_info = [
                ("volume_master", oy + 160),
                ("volume_musica", oy + 230),
                ("volume_sfx", oy + 300)
            ]

            for cid, y_pos in sliders_info:
                track_rect = pygame.Rect(ox + 280, y_pos + 6, 260, 14)
                btn_menos = pygame.Rect(ox + 240, y_pos, 30, 26)
                btn_mais = pygame.Rect(ox + 550, y_pos, 30, 26)

                val_atual = self.gerenciador_config.obter_valor(cid)
                val_atual = 100 if val_atual is None else int(val_atual)

                if mouse_clicado:
                    if btn_menos.collidepoint(mx, my):
                        self.definir_volume_sistema(cid, max(0, val_atual - 5))
                        self._tocar_som("sfx_btn_click")
                        return
                    elif btn_mais.collidepoint(mx, my):
                        self.definir_volume_sistema(cid, min(100, val_atual + 5))
                        self._tocar_som("sfx_btn_click")
                        return
                    elif track_rect.collidepoint(mx, my):
                        self._slider_arrastando = cid

                # Atualiza valor se estiver arrastando com o mouse
                if pressionado_agora and self._slider_arrastando == cid:
                    rel_x = max(0.0, min(1.0, (mx - track_rect.x) / float(track_rect.width)))
                    novo_val = int(round(rel_x * 100))
                    self.definir_volume_sistema(cid, novo_val)

            if not pressionado_agora:
                self._slider_arrastando = None

    def _atualizar_viewport(self, screen: pygame.Surface):
        """Calcula projeção Native-DPI (vx, vy, scale) e atualiza fontes cacheadas por escala."""
        sw, sh = screen.get_size()
        scale = min(sw / float(LARGURA_TELA), sh / float(ALTURA_TELA))
        self._vp_vx = (sw - int(round(LARGURA_TELA * scale))) // 2
        self._vp_vy = (sh - int(round(ALTURA_TELA * scale))) // 2
        self._vp_scale = scale

        self._fonte_titulo = _carregar_fonte_sans(max(8, int(round(22 * scale))), bold=True)
        self._fonte_sub = _carregar_fonte_sans(max(8, int(round(11 * scale))), bold=False)
        self._fonte_aba = _carregar_fonte_sans(max(8, int(round(12 * scale))), bold=True)
        self._fonte_cat = _carregar_fonte_sans(max(8, int(round(9 * scale))), bold=True)
        self._fonte_item_tit = _carregar_fonte_sans(max(8, int(round(12 * scale))), bold=True)
        self._fonte_item_desc = _carregar_fonte_sans(max(8, int(round(10 * scale))), bold=False)
        self._fonte_btn = _carregar_fonte_mono(max(8, int(round(11 * scale))), bold=True)
        self._fonte_det_tit = _carregar_fonte_sans(max(8, int(round(15 * scale))), bold=True)
        self._fonte_det_corpo = _carregar_fonte_sans(max(8, int(round(11 * scale))), bold=False)
        self._fonte_det_flavor = _carregar_fonte_sans(max(8, int(round(10 * scale))), italic=True)
        self._fonte_rodape = _carregar_fonte_mono(max(8, int(round(11 * scale))), bold=False)

    def _px(self, val: float) -> int:
        return self._vp_vx + int(round(val * self._vp_scale))

    def _py(self, val: float) -> int:
        return self._vp_vy + int(round(val * self._vp_scale))

    def _ps(self, val: float) -> int:
        return max(1, int(round(val * self._vp_scale)))

    def _pr(self, r: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(self._px(r.x), self._py(r.y), self._ps(r.width), self._ps(r.height))

    def draw(self, screen: pygame.Surface):
        """Renderiza a janela do menu de configurações em DPI nativo."""
        if not self.ativo or screen is None:
            return

        self._atualizar_viewport(screen)
        sw, sh = screen.get_size()

        # 1. Overlay Escuro de Fundo cobrindo todo o ecrã nativo (reutiliza superfície pré-alocada)
        if self._dark_surf is None or self._dark_surf.get_size() != (sw, sh):
            self._dark_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            self._dark_surf.fill((*_C_BACKDROP, 232))
        screen.blit(self._dark_surf, (0, 0))

        # 2. Painel Principal Centralizado (#0b0e17 + borda #334155 + filete Roxo/Dourado)
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)
        painel_px = self._pr(self.painel_rect)
        pygame.draw.rect(screen, _C_HUD_PANEL, painel_px, border_radius=self._ps(10))
        pygame.draw.rect(screen, _C_BORDER, painel_px, width=max(1, self._ps(1)), border_radius=self._ps(10))
        meio_w = (painel_px.width - self._ps(28)) // 2
        stripe_h = max(2, self._ps(2))
        pygame.draw.rect(screen, _C_PURPLE, (painel_px.x + self._ps(14), painel_px.y + 1, meio_w, stripe_h))
        pygame.draw.rect(screen, _C_GOLD, (painel_px.x + self._ps(14) + meio_w, painel_px.y + 1, meio_w, stripe_h))

        # 3. Cabeçalho com Título e Subtítulo
        tit_surf = self._fonte_titulo.render("CONFIGURAÇÕES DO SISTEMA", True, _C_GOLD)
        screen.blit(tit_surf, (self._px(ox + 50), self._py(oy + 26)))

        sub_txt = "Ative sacrifícios técnicos para desbloquear vantagens mecânicas em tempo real" if self.aba_atual == 0 else "Ajustes de áudio e volumes do sistema"
        sub_surf = self._fonte_sub.render(sub_txt, True, _C_TEXT_SECONDARY)
        screen.blit(sub_surf, (self._px(ox + 50), self._py(oy + 51)))

        # 4. Barra de Abas [ GAMEPLAY ] e [ SISTEMA ]
        aba0_l, aba1_l, btn_fechar_l, btn_menu_l = self._obter_rects_barra_topo()
        aba0_rect = self._pr(aba0_l)
        aba1_rect = self._pr(aba1_l)
        btn_fechar_rect = self._pr(btn_fechar_l)
        btn_menu_rect = self._pr(btn_menu_l) if btn_menu_l is not None else None

        # Aba 0: Gameplay
        cor_aba0 = _C_CARD if self.aba_atual == 0 else _C_HUD_PANEL
        cor_borda0 = _C_GOLD if self.aba_atual == 0 else _C_ELEVATED
        pygame.draw.rect(screen, cor_aba0, aba0_rect, border_radius=self._ps(7))
        pygame.draw.rect(screen, cor_borda0, aba0_rect, width=self._ps(2) if self.aba_atual == 0 else max(1, self._ps(1)), border_radius=self._ps(7))
        t_aba0 = self._fonte_aba.render("GAMEPLAY", True, _C_GOLD if self.aba_atual == 0 else _C_TEXT_SECONDARY)
        screen.blit(t_aba0, t_aba0.get_rect(center=aba0_rect.center))

        # Aba 1: Sistema
        cor_aba1 = _C_CARD if self.aba_atual == 1 else _C_HUD_PANEL
        cor_borda1 = _C_GOLD if self.aba_atual == 1 else _C_ELEVATED
        pygame.draw.rect(screen, cor_aba1, aba1_rect, border_radius=self._ps(7))
        pygame.draw.rect(screen, cor_borda1, aba1_rect, width=self._ps(2) if self.aba_atual == 1 else max(1, self._ps(1)), border_radius=self._ps(7))
        t_aba1 = self._fonte_aba.render("ÁUDIO & SISTEMA", True, _C_GOLD if self.aba_atual == 1 else _C_TEXT_SECONDARY)
        screen.blit(t_aba1, t_aba1.get_rect(center=aba1_rect.center))

        # Botão Sair para o Menu Principal (apenas durante gameplay)
        if btn_menu_rect is not None:
            pygame.draw.rect(screen, (42, 28, 16), btn_menu_rect, border_radius=self._ps(7))
            pygame.draw.rect(screen, _C_AMBER, btn_menu_rect, width=max(1, self._ps(1)), border_radius=self._ps(7))
            t_menu = self._fonte_aba.render("MENU PRINCIPAL", True, _C_GOLD)
            screen.blit(t_menu, t_menu.get_rect(center=btn_menu_rect.center))

        # Botão Fechar [ESC]
        pygame.draw.rect(screen, (42, 18, 21), btn_fechar_rect, border_radius=self._ps(7))
        pygame.draw.rect(screen, _C_CRIMSON, btn_fechar_rect, width=max(1, self._ps(1)), border_radius=self._ps(7))
        t_fec = self._fonte_btn.render("FECHAR [ESC]", True, _C_CRIMSON_SOFT)
        screen.blit(t_fec, t_fec.get_rect(center=btn_fechar_rect.center))

        # 5. Renderização do Conteúdo Específico da Aba
        if self.aba_atual == 0:
            self._desenhar_aba_gameplay(screen)
        else:
            self._desenhar_aba_sistema(screen)

        # 6. Rodapé com Instruções (monospace)
        rodape_txt = "[TAB] Abas   •   [ESC / C] Salvar e Fechar   •   [Mouse] Ajustar Opções"
        rodape_surf = self._fonte_rodape.render(rodape_txt, True, _C_TEXT_MUTED)
        rodape_rect = rodape_surf.get_rect(centerx=painel_px.centerx, bottom=painel_px.bottom - self._ps(10))
        screen.blit(rodape_surf, rodape_rect)

        if hasattr(self, "banner_dicas") and self.banner_dicas is not None:
            dica_rect = pygame.Rect(painel_px.x, painel_px.bottom + self._ps(8), painel_px.width, self._ps(48))
            self.banner_dicas.desenhar(screen, dica_rect, scale=self._vp_scale)

    def _desenhar_aba_gameplay(self, screen: pygame.Surface):
        """Renderiza a lista de 20 configs e o painel de inspeção detalhado à direita em DPI nativo."""
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)

        # 1. Filtros de Categoria no topo da lista
        larguras_cats = {
            "Performance": 82,
            "Interface": 68,
            "Controles": 72,
            "Dificuldade": 76,
            "Experimental": 84
        }
        cat_x = ox + 48
        for cat_nome in self.categorias_lista:
            is_ativa = (self.categoria_filtro is None and cat_nome == "TODAS") or (self.categoria_filtro == cat_nome)
            largura_pill = larguras_cats.get(cat_nome, 76)
            cat_rect = pygame.Rect(self._px(cat_x), self._py(oy + 108), self._ps(largura_pill), self._ps(22))
            cor_bg = (14, 42, 54) if is_ativa else _C_CARD
            cor_borda = _C_CYAN if is_ativa else _C_ELEVATED
            pygame.draw.rect(screen, cor_bg, cat_rect, border_radius=self._ps(5))
            pygame.draw.rect(screen, cor_borda, cat_rect, width=max(1, self._ps(1)), border_radius=self._ps(5))

            cat_surf = self._fonte_cat.render(cat_nome.upper(), True, _C_CYAN if is_ativa else _C_TEXT_SECONDARY)
            screen.blit(cat_surf, cat_surf.get_rect(center=cat_rect.center))
            cat_x += largura_pill + 5

        # 2. Lista de Configurações
        configs_filtradas = [
            cdef for cid, cdef in CONFIGURACOES_GAMEPLAY.items()
            if self.categoria_filtro is None or
               (cdef.categoria.value if hasattr(cdef.categoria, "value") else str(cdef.categoria)) == self.categoria_filtro
        ]

        item_h = 52
        start_y = oy + 136

        # Fundo da lista (#07090e)
        lista_bg = pygame.Rect(self._px(ox + 48), self._py(oy + 134), self._ps(404), self._ps(380))
        pygame.draw.rect(screen, _C_BACKDROP, lista_bg, border_radius=self._ps(8))
        pygame.draw.rect(screen, _C_ELEVATED, lista_bg, width=max(1, self._ps(1)), border_radius=self._ps(8))

        for i, cdef in enumerate(configs_filtradas):
            item_y = start_y + i * item_h - self.scroll_y
            if item_y + item_h < oy + 135 or item_y > oy + 510:
                continue

            item_rect = pygame.Rect(self._px(ox + 50), self._py(item_y), self._ps(400), self._ps(48))
            is_desbloqueada = self.gerenciador_config.is_desbloqueada(cdef.id)
            is_selecionada = (self.config_selecionada_id == cdef.id)
            val_atual = str(self.gerenciador_config.obter_valor(cdef.id))
            is_modificada = is_desbloqueada and (val_atual != str(cdef.valor_padrao))

            if is_selecionada:
                cor_bg = _C_CARD_HOVER if is_desbloqueada else (22, 26, 36)
                cor_borda = _C_GOLD if is_desbloqueada else _C_BORDER
            else:
                cor_bg = _C_CARD if is_desbloqueada else (13, 17, 26)
                cor_borda = _C_BORDER if is_desbloqueada else _C_ELEVATED

            pygame.draw.rect(screen, cor_bg, item_rect, border_radius=self._ps(7))
            pygame.draw.rect(screen, cor_borda, item_rect, width=self._ps(2) if is_selecionada else max(1, self._ps(1)), border_radius=self._ps(7))

            if is_modificada:
                pygame.draw.rect(screen, _C_GREEN, (item_rect.x + 1, item_rect.y + self._ps(8), max(2, self._ps(3)), item_rect.height - self._ps(16)), border_radius=max(1, self._ps(2)))

            # Moldura + Ícone original v1 escalado em cache
            mold_ic = pygame.Rect(self._px(ox + 58), self._py(item_y + 7), self._ps(34), self._ps(34))
            pygame.draw.rect(screen, _C_HUD_PANEL, mold_ic, border_radius=self._ps(6))
            pygame.draw.rect(screen, _C_GOLD if is_selecionada else _C_ELEVATED, mold_ic, width=max(1, self._ps(1)), border_radius=self._ps(6))

            icone_img = self._obter_icone(cdef.id)
            if icone_img is not None:
                if not is_desbloqueada:
                    icone_dark = self._obter_icone_bloqueado(cdef.id)
                    img_base = icone_dark if icone_dark is not None else icone_img
                else:
                    img_base = icone_img
                iw, ih = self._ps(28), self._ps(28)
                ck = (cdef.id, not is_desbloqueada, iw, ih)
                img_s = _ICON_SCALE_CACHE.get(ck)
                if img_s is None:
                    img_s = pygame.transform.scale(img_base, (iw, ih))
                    _ICON_SCALE_CACHE[ck] = img_s
                screen.blit(img_s, img_s.get_rect(center=mold_ic.center))
            else:
                cor_ic = _C_GOLD if is_desbloqueada else _C_TEXT_MUTED
                pygame.draw.circle(screen, cor_ic, mold_ic.center, self._ps(10), width=max(1, self._ps(2)))

            cor_nome = _C_TEXT_PRIMARY if is_desbloqueada else _C_TEXT_MUTED
            nome_surf = self._fonte_item_tit.render(cdef.nome, True, cor_nome)
            screen.blit(nome_surf, (self._px(ox + 100), self._py(item_y + 6)))

            if not is_desbloqueada:
                req_conq = bool(getattr(cdef, "exclusiva_conquista", False) or getattr(cdef, "requer_desbloqueio", None))
                sub_str = "[CONQUISTA]" if req_conq else "Desbloqueie em marcos"
                sub_cor = _C_AMBER if req_conq else _C_TEXT_MUTED
            elif is_modificada:
                sub_str = "Sacrifício ativo"
                sub_cor = _C_GREEN_SOFT
            else:
                sub_str = "Padrão neutro"
                sub_cor = _C_TEXT_MUTED
            cat_surf = self._fonte_item_desc.render(sub_str, True, sub_cor)
            screen.blit(cat_surf, (self._px(ox + 100), self._py(item_y + 25)))

            if is_desbloqueada:
                if cdef.tipo == TipoControleConfig.TOGGLE:
                    is_on = (val_atual in ("ligado", "baixa"))
                    cor_btn = (6, 40, 30) if is_on else (42, 18, 21)
                    cor_btn_borda = _C_GREEN if is_on else _C_CRIMSON
                    txt_btn = f"[{val_atual.upper()}]"

                    btn_rect = pygame.Rect(self._px(ox + 320), self._py(item_y + 10), self._ps(120), self._ps(28))
                    pygame.draw.rect(screen, cor_btn, btn_rect, border_radius=self._ps(6))
                    pygame.draw.rect(screen, cor_btn_borda, btn_rect, width=max(1, self._ps(1)), border_radius=self._ps(6))
                    lbl_btn = self._fonte_btn.render(txt_btn, True, _C_GREEN_SOFT if is_on else _C_CRIMSON_SOFT)
                    screen.blit(lbl_btn, lbl_btn.get_rect(center=btn_rect.center))
                else:
                    btn_prev = pygame.Rect(self._px(ox + 320), self._py(item_y + 10), self._ps(24), self._ps(28))
                    btn_mid = pygame.Rect(self._px(ox + 346), self._py(item_y + 10), self._ps(72), self._ps(28))
                    btn_next = pygame.Rect(self._px(ox + 420), self._py(item_y + 10), self._ps(24), self._ps(28))

                    pygame.draw.rect(screen, _C_ELEVATED, btn_prev, border_radius=self._ps(5))
                    pygame.draw.rect(screen, _C_CYAN if is_selecionada else _C_BORDER, btn_prev, width=max(1, self._ps(1)), border_radius=self._ps(5))
                    pygame.draw.rect(screen, _C_HUD_PANEL, btn_mid, border_radius=self._ps(4))
                    pygame.draw.rect(screen, _C_ELEVATED, btn_next, border_radius=self._ps(5))
                    pygame.draw.rect(screen, _C_CYAN if is_selecionada else _C_BORDER, btn_next, width=max(1, self._ps(1)), border_radius=self._ps(5))

                    surf_prev = self._fonte_btn.render("<", True, _C_CYAN)
                    screen.blit(surf_prev, surf_prev.get_rect(center=btn_prev.center))
                    surf_mid = self._fonte_btn.render(val_atual, True, _C_GOLD if is_modificada else _C_TEXT_PRIMARY)
                    screen.blit(surf_mid, surf_mid.get_rect(center=btn_mid.center))
                    surf_next = self._fonte_btn.render(">", True, _C_CYAN)
                    screen.blit(surf_next, surf_next.get_rect(center=btn_next.center))
            else:
                lock_r = pygame.Rect(self._px(ox + 356), self._py(item_y + 12), self._ps(84), self._ps(24))
                pygame.draw.rect(screen, _C_ELEVATED, lock_r, border_radius=self._ps(5))
                lbl_bloq = self._fonte_btn.render("BLOQUEADA", True, _C_TEXT_MUTED)
                screen.blit(lbl_bloq, lbl_bloq.get_rect(center=lock_r.center))

        # Botões de scroll
        btn_up_rect = pygame.Rect(self._px(ox + 455), self._py(oy + 140), self._ps(20), self._ps(24))
        btn_down_rect = pygame.Rect(self._px(ox + 455), self._py(oy + 480), self._ps(20), self._ps(24))
        pode_subir = self.scroll_y > 0.0
        pode_descer = self.scroll_y < self.max_scroll_y

        pygame.draw.rect(screen, _C_CARD, btn_up_rect, border_radius=self._ps(4))
        pygame.draw.rect(screen, _C_CYAN if pode_subir else _C_ELEVATED, btn_up_rect, width=max(1, self._ps(1)), border_radius=self._ps(4))
        surf_up = self._fonte_btn.render("▲", True, _C_CYAN if pode_subir else _C_TEXT_MUTED)
        screen.blit(surf_up, surf_up.get_rect(center=btn_up_rect.center))

        pygame.draw.rect(screen, _C_CARD, btn_down_rect, border_radius=self._ps(4))
        pygame.draw.rect(screen, _C_CYAN if pode_descer else _C_ELEVATED, btn_down_rect, width=max(1, self._ps(1)), border_radius=self._ps(4))
        surf_down = self._fonte_btn.render("▼", True, _C_CYAN if pode_descer else _C_TEXT_MUTED)
        screen.blit(surf_down, surf_down.get_rect(center=btn_down_rect.center))

        # 3. Painel de Inspeção Detalhado à Direita
        self._desenhar_painel_inspetor(screen)

        if self._toast_conflito_timer > 0.0 and self._toast_conflito:
            t_surf = self._fonte_btn.render(self._toast_conflito, True, _C_AMBAR if "_C_AMBAR" in globals() else _C_AMBER)
            t_rect = pygame.Rect(self._px(ox + 48), self._py(oy + 522), t_surf.get_width() + self._ps(20), self._ps(24))
            pygame.draw.rect(screen, (52, 24, 14), t_rect, border_radius=self._ps(5))
            pygame.draw.rect(screen, _C_AMBER, t_rect, width=max(1, self._ps(1)), border_radius=self._ps(5))
            screen.blit(t_surf, t_surf.get_rect(center=t_rect.center))

    def _desenhar_painel_inspetor(self, screen: pygame.Surface):
        """Renderiza os detalhes completos da configuração selecionada com cards Benefício vs. Sacrifício."""
        rect = self._pr(self.detalhes_rect)
        pygame.draw.rect(screen, _C_CARD, rect, border_radius=self._ps(8))
        pygame.draw.rect(screen, _C_BORDER, rect, width=max(1, self._ps(1)), border_radius=self._ps(8))

        cdef = CONFIGURACOES_GAMEPLAY.get(self.config_selecionada_id)
        if not cdef:
            return

        is_desbloqueada = self.gerenciador_config.is_desbloqueada(cdef.id)
        val_ativo = str(self.gerenciador_config.obter_valor(cdef.id))

        tit_surf = self._fonte_det_tit.render(cdef.nome, True, _C_GOLD if is_desbloqueada else _C_TEXT_MUTED)
        screen.blit(tit_surf, (rect.x + self._ps(12), rect.y + self._ps(12)))

        cat_val = (cdef.categoria.value if hasattr(cdef.categoria, "value") else str(cdef.categoria)).upper()
        cat_surf = self._fonte_cat.render(cat_val, True, _C_CYAN)
        cat_pill = pygame.Rect(rect.x + self._ps(12), rect.y + self._ps(36), cat_surf.get_width() + self._ps(12), cat_surf.get_height() + self._ps(6))
        pygame.draw.rect(screen, (14, 42, 54), cat_pill, border_radius=self._ps(4))
        pygame.draw.rect(screen, _C_CYAN, cat_pill, width=max(1, self._ps(1)), border_radius=self._ps(4))
        screen.blit(cat_surf, cat_surf.get_rect(center=cat_pill.center))

        st_txt = "DESBLOQUEADA" if is_desbloqueada else ("[CONQUISTA]" if (getattr(cdef, "exclusiva_conquista", False) or getattr(cdef, "requer_desbloqueio", None)) else "BLOQUEADA")
        st_fg = _C_GREEN_SOFT if is_desbloqueada else _C_AMBER
        st_bg = (6, 40, 30) if is_desbloqueada else (45, 28, 12)
        st_bd = _C_GREEN if is_desbloqueada else _C_AMBER
        st_surf = self._fonte_cat.render(st_txt, True, st_fg)
        st_pill = pygame.Rect(cat_pill.right + self._ps(6), rect.y + self._ps(36), st_surf.get_width() + self._ps(12), st_surf.get_height() + self._ps(6))
        pygame.draw.rect(screen, st_bg, st_pill, border_radius=self._ps(4))
        pygame.draw.rect(screen, st_bd, st_pill, width=max(1, self._ps(1)), border_radius=self._ps(4))
        screen.blit(st_surf, st_surf.get_rect(center=st_pill.center))

        opt_def = cdef.opcoes.get(val_ativo)
        if opt_def and getattr(opt_def, "incompativel_com", None):
            cf_surf = self._fonte_cat.render("CONFLITO", True, _C_CRIMSON_SOFT)
            cf_pill = pygame.Rect(st_pill.right + self._ps(6), rect.y + self._ps(36), cf_surf.get_width() + self._ps(12), cf_surf.get_height() + self._ps(6))
            pygame.draw.rect(screen, (68, 22, 22), cf_pill, border_radius=self._ps(4))
            pygame.draw.rect(screen, _C_CRIMSON, cf_pill, width=max(1, self._ps(1)), border_radius=self._ps(4))
            screen.blit(cf_surf, cf_surf.get_rect(center=cf_pill.center))

        val_box = pygame.Rect(rect.x + self._ps(12), rect.y + self._ps(64), rect.width - self._ps(24), self._ps(28))
        pygame.draw.rect(screen, _C_HUD_PANEL, val_box, border_radius=self._ps(6))
        pygame.draw.rect(screen, _C_ELEVATED, val_box, width=max(1, self._ps(1)), border_radius=self._ps(6))
        lbl_m = self._fonte_cat.render("MODO ATIVO", True, _C_TEXT_MUTED)
        screen.blit(lbl_m, (val_box.x + self._ps(8), val_box.y + self._ps(8)))
        val_surf = self._fonte_btn.render(val_ativo.upper(), True, _C_GOLD)
        screen.blit(val_surf, val_surf.get_rect(right=val_box.right - self._ps(8), centery=val_box.centery))

        opt_def = cdef.opcoes.get(val_ativo)

        # Sub-card de BENEFÍCIO (Verde Esmeralda #10b981)
        ben_rect = pygame.Rect(rect.x + self._ps(12), val_box.bottom + self._ps(10), rect.width - self._ps(24), self._ps(118))
        pygame.draw.rect(screen, (6, 40, 30), ben_rect, border_radius=self._ps(7))
        pygame.draw.rect(screen, _C_GREEN, ben_rect, width=max(1, self._ps(1)), border_radius=self._ps(7))
        pygame.draw.rect(screen, _C_GREEN, (ben_rect.x, ben_rect.y + self._ps(6), max(2, self._ps(3)), ben_rect.height - self._ps(12)), border_radius=max(1, self._ps(2)))

        bh_surf = self._fonte_cat.render("+ BENEFÍCIO", True, _C_GREEN_SOFT)
        bh_pill = pygame.Rect(ben_rect.x + self._ps(10), ben_rect.y + self._ps(7), bh_surf.get_width() + self._ps(10), bh_surf.get_height() + self._ps(4))
        pygame.draw.rect(screen, (14, 62, 46), bh_pill, border_radius=self._ps(4))
        screen.blit(bh_surf, bh_surf.get_rect(center=bh_pill.center))

        y_pos = bh_pill.bottom + self._ps(6)
        if opt_def and opt_def.buff_text and opt_def.buff_text != "Nenhum":
            b_linhas = _formatar_texto_wrap(opt_def.buff_text, max_chars_por_linha=27)
            for bl in b_linhas[:5]:
                bl_surf = self._fonte_det_corpo.render(bl, True, _C_TEXT_PRIMARY)
                screen.blit(bl_surf, (ben_rect.x + self._ps(10), y_pos))
                y_pos += self._ps(15)
        else:
            nenhum_surf = self._fonte_det_corpo.render("Nenhum bônus ativo no padrão", True, _C_TEXT_MUTED)
            screen.blit(nenhum_surf, (ben_rect.x + self._ps(10), y_pos))

        # Sub-card de SACRIFÍCIO (Carmesim #ef4444)
        sac_rect = pygame.Rect(rect.x + self._ps(12), ben_rect.bottom + self._ps(10), rect.width - self._ps(24), self._ps(102))
        pygame.draw.rect(screen, (42, 18, 21), sac_rect, border_radius=self._ps(7))
        pygame.draw.rect(screen, _C_CRIMSON, sac_rect, width=max(1, self._ps(1)), border_radius=self._ps(7))
        pygame.draw.rect(screen, _C_CRIMSON, (sac_rect.x, sac_rect.y + self._ps(6), max(2, self._ps(3)), sac_rect.height - self._ps(12)), border_radius=max(1, self._ps(2)))

        nh_surf = self._fonte_cat.render("- SACRIFÍCIO", True, _C_CRIMSON_SOFT)
        nh_pill = pygame.Rect(sac_rect.x + self._ps(10), sac_rect.y + self._ps(7), nh_surf.get_width() + self._ps(10), nh_surf.get_height() + self._ps(4))
        pygame.draw.rect(screen, (68, 24, 28), nh_pill, border_radius=self._ps(4))
        screen.blit(nh_surf, nh_surf.get_rect(center=nh_pill.center))

        ny_pos = nh_pill.bottom + self._ps(6)
        if opt_def and opt_def.nerf_text and opt_def.nerf_text != "Nenhum":
            n_linhas = _formatar_texto_wrap(opt_def.nerf_text, max_chars_por_linha=27)
            for nl in n_linhas[:4]:
                nl_surf = self._fonte_det_corpo.render(nl, True, _C_TEXT_PRIMARY)
                screen.blit(nl_surf, (sac_rect.x + self._ps(10), ny_pos))
                ny_pos += self._ps(15)
        else:
            nenhum_n_surf = self._fonte_det_corpo.render("Nenhum sacrifício no padrão", True, _C_TEXT_MUTED)
            screen.blit(nenhum_n_surf, (sac_rect.x + self._ps(10), ny_pos))

        # Flavor Text no rodapé do inspetor
        if opt_def and opt_def.flavor_text:
            fy = sac_rect.bottom + self._ps(10)
            flavor_linhas = _formatar_texto_wrap(f'"{opt_def.flavor_text}"', max_chars_por_linha=30)
            for fl in flavor_linhas[:3]:
                if fy + self._ps(13) < rect.bottom - self._ps(6):
                    fl_surf = self._fonte_det_flavor.render(fl, True, _C_TEXT_MUTED)
                    screen.blit(fl_surf, (rect.x + self._ps(12), fy))
                    fy += self._ps(14)

    def _desenhar_aba_sistema(self, screen: pygame.Surface):
        """Renderiza a aba de configurações sistêmicas (volumes de áudio) em DPI nativo."""
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)

        area_rect = pygame.Rect(self._px(ox + 48), self._py(oy + 110), self._ps(704), self._ps(400))
        pygame.draw.rect(screen, _C_CARD, area_rect, border_radius=self._ps(8))
        pygame.draw.rect(screen, _C_BORDER, area_rect, width=max(1, self._ps(1)), border_radius=self._ps(8))

        tit_audio = self._fonte_det_tit.render("ÁUDIO & MÚSICA", True, _C_GOLD)
        screen.blit(tit_audio, (self._px(ox + 70), self._py(oy + 125)))

        sliders_info = [
            ("volume_master", "Volume Geral (Master)", oy + 160),
            ("volume_musica", "Volume da Música", oy + 230),
            ("volume_sfx", "Volume dos Efeitos (SFX)", oy + 300)
        ]

        for cid, label, y_pos in sliders_info:
            val_atual = self.gerenciador_config.obter_valor(cid)
            val_atual = 100 if val_atual is None else int(val_atual)

            lbl_surf = self._fonte_item_tit.render(label, True, _C_TEXT_PRIMARY)
            screen.blit(lbl_surf, (self._px(ox + 70), self._py(y_pos + 4)))

            btn_menos = pygame.Rect(self._px(ox + 240), self._py(y_pos), self._ps(30), self._ps(26))
            pygame.draw.rect(screen, _C_ELEVATED, btn_menos, border_radius=self._ps(5))
            pygame.draw.rect(screen, _C_CYAN, btn_menos, width=max(1, self._ps(1)), border_radius=self._ps(5))
            m_surf = self._fonte_btn.render("-", True, _C_CYAN)
            screen.blit(m_surf, m_surf.get_rect(center=btn_menos.center))

            track_rect = pygame.Rect(self._px(ox + 280), self._py(y_pos + 6), self._ps(260), self._ps(14))
            pygame.draw.rect(screen, _C_HUD_PANEL, track_rect, border_radius=self._ps(5))

            fill_w = int(track_rect.width * (val_atual / 100.0))
            if fill_w > 0:
                pygame.draw.rect(screen, _C_CYAN, (track_rect.x, track_rect.y, fill_w, track_rect.height), border_radius=self._ps(5))

            pygame.draw.rect(screen, _C_BORDER, track_rect, width=max(1, self._ps(1)), border_radius=self._ps(5))

            btn_mais = pygame.Rect(self._px(ox + 550), self._py(y_pos), self._ps(30), self._ps(26))
            pygame.draw.rect(screen, _C_ELEVATED, btn_mais, border_radius=self._ps(5))
            pygame.draw.rect(screen, _C_CYAN, btn_mais, width=max(1, self._ps(1)), border_radius=self._ps(5))
            p_surf = self._fonte_btn.render("+", True, _C_CYAN)
            screen.blit(p_surf, p_surf.get_rect(center=btn_mais.center))

            val_txt = f"{val_atual:3d}%"
            txt_surf = self._fonte_btn.render(val_txt, True, _C_GOLD)
            screen.blit(txt_surf, (self._px(ox + 595), self._py(y_pos + 5)))



    def _tocar_som(self, chave_som: str):
        """Reproduz efeito sonoro de forma segura."""
        try:
            from PPlay.sound import Sound
            caminho = obter_caminho_asset(chave_som)
            if os.path.isfile(caminho):
                sfx = Sound(caminho)
                sfx.play()
        except Exception:
            pass
