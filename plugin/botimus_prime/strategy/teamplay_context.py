from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from rlutilities.linear_algebra import dot, vec3
from rlutilities.simulation import Car
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.math import clamp01
from tools.vector_math import align, ground, ground_direction, ground_distance


@dataclass
class TeamplayContext:
    team_cars: List[Car]
    intercepts_by_id: Dict[int, Intercept]
    role_order_ids: List[int]
    role_by_id: Dict[int, int]
    attacker_id: int
    attacker_intercept: Intercept
    opponent_fastest_intercept: Optional[Intercept]
    danger: float
    time_advantage: float
    open_attack_window: float
    teammate_commit_density: float
    opportunity_score_by_id: Dict[int, float]


def adaptive_aggression(info: GameInfo, my_car: Car) -> float:
    skill = info.settings.skill
    base = skill.aggression * 0.60 + skill.decision_making * 0.20 + skill.overall * 0.20

    if info.settings.teamplay.follow_human_style:
        follow_strength = info.settings.teamplay.human_follow_strength * 0.4
        human_aggression = info.get_team_human_aggression(my_car)
        base = base * (1.0 - follow_strength) + human_aggression * follow_strength

    return clamp01(base)


def build_context(info: GameInfo, team_cars: List[Car]) -> TeamplayContext:
    their_goal = ground(info.their_goal.center)
    my_goal = ground(info.my_goal.center)

    info.predict_ball()

    intercepts_by_id = {car.id: Intercept(car, info.ball_predictions) for car in team_cars}

    opponent_fastest = None
    opponents = info.get_opponents()
    if opponents:
        opponent_intercepts = [Intercept(opponent, info.ball_predictions) for opponent in opponents]
        opponent_fastest = min(opponent_intercepts, key=lambda intercept: intercept.time)

    def attacker_score(car: Car) -> float:
        intercept = intercepts_by_id[car.id]
        pressure = align(car.position, intercept.ball, their_goal)
        boost_bonus = car.boost / 100 * 0.12
        defensive_penalty = 0.08 if ground_distance(car, my_goal) < 1800 and len(team_cars) >= 3 else 0.0
        return intercept.time - pressure * 0.25 - boost_bonus + defensive_penalty

    attacker = min(team_cars, key=attacker_score)
    attacker_intercept = intercepts_by_id[attacker.id]

    remaining = [car for car in team_cars if car.id != attacker.id]
    role_order = [attacker.id]
    if remaining:
        if len(remaining) == 1:
            role_order.append(remaining[0].id)
        else:
            third_man = min(remaining, key=lambda car: ground_distance(car, my_goal))
            middle = [car for car in remaining if car.id != third_man.id]
            middle.sort(key=lambda car: intercepts_by_id[car.id].time)
            role_order.extend([car.id for car in middle])
            role_order.append(third_man.id)

    role_by_id = {car_id: idx for idx, car_id in enumerate(role_order)}

    if opponent_fastest is not None:
        opponent_time = opponent_fastest.time
    else:
        opponent_time = attacker_intercept.time + 2.0

    def opportunity_score(car: Car) -> float:
        intercept = intercepts_by_id[car.id]
        lane_quality = clamp01((align(car.position, intercept.ball, their_goal) + 0.35) / 1.35)
        opponent_time_edge = clamp01((opponent_time - intercept.time + 0.20) / 1.10)
        attacker_time_edge = clamp01((attacker_intercept.time - intercept.time + 0.15) / 0.85)
        boost_bonus = clamp01((car.boost - 8) / 70)
        depth_bonus = clamp01((ground_distance(intercept, my_goal) - 2300) / 4600)
        return clamp01(
            opponent_time_edge * 0.34
            + attacker_time_edge * 0.28
            + lane_quality * 0.20
            + boost_bonus * 0.10
            + depth_bonus * 0.08
        )

    opportunity_score_by_id = {car.id: opportunity_score(car) for car in team_cars}
    open_attack_window = max(opportunity_score_by_id.values()) if opportunity_score_by_id else 0.0

    if len(team_cars) > 1:
        likely_committers = sum(
            1
            for car in team_cars
            if intercepts_by_id[car.id].time <= attacker_intercept.time + 0.20
            and opportunity_score_by_id[car.id] > 0.52
        )
        teammate_commit_density = clamp01((max(0, likely_committers - 1)) / (len(team_cars) - 1))
    else:
        teammate_commit_density = 0.0

    goal_pressure = clamp01((4200 - ground_distance(info.ball, my_goal)) / 4200)
    if opponent_fastest is not None:
        time_pressure = clamp01((attacker_intercept.time - opponent_fastest.time + 0.30) / 1.20)
        time_advantage = opponent_fastest.time - attacker_intercept.time
    else:
        time_pressure = 0.0
        time_advantage = 2.0

    towards_goal_speed = dot(info.ball.velocity, ground_direction(info.ball, my_goal))
    velocity_pressure = clamp01((towards_goal_speed + 300) / 2000)
    danger = clamp01(goal_pressure * 0.45 + time_pressure * 0.35 + velocity_pressure * 0.20)

    return TeamplayContext(
        team_cars=team_cars,
        intercepts_by_id=intercepts_by_id,
        role_order_ids=role_order,
        role_by_id=role_by_id,
        attacker_id=attacker.id,
        attacker_intercept=attacker_intercept,
        opponent_fastest_intercept=opponent_fastest,
        danger=danger,
        time_advantage=time_advantage,
        open_attack_window=open_attack_window,
        teammate_commit_density=teammate_commit_density,
        opportunity_score_by_id=opportunity_score_by_id,
    )


def get_car_for_role(context: TeamplayContext, role: int) -> Optional[Car]:
    if role < 0 or role >= len(context.role_order_ids):
        return None

    wanted_id = context.role_order_ids[role]
    for car in context.team_cars:
        if car.id == wanted_id:
            return car
    return None


def should_take_over_attack(
    info: GameInfo,
    context: TeamplayContext,
    car: Car,
    commit_window: float,
    takeover_threshold: float = 0.58,
    takeover_bias: float = 0.0,
) -> bool:
    role = context.role_by_id.get(car.id, 99)
    if role == 0:
        return True

    my_intercept = context.intercepts_by_id[car.id]
    attacker_intercept = context.attacker_intercept
    my_score = context.opportunity_score_by_id.get(car.id, 0.0)
    attacker_score = context.opportunity_score_by_id.get(context.attacker_id, 0.0)
    threshold = clamp01(takeover_threshold - takeover_bias * 0.12)

    if my_intercept.time + commit_window < attacker_intercept.time:
        return True

    if (
        my_score > attacker_score + 0.12
        and my_intercept.time < attacker_intercept.time + commit_window * 0.65
    ):
        return True

    if (
        context.open_attack_window >= threshold
        and my_score >= threshold
        and context.teammate_commit_density < 0.70
        and (role <= 1 or context.danger < 0.60)
    ):
        return True

    if context.danger > 0.72 and role == 1 and my_intercept.time < attacker_intercept.time + commit_window * 0.5:
        return True

    return False


def support_face_target(info: GameInfo, context: TeamplayContext, my_car: Car) -> vec3:
    attacker = get_car_for_role(context, 0)
    if attacker is None:
        return info.ball.position

    target = info.ball.position * 0.70 + attacker.position * 0.30
    if info.settings.teamplay.follow_human_style:
        human = info.get_primary_human_teammate(my_car)
        if human is not None:
            amount = info.settings.teamplay.human_follow_strength * 0.35
            target = target * (1.0 - amount) + human.position * amount
    return target


def support_distance_for_role(info: GameInfo, context: TeamplayContext, my_car: Car, role: int) -> float:
    team_size = len(context.team_cars)
    if team_size <= 2:
        base = info.settings.teamplay.support_distance_2v2
    elif role <= 1:
        base = info.settings.teamplay.support_distance_3v3_second
    else:
        base = info.settings.teamplay.support_distance_3v3_third

    aggression = adaptive_aggression(info, my_car)
    rotation = info.settings.skill.rotation_discipline
    human_style = info.settings.human_style

    base -= (aggression - 0.5) * 700
    base += (0.70 - rotation) * 600
    base += context.danger * 900
    base -= (human_style.decisiveness - 0.5) * 220
    base += human_style.mistake_rate * 220

    if role >= 2 and info.settings.teamplay.conservative_last_man:
        base += (1.0 - aggression) * 500

    return max(2800.0, min(7600.0, base))


def is_safe_to_detour_for_boost(info: GameInfo, context: TeamplayContext, car: Car) -> bool:
    my_intercept = context.intercepts_by_id[car.id]
    if context.opponent_fastest_intercept is None:
        return True

    human_style = info.settings.human_style
    if context.open_attack_window > 0.64 + human_style.takeover_bias * 0.08:
        return False

    time_buffer = context.opponent_fastest_intercept.time - my_intercept.time
    risk = info.settings.teamplay.boost_detour_risk * info.settings.skill.decision_making
    required_buffer = 0.25 + (1.0 - risk) * 0.60 + context.danger * 0.40
    return time_buffer > required_buffer and context.danger < 0.82
