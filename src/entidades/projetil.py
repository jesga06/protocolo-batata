"""
Entidade de Projétil — Protocolo: Batata
Controla a física, tempo de vida, renderização e colisões de tiros no jogo.
"""

import math
import os
import pygame
from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset, AMARELO_XP, LARANJA_ALERTA, VERMELHO_DANO
from src.utils.math_utils import normalizar_vetor, distancia


class Projetil:
    """
    Representa um projétil disparado pelo jogador ou inimigos.
    Suporta múltiplos tipos de sprites, dano balístico direto e detonação de área (AoE).
    """
    _sprites: dict = {}

    def __init__(
        self,
        x: float,
        y: float,
        dir_x: float = 1.0,
        dir_y: float = 0.0,
        velocidade: float = 420.0,
        dano: int = 12,
        tempo_vida: float = 2.5,
        dono: str = "jogador",
        largura: int = 8,
        altura: int = 8,
        sprite_key: str = "projetil_pistola",
        explosivo: bool = False,
        raio_explosao: float = 0.0,
        perfurante: bool = False,
        desaceleracao: float = 0.0,
        vx: float = None,
        vy: float = None,
        cor=None
    ):
        self.x = float(x)
        self.y = float(y)
        self.x_origem = float(x)
        self.y_origem = float(y)
        if vx is not None and vy is not None:
            self.velocidade = math.hypot(vx, vy)
            self.dir_x, self.dir_y = normalizar_vetor(vx, vy)
        else:
            self.dir_x, self.dir_y = normalizar_vetor(dir_x, dir_y)
            self.velocidade = float(velocidade)
        self.desaceleracao = float(desaceleracao)
        self.dano = int(dano)
        self.tempo_vida = float(tempo_vida)
        self.tempo_vida_restante = float(tempo_vida)
        self.dono = dono
        self.largura = int(largura)
        self.altura = int(altura)
        self.width = self.largura
        self.height = self.altura
        self.sprite_key = sprite_key
        self.cor = cor
        self.explosivo = bool(explosivo)
        self.raio_explosao = float(raio_explosao)
        self.perfurante = bool(perfurante)
        self.alvos_atingidos = set()
        self.ativo = True
        self.requer_detonacao_ao_expirar = False

    @property
    def vx(self) -> float:
        return self.dir_x * self.velocidade

    @property
    def vy(self) -> float:
        return self.dir_y * self.velocidade

    @classmethod
    def _carregar_sprite(cls, sprite_key: str):
        if sprite_key not in cls._sprites:
            try:
                caminho = obter_caminho_asset(sprite_key)
                if os.path.isfile(caminho):
                    cls._sprites[sprite_key] = pygame.image.load(caminho).convert_alpha()
                else:
                    cls._sprites[sprite_key] = None
            except Exception:
                cls._sprites[sprite_key] = None
        return cls._sprites.get(sprite_key)

    def update(self, dt: float):
        """Atualiza a posição do projétil, desacelera se aplicável e decrementa o tempo de vida."""
        if not self.ativo:
            return

        if self.desaceleracao > 0.0:
            self.velocidade = max(0.0, self.velocidade - self.desaceleracao * dt)

        self.x += self.dir_x * self.velocidade * dt
        self.y += self.dir_y * self.velocidade * dt
        self.tempo_vida_restante -= dt

        if self.tempo_vida_restante <= 0.0:
            self.ativo = False
            if self.explosivo:
                self.requer_detonacao_ao_expirar = True

    def explodir(
        self,
        lista_inimigos: list,
        jogador=None,
        config_sistema=None,
        mult_dano_explosivo: float = 1.0,
        alvo_direto=None
    ) -> list:
        """
        Executa a detonação em área (AoE) do projétil explosivo.
        O alvo de impacto direto recebe 2x de dano (Direct Hit Bonus).
        Demais inimigos no raio de explosão recebem 1x de dano.
        Se Fogo Amigo estiver ativo, aplica dano ao jogador e/ou aos drones do jogador.
        """
        if not self.explosivo or self.raio_explosao <= 0.0:
            return []

        centro_x = self.x + self.largura / 2.0
        centro_y = self.y + self.altura / 2.0
        dano_efetivo = int(round(self.dano * mult_dano_explosivo))

        inimigos_afetados = []
        for inimigo in lista_inimigos:
            if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                continue

            e_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
            e_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
            dist = distancia(centro_x, centro_y, e_cx, e_cy)

            if inimigo is alvo_direto:
                # Bônus de impacto direto: 2x de dano
                inimigo.receber_dano(dano_efetivo * 2)
                inimigos_afetados.append(inimigo)
                if hasattr(inimigo, "aplicar_knockback"):
                    inimigo.aplicar_knockback(self.dir_x, self.dir_y, forca=350.0)
            elif dist <= self.raio_explosao:
                inimigo.receber_dano(dano_efetivo)
                inimigos_afetados.append(inimigo)

                # Aplica knockback radial a partir do epicentro da explosão
                if dist > 0.1 and hasattr(inimigo, "aplicar_knockback"):
                    kx = (e_cx - centro_x) / dist
                    ky = (e_cy - centro_y) / dist
                    inimigo.aplicar_knockback(kx, ky, forca=280.0)

        # Checa fogo amigo para o jogador e drones
        auto_dano_ativo = False
        if config_sistema is not None:
            if hasattr(config_sistema, "obter_modificadores"):
                mods = config_sistema.obter_modificadores()
                auto_dano_ativo = getattr(mods, "auto_dano", False)
            elif hasattr(config_sistema, "obter_valor"):
                auto_dano_ativo = (config_sistema.obter_valor("fogo_amigo") == "ligado")

        if auto_dano_ativo and jogador is not None and getattr(jogador, "vivo", True):
            j_cx = jogador.x + getattr(jogador, "largura", 32) / 2.0
            j_cy = jogador.y + getattr(jogador, "altura", 32) / 2.0
            dist_j = distancia(centro_x, centro_y, j_cx, j_cy)
            if dist_j <= self.raio_explosao:
                jogador.receber_dano(dano_efetivo)

            # Destruição de todos os drones companheiros por fogo amigo (1 HP)
            drones_list = []
            if hasattr(jogador, "drones") and jogador.drones:
                drones_list = list(jogador.drones)
            elif getattr(jogador, "drone", None) is not None:
                drones_list = [jogador.drone]

            for dr in drones_list:
                if getattr(dr, "ativo", True):
                    d_cx = dr.x + getattr(dr, "largura", 24) / 2.0
                    d_cy = dr.y + getattr(dr, "altura", 24) / 2.0
                    dist_d = distancia(centro_x, centro_y, d_cx, d_cy)
                    if dist_d <= self.raio_explosao:
                        dr.receber_dano(dano_efetivo)

        # Reproduz efeito sonoro de explosão
        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_explosao"))
            sfx.play()
        except Exception:
            pass

        return inimigos_afetados

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna (x, y, largura, altura) para teste de colisão AABB."""
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o projétil na tela virtual com coordenadas de câmera e rotação direcional."""
        if not self.ativo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        # Não desenha se estiver completamente fora da tela visível
        if draw_x < -30 or draw_x > janela.largura + 30 or draw_y < -30 or draw_y > janela.altura + 30:
            return

        sprite = self._carregar_sprite(self.sprite_key)
        if sprite is not None:
            # Rotaciona foguetes, granadas e projéteis balísticos de acordo com o vetor de disparo
            if "foguete" in self.sprite_key or "granada" in self.sprite_key or "rifle" in self.sprite_key or "pistola" in self.sprite_key or "minigun" in self.sprite_key:
                ang_deg = -math.degrees(math.atan2(self.dir_y, self.dir_x))
                rot_sprite = pygame.transform.rotate(sprite, ang_deg)
                rot_rect = rot_sprite.get_rect(center=(int(draw_x + self.largura / 2.0), int(draw_y + self.altura / 2.0)))
                janela.screen.blit(rot_sprite, rot_rect)
            else:
                janela.screen.blit(sprite, (int(draw_x), int(draw_y)))
        else:
            # Fallback gráfico baseado na chave do sprite
            cor = AMARELO_XP
            if "foguete" in self.sprite_key or "granada" in self.sprite_key:
                cor = LARANJA_ALERTA
            elif "inimigo" in self.sprite_key:
                cor = VERMELHO_DANO

            pygame.draw.rect(
                janela.screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura)
            )
