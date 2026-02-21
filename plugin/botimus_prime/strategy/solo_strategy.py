from maneuvers .general_defense import GeneralDefense 
from maneuvers .pickup_boostpad import PickupBoostPad 
from maneuvers .recovery import Recovery 
from maneuvers .strikes .strike import Strike 
from rlutilities .linear_algebra import dot 
from rlutilities .simulation import Car 
from strategy import offense ,defense ,kickoffs 
from strategy .boost_management import choose_boostpad_to_pickup ,compute_low_boost_threshold 
from tools .decision_memory import DecisionMemory 
from tools .game_info import GameInfo 
from tools .intercept import Intercept 
from tools .vector_math import align ,ground ,ground_distance ,ground_direction 


def choose_maneuver (
info :GameInfo ,
my_car :Car ,
decision_memory :DecisionMemory |None =None ,
):
    if decision_memory is not None :
        decision_memory .set_teamplay_trace (None )

    ball =info .ball 
    their_goal =ground (info .their_goal .center )
    my_goal =ground (info .my_goal .center )
    opponents =info .get_opponents ()
    skill =info .settings .skill 
    human_style =info .settings .human_style 
    mechanics =skill .mechanics *(0.7 +0.3 *skill .overall )


    if not my_car .on_ground :
        return Recovery (my_car )


    if ball .position [0 ]==0 and ball .position [1 ]==0 :
        return kickoffs .choose_kickoff (info ,my_car )

    info .predict_ball ()

    my_intercept =Intercept (my_car ,info .ball_predictions )
    their_intercepts =[Intercept (opponent ,info .ball_predictions )for opponent in opponents ]
    their_intercept =min (their_intercepts ,key =lambda i :i .time )
    opponent =their_intercept .car 

    banned_boostpads ={pad for pad in info .large_boost_pads if (
    abs (pad .position [1 ]-their_goal [1 ])<abs (my_intercept .position [1 ]-their_goal [1 ])
    or abs (pad .position [0 ]-my_car .position [0 ])>6000 
    )and ground_distance (my_car ,pad )<4000 }
    best_boostpad_to_pickup =choose_boostpad_to_pickup (info ,my_car ,banned_boostpads )


    if (
    ground_distance (my_intercept ,my_goal )<3000 
    and (abs (my_intercept .position [0 ])<2000 or abs (my_intercept .position [1 ])<4500 )
    and my_car .position [2 ]<300 
    ):
        if align (my_car .position ,my_intercept .ball ,their_goal )>0.5 :
            return offense .any_shot (
            info ,
            my_intercept .car ,
            their_goal ,
            my_intercept ,
            allow_dribble =not info .is_puck and mechanics >0.58 ,
            )
        return defense .any_clear (info ,my_intercept .car )


    low_boost_threshold =compute_low_boost_threshold (
    skill_overall =skill .overall ,
    mistake_rate =human_style .mistake_rate ,
    decisiveness =human_style .decisiveness ,
    base =8 ,
    overall_scale =10 ,
    mistake_scale =8 ,
    decisiveness_scale =4 ,
    min_value =6 ,
    max_value =30 ,
    )
    if my_car .boost <low_boost_threshold and ground_distance (my_intercept ,their_goal )>3000 and best_boostpad_to_pickup is not None :
        return PickupBoostPad (my_car ,best_boostpad_to_pickup )

    ball_in_their_half =abs (my_intercept .position [1 ]-their_goal [1 ])<3000 
    shadow_distance =3000 

    if (
    their_intercept .time <my_intercept .time 
    and align (opponent .position ,their_intercept .ball ,my_goal )>-0.1 +opponent .boost /100 
    and ground_distance (opponent ,their_intercept )>300 
    and dot (opponent .velocity ,ground_direction (their_intercept ,my_goal ))>0 
    ):
        return GeneralDefense (my_car ,info ,my_intercept .position ,shadow_distance ,force_nearest =ball_in_their_half )


    shot_alignment_gate =(
    -0.52 
    -human_style .mistake_rate *0.08 
    +human_style .decisiveness *0.16 
    +human_style .takeover_bias *0.08 
    )
    if (
    align (my_car .position ,my_intercept .ball ,their_goal )>shot_alignment_gate 
    or ground_distance (my_intercept ,their_goal )<2000 
    or ground_distance (opponent ,their_intercept )<300 
    ):
        if my_car .position [2 ]<300 :
            shot =offense .any_shot (
            info ,
            my_intercept .car ,
            their_goal ,
            my_intercept ,
            allow_dribble =not info .is_puck and mechanics >0.58 +human_style .mechanical_variance *0.12 ,
            )
            if (
            not isinstance (shot ,Strike )
            or shot .intercept .time <their_intercept .time 
            or abs (shot .intercept .position [0 ])<3500 
            or human_style .takeover_bias >0.05 
            ):
                return shot 

    if my_car .boost <30 +(1.0 -skill .overall )*20 and best_boostpad_to_pickup is not None :
        return PickupBoostPad (my_car ,best_boostpad_to_pickup )


    return GeneralDefense (my_car ,info ,my_intercept .position ,shadow_distance ,force_nearest =ball_in_their_half )
