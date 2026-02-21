import math 
from typing import Callable ,Optional ,Sequence 

from data .acceleration_lut import BOOST ,THROTTLE 
from rlutilities .linear_algebra import angle_between ,dot ,norm 
from rlutilities .mechanics import Drive 
from rlutilities .simulation import Car ,Ball 

from tools .vector_math import direction ,ground ,ground_distance 


class Intercept :
    def __init__ (
    self ,
    car :Car ,
    ball_predictions :Sequence [Ball ],
    predicate :Optional [Callable [[Car ,Ball ],bool ]]=None ,
    ignore_time_estimate :bool =False ,
    backwards :bool =False ,
    ):
        self .ball :Ball =Ball ()
        self .ball .time =math .inf 
        self .car :Car =car 
        self .is_viable :bool =True 
        self .predicate_later_than_time :bool =False 
        found_ball =False 

        for i in range (0 ,len (ball_predictions ),3 ):
            ball =ball_predictions [i ]
            time =estimate_time (car ,ball .position ,-1 if backwards else 1 )
            if time <ball .time -car .time or ignore_time_estimate :
                if predicate is None or predicate (car ,ball ):
                    self .ball =ball 
                    found_ball =True 
                    break 
                self .predicate_later_than_time =True 
            else :
                self .predicate_later_than_time =False 


        if not found_ball :
            if ball_predictions :
                self .ball =ball_predictions [-1 ]
            self .is_viable =False 
        self .time =self .ball .time 
        self .ground_pos =ground (self .ball .position )
        self .position =self .ball .position 


def estimate_time (car :Car ,target ,dd :int =1 )->float :
    turning_radius =1 /Drive .max_turning_curvature (norm (car .velocity )+500 )
    turning =angle_between (car .forward ()*dd ,direction (car ,target ))*turning_radius /1800 
    if turning <0.5 :
        turning =0 

    dist =ground_distance (car ,target )-200 
    if dist <0 :
        return turning 
    speed =dot (car .velocity ,car .forward ())*dd 
    if speed <=1 :
        speed =max (norm (car .velocity ),600.0 )

    time =0 
    result =None 
    if car .boost >0 and dd >0 :
        boost_time =car .boost /33.33 
        result =BOOST .simulate_until_limit (speed ,distance_limit =dist ,time_limit =boost_time )
        dist -=result .distance_traveled 
        time +=result .time_passed 
        speed =result .speed_reached 

    if dist >0 and speed <1410 :
        result =THROTTLE .simulate_until_limit (speed ,distance_limit =dist )
        dist -=result .distance_traveled 
        time +=result .time_passed 
        speed =result .speed_reached 

    if result is None or not result .distance_limit_reached :
        time +=dist /max (speed ,1.0 )

    return time *1.05 +turning 
