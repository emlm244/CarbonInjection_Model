from maneuvers .driving .drive import Drive 
from maneuvers .driving .stop import Stop 
from maneuvers .driving .travel import Travel 
from maneuvers .maneuver import Maneuver 
from rlutilities .linear_algebra import vec3 
from rlutilities .simulation import Car ,BoostPadState 
from tools .arena import Arena 
from tools .drawing import DrawingTool 
from tools .game_info import GameInfo 
from tools .vector_math import nearest_point ,ground_distance ,ground_direction ,ground ,angle_to ,distance ,angle_between 


class GeneralDefense (Maneuver ):
    """
    First, attempt to rotate on the far side, and when far away enough from the target (usually the ball),
    turn around to face it. If already far enough and facing the target, just stop and wait.
    Also try to pickup boost pads along the way.
    This state expires after a short amount of time, so we can look if there's something better to do. If not,
    it can be simply instantiated again.
    """

    DURATION =0.5 
    TURN_MIN_DURATION =0.18 
    TURN_START_ANGLE =0.34 
    TURN_END_ANGLE =0.16 

    BOOST_LOOK_RADIUS =1200 
    BOOST_LOOK_ANGLE =0.5 

    def __init__ (self ,car :Car ,info :GameInfo ,face_target :vec3 ,distance_from_target :float ,force_nearest =False ):
        super ().__init__ (car )

        self .info =info 
        self .face_target =face_target 
        human_style =info .settings .human_style 
        self .duration =self .DURATION +human_style .role_stability *0.18 
        hysteresis =max (0.0 ,min (0.6 ,human_style .defense_turn_hysteresis ))
        self .turn_start_angle =self .TURN_START_ANGLE +hysteresis *0.22 
        self .turn_end_angle =max (0.05 ,self .TURN_END_ANGLE +hysteresis *0.10 )

        dist =min (distance_from_target ,ground_distance (face_target ,self .info .my_goal .center )-50 )
        target_pos =ground (face_target )+ground_direction (face_target ,self .info .my_goal .center )*dist 

        near_goal =abs (car .position [1 ]-info .my_goal .center [1 ])<3000 
        side_shift =400 if near_goal else 1800 
        points =target_pos +vec3 (side_shift ,0 ,0 ),target_pos -vec3 (side_shift ,0 ,0 )
        if abs (self .car .position .x )>3000 :
            force_nearest =True 
        if near_goal or force_nearest :
            target_pos =nearest_point (face_target ,points )
        else :
            side_hint =1 if car .position [0 ]>=0 else -1 
            target_pos =points [0 ]if side_hint >0 else points [1 ]
            other =points [1 ]if side_hint >0 else points [0 ]
            if ground_distance (car ,target_pos )>ground_distance (car ,other )+1600 :
                target_pos =other 
        if abs (face_target [0 ])<1000 or ground_distance (car ,face_target )<1000 :
            target_pos =nearest_point (car .position ,points )
        target_pos =Arena .clamp (target_pos ,500 )

        self .travel =Travel (car ,target_pos )
        self .travel .finish_distance =800 if near_goal else 1500 
        self .drive =Drive (car )
        self .stop =Stop (car )

        self .start_time =car .time 
        self .turning_to_face =False 
        self .turn_commit_until =car .time 

        self .pad =None 

    def interruptible (self )->bool :
        return self .travel .interruptible ()

    def step (self ,dt ):

        self .travel .step (dt )

        if self .travel .finished :
            angle_error =angle_to (self .car ,self .face_target )
            should_turn =False 
            if self .turning_to_face :
                should_turn =angle_error >self .turn_end_angle or self .car .time <self .turn_commit_until 
                if not should_turn :
                    self .turning_to_face =False 
            else :
                should_turn =angle_error >self .turn_start_angle 
                if should_turn :
                    self .turning_to_face =True 
                    self .turn_commit_until =self .car .time +self .TURN_MIN_DURATION 


            if should_turn :
                self .drive .target_pos =self .face_target 
                self .drive .target_speed =450 if ground_distance (self .car ,self .face_target )<1100 else 900 
                self .drive .step (dt )
                self .controls =self .drive .controls 
                self .controls .handbrake =False 
            else :
                self .stop .step (dt )
                self .controls =self .stop .controls 

        else :
            self .pad =None 


            if self .car .boost <90 and self .travel .interruptible ():
                to_target =ground_direction (self .car ,self .travel .target )

                for pad in self .info .large_boost_pads +self .info .small_boost_pads :
                    to_pad =ground_direction (self .car ,pad )

                    if (
                    pad .state ==BoostPadState .Available and distance (self .car ,pad )<self .BOOST_LOOK_RADIUS 
                    and angle_between (to_target ,to_pad )<self .BOOST_LOOK_ANGLE 
                    ):
                        self .pad =pad 
                        self .drive .target_pos =pad .position 
                        self .drive .target_speed =2200 
                        self .drive .step (dt )
                        self .controls =self .drive .controls 
                        break 


            if self .pad is None :
                self .controls =self .travel .controls 


        if self .car .boost <100 and ground_distance (self .car ,self .travel .target )<4000 :
            self .controls .boost =False 

        self .finished =self .travel .driving and self .car .time >self .start_time +self .duration 

    def render (self ,draw :DrawingTool ):
        self .travel .render (draw )


        if self .pad :
            draw .color (draw .blue )
            draw .circle (self .pad .position ,50 )
