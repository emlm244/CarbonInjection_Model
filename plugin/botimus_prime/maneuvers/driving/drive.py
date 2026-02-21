import math 

from maneuvers .maneuver import Maneuver 
from rlutilities .linear_algebra import vec3 ,dot ,norm 
from tools .arena import Arena 
from tools .drawing import DrawingTool 
from tools .math import abs_clamp ,clamp11 ,clamp 
from tools .vector_math import ground ,local ,ground_distance ,distance ,direction 


class Drive (Maneuver ):

    def __init__ (self ,car ,target_pos :vec3 =vec3 (0 ,0 ,0 ),target_speed :float =0 ,backwards :bool =False ):
        super ().__init__ (car )

        self .target_pos =target_pos 
        self .target_speed =target_speed 
        self .backwards =backwards 
        self .drive_on_walls =False 
        self .deadband_applied =False 

    def step (self ,dt ):
        target =self .target_pos 
        self .deadband_applied =False 


        target =Arena .clamp (target ,100 )


        if abs (self .car .position [1 ])>Arena .size [1 ]-50 and abs (self .car .position .x )<1000 :
            target =Arena .clamp (target ,200 )
            target [0 ]=abs_clamp (target [0 ],700 )

        if not self .drive_on_walls :
            seam_radius =100 if abs (self .car .position [1 ])>Arena .size [1 ]-100 else 200 
            if self .car .position [2 ]>seam_radius :
                target =ground (self .car )

        local_target =local (self .car ,target )

        if self .backwards :
            local_target [0 ]*=-1 
            local_target [1 ]*=-1 


        phi =math .atan2 (local_target [1 ],local_target [0 ])
        self .controls .steer =clamp11 (2.5 *phi )


        self .controls .handbrake =False 
        forward_alignment =1.0 
        car_speed =norm (self .car .velocity )
        if car_speed >1 :
            forward_alignment =dot (self .car .velocity /car_speed ,self .car .forward ())
        if (
        abs (phi )>1.5 
        and self .car .position [2 ]<300 
        and (ground_distance (self .car ,target )<3500 or abs (self .car .position [0 ])>3500 )
        and forward_alignment >0.85 
        ):
            self .controls .handbrake =True 


        vf =dot (self .car .velocity ,self .car .forward ())
        if self .backwards :
            vf *=-1 


        speed_error =self .target_speed -vf 
        if (
        abs (speed_error )<90 
        and abs (phi )<0.35 
        and self .target_speed <1300 
        ):
            self .deadband_applied =True 
            self .controls .throttle =0.0 if self .target_speed <200 else 0.15 
            self .controls .boost =False 
        elif vf <self .target_speed :
            self .controls .throttle =1.0 
            if self .target_speed >1400 and vf <2250 and speed_error >50 :
                self .controls .boost =True 
            else :
                self .controls .boost =False 
        else :
            if (vf -self .target_speed )>400 :
                self .controls .throttle =-1.0 
            elif (vf -self .target_speed )>100 :
                if self .car .up ()[2 ]>0.85 :
                    self .controls .throttle =0.0 
                else :
                    self .controls .throttle =0.01 
            self .controls .boost =False 


        if self .backwards :
            self .controls .throttle *=-1 
            self .controls .steer *=-1 
            self .controls .boost =False 
            self .controls .handbrake =False 


        if abs (phi )>0.3 :
            self .controls .boost =False 


        if distance (self .car ,self .target_pos )<100 :
            self .finished =True 

    @staticmethod 
    def turn_radius (speed :float )->float :
        spd =clamp (speed ,0 ,2300 )
        return 156 +0.1 *spd +0.000069 *spd **2 +0.000000164 *spd **3 +-5.62E-11 *spd **4 

    def render (self ,draw :DrawingTool ):
        draw .color (draw .cyan )
        draw .square (self .target_pos ,50 )

        target_direction =direction (self .car .position ,self .target_pos )
        draw .triangle (self .car .position +target_direction *200 ,target_direction ,up =self .car .up ())
