from typing import Optional ,Set 

from rlutilities .simulation import Car ,BoostPad ,BoostPadState 
from tools .game_info import GameInfo 
from tools .intercept import estimate_time 
from tools .vector_math import distance 


def choose_boostpad_to_pickup (
info :GameInfo ,
car :Car ,
forbidden_pads :Optional [Set [BoostPad ]]=None ,
)->Optional [BoostPad ]:
    if forbidden_pads is None :
        forbidden_pads =set ()


    active_pads ={pad for pad in info .large_boost_pads if pad .state ==BoostPadState .Available }
    soon_active_pads ={pad for pad in info .large_boost_pads if estimate_time (car ,pad .position )*0.7 >pad .timer }

    valid_pads =active_pads |soon_active_pads -forbidden_pads 
    if not valid_pads :
        return None 



    pos =(info .ball .position +car .position *2 +info .my_goal .center *2 )/5 


    return min (valid_pads ,key =lambda pad :distance (pad .position ,pos ))


def compute_low_boost_threshold (
*,
skill_overall :float ,
mistake_rate :float ,
decisiveness :float ,
base :float ,
overall_scale :float ,
mistake_scale :float ,
decisiveness_scale :float ,
min_value :int ,
max_value :int ,
)->int :
    threshold =int (
    base 
    +(1.0 -skill_overall )*overall_scale 
    +mistake_rate *mistake_scale 
    -decisiveness *decisiveness_scale 
    )
    return max (min_value ,min (max_value ,threshold ))
