"""
Sistema de Partículas e Feedback Visual — Protocolo: Batata
Gerencia efeitos visuais de alta performance:
- Faíscas balísticas de impacto de tiros
- Bursts cintilantes na coleta de drops (XP, cura, caixas)
- Ondas de choque expansivas e detritos de explosões
"""

import math
import random
import pygame


class Particula:
    """Representa uma partícula individual em coordenadas de mundo."""
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        vida_max: float,
        tamanho_inicial: float,
        tamanho_final: float,
        cor: tuple[int, int, int],
        decaimento_vel: float = 0.92
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.tamanho_inicial = float(tamanho_inicial)
        self.tamanho_final = float(tamanho_final)
        self.cor = cor
        self.decaimento_vel = float(decaimento_vel)

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        """Retorna valor de 0.0 (nascimento) a 1.0 (morte)."""
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= (self.decaimento_vel ** (dt * 60.0))
        self.vy *= (self.decaimento_vel ** (dt * 60.0))

    def obter_tamanho_atual(self) -> float:
        p = self.progresso
        return max(0.5, self.tamanho_inicial + (self.tamanho_final - self.tamanho_inicial) * p)


class OndaChoque:
    """Representa um anel expansivo de onda de choque."""
    def __init__(
        self,
        x: float,
        y: float,
        raio_max: float = 80.0,
        vida_max: float = 0.25,
        cor: tuple[int, int, int] = (255, 140, 30)
    ):
        self.x = float(x)
        self.y = float(y)
        self.raio_max = float(raio_max)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.cor = cor

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt

    def obter_raio_atual(self) -> float:
        return max(1.0, self.raio_max * (self.progresso ** 0.5))


class TextoDano:
    """Representa um número flutuante de dano no espaço do mundo."""
    def __init__(
        self,
        x: float,
        y: float,
        dano: int,
        critico: bool = False,
        vida_max: float = 0.65
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-20.0, 20.0)
        self.vy = random.uniform(-70.0, -100.0)
        self.dano = int(dano)
        self.critico = bool(critico)
        self.vida_max = max(0.01, float(vida_max))
        self.vida = self.vida_max
        self.texto = f"{dano}!" if critico else f"{dano}"
        self.cor = (255, 215, 0) if critico else (255, 255, 255)
        self._surf = None

    @property
    def viva(self) -> bool:
        return self.vida > 0.0

    @property
    def progresso(self) -> float:
        return 1.0 - (self.vida / self.vida_max)

    def update(self, dt: float):
        self.vida -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 60.0 * dt


class SistemaParticulas:
    """
    Gerenciador global de partículas com teto rígido de instâncias e rendering otimizado.
    """
    MAX_PARTICULAS = 300
    MAX_TEXTOS = 100
    MAX_ONDAS = 30
    _fonte_dano = None

    def __init__(self):
        self.particulas: list[Particula] = []
        self.ondas_choque: list[OndaChoque] = []
        self.textos_dano: list[TextoDano] = []
        self.low_graphics: bool = False
        self._surfs_onda_cache: dict[int, pygame.Surface] = {}

    def limpar(self):
        """Descarta todas as partículas, ondas e textos ativos."""
        self.particulas.clear()
        self.ondas_choque.clear()
        self.textos_dano.clear()

    def emitir_texto_dano(
        self,
        x: float,
        y: float,
        dano: int,
        critico: bool = False
    ):
        """Emite número flutuante de dano no mundo."""
        self.textos_dano.append(TextoDano(x, y, dano, critico=critico))
        if len(self.textos_dano) > self.MAX_TEXTOS:
            del self.textos_dano[:len(self.textos_dano) - self.MAX_TEXTOS]

    def emitir_faiscas(
        self,
        x: float,
        y: float,
        dir_x: float = 0.0,
        dir_y: float = 0.0,
        cor: tuple[int, int, int] = (255, 220, 100),
        qtd: int = 6
    ):
        """
        Emite faíscas balísticas direcionais ao atingir um alvo.
        """
        if self.low_graphics:
            qtd = max(1, qtd // 2)

        base_ang = math.atan2(dir_y, dir_x) if (dir_x != 0 or dir_y != 0) else random.uniform(0, 2 * math.pi)

        for _ in range(qtd):
            # Cone de espalhamento de ~90 graus
            ang = base_ang + random.uniform(-0.8, 0.8)
            vel = random.uniform(120.0, 320.0)
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
            vida = random.uniform(0.10, 0.22)
            tam_ini = random.uniform(2.5, 4.0)

            p = Particula(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.5,
                cor=cor,
                decaimento_vel=0.88
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def emitir_burst_drop(self, x: float, y: float, tipo: str = "xp"):
        """
        Emite partículas cintilantes ascendentes ao coletar um drop.
        """
        mapa_cores = {
            "xp": (255, 215, 0),         # Dourado
            "cura": (50, 230, 90),        # Verde
            "arma": (255, 140, 0),        # Laranja
            "equipamento": (175, 75, 255),# Roxo
            "config": (0, 220, 255),      # Ciano
            "overclock": (175, 75, 255)   # Roxo
        }
        cor = mapa_cores.get(tipo, (255, 255, 255))
        qtd = 12 if tipo in ("arma", "equipamento", "overclock") else 8
        if self.low_graphics:
            qtd = max(1, qtd // 2)

        for _ in range(qtd):
            ang = random.uniform(-math.pi * 0.8, -math.pi * 0.2)  # Direção preferencialmente para cima
            vel = random.uniform(60.0, 160.0)
            vx = math.cos(ang) * vel + random.uniform(-20, 20)
            vy = math.sin(ang) * vel
            vida = random.uniform(0.20, 0.40)
            tam_ini = random.uniform(3.0, 5.0)

            p = Particula(
                x=x + random.uniform(-6, 6),
                y=y + random.uniform(-6, 6),
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.0,
                cor=cor,
                decaimento_vel=0.94
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def emitir_onda_choque(
        self,
        x: float,
        y: float,
        raio_max: float = 80.0,
        cor: tuple[int, int, int] = (255, 140, 30)
    ):
        """
        Cria uma onda de choque radial expansiva.
        """
        self.ondas_choque.append(OndaChoque(x=x, y=y, raio_max=raio_max, vida_max=0.28, cor=cor))
        if len(self.ondas_choque) > self.MAX_ONDAS:
            del self.ondas_choque[:len(self.ondas_choque) - self.MAX_ONDAS]

    def emitir_debris(
        self,
        x: float,
        y: float,
        cor: tuple[int, int, int] = (200, 120, 50),
        qtd: int = 10
    ):
        """
        Emite fragmentos de detritos em todas as direções para explosões.
        """
        if self.low_graphics:
            qtd = max(1, qtd // 2)

        for _ in range(qtd):
            ang = random.uniform(0, 2 * math.pi)
            vel = random.uniform(80.0, 260.0)
            vx = math.cos(ang) * vel
            vy = math.sin(ang) * vel
            vida = random.uniform(0.20, 0.45)
            tam_ini = random.uniform(2.0, 4.5)

            p = Particula(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                vida_max=vida,
                tamanho_inicial=tam_ini,
                tamanho_final=0.5,
                cor=cor,
                decaimento_vel=0.90
            )
            self.particulas.append(p)

        if len(self.particulas) > self.MAX_PARTICULAS:
            del self.particulas[:len(self.particulas) - self.MAX_PARTICULAS]

    def update(self, dt: float):
        """
        Atualiza física e tempo de vida de todas as partículas, ondas e textos.
        """
        for p in self.particulas:
            p.update(dt)
        self.particulas = [p for p in self.particulas if p.viva]

        for oc in self.ondas_choque:
            oc.update(dt)
        self.ondas_choque = [oc for oc in self.ondas_choque if oc.viva]

        for td in self.textos_dano:
            td.update(dt)
        self.textos_dano = [td for td in self.textos_dano if td.viva]

    def desenhar(self, janela, camera=None):
        """
        Renderiza todas as partículas, ondas de choque e números de dano na tela virtual com suporte a low_graphics.
        """
        screen = getattr(janela, "screen", janela)
        largura_janela = getattr(janela, "largura", getattr(screen, "get_width", lambda: 800)())
        altura_janela = getattr(janela, "altura", getattr(screen, "get_height", lambda: 600)())
        is_low_graphics = self.low_graphics or getattr(janela, "low_graphics", False)

        # 1. Renderiza ondas de choque
        for oc in self.ondas_choque:
            tx = camera.transform_x(oc.x) if camera else oc.x
            ty = camera.transform_y(oc.y) if camera else oc.y

            if tx < -100 or tx > largura_janela + 100 or ty < -100 or ty > altura_janela + 100:
                continue

            raio = oc.obter_raio_atual()
            if is_low_graphics:
                # Desenha círculo simples diretamente sem alocação de Surface com alpha
                largura_linha = max(1, int(2 * (1.0 - oc.progresso)))
                pygame.draw.circle(screen, oc.cor, (int(tx), int(ty)), int(raio), width=largura_linha)
            else:
                alpha = int(max(0, 255 * (1.0 - oc.progresso)))
                dim = int(raio * 2 + 10)

                if dim > 0 and alpha > 5:
                    try:
                        surf_oc = self._surfs_onda_cache.get(dim)
                        if surf_oc is None:
                            surf_oc = pygame.Surface((dim, dim), pygame.SRCALPHA)
                            self._surfs_onda_cache[dim] = surf_oc
                        else:
                            surf_oc.fill((0, 0, 0, 0))

                        cx = dim // 2
                        cy = dim // 2
                        cor_rgba = (oc.cor[0], oc.cor[1], oc.cor[2], alpha)
                        largura_linha = max(1, int(3 * (1.0 - oc.progresso)))
                        pygame.draw.circle(surf_oc, cor_rgba, (cx, cy), int(raio), width=largura_linha)
                        screen.blit(surf_oc, (int(tx - cx), int(ty - cy)))
                    except Exception:
                        pass

        # 2. Renderiza partículas
        for p in self.particulas:
            tx = camera.transform_x(p.x) if camera else p.x
            ty = camera.transform_y(p.y) if camera else p.y

            if tx < -20 or tx > largura_janela + 20 or ty < -20 or ty > altura_janela + 20:
                continue

            tam = p.obter_tamanho_atual()
            if tam > 0:
                if is_low_graphics:
                    int_tam = max(1, int(tam))
                    pygame.draw.rect(screen, p.cor, (int(tx - int_tam // 2), int(ty - int_tam // 2), int_tam, int_tam))
                else:
                    pygame.draw.circle(screen, p.cor, (int(tx), int(ty)), max(1, int(tam)))

        # 3. Renderiza números flutuantes de dano
        if self.textos_dano:
            if self._fonte_dano is None:
                try:
                    if pygame.font.get_init():
                        self._fonte_dano = pygame.font.SysFont("arial", 16, bold=True)
                except Exception:
                    self._fonte_dano = None

            if self._fonte_dano is not None:
                for td in self.textos_dano:
                    tx = camera.transform_x(td.x) if camera else td.x
                    ty = camera.transform_y(td.y) if camera else td.y

                    if tx < -40 or tx > largura_janela + 40 or ty < -40 or ty > altura_janela + 40:
                        continue

                    try:
                        if getattr(td, "_surf", None) is None:
                            td._surf = self._fonte_dano.render(td.texto, True, td.cor)
                        surf_t = td._surf
                        screen.blit(surf_t, (int(tx - surf_t.get_width() / 2), int(ty)))
                    except Exception:
                        pass
