from __future__ import annotations 

from dataclasses import dataclass 
from typing import List ,Sequence 

from rlutilities .linear_algebra import vec3 
from rlutilities .simulation import BoostPadState 

from tools .game_info import GameInfo 




SOCCAR_BOOST_PAD_COORDS :Sequence [tuple [float ,float ,float ]]=(
(0.0 ,-4240.0 ,70.0 ),
(-1792.0 ,-4184.0 ,70.0 ),
(1792.0 ,-4184.0 ,70.0 ),
(-3072.0 ,-4096.0 ,73.0 ),
(3072.0 ,-4096.0 ,73.0 ),
(-940.0 ,-3308.0 ,70.0 ),
(940.0 ,-3308.0 ,70.0 ),
(0.0 ,-2816.0 ,70.0 ),
(-3584.0 ,-2484.0 ,70.0 ),
(3584.0 ,-2484.0 ,70.0 ),
(-1788.0 ,-2300.0 ,70.0 ),
(1788.0 ,-2300.0 ,70.0 ),
(-2048.0 ,-1036.0 ,70.0 ),
(0.0 ,-1024.0 ,70.0 ),
(2048.0 ,-1036.0 ,70.0 ),
(-3584.0 ,0.0 ,73.0 ),
(-1024.0 ,0.0 ,70.0 ),
(1024.0 ,0.0 ,70.0 ),
(3584.0 ,0.0 ,73.0 ),
(-2048.0 ,1036.0 ,70.0 ),
(0.0 ,1024.0 ,70.0 ),
(2048.0 ,1036.0 ,70.0 ),
(-1788.0 ,2300.0 ,70.0 ),
(1788.0 ,2300.0 ,70.0 ),
(-3584.0 ,2484.0 ,70.0 ),
(3584.0 ,2484.0 ,70.0 ),
(0.0 ,2816.0 ,70.0 ),
(-940.0 ,3310.0 ,70.0 ),
(940.0 ,3308.0 ,70.0 ),
(-3072.0 ,4096.0 ,73.0 ),
(3072.0 ,4096.0 ,73.0 ),
(-1792.0 ,4184.0 ,70.0 ),
(1792.0 ,4184.0 ,70.0 ),
(0.0 ,4240.0 ,70.0 ),
)

SOCCAR_LARGE_PAD_INDICES ={3 ,4 ,15 ,18 ,29 ,30 }


@dataclass (eq =False )
class FallbackBoostPad :
    index :int 
    position :vec3 
    is_large :bool 
    timer :float =0.0 
    state :BoostPadState =BoostPadState .Available 


class FieldInfoProvider :
    def __init__ (self ):
        self .using_fallback =False 
        self ._pads :List [FallbackBoostPad ]=[]

    def initialize_game_info (self ,info :GameInfo ,field_info )->bool :
        if field_info is not None :
            try :
                info .read_field_info (field_info )
                self .using_fallback =False 
                self ._pads =[]
                return True 
            except Exception :
                pass 

        self .install_soccar_fallback (info )
        return False 

    def install_soccar_fallback (self ,info :GameInfo ):
        pads :List [FallbackBoostPad ]=[]
        for index ,(x ,y ,z )in enumerate (SOCCAR_BOOST_PAD_COORDS ):
            pads .append (
            FallbackBoostPad (
            index =index ,
            position =vec3 (x ,y ,z ),
            is_large =index in SOCCAR_LARGE_PAD_INDICES ,
            )
            )

        self ._pads =pads 
        info .large_boost_pads =[pad for pad in pads if pad .is_large ]
        info .small_boost_pads =[pad for pad in pads if not pad .is_large ]
        self .using_fallback =True 

    def update_boostpad_states (self ,packet ):
        if not self .using_fallback or not self ._pads :
            return 

        boosts =getattr (packet ,"game_boosts",None )
        if boosts is None :
            return 

        num_boosts =getattr (packet ,"num_boost",None )
        if num_boosts is None :
            num_boosts =getattr (packet ,"num_boosts",None )
        if num_boosts is None :
            try :
                num_boosts =len (boosts )
            except TypeError :
                return 

        pad_count =min (int (num_boosts ),len (self ._pads ))
        for i in range (pad_count ):
            packet_boost =boosts [i ]
            is_active =bool (getattr (packet_boost ,"is_active",True ))
            timer =float (getattr (packet_boost ,"timer",0.0 ))

            pad =self ._pads [i ]
            pad .state =BoostPadState .Available if is_active else BoostPadState .Unavailable 
            pad .timer =0.0 if is_active else max (0.0 ,timer )
