from maneuvers.strikes.clears import DodgeClear, FastAerialClear
from maneuvers.strikes.strike import Strike
from rlutilities.simulation import Car
from tools.game_info import GameInfo


def any_clear(info: GameInfo, car: Car) -> Strike:
    skill = info.settings.skill
    clears: list[Strike] = [
        DodgeClear(car, info),
    ]

    if (
        not info.is_puck
        and skill.mechanics > 0.72
        and skill.consistency > 0.55
        and car.boost > 35
    ):
        clears.append(FastAerialClear(car, info))

    return min(clears, key=lambda clear: clear.intercept.time)
