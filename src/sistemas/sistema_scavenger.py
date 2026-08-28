"""
Sistema de Inimigo Scavenger — Protocolo: Batata
Implementa o comportamento da regra #15 (Coleta Inimiga):
- Apenas 1 inimigo globalmente pode ser designado Scavenger para disputar um drop elegível (>1s de chão).
- O alvo é selecionado excluindo os 3 inimigos mais próximos ao item e excluindo inimigos > 600px de distância.
- Se o scavenger alcançar o drop antes do jogador, o item é consumido sem recompensas.
"""

import random
from src.utils.math_utils import distancia, vetor_direcao, colisao_aabb
from src.utils.constantes import DROP_TEMPO_SCAVENGER_ATIVAR


class SistemaScavenger:
    """
    Gerenciador singleton de seleção e direcionamento de IA Scavenger.
    """

    def __init__(self, dist_maxima: float = 600.0):
        self.dist_maxima = float(dist_maxima)
        self.scavenger_atual = None
        self.drop_alvo = None

    def selecionar_scavenger(self, lista_inimigos: list, lista_drops: list):
        """
        Avalia se há um scavenger ativo válido. Se não houver, busca um drop elegível (>1s)
        e elege 1 inimigo elegível (excluindo os 3 mais próximos e os acima de 600px).
        """
        # Se já existe um scavenger vivo perseguindo um drop ativo, mantém
        if (
            self.scavenger_atual is not None and
            getattr(self.scavenger_atual, "vivo", False) and
            self.drop_alvo is not None and
            getattr(self.drop_alvo, "ativo", False) and
            not getattr(self.drop_alvo, "coletado", False)
        ):
            return self.scavenger_atual

        # Reseta referências inválidas
        self.scavenger_atual = None
        self.drop_alvo = None

        # Encontra drops elegíveis (tempo decorrido >= 5.0s e ativos)
        drops_elegiveis = [
            d for d in lista_drops
            if getattr(d, "ativo", False) and not getattr(d, "coletado", False) and (
                (hasattr(d, "elegivel_scavenger") and d.elegivel_scavenger()) or
                (getattr(d, "tempo_decorrido", 0.0) >= getattr(d, "tempo_scavenger", DROP_TEMPO_SCAVENGER_ATIVAR))
            )
        ]

        if not drops_elegiveis:
            return None

        # Avalia o primeiro drop elegível
        for drop in drops_elegiveis:
            d_cx = drop.x + getattr(drop, "largura", 16) / 2.0
            d_cy = drop.y + getattr(drop, "altura", 16) / 2.0

            # Filtra inimigos vivos e calcula distância
            candidatos = []
            for inimigo in lista_inimigos:
                if not getattr(inimigo, "vivo", False):
                    continue

                e_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
                e_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
                dist = distancia(e_cx, e_cy, d_cx, d_cy)

                if dist <= self.dist_maxima:
                    candidatos.append((inimigo, dist))

            # Exclui os 3 mais próximos (devem ser pelo menos 4 candidatos)
            if len(candidatos) <= 3:
                continue

            # Ordena por proximidade
            candidatos.sort(key=lambda item: item[1])
            candidatos_validos = [c[0] for c in candidatos[3:]]

            if candidatos_validos:
                # Escolha pseudo-aleatória entre os válidos
                escolhido = random.choice(candidatos_validos)
                self.scavenger_atual = escolhido
                self.drop_alvo = drop
                if hasattr(drop, "alvo_scavenger"):
                    drop.alvo_scavenger = True
                escolhido.pos_alvo_override = (d_cx, d_cy)
                return escolhido

        return None

    def desativar(self, lista_inimigos: list = None):
        """Limpa as referências de scavenger e cancela o override de alvo nos inimigos."""
        if self.scavenger_atual is not None:
            self.scavenger_atual.pos_alvo_override = None
        self.scavenger_atual = None
        self.drop_alvo = None
        if lista_inimigos:
            for inimigo in lista_inimigos:
                if hasattr(inimigo, "pos_alvo_override") and inimigo.pos_alvo_override is not None:
                    inimigo.pos_alvo_override = None

    def update(self, dt: float, lista_inimigos: list, lista_drops: list):
        """
        Atualiza o estado do scavenger:
        - Seleciona scavenger se necessário.
        - Redireciona o movimento do scavenger em direção ao drop.
        - Processa consumo do drop se o scavenger alcançá-lo.
        """
        self.selecionar_scavenger(lista_inimigos, lista_drops)

        if self.scavenger_atual is None or self.drop_alvo is None:
            return

        # Verifica se o scavenger ou drop se tornaram inválidos
        if not getattr(self.scavenger_atual, "vivo", False) or not getattr(self.drop_alvo, "ativo", False):
            if self.scavenger_atual is not None:
                self.scavenger_atual.pos_alvo_override = None
            self.scavenger_atual = None
            self.drop_alvo = None
            return

        s = self.scavenger_atual
        d = self.drop_alvo

        s_cx = s.x + getattr(s, "largura", 28) / 2.0
        s_cy = s.y + getattr(s, "altura", 28) / 2.0
        d_cx = d.x + getattr(d, "largura", 16) / 2.0
        d_cy = d.y + getattr(d, "altura", 16) / 2.0

        s.pos_alvo_override = (d_cx, d_cy)

        # Verifica se colidiu / alcançou o drop
        if colisao_aabb(s.x, s.y, s.largura, s.altura, d.x, d.y, d.largura, d.altura) or distancia(s_cx, s_cy, d_cx, d_cy) <= 24.0:
            # Drop consumido pelo inimigo — sem recompensas para a batata
            d.ativo = False
            d.coletado = True
            s.pos_alvo_override = None
            self.scavenger_atual = None
            self.drop_alvo = None
            return

        # Se chamado diretamente sem o loop de entidades, aplica o deslocamento manual
        dir_x, dir_y = vetor_direcao(s_cx, s_cy, d_cx, d_cy)
        vel = getattr(s, "velocidade", 100.0)
        s.x += dir_x * vel * dt
        s.y += dir_y * vel * dt
