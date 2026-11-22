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
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, BRANCO, PRETO, DOURADO,
    AZUL_CIANO, AMARELO_XP, VERDE_CURA, VERMELHO_HP, LARANJA_ALERTA,
    CINZA_BORDA, CINZA_PAINEL, CINZA_FUNDO, CINZA_TEXTO,
    obter_caminho_asset, SAVE_FILE_PATH
)


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

        # Superfície de overlay escuro pré-alocada
        self._dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._dark_surf.fill((10, 14, 22, 225))

        # Estado de interação do mouse e teclado
        self._mouse_pressionado_anterior: bool = False
        self._slider_arrastando: Optional[str] = None
        self.cooldown_input: float = 0.0

        # Fontes de texto
        self._fonte_titulo = None
        self._fonte_sub = None
        self._fonte_aba = None
        self._fonte_cat = None
        self._fonte_item_tit = None
        self._fonte_item_desc = None
        self._fonte_btn = None
        self._fonte_det_tit = None
        self._fonte_det_corpo = None
        self._fonte_rodape = None

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
        """Inicializa as fontes do Pygame sob demanda."""
        if self._fonte_titulo is None:
            self._fonte_titulo = pygame.font.SysFont("Arial", 24, bold=True)
            self._fonte_sub = pygame.font.SysFont("Arial", 12)
            self._fonte_aba = pygame.font.SysFont("Arial", 14, bold=True)
            self._fonte_cat = pygame.font.SysFont("Arial", 10, bold=True)
            self._fonte_item_tit = pygame.font.SysFont("Arial", 12, bold=True)
            self._fonte_item_desc = pygame.font.SysFont("Arial", 9)
            self._fonte_btn = pygame.font.SysFont("Arial", 11, bold=True)
            self._fonte_det_tit = pygame.font.SysFont("Arial", 14, bold=True)
            self._fonte_det_corpo = pygame.font.SysFont("Arial", 10)
            self._fonte_rodape = pygame.font.SysFont("Arial", 12)

    def abrir(self):
        """Abre o menu de configurações com cooldown de proteção contra duplo disparo."""
        self.ativo = True
        self.scroll_y = 0.0
        self.cooldown_input = 0.25
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
        """Altera o valor de uma configuração de gameplay desbloqueada."""
        sucesso = self.gerenciador_config.definir_valor(config_id, novo_valor)
        if sucesso:
            self._tocar_som("sfx_btn_click")
            if self.cena and hasattr(self.cena, "aplicar_modificadores"):
                self.cena.aplicar_modificadores()
        return sucesso

    def ciclar_opcao_gameplay(self, config_id: str, direcao: int = 1) -> bool:
        """Cicla para a próxima opção disponível de uma configuração de gameplay."""
        if not self.gerenciador_config.is_desbloqueada(config_id):
            return False

        cdef = CONFIGURACOES_GAMEPLAY.get(config_id)
        if not cdef or not cdef.opcoes:
            return False

        chaves_opcoes = list(cdef.opcoes.keys())
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

    def draw(self, screen: pygame.Surface):
        """Renderiza a janela do menu de configurações."""
        if not self.ativo or screen is None:
            return

        self._inicializar_fontes()

        # 1. Overlay Escuro de Fundo (reutiliza superfície pré-alocada)
        if self._dark_surf is None or self._dark_surf.get_size() != (LARGURA_TELA, ALTURA_TELA):
            self._dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
            self._dark_surf.fill((10, 14, 22, 225))
        screen.blit(self._dark_surf, (0, 0))

        # 2. Painel Principal Centralizado
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)
        pygame.draw.rect(screen, (22, 26, 36), self.painel_rect, border_radius=8)
        pygame.draw.rect(screen, (55, 68, 92), self.painel_rect, width=2, border_radius=8)

        # 3. Cabeçalho com Título e Subtítulo
        tit_surf = self._fonte_titulo.render("PAINEL DE CONFIGURAÇÕES", True, DOURADO)
        screen.blit(tit_surf, (ox + 50, oy + 30))

        sub_txt = "Personalize o jogo e ative sacrifícios mecânicos para ganhar bônus" if self.aba_atual == 0 else "Ajustes de áudio"
        sub_surf = self._fonte_sub.render(sub_txt, True, (150, 165, 185))
        screen.blit(sub_surf, (ox + 50, oy + 52))

        # 4. Barra de Abas [ GAMEPLAY ] e [ SISTEMA ]
        aba0_rect, aba1_rect, btn_fechar_rect, btn_menu_rect = self._obter_rects_barra_topo()

        # Aba 0: Gameplay
        cor_aba0 = (38, 48, 68) if self.aba_atual == 0 else (26, 30, 42)
        cor_borda0 = DOURADO if self.aba_atual == 0 else (50, 60, 80)
        pygame.draw.rect(screen, cor_aba0, aba0_rect, border_radius=4)
        pygame.draw.rect(screen, cor_borda0, aba0_rect, width=2 if self.aba_atual == 0 else 1, border_radius=4)
        t_aba0 = self._fonte_aba.render("GAMEPLAY (20)", True, DOURADO if self.aba_atual == 0 else BRANCO)
        screen.blit(t_aba0, t_aba0.get_rect(center=aba0_rect.center))

        # Aba 1: Sistema
        cor_aba1 = (38, 48, 68) if self.aba_atual == 1 else (26, 30, 42)
        cor_borda1 = DOURADO if self.aba_atual == 1 else (50, 60, 80)
        pygame.draw.rect(screen, cor_aba1, aba1_rect, border_radius=4)
        pygame.draw.rect(screen, cor_borda1, aba1_rect, width=2 if self.aba_atual == 1 else 1, border_radius=4)
        t_aba1 = self._fonte_aba.render("SISTEMA (ÁUDIO)", True, DOURADO if self.aba_atual == 1 else BRANCO)
        screen.blit(t_aba1, t_aba1.get_rect(center=aba1_rect.center))

        # Botão Sair para o Menu Principal (apenas durante gameplay)
        if btn_menu_rect is not None:
            pygame.draw.rect(screen, (52, 34, 24), btn_menu_rect, border_radius=4)
            pygame.draw.rect(screen, LARANJA_ALERTA, btn_menu_rect, width=1, border_radius=4)
            t_menu = self._fonte_aba.render("MENU PRINCIPAL", True, DOURADO)
            screen.blit(t_menu, t_menu.get_rect(center=btn_menu_rect.center))

        # Botão Fechar [ESC]
        pygame.draw.rect(screen, (45, 30, 35), btn_fechar_rect, border_radius=4)
        pygame.draw.rect(screen, VERMELHO_HP, btn_fechar_rect, width=1, border_radius=4)
        t_fec = self._fonte_aba.render("FECHAR [ESC]", True, BRANCO)
        screen.blit(t_fec, t_fec.get_rect(center=btn_fechar_rect.center))

        # 5. Renderização do Conteúdo Específico da Aba
        if self.aba_atual == 0:
            self._desenhar_aba_gameplay(screen)
        else:
            self._desenhar_aba_sistema(screen)

        # 6. Rodapé com Instruções
        rodape_txt = "[TAB] Alternar Abas  |  [ESC / C] Fechar e Salvar  |  [Mouse] Ajustar Opções"
        rodape_surf = self._fonte_rodape.render(rodape_txt, True, (130, 145, 165))
        rodape_rect = rodape_surf.get_rect(centerx=LARGURA_TELA // 2, bottom=self.painel_rect.bottom - 10)
        screen.blit(rodape_surf, rodape_rect)

    def _desenhar_aba_gameplay(self, screen: pygame.Surface):
        """Renderiza a lista de 20 configs e o painel de inspeção detalhado à direita."""
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
            cat_rect = pygame.Rect(cat_x, oy + 108, largura_pill, 20)
            cor_bg = (40, 52, 75) if is_ativa else (25, 30, 42)
            cor_borda = AZUL_CIANO if is_ativa else (45, 55, 75)
            pygame.draw.rect(screen, cor_bg, cat_rect, border_radius=3)
            pygame.draw.rect(screen, cor_borda, cat_rect, width=1, border_radius=3)

            cat_surf = self._fonte_cat.render(cat_nome.upper(), True, AZUL_CIANO if is_ativa else (140, 150, 170))
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

        # Fundo da lista
        pygame.draw.rect(screen, (16, 20, 28), pygame.Rect(ox + 48, oy + 134, 404, 380), border_radius=4)
        pygame.draw.rect(screen, (40, 50, 70), pygame.Rect(ox + 48, oy + 134, 404, 380), width=1, border_radius=4)

        for i, cdef in enumerate(configs_filtradas):
            item_y = start_y + i * item_h - self.scroll_y
            if item_y + item_h < oy + 135 or item_y > oy + 510:
                continue

            item_rect = pygame.Rect(ox + 50, item_y, 400, 48)
            is_desbloqueada = self.gerenciador_config.is_desbloqueada(cdef.id)
            is_selecionada = (self.config_selecionada_id == cdef.id)

            # Cor de fundo da linha
            if is_selecionada:
                cor_bg = (35, 45, 65) if is_desbloqueada else (30, 32, 40)
                cor_borda = DOURADO if is_desbloqueada else (80, 85, 95)
            else:
                cor_bg = (24, 30, 42) if is_desbloqueada else (20, 22, 28)
                cor_borda = (45, 55, 75) if is_desbloqueada else (35, 38, 48)

            pygame.draw.rect(screen, cor_bg, item_rect, border_radius=4)
            pygame.draw.rect(screen, cor_borda, item_rect, width=2 if is_selecionada else 1, border_radius=4)

            # Ícone 32x32
            icone_img = self._obter_icone(cdef.id)
            if icone_img is not None:
                if not is_desbloqueada:
                    # Ícone escurecido cacheado se bloqueado
                    icone_dark = self._obter_icone_bloqueado(cdef.id)
                    if icone_dark is not None:
                        screen.blit(icone_dark, (ox + 58, item_y + 8))
                    else:
                        screen.blit(icone_img, (ox + 58, item_y + 8))
                else:
                    screen.blit(icone_img, (ox + 58, item_y + 8))
            else:
                cor_ic = DOURADO if is_desbloqueada else (70, 75, 85)
                pygame.draw.rect(screen, cor_ic, (ox + 58, item_y + 8, 32, 32), border_radius=4)

            # Nome e Categoria
            cor_nome = BRANCO if is_desbloqueada else (110, 115, 125)
            nome_surf = self._fonte_item_tit.render(cdef.nome, True, cor_nome)
            screen.blit(nome_surf, (ox + 98, item_y + 6))

            cat_str = f"[{cdef.categoria.value if hasattr(cdef.categoria, 'value') else cdef.categoria}]"
            cat_surf = self._fonte_cat.render(cat_str, True, AZUL_CIANO if is_desbloqueada else (85, 90, 100))
            screen.blit(cat_surf, (ox + 98, item_y + 26))

            # Controles à direita do item
            if is_desbloqueada:
                val_atual = str(self.gerenciador_config.obter_valor(cdef.id))
                if cdef.tipo == TipoControleConfig.TOGGLE:
                    is_on = (val_atual in ("ligado", "baixa"))
                    cor_btn = (35, 75, 45) if is_on else (65, 35, 40)
                    cor_btn_borda = VERDE_CURA if is_on else VERMELHO_HP
                    txt_btn = f"[{val_atual.upper()}]"

                    btn_rect = pygame.Rect(ox + 320, item_y + 10, 120, 28)
                    pygame.draw.rect(screen, cor_btn, btn_rect, border_radius=4)
                    pygame.draw.rect(screen, cor_btn_borda, btn_rect, width=1, border_radius=4)
                    lbl_btn = self._fonte_btn.render(txt_btn, True, BRANCO)
                    screen.blit(lbl_btn, lbl_btn.get_rect(center=btn_rect.center))
                else:
                    # Grupo: botões < [Opção] >
                    btn_prev = pygame.Rect(ox + 320, item_y + 10, 24, 28)
                    btn_mid = pygame.Rect(ox + 346, item_y + 10, 72, 28)
                    btn_next = pygame.Rect(ox + 420, item_y + 10, 24, 28)

                    pygame.draw.rect(screen, (35, 45, 65), btn_prev, border_radius=3)
                    pygame.draw.rect(screen, AZUL_CIANO, btn_prev, width=1, border_radius=3)
                    pygame.draw.rect(screen, (28, 36, 52), btn_mid)
                    pygame.draw.rect(screen, (35, 45, 65), btn_next, border_radius=3)
                    pygame.draw.rect(screen, AZUL_CIANO, btn_next, width=1, border_radius=3)

                    surf_prev = self._fonte_btn.render("<", True, AZUL_CIANO)
                    screen.blit(surf_prev, surf_prev.get_rect(center=btn_prev.center))
                    surf_mid = self._fonte_btn.render(val_atual, True, DOURADO)
                    screen.blit(surf_mid, surf_mid.get_rect(center=btn_mid.center))
                    surf_next = self._fonte_btn.render(">", True, AZUL_CIANO)
                    screen.blit(surf_next, surf_next.get_rect(center=btn_next.center))
            else:
                # Bloqueado
                lbl_bloq = self._fonte_btn.render("[BLOQUEADO]", True, (110, 115, 130))
                lbl_rect = lbl_bloq.get_rect(right=ox + 440, centery=item_y + 24)
                screen.blit(lbl_bloq, lbl_rect)

        # Botões e setas de scroll (acima e abaixo na barra lateral direita da lista)
        btn_up_rect = pygame.Rect(ox + 455, oy + 140, 20, 24)
        btn_down_rect = pygame.Rect(ox + 455, oy + 480, 20, 24)
        pode_subir = self.scroll_y > 0.0
        pode_descer = self.scroll_y < self.max_scroll_y

        # Seta Cima
        pygame.draw.rect(screen, (32, 40, 56), btn_up_rect, border_radius=3)
        pygame.draw.rect(screen, AZUL_CIANO if pode_subir else (50, 60, 75), btn_up_rect, width=1, border_radius=3)
        surf_up = self._fonte_btn.render("▲", True, AZUL_CIANO if pode_subir else (80, 90, 105))
        screen.blit(surf_up, surf_up.get_rect(center=btn_up_rect.center))

        # Seta Baixo
        pygame.draw.rect(screen, (32, 40, 56), btn_down_rect, border_radius=3)
        pygame.draw.rect(screen, AZUL_CIANO if pode_descer else (50, 60, 75), btn_down_rect, width=1, border_radius=3)
        surf_down = self._fonte_btn.render("▼", True, AZUL_CIANO if pode_descer else (80, 90, 105))
        screen.blit(surf_down, surf_down.get_rect(center=btn_down_rect.center))

        # 3. Painel de Inspeção Detalhado à Direita
        self._desenhar_painel_inspetor(screen)

    def _desenhar_painel_inspetor(self, screen: pygame.Surface):
        """Renderiza os detalhes completos da configuração selecionada."""
        rect = self.detalhes_rect
        pygame.draw.rect(screen, (18, 22, 32), rect, border_radius=6)
        pygame.draw.rect(screen, (50, 62, 85), rect, width=1, border_radius=6)

        cdef = CONFIGURACOES_GAMEPLAY.get(self.config_selecionada_id)
        if not cdef:
            return

        is_desbloqueada = self.gerenciador_config.is_desbloqueada(cdef.id)
        val_ativo = str(self.gerenciador_config.obter_valor(cdef.id))

        # Topo do Inspetor: Nome e Categoria
        tit_surf = self._fonte_det_tit.render(cdef.nome, True, DOURADO if is_desbloqueada else (140, 145, 155))
        screen.blit(tit_surf, (rect.x + 12, rect.y + 12))

        cat_str = f"Categoria: {cdef.categoria.value if hasattr(cdef.categoria, 'value') else cdef.categoria}"
        cat_surf = self._fonte_cat.render(cat_str, True, AZUL_CIANO)
        screen.blit(cat_surf, (rect.x + 12, rect.y + 32))

        # Status Badge
        status_txt = "STATUS: DESBLOQUEADA" if is_desbloqueada else "STATUS: BLOQUEADA"
        status_cor = VERDE_CURA if is_desbloqueada else LARANJA_ALERTA
        status_surf = self._fonte_cat.render(status_txt, True, status_cor)
        screen.blit(status_surf, (rect.x + 12, rect.y + 48))

        # Divisória
        pygame.draw.line(screen, (45, 55, 75), (rect.x + 10, rect.y + 66), (rect.right - 10, rect.y + 66), 1)

        y_pos = rect.y + 74

        # Valor Ativo
        val_txt = f"Valor Atual: {val_ativo}"
        val_surf = self._fonte_item_tit.render(val_txt, True, BRANCO)
        screen.blit(val_surf, (rect.x + 12, y_pos))
        y_pos += 22

        # Opção Ativa Def
        opt_def = cdef.opcoes.get(val_ativo)

        # Flavor Text
        if opt_def and opt_def.flavor_text:
            flavor_linhas = _formatar_texto_wrap(f'"{opt_def.flavor_text}"', max_chars_por_linha=28)
            for fl in flavor_linhas:
                fl_surf = self._fonte_det_corpo.render(fl, True, (160, 175, 195))
                screen.blit(fl_surf, (rect.x + 12, y_pos))
                y_pos += 13
            y_pos += 6

        # Seção de Benefícios Ativos (BUFFS)
        buff_header = self._fonte_cat.render("BENEFICIOS:", True, VERDE_CURA)
        screen.blit(buff_header, (rect.x + 12, y_pos))
        y_pos += 14

        if opt_def and opt_def.buff_text:
            b_linhas = _formatar_texto_wrap(opt_def.buff_text, max_chars_por_linha=28)
            for bl in b_linhas:
                bl_surf = self._fonte_det_corpo.render(f"+ {bl}", True, (170, 245, 180))
                screen.blit(bl_surf, (rect.x + 14, y_pos))
                y_pos += 13
        else:
            nenhum_surf = self._fonte_det_corpo.render("Nenhum bônus ativo no padrão", True, (120, 130, 145))
            screen.blit(nenhum_surf, (rect.x + 14, y_pos))
            y_pos += 13

        y_pos += 6

        # Seção de Sacrifícios (NERF)
        nerf_header = self._fonte_cat.render("SACRIFICIO / NERF:", True, LARANJA_ALERTA)
        screen.blit(nerf_header, (rect.x + 12, y_pos))
        y_pos += 14

        if opt_def and opt_def.nerf_text:
            n_linhas = _formatar_texto_wrap(opt_def.nerf_text, max_chars_por_linha=28)
            for nl in n_linhas:
                nl_surf = self._fonte_det_corpo.render(f"- {nl}", True, (255, 185, 150))
                screen.blit(nl_surf, (rect.x + 14, y_pos))
                y_pos += 13
        else:
            nenhum_n_surf = self._fonte_det_corpo.render("Nenhum sacrifício no padrão", True, (120, 130, 145))
            screen.blit(nenhum_n_surf, (rect.x + 14, y_pos))
            y_pos += 13

    def _desenhar_aba_sistema(self, screen: pygame.Surface):
        """Renderiza a aba de configurações sistêmicas (volumes, filtro daltônico e escala global)."""
        ox = getattr(self, "offset_x", (LARGURA_TELA - 800) // 2)
        oy = getattr(self, "offset_y", (ALTURA_TELA - 600) // 2)

        # Painel central da aba de sistema
        area_rect = pygame.Rect(ox + 48, oy + 110, 704, 400)
        pygame.draw.rect(screen, (18, 22, 32), area_rect, border_radius=6)
        pygame.draw.rect(screen, (45, 55, 75), area_rect, width=1, border_radius=6)

        # 1. Sliders de Áudio
        tit_audio = self._fonte_det_tit.render("AUDIO & MUSICA", True, DOURADO)
        screen.blit(tit_audio, (ox + 70, oy + 125))

        sliders_info = [
            ("volume_master", "Volume Geral (Master)", oy + 160),
            ("volume_musica", "Volume da Música", oy + 230),
            ("volume_sfx", "Volume dos Efeitos (SFX)", oy + 300)
        ]

        for cid, label, y_pos in sliders_info:
            val_atual = self.gerenciador_config.obter_valor(cid)
            val_atual = 100 if val_atual is None else int(val_atual)

            # Rótulo
            lbl_surf = self._fonte_item_tit.render(label, True, BRANCO)
            screen.blit(lbl_surf, (ox + 70, y_pos + 4))

            # Botão Menos [-]
            btn_menos = pygame.Rect(ox + 240, y_pos, 30, 26)
            pygame.draw.rect(screen, (32, 40, 56), btn_menos, border_radius=3)
            pygame.draw.rect(screen, AZUL_CIANO, btn_menos, width=1, border_radius=3)
            m_surf = self._fonte_btn.render("-", True, AZUL_CIANO)
            screen.blit(m_surf, m_surf.get_rect(center=btn_menos.center))

            # Barra do Slider
            track_rect = pygame.Rect(ox + 280, y_pos + 6, 260, 14)
            pygame.draw.rect(screen, (28, 34, 48), track_rect, border_radius=3)

            # Preenchimento
            fill_w = int(260 * (val_atual / 100.0))
            if fill_w > 0:
                pygame.draw.rect(screen, AZUL_CIANO, (ox + 280, y_pos + 6, fill_w, 14), border_radius=3)

            # Borda do Slider
            pygame.draw.rect(screen, (60, 75, 100), track_rect, width=1, border_radius=3)

            # Botão Mais [+]
            btn_mais = pygame.Rect(ox + 550, y_pos, 30, 26)
            pygame.draw.rect(screen, (32, 40, 56), btn_mais, border_radius=3)
            pygame.draw.rect(screen, AZUL_CIANO, btn_mais, width=1, border_radius=3)
            p_surf = self._fonte_btn.render("+", True, AZUL_CIANO)
            screen.blit(p_surf, p_surf.get_rect(center=btn_mais.center))

            # Texto numérico
            val_txt = f"{val_atual}%"
            txt_surf = self._fonte_item_tit.render(val_txt, True, DOURADO)
            screen.blit(txt_surf, (ox + 595, y_pos + 4))



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
