"""
Módulo de Cálculo de Trajetórias Suaves Bézier e Easing para o Mouse.

Gera caminhos cinemáticos naturais simulando a mão humana com curvas de
Bézier cúbicas e desaceleração gradual (easeInOutCubic), evitando movimentos
robóticos instantâneos que causam falhas de detecção em interfaces.
"""

import math
import random
from typing import List, Tuple

def ease_in_out_cubic(t: float) -> float:
    """Função de aceleração e desaceleração suave (S-curve)."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

def cubic_bezier_point(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    t: float
) -> Tuple[int, int]:
    """Calcula um ponto (x, y) na curva de Bézier cúbica para o parâmetro t em [0, 1]."""
    u = 1.0 - t
    tt = t * t
    uu = u * u
    uuu = uu * u
    ttt = tt * t

    x = (uuu * p0[0]) + (3 * uu * t * p1[0]) + (3 * u * tt * p2[0]) + (ttt * p3[0])
    y = (uuu * p0[1]) + (3 * uu * t * p1[1]) + (3 * u * tt * p2[1]) + (ttt * p3[1])
    return int(round(x)), int(round(y))

def generate_bezier_trajectory(
    start: Tuple[int, int],
    target: Tuple[int, int],
    steps: int = 25
) -> List[Tuple[int, int]]:
    """Gera uma lista de coordenadas interpoladas entre o ponto inicial e o destino."""
    if steps <= 1 or start == target:
        return [target]

    dx = target[0] - start[0]
    dy = target[1] - start[1]
    dist = math.hypot(dx, dy)

    if dist < 5.0:
        return [target]

    # Vetor perpendicular para desvio orgânico suave
    perp_x = -dy / dist
    perp_y = dx / dist

    # Desvio sutil proporcional à distância percorrida
    offset_magnitude = min(dist * 0.2, 60.0)
    desvio1 = (random.random() - 0.5) * offset_magnitude
    desvio2 = (random.random() - 0.5) * offset_magnitude

    # Pontos de controle intermediários
    p0 = (float(start[0]), float(start[1]))
    p1 = (start[0] + dx * 0.3 + perp_x * desvio1, start[1] + dy * 0.3 + perp_y * desvio1)
    p2 = (start[0] + dx * 0.7 + perp_x * desvio2, start[1] + dy * 0.7 + perp_y * desvio2)
    p3 = (float(target[0]), float(target[1]))

    path: List[Tuple[int, int]] = []
    for i in range(1, steps + 1):
        linear_t = i / steps
        eased_t = ease_in_out_cubic(linear_t)
        pt = cubic_bezier_point(p0, p1, p2, p3, eased_t)
        path.append(pt)

    # Garante que o último ponto coincida estritamente com o alvo final
    if path[-1] != target:
        path[-1] = target

    return path
