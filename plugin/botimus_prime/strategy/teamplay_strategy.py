from __future__ import annotations 

from typing import Any 

from maneuvers .general_defense import GeneralDefense 
from maneuvers .recovery import Recovery 
from maneuvers .pickup_boostpad import PickupBoostPad 
from rlutilities .simulation import Car 
from strategy import offense ,kickoffs ,defense 
from strategy .boost_management import choose_boostpad_to_pickup ,compute_low_boost_threshold 
from strategy .teamplay_context import (
adaptive_aggression ,
build_context ,
is_safe_to_detour_for_boost ,
should_take_over_attack ,
support_distance_for_role ,
support_face_target ,
)
from tools .decision_memory import DecisionMemory 
from tools .game_info import GameInfo 
from tools .vector_math import align ,ground ,distance ,ground_distance 


def _role_label (role :int )->str :
    if role <=0 :
        return "first_man"
    if role ==1 :
        return "second_man"
    return "third_man"


def _simple_trace (
info :GameInfo ,
my_car :Car ,
*,
role :int ,
reason :str ,
maneuver_name :str ,
)->dict [str ,Any ]:
    return {
    "time":float (info .time ),
    "car_id":int (my_car .id ),
    "role_index":int (role ),
    "role_label":_role_label (role ),
    "reason":reason ,
    "maneuver":maneuver_name ,
    }


def choose_maneuver (
info :GameInfo ,
my_car :Car ,
decision_memory :DecisionMemory |None =None ,
):
    ball =info .ball 
    teammates =info .get_teammates (my_car )
    my_team =[my_car ]+teammates 
    their_goal =ground (info .their_goal .center )
    my_goal =ground (info .my_goal .center )


    if not my_car .on_ground :
        if decision_memory is not None :
            decision_memory .set_teamplay_trace (
            _simple_trace (
            info ,
            my_car ,
            role =decision_memory .last_role if decision_memory .last_role >=0 else 1 ,
            reason ="recovery_airborne",
            maneuver_name ="Recovery",
            )
            )
        return Recovery (my_car )


    if ball .position [0 ]==0 and ball .position [1 ]==0 :


        if distance (my_car ,ball )==min (distance (car ,ball )for car in my_team ):
            if decision_memory is not None :
                decision_memory .set_teamplay_trace (
                _simple_trace (
                info ,
                my_car ,
                role =0 ,
                reason ="kickoff_commit",
                maneuver_name ="Kickoff",
                )
                )
            return kickoffs .choose_kickoff (info ,my_car )
        if decision_memory is not None :
            decision_memory .set_teamplay_trace (
            _simple_trace (
            info ,
            my_car ,
            role =1 ,
            reason ="kickoff_support",
            maneuver_name ="GeneralDefense",
            )
            )

    skill =info .settings .skill 
    human_style =info .settings .human_style 
    mechanics =skill .mechanics *(0.7 +0.3 *skill .overall )
    decision_quality =skill .decision_making *(0.7 +0.3 *skill .overall )
    aggression =adaptive_aggression (info ,my_car )
    awareness =skill .teammate_awareness 
    takeover_threshold =(
    0.56 
    +(1.0 -human_style .decisiveness )*0.08 
    +human_style .mistake_rate *0.06 
    )

    context =build_context (info ,my_team )
    my_intercept =context .intercepts_by_id [my_car .id ]
    my_role =context .role_by_id .get (my_car .id ,len (my_team )-1 )

    if (
    decision_memory is not None 
    and decision_memory .is_role_locked (info .time )
    and decision_memory .last_role >=0 
    and context .danger <0.82 
    and my_role !=0 
    and context .open_attack_window <takeover_threshold +0.08 
    ):
        my_role =min (decision_memory .last_role ,len (my_team )-1 )
        context .role_by_id [my_car .id ]=my_role 
    elif decision_memory is not None :
        role_lock_duration =0.15 +human_style .role_stability *0.50 
        decision_memory .lock_role (my_role ,info .time ,role_lock_duration )

    commit_window =(
    info .settings .teamplay .double_commit_window 
    +(1.0 -decision_quality )*0.16 
    +(1.0 -awareness )*0.10 
    +(1.0 -human_style .role_stability )*0.08 
    +human_style .mechanical_variance *0.04 
    +(1.0 -human_style .decisiveness )*0.06 
    )
    commit_window =max (0.08 ,min (0.65 ,commit_window ))

    trace :dict [str ,Any ]={
    "time":float (info .time ),
    "car_id":int (my_car .id ),
    "team_size":int (len (my_team )),
    "attacker_id":int (context .attacker_id ),
    "role_index":int (my_role ),
    "role_label":_role_label (my_role ),
    "my_intercept_time":float (my_intercept .time ),
    "attacker_intercept_time":float (context .attacker_intercept .time ),
    "opponent_fastest_time":(
    float (context .opponent_fastest_intercept .time )
    if context .opponent_fastest_intercept is not None 
    else None 
    ),
    "danger":float (context .danger ),
    "time_advantage":float (context .time_advantage ),
    "open_attack_window":float (context .open_attack_window ),
    "teammate_commit_density":float (context .teammate_commit_density ),
    "opportunity_score_self":float (context .opportunity_score_by_id .get (my_car .id ,0.0 )),
    "opportunity_score_attacker":float (context .opportunity_score_by_id .get (context .attacker_id ,0.0 )),
    "commit_window":float (commit_window ),
    "takeover_threshold":float (takeover_threshold ),
    "takeover_bias":float (human_style .takeover_bias ),
    "should_attack":False ,
    "maneuver":"",
    "reason":"",
    }

    def finalize (maneuver ,reason :str ,**extra ):
        trace ["maneuver"]=type (maneuver ).__name__ 
        trace ["reason"]=reason 
        if extra :
            trace .update (extra )
        if decision_memory is not None :
            decision_memory .set_teamplay_trace (trace )
        return maneuver 

    low_boost_threshold =compute_low_boost_threshold (
    skill_overall =skill .overall ,
    mistake_rate =human_style .mistake_rate ,
    decisiveness =human_style .decisiveness ,
    base =12 ,
    overall_scale =14 ,
    mistake_scale =6 ,
    decisiveness_scale =4 ,
    min_value =8 ,
    max_value =34 ,
    )
    trace ["low_boost_threshold"]=int (low_boost_threshold )
    if (
    my_car .boost <low_boost_threshold 
    and my_role >0 
    and is_safe_to_detour_for_boost (info ,context ,my_car )
    ):
        best_boostpad =choose_boostpad_to_pickup (info ,my_car )
        if best_boostpad is not None :
            return finalize (
            PickupBoostPad (my_car ,best_boostpad ),
            "boost_detour_safe",
            boost_pad ={"x":float (best_boostpad .position [0 ]),"y":float (best_boostpad .position [1 ])},
            )

    if context .danger >0.86 and ground_distance (my_intercept ,my_goal )<4600 :
        if my_role <=1 or my_intercept .time <=context .attacker_intercept .time +0.10 :
            return finalize (defense .any_clear (info ,my_car ),"danger_forced_clear")

    should_attack =should_take_over_attack (
    info ,
    context ,
    my_car ,
    commit_window ,
    takeover_threshold =takeover_threshold ,
    takeover_bias =human_style .takeover_bias ,
    )
    trace ["should_attack"]=bool (should_attack )
    if should_attack :
        attack_alignment =align (my_intercept .car .position ,my_intercept .ball ,their_goal )
        opportunity_score =context .opportunity_score_by_id .get (my_car .id ,0.0 )
        alignment_threshold =-0.30 +aggression *0.34 -human_style .mistake_rate *0.05 
        trace ["attack_alignment"]=float (attack_alignment )
        trace ["alignment_threshold"]=float (alignment_threshold )
        if (
        attack_alignment >alignment_threshold 
        or ground_distance (my_intercept ,my_goal )>5600 
        or context .time_advantage >0.18 
        or opportunity_score >takeover_threshold +0.05 
        ):
            return finalize (
            offense .any_shot (
            info ,
            my_intercept .car ,
            their_goal ,
            my_intercept ,
            allow_dribble =not info .is_puck and mechanics >0.55 +human_style .mechanical_variance *0.18 ,
            ),
            "attack_takeover_shot",
            )
        return finalize (defense .any_clear (info ,my_intercept .car ),"attack_takeover_clear")


    if (
    my_role >=2 
    and context .danger >0.74 
    and my_intercept .time <context .attacker_intercept .time +commit_window 
    ):
        return finalize (defense .any_clear (info ,my_car ),"third_man_relief_clear")

    if (
    my_role ==1 
    and my_car .boost <35 
    and context .danger <0.45 
    and context .open_attack_window <0.60 
    and is_safe_to_detour_for_boost (info ,context ,my_car )
    ):
        best_boostpad =choose_boostpad_to_pickup (info ,my_car )
        if best_boostpad is not None :
            return finalize (
            PickupBoostPad (my_car ,best_boostpad ),
            "second_man_boost_detour",
            boost_pad ={"x":float (best_boostpad .position [0 ]),"y":float (best_boostpad .position [1 ])},
            )

    face_target =support_face_target (info ,context ,my_car )
    support_target_reused =False 
    if decision_memory is not None :
        cooldown =human_style .support_repath_cooldown 
        if (
        not decision_memory .can_repath_support (info .time ,cooldown )
        and decision_memory .last_support_target is not None 
        ):
            face_target =decision_memory .last_support_target 
            support_target_reused =True 
        else :
            decision_memory .remember_support_target (face_target ,info .time )
    support_distance =support_distance_for_role (info ,context ,my_car ,my_role )
    force_nearest =(
    my_role >=len (my_team )-1 
    and info .settings .teamplay .conservative_last_man 
    and context .danger >0.40 
    )
    return finalize (
    GeneralDefense (my_car ,info ,face_target ,support_distance ,force_nearest =force_nearest ),
    "support_shape_hold",
    support_target ={
    "x":float (face_target [0 ]),
    "y":float (face_target [1 ]),
    "z":float (face_target [2 ]),
    },
    support_distance =float (support_distance ),
    support_target_reused =support_target_reused ,
    force_nearest =force_nearest ,
    )
