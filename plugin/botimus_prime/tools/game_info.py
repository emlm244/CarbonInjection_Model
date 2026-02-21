from __future__ import annotations 

import math 
import os 
import ctypes 
from typing import TYPE_CHECKING ,Any ,Dict ,List ,Optional ,Tuple 

if TYPE_CHECKING :
    from rlbot .utils .structures .game_data_struct import GameTickPacket ,FieldInfoPacket 
else :
    GameTickPacket =Any 
    FieldInfoPacket =Any 

from rlutilities .linear_algebra import vec3 ,vec2 ,norm ,normalize ,cross ,rotation ,dot ,xy ,mat3 
from rlutilities .simulation import Game ,Car ,Ball ,BoostPad ,BoostPadType 
from tools .bot_settings import BotSettings ,default_settings 
from tools .math import clamp01 
from tools .vector_math import distance 


class Goal :

    WIDTH =1784.0 
    HEIGHT =640.0 
    DISTANCE =5120.0 

    def __init__ (self ,team ):
        self .sign =1 -2 *team 
        self .l_post =vec3 (self .sign *Goal .WIDTH /2 ,-self .sign *Goal .DISTANCE ,0 )
        self .r_post =vec3 (-self .sign *Goal .WIDTH /2 ,-self .sign *Goal .DISTANCE ,0 )
        self .team =team 

    def inside (self ,pos )->bool :
        return pos [1 ]<-Goal .DISTANCE if self .team ==0 else pos [1 ]>Goal .DISTANCE 

    @property 
    def center (self ):
        return vec3 (0 ,-self .sign *Goal .DISTANCE ,Goal .HEIGHT /2.0 )


class GameInfo (Game ):

    def __init__ (self ,team ,settings :Optional [BotSettings ]=None ):
        super ().__init__ ()
        self .team =team 
        self .my_goal =Goal (team )
        self .their_goal =Goal (1 -team )
        self .settings =settings or default_settings ()

        self .ball_predictions :List [Ball ]=[]
        self .about_to_score =False 
        self .about_to_be_scored_on =False 
        self .time_of_goal =-1 
        self ._prediction_time =-1.0 
        self ._prediction_duration =0.0 
        self ._prediction_dt =0.0 
        self ._external_ball_prediction =None 

        self .large_boost_pads :List [BoostPad ]=[]
        self .small_boost_pads :List [BoostPad ]=[]

        self .car_names :Dict [int ,str ]={}
        self .car_is_bot :Dict [int ,bool ]={}
        self ._human_aggression :Dict [int ,float ]={}

        self .object_mode ="ball"
        self .object_rest_height =self .settings .object_mode .ball_rest_height 
        self .object_ground_cutoff =self .settings .object_mode .ball_ground_cutoff 
        self .object_render_radius =self .settings .object_mode .ball_render_radius 
        self .packet_read_mode =os .environ .get ("BOTIMUS_PACKET_READ_MODE","auto").strip ().lower ()

    def read_field_info (self ,field_info :FieldInfoPacket ):
        super ().read_field_info (field_info )
        self .large_boost_pads =[pad for pad in self .pads if pad .type ==BoostPadType .Full ]
        self .small_boost_pads =[pad for pad in self .pads if pad .type ==BoostPadType .Partial ]

    def apply_settings (self ,settings :BotSettings ):
        self .settings =settings 
        if settings .object_mode .mode in {"ball","puck"}:
            self ._set_object_mode (settings .object_mode .mode )

    def read_packet (self ,packet :GameTickPacket ):
        if self ._should_use_native_packet_reader (packet ):
            super ().read_packet (packet )
        else :
            self ._read_packet_compat (packet )


        for pad in self .large_boost_pads :
            pad .timer =10.0 -pad .timer 
        for pad in self .small_boost_pads :
            pad .timer =4.0 -pad .timer 

        self ._prediction_time =-1.0 

        car_count =getattr (packet ,"num_cars",len (self .cars ))
        for i in range (car_count ):
            packet_car =packet .game_cars [i ]
            self .car_names [i ]=packet_car .name 
            self .car_is_bot [i ]=bool (getattr (packet_car ,"is_bot",True ))

        self ._update_object_mode (packet )
        self ._update_human_aggression ()

    def _should_use_native_packet_reader (self ,packet :GameTickPacket )->bool :
        mode =self .packet_read_mode 
        if mode =="native":
            return True 
        if mode =="compat":
            return False 

        packet_type =type (packet )
        module =getattr (packet_type ,"__module__","")
        if module .startswith ("rlbot."):
            return True 

        try :
            if isinstance (packet ,ctypes .Structure ):
                return True 
        except Exception :
            pass 

        return False 

    def _read_packet_compat (self ,packet :GameTickPacket ):
        prev_time =float (getattr (self ,"time",0.0 ))
        game_info =getattr (packet ,"game_info",None )
        seconds_elapsed =getattr (game_info ,"seconds_elapsed",None )

        if seconds_elapsed is None :
            now =prev_time +(1 /120 )
        else :
            now =float (seconds_elapsed )

        dt =now -prev_time if prev_time >0 else (1 /120 )
        self .time_delta =max (1 /240 ,min (0.1 ,dt ))
        self .time =now 

        if not isinstance (getattr (self ,"ball",None ),Ball ):
            self .ball =Ball ()

        packet_ball =getattr (packet ,"game_ball",None )
        ball_physics =getattr (packet_ball ,"physics",None )
        if ball_physics is not None :
            self .ball .position =self ._vec3_from_packet_obj (getattr (ball_physics ,"location",None ))
            self .ball .velocity =self ._vec3_from_packet_obj (getattr (ball_physics ,"velocity",None ))
            self .ball .angular_velocity =self ._vec3_from_packet_obj (getattr (ball_physics ,"angular_velocity",None ))
        self .ball .time =self .time 

        packet_cars =getattr (packet ,"game_cars",[])
        num_cars =getattr (packet ,"num_cars",None )
        if num_cars is None :
            try :
                num_cars =len (packet_cars )
            except TypeError :
                num_cars =0 
        num_cars =max (0 ,int (num_cars ))

        if len (self .cars )!=num_cars :
            self .cars =[Car ()for _ in range (num_cars )]

        for i in range (num_cars ):
            try :
                packet_car =packet_cars [i ]
            except Exception :
                break 

            car =self .cars [i ]
            car .id =i 
            car .team =int (getattr (packet_car ,"team",0 ))

            physics =getattr (packet_car ,"physics",None )
            if physics is not None :
                car .position =self ._vec3_from_packet_obj (getattr (physics ,"location",None ))
                car .velocity =self ._vec3_from_packet_obj (getattr (physics ,"velocity",None ))
                car .angular_velocity =self ._vec3_from_packet_obj (getattr (physics ,"angular_velocity",None ))
                rotation_obj =getattr (physics ,"rotation",None )
                if rotation_obj is not None :
                    car .orientation =self ._mat3_from_packet_rotation (rotation_obj )

            boost_value =float (getattr (packet_car ,"boost",0.0 ))
            car .boost =max (0 ,min (100 ,int (round (boost_value ))))
            car .on_ground =bool (getattr (packet_car ,"has_wheel_contact",False ))
            car .supersonic =bool (getattr (packet_car ,"is_super_sonic",False ))
            car .jumped =bool (getattr (packet_car ,"jumped",False ))
            car .double_jumped =bool (getattr (packet_car ,"double_jumped",False ))
            car .demolished =bool (getattr (packet_car ,"is_demolished",False ))
            car .time =self .time 

    def set_external_ball_prediction (self ,prediction ):
        self ._external_ball_prediction =prediction 

    def get_teammates (self ,my_car :Car )->List [Car ]:
        return [car for car in self .cars if car .team ==self .team and car .id !=my_car .id ]

    def get_opponents (self )->List [Car ]:
        return [car for car in self .cars if car .team !=self .team ]

    def get_human_teammates (self ,my_car :Car )->List [Car ]:
        return [car for car in self .get_teammates (my_car )if not self .car_is_bot .get (car .id ,True )]

    def get_human_aggression (self ,car :Car )->float :
        return self ._human_aggression .get (car .id ,0.5 )

    def get_team_human_aggression (self ,my_car :Car )->float :
        humans =self .get_human_teammates (my_car )
        if not humans :
            return 0.5 
        return sum (self .get_human_aggression (car )for car in humans )/len (humans )

    def get_primary_human_teammate (self ,my_car :Car )->Optional [Car ]:
        humans =self .get_human_teammates (my_car )
        if not humans :
            return None 
        return max (
        humans ,
        key =lambda car :self .get_human_aggression (car )
        +clamp01 ((3200 -distance (car ,self .ball ))/3200 )*0.35 ,
        )

    @property 
    def is_puck (self )->bool :
        return self .object_mode =="puck"

    def predict_ball (self ,duration =5.0 ,dt =1 /120 ):
        if (
        self ._prediction_time ==self .time 
        and self ._prediction_duration >=duration 
        and self ._prediction_dt <=dt 
        and self .ball_predictions 
        ):
            return 

        self ._prediction_time =self .time 
        self ._prediction_duration =duration 
        self ._prediction_dt =dt 

        self .about_to_score =False 
        self .about_to_be_scored_on =False 
        self .time_of_goal =-1 

        self .ball_predictions =[]
        if self ._should_use_external_prediction ()and self ._predict_ball_external (duration ,dt ):
            return 

        self ._predict_ball_internal (duration ,dt )

    def _should_use_external_prediction (self )->bool :
        if self ._external_ball_prediction is None :
            return False 
        if self .is_puck :
            return self .settings .object_mode .use_rlbot_prediction_for_puck 
        return self .settings .object_mode .use_rlbot_prediction_for_ball 

    def _predict_ball_internal (self ,duration =5.0 ,dt =1 /120 ):
        prediction =Ball (self .ball )

        while prediction .time <self .time +duration :
            prediction .step (dt )
            self ._add_prediction_slice (Ball (prediction ))

    @staticmethod 
    def _vec3_from_packet_obj (packet_vector )->vec3 :
        if packet_vector is None :
            return vec3 (0.0 ,0.0 ,0.0 )
        x =getattr (packet_vector ,"x",getattr (packet_vector ,"X",0.0 ))
        y =getattr (packet_vector ,"y",getattr (packet_vector ,"Y",0.0 ))
        z =getattr (packet_vector ,"z",getattr (packet_vector ,"Z",0.0 ))
        return vec3 (x ,y ,z )

    @staticmethod 
    def _mat3_from_packet_rotation (rotation_obj )->mat3 :
        pitch =float (getattr (rotation_obj ,"pitch",0.0 ))
        yaw =float (getattr (rotation_obj ,"yaw",0.0 ))
        roll =float (getattr (rotation_obj ,"roll",0.0 ))

        cp =math .cos (pitch )
        sp =math .sin (pitch )
        cy =math .cos (yaw )
        sy =math .sin (yaw )
        cr =math .cos (roll )
        sr =math .sin (roll )

        forward =vec3 (cp *cy ,cp *sy ,sp )
        left =vec3 (cr *sy -cy *sp *sr ,-cr *cy -sy *sp *sr ,cp *sr )
        up =vec3 (-cr *cy *sp -sr *sy ,-cr *sy *sp +sr *cy ,cp *cr )
        return mat3 (
        forward [0 ],left [0 ],up [0 ],
        forward [1 ],left [1 ],up [1 ],
        forward [2 ],left [2 ],up [2 ],
        )

    def _predict_ball_external (self ,duration :float ,dt :float )->bool :
        prediction =self ._external_ball_prediction 
        slices =getattr (prediction ,"slices",None )
        if slices is None :
            return False 

        num_slices =int (getattr (prediction ,"num_slices",0 )or 0 )
        if num_slices <=0 :
            try :
                num_slices =len (slices )
            except TypeError :
                return False 

        if num_slices <=0 :
            return False 

        step =max (1 ,int (round (dt /(1 /60 ))))
        start_time =self .time +1e-4 
        end_time =self .time +duration 

        for i in range (0 ,num_slices ,step ):
            prediction_slice =slices [i ]
            prediction_time =float (getattr (prediction_slice ,"game_seconds",-1.0 ))
            if prediction_time <start_time :
                continue 
            if prediction_time >end_time :
                break 

            try :
                physics =prediction_slice .physics 
                ball =Ball (self .ball )
                ball .time =prediction_time 
                ball .position =self ._vec3_from_packet_obj (physics .location )
                ball .velocity =self ._vec3_from_packet_obj (physics .velocity )
                ball .angular_velocity =self ._vec3_from_packet_obj (physics .angular_velocity )
                self ._add_prediction_slice (ball )
            except AttributeError :
                continue 

        return bool (self .ball_predictions )

    def _add_prediction_slice (self ,ball :Ball ):
        self .ball_predictions .append (ball )

        if self .time_of_goal ==-1 :
            if self .my_goal .inside (ball .position ):
                self .about_to_be_scored_on =True 
                self .time_of_goal =ball .time 
            if self .their_goal .inside (ball .position ):
                self .about_to_score =True 
                self .time_of_goal =ball .time 

    @staticmethod 
    def predict_car_drive (car :Car ,time_limit =2.0 ,dt =1 /60 )->List [vec3 ]:
        """Simple prediction of a driving car assuming no acceleration."""
        time_steps =int (time_limit /dt )
        speed =norm (car .velocity )
        ang_vel_z =car .angular_velocity [2 ]


        if ang_vel_z !=0 and car .on_ground :
            radius =speed /ang_vel_z 
            centre =car .position -cross (normalize (xy (car .velocity )),vec3 (0 ,0 ,1 ))*radius 
            centre_to_car =vec2 (car .position -centre )
            return [
            vec3 (dot (rotation (ang_vel_z *dt *i ),centre_to_car ))+centre 
            for i in range (time_steps )]


        return [car .position +car .velocity *dt *i for i in range (time_steps )]

    COLLISION_THRESHOLD =150 

    def detect_collisions (self ,time_limit =0.5 ,dt =1 /60 )->List [Tuple [int ,int ,float ]]:
        """Returns a list of tuples, where the first two elements are
        indices of cars and the last is time from now until the collision.
        """
        time_steps =int (time_limit /dt )
        predictions =[self .predict_car_drive (car ,time_limit =time_limit ,dt =dt )for car in self .cars ]
        collisions =[]
        for i in range (len (self .cars )):
            for j in range (len (self .cars )):
                if i >=j :
                    continue 

                for step in range (time_steps ):
                    pos1 =predictions [i ][step ]
                    pos2 =predictions [j ][step ]
                    if distance (pos1 ,pos2 )<self .COLLISION_THRESHOLD :
                        collisions .append ((i ,j ,step *dt ))
                        break 

        return collisions 

    def _update_object_mode (self ,packet :GameTickPacket ):
        preference =self .settings .object_mode .mode 
        if preference in {"ball","puck"}:
            self ._set_object_mode (preference )
            return 

        game_info =getattr (packet ,"game_info",None )
        game_mode =getattr (game_info ,"game_mode",None )
        if isinstance (game_mode ,str ):
            lower =game_mode .lower ()
            if any (keyword in lower for keyword in ("hockey","snow","puck")):
                self ._set_object_mode ("puck")
                return 
        elif isinstance (game_mode ,int ):
            if game_mode in {3 ,4 }:
                self ._set_object_mode ("puck")
                return 

        ball_z =float (packet .game_ball .physics .location .z )
        self ._set_object_mode ("puck"if ball_z <80 else "ball")

    def _set_object_mode (self ,mode :str ):
        self .object_mode =mode 
        if mode =="puck":
            self .object_rest_height =self .settings .object_mode .puck_rest_height 
            self .object_ground_cutoff =self .settings .object_mode .puck_ground_cutoff 
            self .object_render_radius =self .settings .object_mode .puck_render_radius 
        else :
            self .object_rest_height =self .settings .object_mode .ball_rest_height 
            self .object_ground_cutoff =self .settings .object_mode .ball_ground_cutoff 
            self .object_render_radius =self .settings .object_mode .ball_render_radius 

    def _update_human_aggression (self ):
        attack_sign =1.0 if self .team ==0 else -1.0 
        active_humans =set ()

        for car in self .cars :
            if car .team !=self .team or self .car_is_bot .get (car .id ,True ):
                continue 

            active_humans .add (car .id )
            ahead_of_ball =clamp01 ((attack_sign *(car .position [1 ]-self .ball .position [1 ])+900 )/2800 )
            close_to_ball =clamp01 ((3400 -distance (car ,self .ball ))/3400 )
            speed_forward =clamp01 ((attack_sign *car .velocity [1 ]+300 )/2000 )
            sample =ahead_of_ball *0.45 +close_to_ball *0.35 +speed_forward *0.20 

            previous =self ._human_aggression .get (car .id ,0.5 )
            self ._human_aggression [car .id ]=previous *0.96 +sample *0.04 

        stale_ids =[car_id for car_id in self ._human_aggression if car_id not in active_humans ]
        for car_id in stale_ids :
            del self ._human_aggression [car_id ]
