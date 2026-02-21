from typing import Any, Sequence

from rlutilities.linear_algebra import vec3, norm, normalize, dot, mat3, angle_between, vec2, xy
from rlutilities.simulation import Car, Ball


def to_vec3(obj: Any) -> vec3:
    if isinstance(obj, vec3):
        return obj
    if isinstance(obj, vec2):
        return vec3(obj)
    if hasattr(obj, "position"):
        return obj.position
    if hasattr(obj, "x"):
        return vec3(obj.x, obj.y, obj.z)
    if hasattr(obj, "X"):
        return vec3(obj.X, obj.Y, obj.Z)
    raise TypeError(f"Unsupported vec3 conversion source: {type(obj)!r}")


def ground(pos) -> vec3:
    pos = to_vec3(pos)
    return vec3(pos[0], pos[1], 0)


def distance(obj1, obj2) -> float:
    return norm(to_vec3(obj1) - to_vec3(obj2))


def ground_distance(obj1, obj2) -> float:
    return norm(ground(obj1) - ground(obj2))


def direction(source, target) -> vec3:
    delta = to_vec3(target) - to_vec3(source)
    if norm(delta) == 0:
        return vec3(1, 0, 0)
    return normalize(delta)


def ground_direction(source, target) -> vec3:
    delta = ground(target) - ground(source)
    if norm(delta) == 0:
        return vec3(1, 0, 0)
    return normalize(delta)


def local(car: Car, pos: vec3) -> vec3:
    return dot(to_vec3(pos) - car.position, car.orientation)


def world(car: Car, pos: vec3) -> vec3:
    return car.position + dot(car.orientation, to_vec3(pos))


def angle_to(car: Car, target: vec3, backwards=False) -> float:
    return abs(angle_between(xy(car.forward()) * (-1 if backwards else 1), ground_direction(car.position, target)))


def forward(mat: mat3) -> vec3:
    return vec3(mat[0, 0], mat[1, 0], mat[2, 0])


def align(pos: vec3, ball: Ball, goal: vec3) -> float:
    pos_to_ball = ground_direction(pos, ball)
    return max(
        dot(pos_to_ball, ground_direction(ball, goal)),
        dot(pos_to_ball, ground_direction(ball, goal + vec3(800, 0, 0))),
        dot(pos_to_ball, ground_direction(ball, goal - vec3(800, 0, 0)))
    )


def nearest_point(pos: vec3, points: Sequence[vec3]) -> vec3:
    if not points:
        raise ValueError("nearest_point requires at least one point")
    return min(points, key=lambda p: distance(pos, p))


def farthest_point(pos: vec3, points: Sequence[vec3]) -> vec3:
    if not points:
        raise ValueError("farthest_point requires at least one point")
    return max(points, key=lambda p: distance(pos, p))


def three_vec3_to_mat3(f: vec3, left: vec3, u: vec3) -> mat3:
    """Create a mat3 from three vec3 by taking them as columns."""
    return mat3(f[0], left[0], u[0], f[1], left[1], u[1], f[2], left[2], u[2])
