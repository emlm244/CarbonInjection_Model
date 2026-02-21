"""Structured match diagnostics logging for Botimus Prime."""

from __future__ import annotations 

import json 
import os 
import shutil 
from datetime import datetime 
from pathlib import Path 
from typing import Any ,TextIO 

from tools .bot_settings import DiagnosticsSettings 


class MatchDiagnosticsLogger :
    """Writes newline-delimited JSON events for each match tick when enabled."""

    def __init__ (self ,settings :DiagnosticsSettings ):
        self .enabled =settings .enabled 
        self .mode =settings .mode 
        self .root_dir =settings .root_dir 
        self .flush_every =max (1 ,settings .flush_every )
        self .reset_on_start =settings .reset_on_start 
        self .log_every_tick =settings .log_every_tick 
        self .top_k_alternatives =max (1 ,settings .top_k_alternatives )
        self .include_snapshots =settings .include_snapshots 
        self .include_opponent_cars =settings .include_opponent_cars 

        self ._line_counter =0 
        self ._match_index =0 
        self ._tick_index =0 
        self ._last_game_time :float |None =None 
        self ._handle :TextIO |None =None 
        self ._session_dir :Path |None =None 
        self ._runtime_boot_event :dict [str ,Any ]|None =None 
        self ._pending_runtime_faults :list [dict [str ,Any ]]=[]

        if not self .enabled :
            return 

        base_dir =Path (self .root_dir )
        if self .reset_on_start :
            self ._prune_prior_sessions (base_dir )

        session_stamp =datetime .now ().strftime ("%Y%m%d_%H%M%S")
        self ._session_dir =base_dir /f"session_{session_stamp }"
        self ._session_dir .mkdir (parents =True ,exist_ok =True )

        meta ={
        "created_at":datetime .now ().isoformat (timespec ="seconds"),
        "mode":self .mode ,
        "flush_every":self .flush_every ,
        "log_every_tick":self .log_every_tick ,
        "top_k_alternatives":self .top_k_alternatives ,
        "include_snapshots":self .include_snapshots ,
        "include_opponent_cars":self .include_opponent_cars ,
        "reset_on_start":self .reset_on_start ,
        }
        (self ._session_dir /"session_meta.json").write_text (
        json .dumps (meta ,indent =2 ),
        encoding ="utf-8",
        )

    @staticmethod 
    def _prune_prior_sessions (base_dir :Path )->None :
        if not base_dir .exists ():
            return 
        for prior in base_dir .glob ("session_*"):
            try :
                if prior .is_dir ():
                    shutil .rmtree (prior )
                else :
                    prior .unlink (missing_ok =True )
            except OSError :
                continue 

    @property 
    def session_dir (self )->Path |None :
        return self ._session_dir 

    def log_boot_event (self ,payload :dict [str ,Any ])->None :
        if not self .enabled :
            return 
        self ._runtime_boot_event =payload 

    def log_runtime_fault (self ,payload :dict [str ,Any ])->None :
        if not self .enabled :
            return 
        event ={
        "event":"runtime_fault",
        "timestamp":datetime .now ().isoformat (timespec ="milliseconds"),
        "match_index":self ._match_index ,
        "payload":payload ,
        }
        if self ._handle is None :
            self ._pending_runtime_faults .append (event )
            return 
        self ._write (event )

    def _open_new_match_file (self ,*,mode :str ,team :int ,self_index :int )->None :
        if self ._session_dir is None :
            return 
        self .close ()
        self ._match_index +=1 
        self ._tick_index =0 
        file_path =self ._session_dir /(
        f"match_{self ._match_index :02d}_i{self_index }_p{os .getpid ()}.jsonl"
        )
        self ._handle =file_path .open ("a",encoding ="utf-8",newline ="\n")
        self ._write (
        {
        "event":"match_start",
        "match_index":self ._match_index ,
        "mode":mode ,
        "team":team ,
        "self_index":self_index ,
        "started_at":datetime .now ().isoformat (timespec ="seconds"),
        }
        )
        if self ._runtime_boot_event is not None :
            self ._write (
            {
            "event":"runtime_boot",
            "match_index":self ._match_index ,
            "payload":self ._runtime_boot_event ,
            }
            )
        while self ._pending_runtime_faults :
            pending =self ._pending_runtime_faults .pop (0 )
            pending ["match_index"]=self ._match_index 
            self ._write (pending )

    def _maybe_rotate (self ,*,game_time :float ,mode :str ,team :int ,self_index :int )->None :
        if self ._handle is None :
            self ._open_new_match_file (mode =mode ,team =team ,self_index =self_index )
        elif self ._last_game_time is not None and game_time +5.0 <self ._last_game_time :
            self ._open_new_match_file (mode =mode ,team =team ,self_index =self_index )
        self ._last_game_time =game_time 

    def _write (self ,payload :dict [str ,Any ])->None :
        if self ._handle is None :
            return 
        self ._handle .write (json .dumps (payload ,separators =(",",":"),ensure_ascii =True ))
        self ._handle .write ("\n")
        self ._line_counter +=1 
        if self ._line_counter %self .flush_every ==0 :
            self ._handle .flush ()

    def _log_match_event (
    self ,
    *,
    event :str ,
    game_time :float ,
    mode :str ,
    team :int ,
    self_index :int ,
    payload :dict [str ,Any ],
    with_tick_index :bool =False ,
    )->None :
        self ._maybe_rotate (game_time =game_time ,mode =mode ,team =team ,self_index =self_index )
        if self ._handle is None :
            return 
        event_payload ={
        "event":event ,
        "timestamp":datetime .now ().isoformat (timespec ="milliseconds"),
        "match_index":self ._match_index ,
        "game_time":float (game_time ),
        "mode":mode ,
        "team":team ,
        "self_index":self_index ,
        "payload":payload ,
        }
        if with_tick_index :
            self ._tick_index +=1 
            event_payload ["tick_index"]=self ._tick_index 
        self ._write (event_payload )

    def log_tick (
    self ,
    *,
    game_time :float ,
    mode :str ,
    team :int ,
    self_index :int ,
    payload :dict [str ,Any ],
    )->None :
        if not self .enabled or not self .log_every_tick :
            return 
        try :
            self ._log_match_event (
            event ="tick",
            game_time =game_time ,
            mode =mode ,
            team =team ,
            self_index =self_index ,
            payload =payload ,
            with_tick_index =True ,
            )
        except Exception :

            return 

    def log_match_summary (
    self ,
    *,
    game_time :float ,
    mode :str ,
    team :int ,
    self_index :int ,
    payload :dict [str ,Any ],
    )->None :
        if not self .enabled :
            return 
        try :
            self ._log_match_event (
            event ="match_summary",
            game_time =game_time ,
            mode =mode ,
            team =team ,
            self_index =self_index ,
            payload =payload ,
            )
        except Exception :
            return 

    def close (self )->None :
        if self ._handle is None :
            return 
        self ._handle .flush ()
        self ._handle .close ()
        self ._handle =None 
