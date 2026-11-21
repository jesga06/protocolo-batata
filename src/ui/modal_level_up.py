"""
Modal de Level Up (3-Card Upgrade Draw) — Protocolo: Batata
SSOT: CONFIGURACOES.md, s5.md, User Directives (Milestone & Pity Buffer Architecture)
Exibe a tela modal interativa de seleção de 3 cartas ao subir de nível pelo SistemaXP.
Pausa o gameplay, implementa arquitetura em tiers para consumíveis, posiciona configs de gameplay
no card central (slot 2) em níveis de marco (múltiplos de 5) e mantém buffer de misericórdia (pity buffer).
"""

import os
import random
import pygame
from typing import Optional, Any
from src.sistemas.config_dados import ConfiguracaoDef, CONFIGURACOES_GAMEPLAY
from src.sistemas.config_sistema import GerenciadorConfiguracoes
from src.entidades.jogador import Jogador
from src.utils.math_utils import clamp
from src.utils.constantes import (
    LARGURA_TELA, ALTURA_TELA, BRANCO, PRETO, DOURADO,
    AZUL_CIANO, AMARELO_XP, VERDE_CURA, VERMELHO_HP, LARANJA_ALERTA,
    CINZA_BORDA, CINZA_PAINEL, ROXO_ACENTO, ROXO_CLARO, ROXO_ESCURO,
    obter_caminho_asset, SAVE_FILE_PATH
)


def _formatar_texto_wrap(texto: str, max_chars_por_linha: int = 22) -> list[str]:
    """Divide um texto longo em múltiplas linhas respeitando palavras inteiras."""
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


def extrair_resumo_config(cdef: ConfiguracaoDef) -> tuple[list[str], list[str]]:
    """Extrai listas resumidas de benefícios (buffs) e sacrifícios (nerfs) da configuração."""
    buffs = []
    nerfs = []

    for opt_id, opt in cdef.opcoes.items():
        if opt_id == str(cdef.valor_padrao):
            continue
        if opt.buff_text and opt.buff_text != "Nenhum" and opt.buff_text not in buffs:
            buffs.append(opt.buff_text)
        if opt.nerf_text and opt.nerf_text != "Nenhum" and opt.nerf_text not in nerfs:
            nerfs.append(opt.nerf_text)

    if not buffs:
        buffs.append("Personalização flexível")
    if not nerfs:
        nerfs.append("Nenhum sacrifício")

    return buffs, nerfs


def obter_tier_nivel(nivel: int) -> int:
    """
    Retorna o tier de progressão de consumíveis conforme o nível:
    - Tier 1: Níveis 1 a 4 (buffs modestos)
    - Tier 2: Níveis 5 a 9 (buffs médios)
    - Tier 3: Níveis 10 a 14 (buffs fortes)
    - Tier 4: Níveis 15 a 20+ (buffs máximos/épicos)
    """
    lvl = max(1, int(nivel))
    if lvl <= 4:
        return 1
    elif lvl <= 9:
        return 2
    elif lvl <= 14:
        return 3
    else:
        return 4


def gerar_pool_consumiveis_por_tier(tier: int) -> list[dict[str, Any]]:
    """
    Gera lista completa de cartas consumíveis escaladas para o tier informado (12 cards no total):
    1. cura_pequena: +25 HP
    2. cura_grande: +50 HP
    3. xp_pequeno: +15 XP
    4. xp_grande: +30 XP
    5. buff_dano_temp: +5% Dano por 15s
    6. buff_vel_temp: +8% Velocidade por 15s
    7. buff_cadencia_temp: +8% Cadência por 15s
    8. buff_resistencia_temp: -8% Dano Recebido por 15s
    9. escudo: Escudo Protetor (absorve 1 hit / 4s invulnerabilidade)
    10. pulso_magnetico: Atrai todos os drops da arena
    11. caixa_arma: Desbloqueia/equipa arma aleatória no Slot 3
    12. caixa_equip: Desbloqueia/equipa drone/equipamento aleatório no Slot 4
    """
    card_cura_pequena = {
        "tipo": "cura",
        "subtipo": "cura_pequena",
        "nome": "Reparo +25",
        "categoria": "Consumível",
        "icone_asset": "drop_cura",
        "valor": 25,
        "buffs": ["Recupera 25 de vida na hora."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_cura_grande = {
        "tipo": "cura",
        "subtipo": "cura_grande",
        "nome": "Reparo +50",
        "categoria": "Consumível",
        "icone_asset": "drop_cura",
        "valor": 50,
        "buffs": ["Recupera 50 de vida na hora."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_xp_pequeno = {
        "tipo": "xp",
        "subtipo": "xp_pequeno",
        "nome": "Pacote de XP +15",
        "categoria": "Consumível",
        "icone_asset": "drop_xp",
        "valor": 15,
        "buffs": ["Concede 15 de XP imediatamente."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_xp_grande = {
        "tipo": "xp",
        "subtipo": "xp_grande",
        "nome": "Pacote de XP +30",
        "categoria": "Consumível",
        "icone_asset": "drop_xp",
        "valor": 30,
        "buffs": ["Concede 30 de XP imediatamente."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_buff_dano = {
        "tipo": "buff_dano_temp",
        "subtipo": "buff_dano_temp",
        "nome": "Munição Superaquecida",
        "categoria": "Consumível",
        "icone_asset": "mira_crosshair",
        "valor": 0.05,
        "duracao": 15.0,
        "descricao": "+5% de dano. Tiros soltam brasas e atravessam +1 alvo por 15s.",
        "buffs": ["+5% de dano por 15s. Seus tiros soltam brasas e atravessam +1 inimigo."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_buff_vel = {
        "tipo": "buff_vel_temp",
        "subtipo": "buff_vel_temp",
        "nome": "Passo Fantasma",
        "categoria": "Consumível",
        "icone_asset": "icon_vsync",
        "valor": 0.08,
        "duracao": 15.0,
        "descricao": "+8% de velocidade e desacelera inimigos colados em 40% por 15s.",
        "buffs": ["+8% de velocidade por 15s. Desacelera inimigos muito próximos em 40%."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_buff_cadencia = {
        "tipo": "buff_cadencia_temp",
        "subtipo": "buff_cadencia_temp",
        "nome": "Gatilho Magnético",
        "categoria": "Consumível",
        "icone_asset": "icon_auto_fire",
        "valor": 0.08,
        "duracao": 15.0,
        "descricao": "+8% de cadência. Armas especiais não gastam munição por 15s.",
        "buffs": ["+8% de cadência de tiro por 15s. Armas especiais não gastam munição."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_buff_resistencia = {
        "tipo": "buff_resistencia_temp",
        "subtipo": "buff_resistencia_temp",
        "nome": "Casco Eletrostático",
        "categoria": "Consumível",
        "icone_asset": "icon_fps_cap",
        "valor": 0.08,
        "duracao": 15.0,
        "descricao": "-8% de dano recebido. Empurra e dá choque em quem encostar por 15s.",
        "buffs": ["-8% de dano recebido por 15s. Empurra e dá choque em inimigos que encostarem."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_escudo = {
        "tipo": "escudo",
        "subtipo": "escudo",
        "nome": "Escudo de Emergência",
        "categoria": "Consumível",
        "icone_asset": "drone_suporte",
        "valor": 1,
        "buffs": ["Bloqueia o próximo dano recebido e garante 4s de invulnerabilidade."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_pulso = {
        "tipo": "pulso_magnetico",
        "subtipo": "pulso_magnetico",
        "nome": "Ímã de Arena",
        "categoria": "Consumível",
        "icone_asset": "drop_xp",
        "valor": 1,
        "buffs": ["Puxa todos os itens e gemas de XP da arena até você."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_caixa_arma = {
        "tipo": "caixa_arma",
        "subtipo": "caixa_arma",
        "nome": "Caixa de Arma Especial",
        "categoria": "Consumível",
        "icone_asset": "drop_arma",
        "valor": 1,
        "buffs": ["Equipa uma arma especial aleatória no Slot 3."],
        "nerfs": [],
        "flavor_text": ""
    }

    card_caixa_equip = {
        "tipo": "caixa_equip",
        "subtipo": "caixa_equip",
        "nome": "Módulo de Drone",
        "categoria": "Consumível",
        "icone_asset": "drop_equipamento",
        "valor": 1,
        "buffs": ["Ativa um drone no Slot 4 por 30s (ou evolui um ativo para MK-II/MK-III)."],
        "nerfs": [],
        "flavor_text": ""
    }

    if tier == 1:
        return [
            card_cura_pequena,
            card_xp_pequeno,
            card_buff_dano,
            card_buff_vel,
            card_buff_cadencia,
            card_buff_resistencia
        ]
    elif tier == 2:
        return [
            card_cura_pequena,
            card_cura_grande,
            card_xp_pequeno,
            card_xp_grande,
            card_buff_dano,
            card_buff_vel,
            card_buff_cadencia,
            card_buff_resistencia,
            card_escudo,
            card_pulso
        ]
    elif tier == 3:
        return [
            card_cura_grande,
            card_xp_grande,
            card_buff_dano,
            card_buff_vel,
            card_buff_cadencia,
            card_buff_resistencia,
            card_escudo,
            card_pulso,
            card_caixa_arma,
            card_caixa_equip
        ]
    else:  # Tier 4 (Níveis 15-20+)
        return [
            card_cura_grande,
            card_xp_grande,
            card_buff_dano,
            card_buff_vel,
            card_buff_cadencia,
            card_buff_resistencia,
            card_escudo,
            card_pulso,
            card_caixa_arma,
            card_caixa_equip
        ]


class ModalLevelUp:
    """
    Modal interativo de Level Up com sorteio de 3 cards:
    - Níveis normais (não múltiplos de 5): 3 consumíveis com escala de tier.
    - Níveis de marco (múltiplos de 5: 5, 10, 15, 20): Card do meio (slot 2 / índice 1) é uma Configuração de Gameplay bloqueada.
    - Buffer de Misericórdia (Pity Buffer): Se a configuração do meio não for escolhida, ela persiste no slot central até ser selecionada.
    """
    _card_bg_img = None
    _icones_cache: dict[str, pygame.Surface] = {}
    _assets_carregados = False

    def __init__(
        self,
        gerenciador_config: GerenciadorConfiguracoes,
        jogador: Jogador,
        cena=None
    ):
        self.gerenciador_config = gerenciador_config
        self.jogador = jogador
        self.cena = cena

        self.ativo: bool = False
        self.fila_niveis: list[int] = []
        self.nivel_atual_draw: int = 1
        self.cards_sorteados: list[dict[str, Any]] = []

        # Buffer de Misericórdia (Pity Buffer) para configurações não selecionadas em marcos
        self.config_pity_buffer: Optional[ConfiguracaoDef] = None

        # Configuração visual das 3 cartas centralizadas na tela virtual (1280x720)
        # Largura: 280px, Altura: 420px, Espaçamento: 44px
        self.card_largura = 280
        self.card_altura = 420
        self.card_y = (ALTURA_TELA - self.card_altura) // 2 + 20
        start_x = (LARGURA_TELA - (3 * self.card_largura + 2 * 44)) // 2
        self.card_xs = [start_x, start_x + self.card_largura + 44, start_x + 2 * (self.card_largura + 44)]
        self.card_rects = [
            pygame.Rect(x, self.card_y, self.card_largura, self.card_altura)
            for x in self.card_xs
        ]

        self.card_hovered: Optional[int] = None
        self._ultimo_hover: Optional[int] = None
        self._mouse_pressionado_anterior: bool = True  # Inicia True para ignorar clique que causou level up
        self.tempo_transicao_entrada: float = 0.35  # 350ms de transição com input bloqueado
        self.tempo_transicao_saida: float = 0.0

        # Superfícies pré-alocadas / reutilizadas em draw()
        self._dark_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._layer_surf = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        self._glow_surf = pygame.Surface((self.card_largura, self.card_altura), pygame.SRCALPHA)

        # Fontes de texto
        self._fonte_titulo = None
        self._fonte_sub = None
        self._fonte_card_tit = None
        self._fonte_card_cat = None
        self._fonte_card_badge = None
        self._fonte_card_sec = None
        self._fonte_card_corpo = None
        self._fonte_rodape = None

    @classmethod
    def _carregar_assets(cls):
        """Carrega e armazena em cache o fundo do card e os ícones."""
        if cls._assets_carregados:
            return

        try:
            caminho_bg = obter_caminho_asset("card_upgrade_bg")
            if os.path.isfile(caminho_bg):
                cls._card_bg_img = pygame.image.load(caminho_bg).convert_alpha()
        except Exception:
            cls._card_bg_img = None

        cls._assets_carregados = True

    def _obter_icone(self, chave_icone: str) -> Optional[pygame.Surface]:
        """Recupera ou carrega um ícone 32x32 para a configuração ou consumível."""
        if not chave_icone:
            return None

        if chave_icone in self._icones_cache:
            return self._icones_cache[chave_icone]

        chaves_candidatas = [chave_icone]
        # Evita double-prefix 'icon_icon_*.png' e suporta 'vsync' -> 'icon_vsync'
        if chave_icone.startswith("icon_"):
            chaves_candidatas.append(chave_icone[5:])
        else:
            chaves_candidatas.append(f"icon_{chave_icone}")

        img = None
        for chave in chaves_candidatas:
            try:
                caminho = obter_caminho_asset(chave)
                if os.path.isfile(caminho):
                    img = pygame.image.load(caminho).convert_alpha()
                    break
            except (KeyError, pygame.error, OSError):
                continue

        if img is None:
            try:
                from src.utils.constantes import ASSETS_DIR
                nome_sem_prefixo = chave_icone[5:] if chave_icone.startswith("icon_") else chave_icone
                direto = os.path.join(ASSETS_DIR, "ui", "icones_configs", f"icon_{nome_sem_prefixo}.png")
                if os.path.isfile(direto):
                    img = pygame.image.load(direto).convert_alpha()
            except (KeyError, pygame.error, OSError):
                img = None

        if img is not None:
            self._icones_cache[chave_icone] = img
        return img

    def _inicializar_fontes(self):
        """Inicializa as fontes do Pygame sob demanda em escala nativa 1280x720."""
        if self._fonte_titulo is None:
            self._fonte_titulo = pygame.font.SysFont("Arial", 38, bold=True)
            self._fonte_sub = pygame.font.SysFont("Arial", 18, bold=True)
            self._fonte_card_tit = pygame.font.SysFont("Arial", 16, bold=True)
            self._fonte_card_cat = pygame.font.SysFont("Arial", 12, bold=True)
            self._fonte_card_badge = pygame.font.SysFont("Arial", 13, bold=True)
            self._fonte_card_sec = pygame.font.SysFont("Arial", 12, bold=True)
            self._fonte_card_corpo = pygame.font.SysFont("Arial", 12)
            self._fonte_rodape = pygame.font.SysFont("Arial", 15)

    @property
    def fila_level_ups(self) -> int:
        """Propriedade legada mantida para retrocompatibilidade: retorna a quantidade de níveis na fila FIFO."""
        return len(self.fila_niveis)

    @fila_level_ups.setter
    def fila_level_ups(self, valor: int):
        val = max(0, int(valor))
        atual = len(self.fila_niveis)
        if val == atual:
            return
        if val < atual:
            self.fila_niveis = self.fila_niveis[:val]
        else:
            lvl = self.nivel_atual_draw if self.nivel_atual_draw else (self.jogador.nivel if self.jogador else 1)
            self.fila_niveis.extend([lvl] * (val - atual))

    def enfileirar_level_up(self, novo_nivel: int = None):
        """
        Adiciona um level up à fila FIFO e ativa o modal se ele ainda não estiver ativo.
        """
        if novo_nivel is not None:
            lvl = int(novo_nivel)
        elif self.jogador is not None:
            lvl = int(self.jogador.nivel)
        else:
            lvl = self.nivel_atual_draw if self.nivel_atual_draw else 1

        self.fila_niveis.append(lvl)

        if not self.ativo:
            self.abrir(self.fila_niveis[0])

    def abrir(self, nivel: int = None):
        """Ativa o modal e sorteia a primeira trinca de cartas com transição suave."""
        if nivel is not None:
            self.nivel_atual_draw = int(nivel)
        elif self.jogador is not None:
            self.nivel_atual_draw = int(self.jogador.nivel)

        if not self.fila_niveis:
            self.fila_niveis.append(self.nivel_atual_draw)

        self.ativo = True
        self.tempo_transicao_entrada = 0.35
        self.tempo_transicao_saida = 0.0
        self._mouse_pressionado_anterior = True
        self._gerar_cards(self.nivel_atual_draw)
        self._tocar_som("sfx_levelup")

    def _gerar_cards(self, nivel: int = None):
        """
        Sorteia 3 cartas de acordo com as regras obrigatórias:
        1. Níveis normais (não múltiplos de 5 sem pity buffer ativo): 3 consumíveis escalados por tier.
        2. Níveis marco (múltiplos de 5: Lvl 5, 10, 15, 20) OU com Pity Buffer ativo:
           O card central (índice 1) é uma Configuração de Gameplay bloqueada.
        """
        if nivel is None:
            nivel = self.nivel_atual_draw if self.nivel_atual_draw else (self.jogador.nivel if self.jogador else 1)

        self.cards_sorteados.clear()
        tier = obter_tier_nivel(nivel)
        pool_consumiveis = gerar_pool_consumiveis_por_tier(tier)

        bloqueadas = self.gerenciador_config.obter_bloqueadas()
        is_marco = (nivel in (5, 11) or nivel % 5 == 0)
        tem_pity = (self.config_pity_buffer is not None and self.config_pity_buffer.id not in self.gerenciador_config.desbloqueadas)

        # Determina se o slot central terá uma configuração
        deve_ofertar_config = (is_marco or tem_pity) and (len(bloqueadas) > 0 or tem_pity)

        if deve_ofertar_config:
            # 1. Garante pity buffer se ainda não definido
            if not tem_pity and bloqueadas:
                self.config_pity_buffer = random.choice(bloqueadas)

            configs_ofertadas = []
            if self.config_pity_buffer is not None and self.config_pity_buffer.id not in self.gerenciador_config.desbloqueadas:
                configs_ofertadas.append(self.config_pity_buffer)

            restantes = [c for c in bloqueadas if c.id not in {cfg.id for cfg in configs_ofertadas}]
            if restantes:
                qtd_extra = min(3 - len(configs_ofertadas), len(restantes))
                configs_ofertadas.extend(random.sample(restantes, qtd_extra))

            cards_cfg = []
            for cdef in configs_ofertadas:
                buffs, nerfs = extrair_resumo_config(cdef)
                cards_cfg.append({
                    "tipo": "config",
                    "config_id": cdef.id,
                    "cdef": cdef,
                    "nome": cdef.nome,
                    "categoria": str(cdef.categoria.value if hasattr(cdef.categoria, "value") else cdef.categoria),
                    "icone_asset": cdef.id,
                    "buffs": buffs,
                    "nerfs": nerfs,
                    "flavor_text": ""
                })

            # Caso restem menos de 3 configurações bloqueadas, completa com consumíveis
            if len(cards_cfg) < 3:
                faltam = 3 - len(cards_cfg)
                cards_cfg.extend(random.sample(pool_consumiveis, min(faltam, len(pool_consumiveis))))

            self.cards_sorteados = cards_cfg[:3]
        else:
            # 3. Nível normal: sorteia 3 consumíveis únicos escalados para o tier atual
            num_cons = min(3, len(pool_consumiveis))
            self.cards_sorteados = random.sample(pool_consumiveis, num_cons)

    def selecionar_card(self, index: int) -> bool:
        """
        Processa a escolha de uma carta pelo jogador:
        - Se escolher a configuração (slot central), destrava e limpa o pity buffer.
        - Se escolher um consumível, aplica o buff e preserva o pity buffer para os próximos níveis.
        """
        if not self.ativo or index < 0 or index >= len(self.cards_sorteados):
            return False

        card = self.cards_sorteados[index]
        self._tocar_som("sfx_btn_click")

        # 1. Aplica efeito da carta selecionada
        if card["tipo"] == "config":
            cid = card["config_id"]
            self.gerenciador_config.desbloquear_config(cid)
            # Mantém a configuração em seu valor padrão neutro (R1)
            self.gerenciador_config.salvar_arquivo(SAVE_FILE_PATH)
            self.config_pity_buffer = None
        elif card["tipo"] == "cura":
            if self.jogador:
                if card.get("subtipo") == "cura_total":
                    self.jogador.curar(self.jogador.hp_max)
                else:
                    self.jogador.curar(card.get("valor", 25))
        elif card["tipo"] in ("xp", "xp_burst"):
            if self.jogador:
                val = card.get("valor", 15)
                self.jogador.ganhar_xp(val)
        elif card["tipo"] == "buff_dano_temp":
            if self.jogador:
                self.jogador.buff_dano_timer = float(card.get("duracao", 15.0))
        elif card["tipo"] == "buff_vel_temp":
            if self.jogador:
                self.jogador.buff_vel_timer = float(card.get("duracao", 15.0))
        elif card["tipo"] == "buff_cadencia_temp":
            if self.jogador:
                self.jogador.buff_cadencia_timer = float(card.get("duracao", 15.0))
        elif card["tipo"] == "buff_resistencia_temp":
            if self.jogador:
                self.jogador.buff_resistencia_timer = float(card.get("duracao", 15.0))
        elif card["tipo"] in ("escudo", "escudo_protetor"):
            if self.jogador:
                self.jogador.escudo_ativo = True
        elif card["tipo"] == "pulso_magnetico":
            if self.jogador:
                drops_lista = []
                if self.cena and hasattr(self.cena, "sistema_drops") and hasattr(self.cena.sistema_drops, "drops"):
                    drops_lista = self.cena.sistema_drops.drops
                self.jogador.aplicar_pulso_magnetico(drops_lista)
        elif card["tipo"] == "caixa_arma":
            if self.jogador:
                from src.armas import Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun
                armas_especiais = [Minigun, Shotgun, RifleAssalto, LancaFoguetes, LancaGranadas, Railgun]
                classe_arma = random.choice(armas_especiais)
                nova_arma = classe_arma()
                if hasattr(self.jogador, "equipar_arma_especial"):
                    self.jogador.equipar_arma_especial(nova_arma)
                elif getattr(self.jogador, "bios_modding", False) and self.jogador.arma_especial is not None:
                    if len(self.jogador.armas) > 1:
                        self.jogador.armas[1] = nova_arma
                    self.jogador.arma_especial_secundaria = nova_arma
                    self.jogador.selecionar_slot(2)
                else:
                    self.jogador.arma_especial = nova_arma
                    self.jogador.selecionar_slot(3)
        elif card["tipo"] in ("caixa_equip", "caixa_equipamento"):
            if self.jogador:
                from src.equipamentos import DroneCura, DroneCombate, DroneSuporte
                drones_classes = [DroneCura, DroneCombate, DroneSuporte]
                classe_drone = random.choice(drones_classes)
                novo_drone = classe_drone(tempo_vida=30.0)
                if hasattr(self.jogador, "adicionar_drone"):
                    self.jogador.adicionar_drone(novo_drone)
                else:
                    self.jogador.drone = novo_drone

        # 2. Atualiza modificadores na cena vinculada e reseta buffer de tiro
        if self.cena and hasattr(self.cena, "aplicar_modificadores"):
            self.cena.aplicar_modificadores()
        if self.cena and hasattr(self.cena, "buffer_tiro"):
            self.cena.buffer_tiro = 0.0

        # 3. Trata a fila de level-ups FIFO
        if self.fila_niveis:
            self.fila_niveis.pop(0)

        if self.fila_niveis:
            # Sorteia para o próximo nível acumulado na ordem FIFO (preserva marcos 5/10/15/20)
            self.nivel_atual_draw = self.fila_niveis[0]
            self.tempo_transicao_entrada = 0.25
            self.tempo_transicao_saida = 0.0
            self._mouse_pressionado_anterior = True
            self._gerar_cards(self.nivel_atual_draw)
            self._tocar_som("sfx_levelup")
        else:
            # Fila concluída -> desativa seleção e inicia fade-out visual
            self.ativo = False
            self._ultimo_hover = None
            self.card_hovered = None
            self.tempo_transicao_saida = 0.25
            if self.cena and hasattr(self.cena, "pausado"):
                self.cena.pausado = False

            # Se o jogador atingiu o nível máximo (12) e completou os upgrades, inicia a cutscene do Chefe Final
            nivel_max = getattr(getattr(self.jogador, "sistema_xp", None), "nivel_max", 12) if self.jogador else 12
            if self.jogador and self.jogador.nivel >= nivel_max:
                if self.cena and hasattr(self.cena, "iniciar_boss_cutscene"):
                    self.cena.iniciar_boss_cutscene()

        return True

    def update(self, dt: float, teclado=None, mouse=None):
        """Processa inputs de teclado (1, 2, 3) e mouse para seleção de cartas e animações."""
        # 1. Trata animação de fade-out de saída
        if self.tempo_transicao_saida > 0.0:
            self.tempo_transicao_saida = max(0.0, self.tempo_transicao_saida - dt)
            if self.tempo_transicao_saida <= 0.0:
                self._ultimo_hover = None
                self.card_hovered = None
            return

        if not self.ativo:
            self._ultimo_hover = None
            self.card_hovered = None
            return

        # 2. Decrementa o tempo de transição inicial onde os cliques acidentais são bloqueados
        if self.tempo_transicao_entrada > 0.0:
            self.tempo_transicao_entrada = max(0.0, self.tempo_transicao_entrada - dt)
            if self.tempo_transicao_entrada > 0.0:
                return

        # 3. Inputs de Teclado (1, 2, 3 e KP1, KP2, KP3)
        if teclado is not None:
            # Tecla 1 / KP1
            if (hasattr(teclado, "key_down") and (teclado.key_down("1") or teclado.key_down("KP1"))) or \
               (not hasattr(teclado, "key_down") and hasattr(teclado, "key_pressed") and (teclado.key_pressed("1") or teclado.key_pressed("KP1"))):
                self.selecionar_card(0)
                return

            # Tecla 2 / KP2
            if (hasattr(teclado, "key_down") and (teclado.key_down("2") or teclado.key_down("KP2"))) or \
               (not hasattr(teclado, "key_down") and hasattr(teclado, "key_pressed") and (teclado.key_pressed("2") or teclado.key_pressed("KP2"))):
                self.selecionar_card(1)
                return

            # Tecla 3 / KP3
            if (hasattr(teclado, "key_down") and (teclado.key_down("3") or teclado.key_down("KP3"))) or \
               (not hasattr(teclado, "key_down") and hasattr(teclado, "key_pressed") and (teclado.key_pressed("3") or teclado.key_pressed("KP3"))):
                self.selecionar_card(2)
                return

        # 4. Inputs de Mouse
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

        # Atualiza hover e processa clique nos cards
        self.card_hovered = None
        for i, rect in enumerate(self.card_rects):
            if i < len(self.cards_sorteados) and rect.collidepoint(mx, my):
                self.card_hovered = i
                # Toca som de hover se mudou o card focado
                if self.card_hovered != self._ultimo_hover:
                    self._tocar_som("sfx_btn_hover")
                    self._ultimo_hover = self.card_hovered
                
                if mouse_clicado:
                    self.selecionar_card(i)
                    return

    def draw(self, screen: pygame.Surface):
        """Renderiza o modal de level-up com animação completa de fade-in e fade-out."""
        if (not self.ativo and self.tempo_transicao_saida <= 0.0) or screen is None:
            return

        self._carregar_assets()
        self._inicializar_fontes()

        # Fator de interpolação da transição (0.0 a 1.0)
        if self.tempo_transicao_saida > 0.0:
            fator_anim = clamp(self.tempo_transicao_saida / 0.25, 0.0, 1.0)
        elif self.tempo_transicao_entrada > 0.0:
            fator_anim = clamp(1.0 - (self.tempo_transicao_entrada / 0.35), 0.0, 1.0)
        else:
            fator_anim = 1.0

        slide_offset_y = int((1.0 - fator_anim) * 25.0)
        alpha_fundo = int(fator_anim * 225)
        alpha_conteudo = int(fator_anim * 255)

        # 1. Overlay Escuro Translúcido sobre o Gameplay
        self._dark_surf.fill((10, 8, 20, alpha_fundo))
        screen.blit(self._dark_surf, (0, 0))

        # 2. Superfície de Conteúdo com Transparência Global
        self._layer_surf.fill((0, 0, 0, 0))
        layer_surf = self._layer_surf

        # 2. Título Centralizado: LEVEL UP!
        tit_surf = self._fonte_titulo.render("LEVEL UP!", True, DOURADO)
        tit_rect = tit_surf.get_rect(centerx=LARGURA_TELA // 2, top=45 + slide_offset_y)
        tit_sombra = self._fonte_titulo.render("LEVEL UP!", True, (0, 0, 0))
        layer_surf.blit(tit_sombra, (tit_rect.x + 2, tit_rect.y + 2))
        layer_surf.blit(tit_surf, tit_rect)

        # 3. Subtítulo
        sub_texto = "ESCOLHA UM UPGRADE DO SISTEMA"
        sub_surf = self._fonte_sub.render(sub_texto, True, ROXO_CLARO)
        sub_rect = sub_surf.get_rect(centerx=LARGURA_TELA // 2, top=85 + slide_offset_y)
        layer_surf.blit(sub_surf, sub_rect)

        # Indicador de Níveis na Fila (se > 1)
        if self.fila_level_ups > 1:
            fila_texto = f"+{self.fila_level_ups - 1} UPGRADE(S) RESTANTE(S) NA FILA"
            fila_surf = self._fonte_sub.render(fila_texto, True, LARANJA_ALERTA)
            fila_rect = fila_surf.get_rect(centerx=LARGURA_TELA // 2, top=115 + slide_offset_y)
            pill_rect = pygame.Rect(fila_rect.x - 12, fila_rect.y - 3, fila_rect.width + 24, fila_rect.height + 6)
            pygame.draw.rect(layer_surf, (40, 20, 15), pill_rect, border_radius=4)
            pygame.draw.rect(layer_surf, LARANJA_ALERTA, pill_rect, width=1, border_radius=4)
            layer_surf.blit(fila_surf, fila_rect)

        # 4. Renderização das 3 Cartas
        for i, card in enumerate(self.cards_sorteados):
            if i >= len(self.card_rects):
                break

            base_rect = self.card_rects[i]
            rect = pygame.Rect(base_rect.x, base_rect.y + slide_offset_y, base_rect.width, base_rect.height)
            is_hovered = (self.card_hovered == i)
            is_config = (card.get("tipo") == "config")

            # 4.1 Fundo do Card (Dourado para Configurações, Roxo Escuro para Consumíveis)
            if is_config:
                cor_bg = (45, 36, 16) if not is_hovered else (65, 52, 22)
                cor_borda = DOURADO
                largura_borda = 3 if is_hovered else 2
            else:
                cor_bg = (28, 22, 40) if not is_hovered else (42, 32, 60)
                cor_borda = ROXO_ACENTO if is_hovered else (95, 65, 135)
                largura_borda = 2 if is_hovered else 1

            pygame.draw.rect(layer_surf, cor_bg, rect, border_radius=6)

            # 4.2 Destaque de Hover / Borda e Glow
            if is_hovered:
                glow_cor = (255, 215, 0, 25) if is_config else (175, 75, 255, 25)
                self._glow_surf.fill(glow_cor)
                layer_surf.blit(self._glow_surf, (rect.x, rect.y))

            pygame.draw.rect(layer_surf, cor_borda, rect, width=largura_borda, border_radius=6)

            # 4.3 Badge de Atalho do Teclado [ 1 ], [ 2 ], [ 3 ] no Top-Right
            badge_texto = f"[{i + 1}]"
            badge_cor = DOURADO if is_config else (ROXO_CLARO if is_hovered else ROXO_ACENTO)
            badge_surf = self._fonte_card_badge.render(badge_texto, True, badge_cor)
            badge_rect = badge_surf.get_rect(right=rect.right - 12, top=rect.top + 10)
            badge_bg = pygame.Rect(badge_rect.x - 4, badge_rect.y - 2, badge_rect.width + 8, badge_rect.height + 4)
            pygame.draw.rect(layer_surf, (15, 12, 24), badge_bg, border_radius=3)
            pygame.draw.rect(layer_surf, badge_cor, badge_bg, width=1, border_radius=3)
            layer_surf.blit(badge_surf, badge_rect)

            # 4.4 Tag de Categoria (ex: [CONFIGURACAO], [CONSUMIVEL])
            if is_config:
                cat_texto = "[CONFIGURACAO]"
                cor_cat = DOURADO
            else:
                cat_texto = f"[{card.get('categoria', 'Consumivel').upper()}]"
                cor_cat = ROXO_CLARO

            cat_surf = self._fonte_card_cat.render(cat_texto, True, cor_cat)
            layer_surf.blit(cat_surf, (rect.x + 12, rect.top + 12))

            # 4.5 Nome da Configuração / Consumível (Wrap de 1-2 linhas perfeitamente centralizado)
            nome_linhas = _formatar_texto_wrap(card["nome"], max_chars_por_linha=24)
            offset_y_nome = rect.top + 36
            for linha in nome_linhas[:2]:
                cor_tit = DOURADO if (is_hovered or is_config) else BRANCO
                nome_surf = self._fonte_card_tit.render(linha, True, cor_tit)
                nome_rect = nome_surf.get_rect(centerx=rect.centerx, top=offset_y_nome)
                layer_surf.blit(nome_surf, nome_rect)
                offset_y_nome += 18

            # 4.6 Ícone Central (Moldura 48x48 perfeitamente centralizada)
            icone_img = self._obter_icone(card.get("icone_asset", card.get("config_id", "")))
            icone_cx = rect.centerx
            icone_cy = rect.top + 100
            moldura_rect = pygame.Rect(icone_cx - 24, icone_cy - 24, 48, 48)
            pygame.draw.rect(layer_surf, (18, 14, 28), moldura_rect, border_radius=6)
            cor_moldura = DOURADO if is_config else (90, 60, 130)
            pygame.draw.rect(layer_surf, cor_moldura, moldura_rect, width=1, border_radius=6)

            if icone_img is not None:
                icon_rect = icone_img.get_rect(center=moldura_rect.center)
                layer_surf.blit(icone_img, icon_rect)
            else:
                cor_ph = DOURADO if is_config else ROXO_ACENTO
                pygame.draw.circle(layer_surf, cor_ph, (icone_cx, icone_cy), 14, width=2)

            # Linha divisória horizontal
            div_y = rect.top + 136
            div_cor = (80, 65, 30) if is_config else (60, 45, 85)
            pygame.draw.line(layer_surf, div_cor, (rect.x + 14, div_y), (rect.right - 14, div_y), 1)

            # 4.7 Seção de Benefícios (EFEITO para Power-Ups/Consumíveis; BENEFICIOS + SACRIFICIO apenas para Configurações)
            y_cursor = div_y + 10
            header_label = "BENEFICIOS:" if is_config else "EFEITO:"
            buff_header_surf = self._fonte_card_sec.render(header_label, True, VERDE_CURA)
            layer_surf.blit(buff_header_surf, (rect.x + 14, y_cursor))
            y_cursor += 18

            buffs = card.get("buffs", ["Nenhum"])
            max_linhas_buff = 3 if is_config else 5
            for b_txt in buffs[:2]:
                linhas_buff = _formatar_texto_wrap(b_txt, max_chars_por_linha=30)
                for idx_bl, bl in enumerate(linhas_buff[:max_linhas_buff]):
                    prefixo = "+ " if idx_bl == 0 else "   "
                    b_surf = self._fonte_card_corpo.render(f"{prefixo}{bl}", True, (160, 240, 170))
                    layer_surf.blit(b_surf, (rect.x + 16, y_cursor))
                    y_cursor += 16

            # 4.8 Seção de Sacrifícios / Nerfs (EXCLUSIVA para Configurações)
            if is_config:
                y_cursor = max(y_cursor + 8, div_y + 118)
                nerf_header_surf = self._fonte_card_sec.render("SACRIFICIO:", True, LARANJA_ALERTA)
                layer_surf.blit(nerf_header_surf, (rect.x + 14, y_cursor))
                y_cursor += 18

                nerfs = card.get("nerfs", ["Nenhum"])
                for n_txt in nerfs[:2]:
                    linhas_nerf = _formatar_texto_wrap(n_txt, max_chars_por_linha=30)
                    for idx_nl, nl in enumerate(linhas_nerf[:3]):
                        cor_n = (255, 180, 140) if nl != "Nenhum" and nl != "Nenhum sacrifício" else (130, 140, 155)
                        prefixo_n = "- " if idx_nl == 0 else "   "
                        n_surf = self._fonte_card_corpo.render(f"{prefixo_n}{nl}", True, cor_n)
                        layer_surf.blit(n_surf, (rect.x + 16, y_cursor))
                        y_cursor += 16

            # 4.9 Prompt de Escolha no Rodapé do Card
            prompt_cor = DOURADO if (is_hovered or is_config) else ROXO_CLARO
            prompt_surf = self._fonte_card_cat.render(f"Pressione [{i + 1}]", True, prompt_cor)
            prompt_rect = prompt_surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 12)
            layer_surf.blit(prompt_surf, prompt_rect)

        # 5. Rodapé Geral com Instruções de Controle
        rodape_txt = "Pressione [1], [2], [3] no teclado ou clique com o mouse para escolher"
        rodape_surf = self._fonte_rodape.render(rodape_txt, True, (170, 155, 195))
        rodape_rect = rodape_surf.get_rect(centerx=LARGURA_TELA // 2, bottom=ALTURA_TELA - 45)
        layer_surf.blit(rodape_surf, rodape_rect)

        # Blit da camada com transparência de transição aplicada
        if alpha_conteudo < 255:
            layer_surf.set_alpha(alpha_conteudo)
        screen.blit(layer_surf, (0, 0))

    def _tocar_som(self, chave_som: str):
        """Reproduz efeito sonoro de forma segura sem crash em ambiente headless."""
        try:
            from PPlay.sound import Sound
            caminho = obter_caminho_asset(chave_som)
            if os.path.isfile(caminho):
                sfx = Sound(caminho)
                sfx.play()
        except Exception:
            pass
