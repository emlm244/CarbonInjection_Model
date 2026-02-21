from __future__ import annotations 


import importlib 
import datetime as dt 
import math 
import os 
import pathlib 
import sys 
import threading 
import time 
import traceback 
import ctypes 
from typing import Any ,Optional ,Protocol ,cast 

os .environ .setdefault ("BOTIMUS_PACKET_READ_MODE","compat")
os .environ .setdefault ("BOTIMUS_AUTO_NOCHECK_RLUTILITIES","0")
os .environ .setdefault ("BOTIMUS_AUTO_ENABLE_BASE_BOT","0")
os .environ .setdefault ("BOTIMUS_FORCE_UNSAFE_CORE_IMPORT","0")
os .environ .setdefault ("BOTIMUS_CARBON_ARCHIVED","1")
os .environ .setdefault ("BOTIMUS_CARBON_SILENT_ARCHIVE","1")

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


class _BotimusCoreLike (Protocol ):
    def initialize (self ,field_info :Any =None ,renderer :Any =None )->None :...
    def retire (self )->None :...
    def tick (self ,packet :Any ,external_ball_prediction :Any =None )->Optional [SimpleControllerState ]:...


_BOTIMUS_CORE_IMPORT_ERROR :Optional [str ]=None 


class _BotimusCoreFactory (Protocol ):
    def __call__ (
    self ,
    *,
    name :str ,
    team :int ,
    index :int ,
    enable_rendering :bool ,
    logger :Any ,
    )->_BotimusCoreLike :...


_BOTIMUS_CORE_CLASS :Optional [_BotimusCoreFactory ]=None 

def _read_bool_env (name :str ,default :bool )->bool :
    raw =os .environ .get (name )
    if raw is None :
        return bool (default )
    lowered =raw .strip ().lower ()
    if lowered in {"1","true","yes","on"}:
        return True 
    if lowered in {"0","false","no","off"}:
        return False 
    return bool (default )


def _probe_py_get_version_sanity ()->tuple [bool ,str ]:
    try :
        ctypes .pythonapi .Py_GetVersion .restype =ctypes .c_char_p 
        raw =ctypes .pythonapi .Py_GetVersion ()
        if raw is None :
            return False ,"raw=None"
        text =bytes (raw ).decode ("utf-8",errors ="replace").strip ()
        if not text :
            return False ,"empty"
        if text [0 ]in "0123456789":
            return True ,text [:64 ]
        return False ,text [:64 ]
    except Exception as exc :
        return False ,f"probe_failed={type (exc ).__name__ }: {exc }"


def _core_import_guard ()->tuple [bool ,str ]:
    if _read_bool_env ("BOTIMUS_FORCE_UNSAFE_CORE_IMPORT",False ):
        return True ,"forced_unsafe_core_import=true"
    sane ,sample =_probe_py_get_version_sanity ()
    if sane :
        return True ,"py_get_version_probe_sane"
    return False ,f"py_get_version_probe_unsafe sample={sample !r }"


_BOTIMUS_CARBON_ARCHIVED_DEFAULT =_read_bool_env ("BOTIMUS_CARBON_ARCHIVED",True )
if _BOTIMUS_CARBON_ARCHIVED_DEFAULT :
    _BOTIMUS_CORE_IMPORT_ALLOWED =False 
    _BOTIMUS_CORE_IMPORT_GUARD_REASON ="botimus_carbon_archived=true"
else :
    _BOTIMUS_CORE_IMPORT_ALLOWED ,_BOTIMUS_CORE_IMPORT_GUARD_REASON =_core_import_guard ()
    if not _BOTIMUS_CORE_IMPORT_ALLOWED :
        _BOTIMUS_CORE_IMPORT_ERROR =(
        "CORE_IMPORT_GUARD_BLOCK\n"
        f"reason={_BOTIMUS_CORE_IMPORT_GUARD_REASON }\n"
        "Set BOTIMUS_FORCE_UNSAFE_CORE_IMPORT=1 to bypass guard (may crash host)."
        )


def _load_botimus_core_class ()->Optional [_BotimusCoreFactory ]:
    global _BOTIMUS_CORE_CLASS ,_BOTIMUS_CORE_IMPORT_ERROR 

    if _BOTIMUS_CORE_CLASS is not None :
        return _BOTIMUS_CORE_CLASS 
    if _BOTIMUS_CORE_IMPORT_ERROR is not None :
        return None 
    if not _BOTIMUS_CORE_IMPORT_ALLOWED :
        return None 

    try :
        module =importlib .import_module ("runtime.botimus_core")
        loaded =getattr (module ,"BotimusCore",None )
        if loaded is None :
            _BOTIMUS_CORE_IMPORT_ERROR ="CORE_IMPORT_FAIL runtime.botimus_core.BotimusCore missing"
            return None 
        _BOTIMUS_CORE_CLASS =cast (_BotimusCoreFactory ,loaded )
        return _BOTIMUS_CORE_CLASS 
    except Exception :
        _BOTIMUS_CORE_IMPORT_ERROR =traceback .format_exc ()
        return None 


class plugin_BotimusPrime :
    def __init__ (self ,player_index =0 ,ConsoleLogger =None ,BotController =None ):
        self .controller :Optional [SimpleControllerState ]=None 
        self .player_index =int (player_index )
        self .game_tick_packet =None 
        self .ConsoleLogger =ConsoleLogger 
        self .BotController =BotController 
        self .playername ="default"
        self .pid =None 

        self ._core :Optional [_BotimusCoreLike ]=None 
        self ._core_team :Optional [int ]=None 
        self ._core_index :Optional [int ]=None 
        self ._lock =threading .Lock ()
        self ._bot_enable_requested =False 
        self ._core_import_error_logged =False 
        self ._last_process_id =None 
        self ._tick_counter =0 
        self ._last_tick_time =0.0 
        self ._last_controller_time =0.0 
        self ._last_watchdog_log =0.0 
        self ._last_controller_none_log =0.0 
        self ._first_tick_logged =False 
        self ._integration_archived =self ._read_bool_env ("BOTIMUS_CARBON_ARCHIVED",True )
        self ._silent_archive =self ._read_bool_env ("BOTIMUS_CARBON_SILENT_ARCHIVE",True )
        self ._log_file_path :Optional [pathlib .Path ]=None 
        if not (self ._integration_archived and self ._silent_archive ):
            self ._log_file_path =self ._resolve_log_file_path ()
        self ._core_unavailable_mode =self ._read_core_unavailable_mode ()
        self ._fallback_mode_logged =False 
        self ._fallback_last_log =0.0 
        self ._passthrough_mode_logged =False 
        self ._passthrough_last_log =0.0 
        self ._auto_enable_base_bot =self ._read_bool_env ("BOTIMUS_AUTO_ENABLE_BASE_BOT",False )
        self ._base_bot_candidates =self ._read_base_bot_candidates ()
        self ._base_bot_enabled_name :Optional [str ]=None 
        if not self ._integration_archived :
            self ._log_runtime_probe ()
        elif not self ._silent_archive :
            self ._log ("BOTIMUS_INTEGRATION_ARCHIVED active=true")

    def Name (self ):
        if self ._integration_archived and self ._silent_archive :
            return 
        self ._log ("Botimus Prime")

    def Description (self ):
        if self ._integration_archived and self ._silent_archive :
            return 
        self ._log ("Botimus runtime hosted through Carbon plugin API")

    def Author (self ):
        if self ._integration_archived and self ._silent_archive :
            return 
        self ._log ("Botimus + Carbon adapter")

    def Version (self ):
        if self ._integration_archived and self ._silent_archive :
            return 
        self ._log ("v1.0-carbon-wrapper")

    def _resolve_log_file_path (self )->pathlib .Path :
        module_path =pathlib .Path (__file__ ).resolve ()
        plugin_dir =module_path .parent 
        plugins_dir =plugin_dir .parent if plugin_dir .name =="botimus_prime"else plugin_dir 
        runtime_dir =plugins_dir .parent if plugins_dir .name =="plugins"else plugins_dir 
        logs_dir =runtime_dir /"logs"
        try :
            logs_dir .mkdir (parents =True ,exist_ok =True )
            return logs_dir /"botimus_plugin_runtime.log"
        except OSError :
            return plugin_dir /"botimus_plugin_runtime.log"

    @staticmethod 
    def _read_core_unavailable_mode ()->str :
        mode =os .environ .get ("BOTIMUS_CORE_FAIL_MODE","passthrough").strip ().lower ()
        if mode not in {"passthrough","fallback"}:
            return "passthrough"
        return mode 

    @staticmethod 
    def _read_bool_env (name :str ,default :bool )->bool :
        raw =os .environ .get (name )
        if raw is None :
            return bool (default )
        lowered =raw .strip ().lower ()
        if lowered in {"1","true","yes","on"}:
            return True 
        if lowered in {"0","false","no","off"}:
            return False 
        return bool (default )

    @staticmethod 
    def _read_base_bot_candidates ()->list [str ]:

        primary =os .environ .get ("BOTIMUS_BASE_BOTNAME","brainbot")
        fallback =os .environ .get ("BOTIMUS_BASE_BOT_FALLBACKS","carbon")
        merged =f"{primary },{fallback }"
        candidates :list [str ]=[]
        for raw in merged .replace (";",",").split (","):
            botname =raw .strip ().lower ()
            if not botname or botname in candidates :
                continue 
            candidates .append (botname )
        if not candidates :
            return ["brainbot","carbon"]
        return candidates 

    @staticmethod 
    def _resolve_rlutilities_candidate ()->tuple [str ,bool ]:
        raw_candidates =os .environ .get ("BOTIMUS_RLUTILITIES_CANDIDATES","").strip ()
        if not raw_candidates :
            return "",False 
        candidates =[item .strip ()for item in raw_candidates .replace (";",",").split (",")if item .strip ()]
        for candidate in candidates :
            try :
                candidate_path =pathlib .Path (candidate )
                if candidate_path .exists ():
                    return str (candidate_path .resolve ()),True 
            except OSError :
                continue 
        return candidates [0 ],False 

    @staticmethod 
    def _now_stamp ()->str :
        return dt .datetime .now ().strftime ("%Y-%m-%d %H:%M:%S.%f")[:-3 ]

    def _log (self ,message :str ):
        if self ._integration_archived and self ._silent_archive :
            return 
        line =f"[{self ._now_stamp ()}] {message }"
        if self .ConsoleLogger is not None :
            try :
                self .ConsoleLogger (line )
            except Exception :
                pass 

        if self ._log_file_path is not None :
            try :
                with self ._log_file_path .open ("a",encoding ="utf-8")as handle :
                    handle .write (line +"\n")
            except OSError :
                pass 

    def _log_runtime_probe (self ):
        self ._log (
        "PLUGIN_INIT "
        f"python={sys .version .split ()[0 ]} "
        f"executable={sys .executable } "
        f"cwd={pathlib .Path .cwd ()} "
        f"module={pathlib .Path (__file__ ).resolve ()}"
        )
        self ._log (f"PLUGIN_PY_VERSION_REPR {sys .version !r }")
        self ._log (f"PLUGIN_PY_HEXVERSION 0x{sys .hexversion :x}")
        self ._log (f"PLUGIN_MEIPASS {getattr (sys ,'_MEIPASS',None )}")
        self ._log (self ._py_get_version_probe ())
        self ._log (
        "CORE_IMPORT_GUARD "
        f"allowed={_BOTIMUS_CORE_IMPORT_ALLOWED } "
        f"reason={_BOTIMUS_CORE_IMPORT_GUARD_REASON }"
        )
        if not _BOTIMUS_CORE_IMPORT_ALLOWED :
            self ._log (
            "CORE_IMPORT_BLOCKED_BY_GUARD "
            f"reason={_BOTIMUS_CORE_IMPORT_GUARD_REASON }"
            )
        self ._log (f"CORE_FAIL_MODE mode={self ._core_unavailable_mode }")
        self ._log (f"PLUGIN_BASE_BOT_CANDIDATES {self ._base_bot_candidates }")
        self ._log (f"PLUGIN_AUTO_ENABLE_BASE_BOT {self ._auto_enable_base_bot }")
        self ._log (f"PLUGIN_PACKET_READ_MODE {os .environ .get ('BOTIMUS_PACKET_READ_MODE','auto')}")
        self ._log (
        "PLUGIN_NOCHECK_ENV "
        f"allow={os .environ .get ('BOTIMUS_ALLOW_NOCHECK_RLUTILITIES','')} "
        f"auto={os .environ .get ('BOTIMUS_AUTO_NOCHECK_RLUTILITIES','')}"
        )
        candidate_override =os .environ .get ("BOTIMUS_RLUTILITIES_CANDIDATES","").strip ()
        if candidate_override :
            self ._log (f"PLUGIN_RLUTILITIES_CANDIDATE_OVERRIDE {candidate_override }")
        candidate_resolved ,candidate_exists =self ._resolve_rlutilities_candidate ()
        if candidate_resolved :
            self ._log (
            "PLUGIN_RLUTILITIES_CANDIDATE_RESOLVED "
            f"path={candidate_resolved } exists={candidate_exists }"
            )
        else :
            self ._log ("PLUGIN_RLUTILITIES_CANDIDATE_RESOLVED path=<none> exists=False")
        self ._log (f"PLUGIN_SYS_PATH_HEAD {sys .path [:5 ]}")
        core_class =_load_botimus_core_class ()if _BOTIMUS_CORE_IMPORT_ALLOWED else None 
        if _BOTIMUS_CORE_IMPORT_ERROR :
            self ._core_import_error_logged =True 
            self ._log ("CORE_IMPORT_FAIL")
            self ._log (_BOTIMUS_CORE_IMPORT_ERROR .strip ())
        elif core_class is None and _BOTIMUS_CORE_IMPORT_ALLOWED :
            self ._log ("CORE_IMPORT_UNKNOWN BotimusCore=None")
        else :
            self ._log ("CORE_IMPORT_OK")

    @staticmethod 
    def _py_get_version_probe ()->str :
        try :
            ctypes .pythonapi .Py_GetVersion .restype =ctypes .c_char_p 
            raw =ctypes .pythonapi .Py_GetVersion ()
            if raw is None :
                return "PY_GET_VERSION raw=None"
            raw_bytes =bytes (raw )
            head =" ".join (f"{b :02x}"for b in raw_bytes [:12 ])
            decoded =raw_bytes .decode ("utf-8",errors ="replace")
            return f"PY_GET_VERSION text={decoded !r } hex_head={head }"
        except Exception as exc :
            return f"PY_GET_VERSION probe_failed={type (exc ).__name__ }: {exc }"

    def _safe_team_from_packet (self ,packet ,local_player_index :int )->int :
        try :
            return int (packet .game_cars [local_player_index ].team )
        except Exception :
            return 0 

    def _read_host_hook (self ,*names ):
        for name in names :
            obj =getattr (self ,name ,None )
            if obj is None :
                continue 
            if callable (obj ):
                try :
                    return obj ()
                except TypeError :
                    continue 
                except Exception :
                    continue 
            return obj 
        return None 

    def _get_host_field_info (self ):
        return self ._read_host_hook (
        "get_field_info",
        "GetFieldInfo",
        "field_info",
        "FieldInfo",
        )

    def _get_host_ball_prediction (self ):
        return self ._read_host_hook (
        "get_ball_prediction_struct",
        "GetBallPredictionStruct",
        "ball_prediction_struct",
        "BallPredictionStruct",
        )

    def _ensure_core (self ,packet ,local_player_index :int ):
        if self ._integration_archived :
            return 
        core_class =_load_botimus_core_class ()
        if core_class is None :
            if not self ._core_import_error_logged :
                self ._core_import_error_logged =True 
                self ._log ("CORE_IMPORT_FAIL BotimusCore unavailable")
                if _BOTIMUS_CORE_IMPORT_ERROR :
                    self ._log (_BOTIMUS_CORE_IMPORT_ERROR .strip ())
            return 

        team =self ._safe_team_from_packet (packet ,local_player_index )
        requires_reinit =(
        self ._core is None 
        or self ._core_team !=team 
        or self ._core_index !=local_player_index 
        )
        if not requires_reinit :
            return 

        if self ._core is not None :
            self ._core .retire ()

        self ._core_team =team 
        self ._core_index =local_player_index 
        try :
            self ._core =core_class (
            name =f"BotimusPrime[{self .playername }]",
            team =team ,
            index =local_player_index ,
            enable_rendering =False ,
            logger =self ._log ,
            )
            self ._core .initialize (field_info =self ._get_host_field_info (),renderer =None )
            self ._log (f"CORE_READY index={local_player_index } team={team }")
        except Exception :
            self ._core =None 
            self ._log ("CORE_INIT_FAIL")
            self ._log (traceback .format_exc ().strip ())

    def _ensure_base_bot_enabled (self ):
        if self ._integration_archived :
            return 
        if self ._bot_enable_requested :
            return 
        self ._bot_enable_requested =True 

        if not self ._auto_enable_base_bot :
            self ._log ("BOT_ENABLE_SKIPPED auto_enable_base_bot=false using=manual_selection")
            return 

        if self .BotController is None :
            self ._log ("BotController hook not present; skipping auto-enable.")
            return 

        failures :list [str ]=[]
        for botname in self ._base_bot_candidates :
            try :
                self .BotController ("enable",botname =botname ,source ="plugin_botimus_prime")
                self ._base_bot_enabled_name =botname 
                self ._log (f"BOT_ENABLE_REQUESTED botname={botname }")
                return 
            except Exception as e :
                failures .append (f"{botname }: {e }")

        if failures :
            self ._log ("Bot enable request failed for all candidates.")
            for failure in failures :
                self ._log (f"BOT_ENABLE_FAIL {failure }")

    @staticmethod 
    def _clamp (value :float ,lower :float ,upper :float )->float :
        return max (lower ,min (upper ,value ))

    @staticmethod 
    def _wrap_angle (value :float )->float :
        while value >math .pi :
            value -=2.0 *math .pi 
        while value <-math .pi :
            value +=2.0 *math .pi 
        return value 

    def _fallback_controller_from_packet (self ,packet )->SimpleControllerState :
        controller =SimpleControllerState ()
        try :
            car =packet .game_cars [self .player_index ]
            ball =packet .game_ball 
            car_loc =car .physics .location 
            car_vel =car .physics .velocity 
            car_rot =car .physics .rotation 
            ball_loc =ball .physics .location 

            dx =float (ball_loc .x )-float (car_loc .x )
            dy =float (ball_loc .y )-float (car_loc .y )
            distance =math .sqrt (dx *dx +dy *dy )
            target_yaw =math .atan2 (dy ,dx )
            yaw =float (car_rot .yaw )
            yaw_error =self ._wrap_angle (target_yaw -yaw )

            steer =self ._clamp (yaw_error *2.8 ,-1.0 ,1.0 )
            speed =math .sqrt (float (car_vel .x )**2 +float (car_vel .y )**2 +float (car_vel .z )**2 )
            on_ground =bool (getattr (car ,"has_wheel_contact",False ))
            ball_height =float (getattr (ball_loc ,"z",0.0 ))
            car_height =float (getattr (car_loc ,"z",0.0 ))

            throttle =1.0 
            if abs (yaw_error )>1.6 :
                throttle =-0.35 
            elif abs (yaw_error )>0.9 :
                throttle =0.45 

            controller .steer =steer 
            controller .throttle =throttle 
            controller .boost =on_ground and throttle >0.8 and abs (yaw_error )<0.20 and speed <2200.0 
            controller .handbrake =abs (yaw_error )>1.4 and speed >900.0 


            if on_ground and distance <185.0 and abs (ball_height -car_height )<180.0 and speed <1350.0 :
                controller .jump =True 
        except Exception :
            self ._log ("FALLBACK_CONTROLLER_EXCEPTION")
            self ._log (traceback .format_exc ().strip ())

        return controller 

    def game_tick_packet_set (self ,packet ,local_player_index =0 ,playername ="default",process_id =None ):
        with self ._lock :
            now =time .time ()
            self ._last_tick_time =now 
            self ._tick_counter +=1 
            if self ._integration_archived :
                self .controller =None 
                self ._last_controller_time =now 
                return None 
            try :
                self .game_tick_packet =packet 
                self .player_index =int (local_player_index )
                self .playername =str (playername )
                self .pid =process_id 

                if not self ._first_tick_logged :
                    self ._first_tick_logged =True 
                    self ._log (
                    "PACKET_STREAM_ACTIVE "
                    f"player_index={self .player_index } "
                    f"player_name={self .playername } "
                    f"pid={process_id }"
                    )
                elif process_id !=self ._last_process_id :
                    self ._log (f"PID_CHANGED old={self ._last_process_id } new={process_id }")
                self ._last_process_id =process_id 

                self ._ensure_core (packet ,self .player_index )
                self ._ensure_base_bot_enabled ()
                if self ._core is None :
                    if self ._core_unavailable_mode =="fallback":
                        self .controller =self ._fallback_controller_from_packet (packet )
                        self ._last_controller_time =now 
                        if now -self ._last_controller_none_log >=5.0 :
                            self ._last_controller_none_log =now 
                            self ._log ("CONTROLLER_UNAVAILABLE reason=core_not_ready using=fallback")
                        if not self ._fallback_mode_logged :
                            self ._fallback_mode_logged =True 
                            self ._log ("FALLBACK_CONTROLLER_ACTIVE reason=core_not_ready")
                        elif now -self ._fallback_last_log >=15.0 :
                            self ._fallback_last_log =now 
                            self ._log (
                            f"FALLBACK_HEARTBEAT ticks={self ._tick_counter } "
                            f"player_index={self .player_index } pid={self .pid }"
                            )
                        return self .controller 

                    self .controller =None 
                    self ._last_controller_time =now 
                    if now -self ._last_controller_none_log >=5.0 :
                        self ._last_controller_none_log =now 
                        self ._log ("CONTROLLER_PASSTHROUGH reason=core_not_ready using=selected_model")
                    if not self ._passthrough_mode_logged :
                        self ._passthrough_mode_logged =True 
                        self ._log ("PASSTHROUGH_ACTIVE reason=core_not_ready")
                    elif now -self ._passthrough_last_log >=15.0 :
                        self ._passthrough_last_log =now 
                        self ._log (
                        f"PASSTHROUGH_HEARTBEAT ticks={self ._tick_counter } "
                        f"player_index={self .player_index } pid={self .pid }"
                        )
                    return None 

                prediction =self ._get_host_ball_prediction ()
                self .controller =self ._core .tick (packet ,external_ball_prediction =prediction )
                if self .controller is None :
                    if now -self ._last_controller_none_log >=5.0 :
                        self ._last_controller_none_log =now 
                        self ._log ("CONTROLLER_NONE")
                else :
                    self ._last_controller_time =now 

                if self ._tick_counter %240 ==0 :
                    self ._log (
                    "TICK_HEARTBEAT "
                    f"ticks={self ._tick_counter } "
                    f"seconds_since_controller={now -self ._last_controller_time :.2f}"
                    )

                return self .controller 
            except Exception :
                self .controller =None 
                self ._log ("TICK_EXCEPTION")
                self ._log (traceback .format_exc ().strip ())
                return None 

    def main (self ):
        target_fps =120.0 
        frame_duration =1.0 /target_fps 
        while True :
            try :
                time .sleep (frame_duration )
                if self ._integration_archived and self ._silent_archive :
                    continue 
                now =time .time ()
                if self ._last_tick_time >0 and now -self ._last_tick_time >=2.0 and now -self ._last_watchdog_log >=5.0 :
                    self ._last_watchdog_log =now 
                    self ._log (f"WATCHDOG_NO_TICK seconds={now -self ._last_tick_time :.2f}")

                if (
                self ._last_tick_time >0 
                and self ._last_controller_time >0 
                and now -self ._last_tick_time <1.0 
                and now -self ._last_controller_time >=2.0 
                and now -self ._last_controller_none_log >=5.0 
                ):
                    self ._last_controller_none_log =now 
                    self ._log (f"WATCHDOG_STALE_CONTROLLER seconds={now -self ._last_controller_time :.2f}")
            except Exception as e :
                self ._log (f"Plugin loop error: {e }")
                time .sleep (1.0 )

