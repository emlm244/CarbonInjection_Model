from maneuvers.jumps.aim_dodge import AimDodge
from maneuvers.strikes.strike import Strike
from rlutilities.linear_algebra import cross, norm, dot, normalize, vec3
from rlutilities.simulation import Car, Ball
from tools.intercept import Intercept
from tools.math import clamp
from tools.vector_math import ground_direction


class DodgeStrike(Strike):
    """
    Strike the ball by dodging into it.
    """

    allow_backwards = False
    additional_jump_time = 0.0

    def intercept_predicate(self, car: Car, ball: Ball):
        if (ball.time - car.time) < self.get_jump_duration(ball.position[2]):
            return False
        return ball.position[2] < self.info.object_ground_cutoff

    def __init__(self, car: Car, info, target=None):
        self.dodge = AimDodge(car, 0.1, info.ball.position)
        self.dodging = False

        super().__init__(car, info, target)

    def get_jump_duration(self, ball_height: float) -> float:
        base_height = self.info.object_rest_height
        return 0.05 + clamp((ball_height - base_height) / 500, 0, 1.5) + self.additional_jump_time

    def configure(self, intercept: Intercept):
        super().configure(intercept)

        ball = intercept.ball
        target_direction = ground_direction(ball, self.target)
        hit_dir = ground_direction(ball.velocity, target_direction * (norm(ball.velocity) * 3 + 500))
        hit_offset = 165

        to_ball = ground_direction(self.car, ball)
        if dot(hit_dir, to_ball) < 0:
            perpendicular_dir = cross(to_ball, vec3(0, 0, 1))
            hit_dir = perpendicular_dir if dot(perpendicular_dir, hit_dir) > 0 else perpendicular_dir * -1
            hit_offset = 130

        self.arrive.target = intercept.ground_pos - hit_dir * hit_offset
        self.arrive.target_direction = hit_dir

        jump_duration = self.get_jump_duration(ball.position[2])
        self.dodge.jump.duration = jump_duration
        self.dodge.target = intercept.ball.position
        self.arrive.additional_shift = jump_duration * 1000

    def interruptible(self) -> bool:
        if self.info.ball.position[2] > self.info.object_rest_height + 60 and self.dodging:
            return True
        return not self.dodging and super().interruptible()

    def step(self, dt):
        if self.dodging:
            self.dodge.step(dt)
            self.controls = self.dodge.controls
        else:
            super().step(dt)
            if (
                self.arrive.arrival_time - self.car.time < self.dodge.jump.duration + 0.13
                and abs(self.arrive.drive.target_speed - norm(self.car.velocity)) < 1000
                and (
                    norm(self.car.velocity) < 500
                    or (
                        norm(self.car.velocity) > 1
                        and dot(normalize(self.car.velocity), ground_direction(self.car, self.arrive.target)) > 0.95
                    )
                )
            ):
                self.dodging = True

        if self.dodge.finished:
            self.finished = True
