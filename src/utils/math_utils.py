"""
Utilitários Matemáticos — Protocolo: Batata
Funções para cálculo vetorial, normalização, distâncias, interpolação e detecção de colisão AABB/círculo.
"""

import math


def distancia_sq(x1: float, y1: float, x2: float, y2: float) -> float:
    """Retorna a distância euclidiana ao quadrado entre dois pontos (otimizada para comparações)."""
    dx = x2 - x1
    dy = y2 - y1
    return dx * dx + dy * dy


def distancia(x1: float, y1: float, x2: float, y2: float) -> float:
    """Retorna a distância euclidiana entre dois pontos."""
    return math.sqrt(distancia_sq(x1, y1, x2, y2))


def normalizar_vetor(dx: float, dy: float) -> tuple[float, float]:
    """
    Normaliza um vetor 2D para magnitude unitária (com proteção contra divisão por zero).
    Retorna (0.0, 0.0) caso a magnitude seja zero.
    """
    mag_sq = dx * dx + dy * dy
    if mag_sq <= 1e-10:
        return 0.0, 0.0
    mag = math.sqrt(mag_sq)
    return dx / mag, dy / mag


def vetor_direcao(origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> tuple[float, float]:
    """Retorna o vetor unitário apontando de (origem) para (destino)."""
    return normalizar_vetor(destino_x - origem_x, destino_y - origem_y)


def clamp(valor: float, min_val: float, max_val: float) -> float:
    """Restringe um valor numérico entre os limites [min_val, max_val]."""
    if valor < min_val:
        return min_val
    if valor > max_val:
        return max_val
    return valor


def lerp(a: float, b: float, t: float) -> float:
    """Interpolação linear entre a e b com fator t [0.0, 1.0]."""
    return a + (b - a) * t


def colisao_aabb(
    x1: float, y1: float, w1: float, h1: float,
    x2: float, y2: float, w2: float, h2: float
) -> bool:
    """
    Verifica colisão entre duas caixas delimitadoras alinhadas aos eixos (AABB).
    Retorna True se houver sobreposição.
    """
    return (
        x1 < x2 + w2 and
        x1 + w1 > x2 and
        y1 < y2 + h2 and
        y1 + h1 > y2
    )


def colisao_circulo(x1: float, y1: float, r1: float, x2: float, y2: float, r2: float) -> bool:
    """Verifica colisão entre dois círculos dados centro e raio."""
    dist_max = r1 + r2
    return distancia_sq(x1, y1, x2, y2) <= (dist_max * dist_max)


def ponto_em_retangulo(px: float, py: float, rx: float, ry: float, rw: float, rh: float) -> bool:
    """Verifica se um ponto 2D (px, py) está dentro do retângulo [rx, ry, rw, rh]."""
    return rx <= px <= rx + rw and ry <= py <= ry + rh


def angulo_radianos(origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> float:
    """Retorna o ângulo em radianos entre dois pontos em relação ao eixo horizontal."""
    return math.atan2(destino_y - origem_y, destino_x - origem_x)


def angulo_graus(origem_x: float, origem_y: float, destino_x: float, destino_y: float) -> float:
    """Retorna o ângulo em graus [0, 360) entre dois pontos."""
    rad = angulo_radianos(origem_x, origem_y, destino_x, destino_y)
    deg = math.degrees(rad)
    return deg if deg >= 0 else deg + 360.0


def rotacionar_vetor(vx: float, vy: float, rad: float) -> tuple[float, float]:
    """Rotaciona um vetor 2D (vx, vy) pelo ângulo rad (em radianos)."""
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return (vx * cos_a - vy * sin_a, vx * sin_a + vy * cos_a)
