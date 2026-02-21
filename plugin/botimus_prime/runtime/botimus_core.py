from __future__ import annotations 

import math 
from typing import TYPE_CHECKING ,Any ,Callable ,Optional 

try :
    from rlbot .agents .base_agent import SimpleControllerState 
except ModuleNotFoundError :
    class SimpleControllerState :
        def __init__ (
        self ,
        steer =0.0 ,
        throttle =0.0 ,
        pitch =0.0 ,
        yaw =0.0 ,
        roll =0.0 ,
        jump =False ,
        boost =False ,
        handbrake =False ,
        use_item =False ,
        ):
            self .steer =steer 
            self .throttle =throttle 
            self .pitch =pitch 
            self .yaw =yaw 
            self .roll =roll 
            self .jump =jump 
            self .boost =boost 
            self .handbrake =handbrake 
            self .use_item =use_item 

from maneuvers .general_defense import GeneralDefense 
from maneuvers .kickoffs .kickoff import Kickoff 
from maneuvers .maneuver import Maneuver 
from maneuvers .pickup_boostpad import PickupBoostPad 
from maneuvers .strikes .strike import Strike 
from rlutilities .linear_algebra import vec3 
from strategy import solo_strategy ,teamplay_strategy 
from tools .bot_settings import BotSettingsManager 
from tools .decision_memory import DecisionMemory 
from tools .diagnostics_logger import MatchDiagnosticsLogger 
from tools .game_info import GameInfo 
from tools .math import clamp01 
from tools .vector_math import ground_distance 

from runtime .field_info_provider import FieldInfoProvider 

if TYPE_CHECKING :
    from tools .drawing import DrawingTool 


class BotimusCore :
    def __init__ (
    self ,
    *,
    name :str ,
    team :int ,
    index :int ,
    enable_rendering :bool =True ,
    logger :Optional [Callable [[str ],None ]]=None ,
    ):
        self .name =name 
        self .team =team 
        self .index =index 
        self .RENDERING =bool (enable_rendering )
        self ._logger =logger 

        self .info :Optional [GameInfo ]=None 
        self .draw :Optional ["DrawingTool"]=None 

        self .tick_counter =0 
        self .last_latest_touch_time =0.0 

        self .maneuver :Optional [Maneuver ]=None 
        self .controls :SimpleControllerState =SimpleControllerState ()
        self .settings_manager :Optional [BotSettingsManager ]=None 
        self .decision_memory :DecisionMemory =DecisionMemory ()
        self .diagnostics :Optional [MatchDiagnosticsLogger ]=None 
        self ._diag_signature :Optional [tuple ]=None 
        self ._diag_last_trace_time =-999.0 
        self ._diag_prev_role_label :Optional [str ]=None 
        self ._diag_prev_role_time =-999.0 
        self ._diag_recent_role_thrash =False 
        self ._diag_counters =self ._new_diag_counters ()
        self ._last_num_cars =0 

        self .field_info_provider =FieldInfoProvider ()
        self ._fallback_notice_logged =False 

    def initialize (self ,field_info =None ,renderer =None ):
        self .settings_manager =BotSettingsManager ()
        self .info =GameInfo (self .team ,settings =self .settings_manager .settings )
        self .info .set_mode ("soccar")

        initialized_with_field_info =self .field_info_provider .initialize_game_info (self .info ,field_info )
        if not initialized_with_field_info and not self ._fallback_notice_logged :
            self ._fallback_notice_logged =True 
            self ._log ("FieldInfo unavailable; using fallback soccar boost pad layout.")

        if renderer is not None and self .RENDERING :
            from tools .drawing import DrawingTool 

            self .draw =DrawingTool (renderer ,self .team )
        else :
            self .draw =None 

        self .decision_memory .reset ()
        self ._sync_diagnostics_logger (force =True )

    def tick (self ,packet :Any ,external_ball_prediction =None )->SimpleControllerState :
        if self .info is None :
            self .initialize ()


        if self .tick_counter <20 :
            self .tick_counter +=1 
            return self .controls 

        game_info =getattr (packet ,"game_info",None )
        seconds_elapsed =float (getattr (game_info ,"seconds_elapsed",self .info .time ))
        self .info .apply_settings (self .settings_manager .maybe_reload (seconds_elapsed ))
        self ._sync_diagnostics_logger ()
        self .info .read_packet (packet )
        self .field_info_provider .update_boostpad_states (packet )
        self ._last_num_cars =int (getattr (packet ,"num_cars",len (self .info .cars )))
        self .info .set_external_ball_prediction (external_ball_prediction )


        if bool (getattr (game_info ,"is_kickoff_pause",False ))and not isinstance (self .maneuver ,Kickoff ):
            self .maneuver =None 
            self .decision_memory .reset ()
            self ._diag_prev_role_label =None 
            self ._diag_prev_role_time =self .info .time 


        touch =getattr (getattr (packet ,"game_ball",None ),"latest_touch",None )
        if touch is not None :
            touch_time =float (getattr (touch ,"time_seconds",-1.0 ))
            my_name =None 
            packet_cars =getattr (packet ,"game_cars",[])
            if self .index <len (packet_cars ):
                my_name =getattr (packet_cars [self .index ],"name",None )

            if touch_time >self .last_latest_touch_time and getattr (touch ,"player_name",None )!=my_name :
                self .last_latest_touch_time =touch_time 


                if self .maneuver and self .maneuver .interruptible ():
                    should_cancel =True 
                    locked =self .decision_memory .is_action_locked (self .info .time )
                    if locked :
                        resist =self .info .settings .human_style .touch_reset_resist 
                        emergency_danger =0.72 +(1.0 -resist )*0.16 
                        should_cancel =self ._estimate_own_goal_danger ()>=emergency_danger 
                    if should_cancel :
                        self .maneuver =None 
                        if locked :
                            self ._diag_counters ["touch_resets_forced_by_emergency"]+=1 
                    elif locked :
                        self ._diag_counters ["touch_resets_blocked_by_lock"]+=1 

        if self .index >=len (self .info .cars ):
            return self .controls 


        if self .maneuver is None :
            if self .RENDERING and self .draw is not None :
                self .draw .clear ()

            car =self .info .cars [self .index ]
            if self .info .get_teammates (car ):
                self .maneuver =teamplay_strategy .choose_maneuver (
                self .info ,
                car ,
                self .decision_memory ,
                )
            else :
                self .maneuver =solo_strategy .choose_maneuver (
                self .info ,
                car ,
                self .decision_memory ,
                )

            if self .maneuver is not None :
                self ._lock_from_maneuver (self .maneuver )
                self ._update_diagnostics_counters_from_trace (self .decision_memory .last_teamplay_trace )


        if self .maneuver is not None :
            self .maneuver .step (self .info .time_delta )
            self .controls =self .maneuver .controls 

            if self .RENDERING and self .draw is not None :
                self .draw .group ("maneuver")
                self .draw .color (self .draw .yellow )
                self .draw .string (self .info .cars [self .index ].position +vec3 (0 ,0 ,50 ),type (self .maneuver ).__name__ )
                self .maneuver .render (self .draw )


            if self .maneuver .finished :
                self .maneuver =None 

        if self .RENDERING and self .draw is not None :
            self .draw .execute ()

        try :
            self ._log_tick ()
        except Exception as e :
            if self .diagnostics is not None :
                self .diagnostics .log_runtime_fault (
                {
                "source":"diagnostics_tick",
                "error":str (e ),
                }
                )

        return self .controls 

    def retire (self ):
        if self .diagnostics is None :
            return 
        seen =self ._diag_counters ["charge_opportunities_seen"]
        taken =self ._diag_counters ["charge_opportunities_taken"]
        charge_conversion =(taken /seen )if seen >0 else None 
        self .diagnostics .log_match_summary (
        game_time =float (getattr (self .info ,"time",0.0 )if self .info is not None else 0.0 ),
        mode =str (getattr (self .info ,"mode","soccar")if self .info is not None else "soccar"),
        team =self .team ,
        self_index =self .index ,
        payload ={
        "counters":dict (self ._diag_counters ),
        "charge_conversion":charge_conversion ,
        "settings":{
        "skill_preset":self .info .settings .skill .preset if self .info is not None else "unknown",
        },
        },
        )
        self .diagnostics .close ()

    def _log (self ,message :str ):
        if self ._logger is None :
            return 
        try :
            self ._logger (message )
        except Exception :
            pass 

    def _estimate_own_goal_danger (self )->float :
        my_goal_y =self .info .my_goal .center [1 ]
        goal_dist =abs (self .info .ball .position [1 ]-my_goal_y )
        goal_pressure =clamp01 ((4200 -goal_dist )/4200 )
        toward_goal_sign =-1.0 if self .team ==0 else 1.0 
        toward_goal_speed =toward_goal_sign *self .info .ball .velocity [1 ]
        speed_pressure =clamp01 ((toward_goal_speed +200 )/1800 )
        return clamp01 (goal_pressure *0.70 +speed_pressure *0.30 )

    def _lock_from_maneuver (self ,maneuver :Maneuver ):
        if isinstance (maneuver ,Kickoff ):
            return 

        human_style =self .info .settings .human_style 
        base_hold =human_style .commit_hold_time *(0.65 +0.35 *human_style .decisiveness )

        if isinstance (maneuver ,Strike ):
            duration =base_hold *1.20 
        elif isinstance (maneuver ,PickupBoostPad ):
            duration =base_hold *0.70 
        elif isinstance (maneuver ,GeneralDefense ):
            duration =base_hold *(0.70 +human_style .role_stability *0.20 )
        else :
            duration =base_hold *0.85 

        duration =max (0.10 ,min (1.25 ,duration ))
        self .decision_memory .lock_action (type (maneuver ).__name__ ,self .info .time ,duration )

    def _new_diag_counters (self )->dict [str ,int ]:
        return {
        "decisions_seen":0 ,
        "role_first_ticks":0 ,
        "role_second_ticks":0 ,
        "role_third_ticks":0 ,
        "role_switch_count":0 ,
        "role_thrash_count":0 ,
        "charge_opportunities_seen":0 ,
        "charge_opportunities_taken":0 ,
        "open_window_ignored_count":0 ,
        "support_repath_count":0 ,
        "touch_resets_blocked_by_lock":0 ,
        "touch_resets_forced_by_emergency":0 ,
        "hesitation_flag_count":0 ,
        }

    def _diag_signature_for_current_settings (self )->tuple :
        d =self .info .settings .diagnostics 
        return (
        d .enabled ,
        d .mode ,
        d .root_dir ,
        d .flush_every ,
        d .reset_on_start ,
        d .log_every_tick ,
        d .top_k_alternatives ,
        d .include_snapshots ,
        d .include_opponent_cars ,
        )

    def _sync_diagnostics_logger (self ,force :bool =False ):
        signature =self ._diag_signature_for_current_settings ()
        if not force and signature ==self ._diag_signature :
            return 

        if self .diagnostics is not None :
            self .diagnostics .close ()

        self .diagnostics =MatchDiagnosticsLogger (self .info .settings .diagnostics )
        self ._diag_signature =signature 
        self ._diag_last_trace_time =-999.0 
        self ._diag_prev_role_label =None 
        self ._diag_prev_role_time =-999.0 
        self ._diag_recent_role_thrash =False 
        self ._diag_counters =self ._new_diag_counters ()
        self ._log_boot_event ()

    def _log_boot_event (self ):
        if self .diagnostics is None :
            return 
        settings =self .info .settings 
        self .diagnostics .log_boot_event (
        {
        "bot_name":self .name ,
        "team":self .team ,
        "index":self .index ,
        "object_mode":settings .object_mode .mode ,
        "skill_preset":settings .skill .preset ,
        "human_style":{
        "decisiveness":settings .human_style .decisiveness ,
        "takeover_bias":settings .human_style .takeover_bias ,
        "role_stability":settings .human_style .role_stability ,
        "commit_hold_time":settings .human_style .commit_hold_time ,
        "touch_reset_resist":settings .human_style .touch_reset_resist ,
        "mistake_rate":settings .human_style .mistake_rate ,
        "mechanical_variance":settings .human_style .mechanical_variance ,
        },
        "diagnostics":{
        "mode":settings .diagnostics .mode ,
        "root_dir":settings .diagnostics .root_dir ,
        "include_snapshots":settings .diagnostics .include_snapshots ,
        "include_opponent_cars":settings .diagnostics .include_opponent_cars ,
        },
        }
        )

    @staticmethod 
    def _safe_float (value :Any ,fallback :float =0.0 )->float :
        try :
            return float (value )
        except (TypeError ,ValueError ):
            return fallback 

    @staticmethod 
    def _safe_bool (value :Any )->bool :
        return bool (value )

    @staticmethod 
    def _vec_payload (vec )->dict [str ,float ]:
        return {
        "x":float (vec [0 ]),
        "y":float (vec [1 ]),
        "z":float (vec [2 ]),
        }

    def _car_payload (self ,car )->dict [str ,Any ]:
        try :
            car_id =int (getattr (car ,"id",-1 ))
            team =int (getattr (car ,"team",-1 ))
            position =self ._vec_payload (car .position )
            velocity =self ._vec_payload (car .velocity )
            angular_velocity =self ._vec_payload (car .angular_velocity )
            boost =float (getattr (car ,"boost",0.0 ))
            on_ground =bool (getattr (car ,"on_ground",False ))
            demolished =bool (getattr (car ,"demolished",False ))
        except Exception :
            car_id =-1 
            team =-1 
            position ={"x":0.0 ,"y":0.0 ,"z":0.0 }
            velocity ={"x":0.0 ,"y":0.0 ,"z":0.0 }
            angular_velocity ={"x":0.0 ,"y":0.0 ,"z":0.0 }
            boost =0.0 
            on_ground =False 
            demolished =False 

        return {
        "id":car_id ,
        "name":self .info .car_names .get (car_id ,f"car_{car_id }"),
        "team":team ,
        "is_bot":self .info .car_is_bot .get (car_id ,True ),
        "position":position ,
        "velocity":velocity ,
        "angular_velocity":angular_velocity ,
        "boost":boost ,
        "on_ground":on_ground ,
        "demolished":demolished ,
        }

    def _controls_payload (self )->dict [str ,Any ]:
        return {
        "throttle":float (getattr (self .controls ,"throttle",0.0 )),
        "steer":float (getattr (self .controls ,"steer",0.0 )),
        "pitch":float (getattr (self .controls ,"pitch",0.0 )),
        "yaw":float (getattr (self .controls ,"yaw",0.0 )),
        "roll":float (getattr (self .controls ,"roll",0.0 )),
        "boost":self ._safe_bool (getattr (self .controls ,"boost",False )),
        "jump":self ._safe_bool (getattr (self .controls ,"jump",False )),
        "handbrake":self ._safe_bool (getattr (self .controls ,"handbrake",False )),
        }

    def _update_diagnostics_counters_from_trace (self ,trace :Optional [dict [str ,Any ]]):
        self ._diag_recent_role_thrash =False 
        if not trace :
            return 

        trace_time =self ._safe_float (trace .get ("time"),-1.0 )
        if trace_time <=self ._diag_last_trace_time +1e-6 :
            return 

        self ._diag_last_trace_time =trace_time 
        self ._diag_counters ["decisions_seen"]+=1 

        role_label =str (trace .get ("role_label",""))
        if role_label =="first_man":
            self ._diag_counters ["role_first_ticks"]+=1 
        elif role_label =="second_man":
            self ._diag_counters ["role_second_ticks"]+=1 
        elif role_label =="third_man":
            self ._diag_counters ["role_third_ticks"]+=1 

        if role_label :
            if self ._diag_prev_role_label is not None and role_label !=self ._diag_prev_role_label :
                self ._diag_counters ["role_switch_count"]+=1 
                if self .info .time -self ._diag_prev_role_time <0.55 :
                    self ._diag_recent_role_thrash =True 
                    self ._diag_counters ["role_thrash_count"]+=1 
            self ._diag_prev_role_label =role_label 
            self ._diag_prev_role_time =self .info .time 

        open_window =self ._safe_float (trace .get ("open_attack_window"),-1.0 )
        takeover_threshold =self ._safe_float (trace .get ("takeover_threshold"),1.0 )
        should_attack =self ._safe_bool (trace .get ("should_attack"))
        reason =str (trace .get ("reason",""))
        if open_window >=takeover_threshold >=0.0 :
            self ._diag_counters ["charge_opportunities_seen"]+=1 
            if should_attack or reason .startswith ("attack_takeover"):
                self ._diag_counters ["charge_opportunities_taken"]+=1 
            else :
                self ._diag_counters ["open_window_ignored_count"]+=1 

        if reason =="support_shape_hold"and not self ._safe_bool (trace .get ("support_target_reused")):
            self ._diag_counters ["support_repath_count"]+=1 

    def _build_quality_flags (
    self ,
    trace :Optional [dict [str ,Any ]],
    maneuver_name :str ,
    controls :dict [str ,Any ],
    )->dict [str ,bool ]:
        my_car =self .info .cars [self .index ]
        speed =math .sqrt (sum (float (x )*float (x )for x in my_car .velocity ))

        open_window =self ._safe_float (trace .get ("open_attack_window"),-1.0 )if trace else -1.0 
        takeover_threshold =self ._safe_float (trace .get ("takeover_threshold"),1.0 )if trace else 1.0 
        should_attack =self ._safe_bool (trace .get ("should_attack"))if trace else False 
        role_index =int (self ._safe_float (trace .get ("role_index"),99 ))if trace else 99 
        teammate_commit_density =self ._safe_float (trace .get ("teammate_commit_density"),0.0 )if trace else 0.0 
        reason =str (trace .get ("reason",""))if trace else ""

        hesitation_loop =(
        maneuver_name =="GeneralDefense"
        and abs (float (controls ["throttle"]))<0.16 
        and abs (float (controls ["steer"]))>0.55 
        and speed <600 
        and ground_distance (my_car ,self .info .ball )<2600 
        )
        late_challenge =open_window >=takeover_threshold and not should_attack and role_index <=1 
        over_support_hold =reason =="support_shape_hold"and open_window >=takeover_threshold +0.06 
        double_commit_risk_high =teammate_commit_density >0.74 
        open_window_ignored =open_window >=takeover_threshold and not should_attack 
        panic_clear ="Clear"in maneuver_name and self ._estimate_own_goal_danger ()>0.62 
        role_thrash =self ._diag_recent_role_thrash 

        flags ={
        "hesitation_loop":hesitation_loop ,
        "late_challenge":late_challenge ,
        "over_support_hold":over_support_hold ,
        "double_commit_risk_high":double_commit_risk_high ,
        "open_window_ignored":open_window_ignored ,
        "panic_clear":panic_clear ,
        "role_thrash":role_thrash ,
        }
        if hesitation_loop :
            self ._diag_counters ["hesitation_flag_count"]+=1 
        return flags 

    def _movement_flags (self )->dict [str ,Any ]:
        if not isinstance (self .maneuver ,GeneralDefense ):
            return {
            "anti_rocking_active":False ,
            "turning_to_face":False ,
            "turn_commit_remaining_s":0.0 ,
            "drive_deadband_applied":False ,
            }

        turn_commit_remaining =max (0.0 ,float (getattr (self .maneuver ,"turn_commit_until",0.0 )-self .info .time ))
        drive =getattr (self .maneuver ,"drive",None )
        return {
        "anti_rocking_active":True ,
        "turning_to_face":bool (getattr (self .maneuver ,"turning_to_face",False )),
        "turn_commit_remaining_s":turn_commit_remaining ,
        "drive_deadband_applied":bool (getattr (drive ,"deadband_applied",False )),
        }

    def _snapshot_payload (self )->dict [str ,Any ]:
        settings =self .info .settings .diagnostics 
        safe_num_cars =max (0 ,min (self ._last_num_cars ,len (self .info .cars )))
        valid_indices =[i for i in range (safe_num_cars )if i <len (self .info .cars )]
        if self .index >=len (self .info .cars ):
            return {"self":None ,"ball":None }

        my_car =self .info .cars [self .index ]
        payload :dict [str ,Any ]={
        "self":self ._car_payload (my_car ),
        "ball":{
        "position":self ._vec_payload (self .info .ball .position ),
        "velocity":self ._vec_payload (self .info .ball .velocity ),
        "angular_velocity":self ._vec_payload (self .info .ball .angular_velocity ),
        },
        }
        if not settings .include_snapshots :
            return payload 

        payload ["allies"]=[
        self ._car_payload (self .info .cars [i ])
        for i in valid_indices 
        if self .info .cars [i ].team ==self .team and self .info .cars [i ].id !=my_car .id 
        ]
        if settings .include_opponent_cars :
            payload ["opponents"]=[
            self ._car_payload (self .info .cars [i ])
            for i in valid_indices 
            if self .info .cars [i ].team !=self .team 
            ]
        return payload 

    def _log_tick (self ):
        if self .diagnostics is None :
            return 

        trace =self .decision_memory .last_teamplay_trace 
        self ._update_diagnostics_counters_from_trace (trace )
        controls =self ._controls_payload ()
        maneuver_name =type (self .maneuver ).__name__ if self .maneuver is not None else "None"
        quality_flags =self ._build_quality_flags (trace ,maneuver_name ,controls )

        payload ={
        "decision":{
        "maneuver":maneuver_name ,
        "action_tag":self .decision_memory .last_action_tag ,
        "teamplay_trace":trace ,
        },
        "controls":controls ,
        "movement_flags":self ._movement_flags (),
        "danger":{
        "own_goal_danger":float (self ._estimate_own_goal_danger ()),
        },
        "preset_profile":{
        "skill_preset":self .info .settings .skill .preset ,
        "skill":{
        "overall":self .info .settings .skill .overall ,
        "mechanics":self .info .settings .skill .mechanics ,
        "decision_making":self .info .settings .skill .decision_making ,
        "aggression":self .info .settings .skill .aggression ,
        "rotation_discipline":self .info .settings .skill .rotation_discipline ,
        "teammate_awareness":self .info .settings .skill .teammate_awareness ,
        "consistency":self .info .settings .skill .consistency ,
        },
        "human_style":{
        "decisiveness":self .info .settings .human_style .decisiveness ,
        "takeover_bias":self .info .settings .human_style .takeover_bias ,
        "role_stability":self .info .settings .human_style .role_stability ,
        "commit_hold_time":self .info .settings .human_style .commit_hold_time ,
        "touch_reset_resist":self .info .settings .human_style .touch_reset_resist ,
        "mistake_rate":self .info .settings .human_style .mistake_rate ,
        "mechanical_variance":self .info .settings .human_style .mechanical_variance ,
        },
        },
        "quality_flags":quality_flags ,
        "counters":dict (self ._diag_counters ),
        "snapshot":self ._snapshot_payload (),
        }

        self .diagnostics .log_tick (
        game_time =float (self .info .time ),
        mode =str (getattr (self .info ,"mode","soccar")),
        team =self .team ,
        self_index =self .index ,
        payload =payload ,
        )
