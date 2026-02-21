
def sign(x: float) -> int:
    return 1 if x >= 0 else -1


def clamp(x: float, low: float, high: float) -> float:
    return max(min(x, high), low)


def clamp01(x: float) -> float:
    return clamp(x, 0, 1)


def clamp11(x: float) -> float:
    return clamp(x, -1, 1)


def abs_clamp(x: float, limit: float) -> float:
    return clamp(x, -limit, limit)


def nonzero(value: float) -> float:
    return max(value, 0.000001)


def range_map(x: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    if in_max == in_min:
        return out_min
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
