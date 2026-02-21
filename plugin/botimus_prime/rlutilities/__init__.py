import ctypes 
import importlib .util 
import os 
import sys 
from pathlib import Path 

_NOCHECK_MODE :str |None =None 
_DLL_DIR_HANDLES :list [object ]=[]


def _bool_env (value :str |None )->bool |None :
    if value is None :
        return None 
    lowered =value .strip ().lower ()
    if lowered in {"1","true","yes","on"}:
        return True 
    if lowered in {"0","false","no","off"}:
        return False 
    return None 


def _probe_py_get_version_text ()->str |None :
    try :
        ctypes .pythonapi .Py_GetVersion .restype =ctypes .c_char_p 
        raw =ctypes .pythonapi .Py_GetVersion ()
        if raw is None :
            return None 
        return bytes (raw ).decode ("utf-8",errors ="replace")
    except Exception :
        return None 


def _auto_allow_nocheck_candidate ()->bool :
    auto_switch =_bool_env (os .environ .get ("BOTIMUS_AUTO_NOCHECK_RLUTILITIES"))

    if auto_switch is not True :
        return False 

    packet_mode =os .environ .get ("BOTIMUS_PACKET_READ_MODE","").strip ().lower ()
    if packet_mode !="compat":
        return False 

    if not (getattr (sys ,"frozen",False )or getattr (sys ,"_MEIPASS",None )):
        return False 

    version_text =_probe_py_get_version_text ()
    if not version_text :
        return True 

    stripped =version_text .strip ()
    if not stripped :
        return True 


    return stripped [0 ]not in "0123456789"


def _nocheck_mode ()->str :
    global _NOCHECK_MODE 
    if _NOCHECK_MODE is not None :
        return _NOCHECK_MODE 

    explicit =_bool_env (os .environ .get ("BOTIMUS_ALLOW_NOCHECK_RLUTILITIES"))
    if explicit is True :
        _NOCHECK_MODE ="forced"
    elif explicit is False :
        _NOCHECK_MODE ="disabled"
    elif _auto_allow_nocheck_candidate ():
        _NOCHECK_MODE ="auto"
    else :
        _NOCHECK_MODE ="disabled"
    return _NOCHECK_MODE 


def _allow_nocheck_candidate ()->bool :
    return _nocheck_mode ()!="disabled"


def _candidate_sort_key (path :Path ):
    name =path .name .lower ()
    if "nocheck"in name :
        mode =_nocheck_mode ()
        if mode =="forced":
            return (-2 ,name )
        if mode =="auto":

            return (6 ,name )
        return (99 ,name )
    if "nopyver2"in name :
        return (-1 ,name )
    if "nopyver"in name :
        return (0 ,name )
    if "carb3110"in name :
        return (1 ,name )
    if "cp311"in name :
        return (2 ,name )
    if "cp37"in name :
        return (3 ,name )
    return (4 ,name )


def _iter_windows_dll_dirs (package_dir :Path ):
    seen :set [Path ]=set ()
    meipass =getattr (sys ,"_MEIPASS",None )
    roots =[
    Path (meipass )if meipass else None ,
    package_dir ,
    package_dir .parent ,
    Path (sys .executable ).resolve ().parent if sys .executable else None ,
    ]

    for root in roots :
        if root is None :
            continue 
        for candidate in (
        root ,
        root /"DLLs",
        root /"python3.11",
        root /"python3.11"/"DLLs",
        root /"python311",
        root /"python311"/"DLLs",
        ):
            try :
                resolved =candidate .resolve ()
            except OSError :
                continue 
            if not resolved .exists ()or resolved in seen :
                continue 
            seen .add (resolved )
            yield resolved 


def _prepare_windows_dll_resolution (package_dir :Path ):
    if os .name !="nt":
        return []

    diagnostics =[]
    search_dirs =list (_iter_windows_dll_dirs (package_dir ))
    if not search_dirs :
        return diagnostics 


    for dll_dir in search_dirs :
        try :
            handle =os .add_dll_directory (str (dll_dir ))
            _DLL_DIR_HANDLES .append (handle )
            diagnostics .append (f"dll_dir_added={dll_dir }")
        except Exception as exc :
            diagnostics .append (f"dll_dir_add_failed={dll_dir }: {type (exc ).__name__ }: {exc }")

    old_path =os .environ .get ("PATH","")
    existing =[p for p in old_path .split (os .pathsep )if p ]
    inject =[str (p )for p in search_dirs if str (p )not in existing ]
    if inject :
        os .environ ["PATH"]=os .pathsep .join (inject +existing )
        diagnostics .append (f"dll_path_injected={inject [:4 ]}")

    py_dll_names =[
    f"python{sys .version_info .major }{sys .version_info .minor }.dll",
    "python3.dll",
    ]
    for dll_dir in search_dirs :
        for dll_name in py_dll_names :
            dll_path =dll_dir /dll_name 
            if not dll_path .exists ():
                continue 
            try :
                ctypes .WinDLL (str (dll_path ))
                diagnostics .append (f"dll_preload_ok={dll_path }")
            except Exception as exc :
                diagnostics .append (f"dll_preload_failed={dll_path }: {type (exc ).__name__ }: {exc }")
    return diagnostics 


def _iter_search_roots (package_dir :Path ):
    yield package_dir 

    env_candidates =os .environ .get ("BOTIMUS_RLUTILITIES_CANDIDATES","").strip ()
    if env_candidates :
        for part in env_candidates .split (";"):
            candidate =Path (part .strip ())
            if candidate .exists ():
                yield candidate 

def _iter_candidate_paths (package_dir :Path ):
    seen =set ()
    allow_nocheck =_allow_nocheck_candidate ()

    def _yield (path :Path ):
        if "nocheck"in path .name .lower ()and not allow_nocheck :
            return 
        resolved =path .resolve ()
        if resolved in seen :
            return 
        seen .add (resolved )
        yield resolved 

    direct_patterns =["rlutilities*.pyd","rlutilities*.so"]
    for pattern in direct_patterns :
        for candidate in sorted (package_dir .glob (pattern ),key =_candidate_sort_key ):
            yield from _yield (candidate )

    for root in _iter_search_roots (package_dir ):
        if root .is_file ():
            yield from _yield (root )
            continue 

        patterns =[
        "*/rlutilities/rlutilities*.pyd",
        "*/src/rlutilities/rlutilities*.pyd",
        "*/rlutilities/rlutilities*.so",
        "*/src/rlutilities/rlutilities*.so",
        ]
        for pattern in patterns :
            for candidate in sorted (root .glob (pattern ),key =_candidate_sort_key ):
                yield from _yield (candidate )


def _load_native_bindings ():
    package_dir =Path (__file__ ).parent 
    module_name =f"{__name__ }.rlutilities"
    dll_diagnostics =_prepare_windows_dll_resolution (package_dir )

    primary_error =None 
    try :
        from .rlutilities import mechanics ,simulation ,linear_algebra ,initialize 

        return mechanics ,simulation ,linear_algebra ,initialize 
    except Exception as exc :
        primary_error =exc 
        sys .modules .pop (module_name ,None )

    failures =[]
    for candidate in _iter_candidate_paths (package_dir ):
        spec =importlib .util .spec_from_file_location (module_name ,candidate )
        if spec is None or spec .loader is None :
            continue 

        try :
            module =importlib .util .module_from_spec (spec )
            sys .modules [module_name ]=module 
            spec .loader .exec_module (module )
            return module .mechanics ,module .simulation ,module .linear_algebra ,module .initialize 
        except Exception as exc :
            sys .modules .pop (module_name ,None )
            failures .append ((candidate ,exc ))

    lines =[]
    lines .append (f"nocheck_mode={_nocheck_mode ()}")
    lines .append (f"packet_read_mode={os .environ .get ('BOTIMUS_PACKET_READ_MODE','')}")
    if primary_error is not None :
        lines .append (f"primary import failed: {type (primary_error ).__name__ }: {primary_error }")
    for probe in dll_diagnostics [:8 ]:
        lines .append (probe )
    for candidate ,err in failures [:8 ]:
        lines .append (f"candidate failed: {candidate } -> {type (err ).__name__ }: {err }")

    detail ="\n".join (lines )
    if detail :
        raise ImportError (f"Unable to load rlutilities native bindings.\n{detail }")from primary_error 
    raise ImportError ("Unable to load rlutilities native bindings.")from primary_error 


mechanics ,simulation ,linear_algebra ,initialize =_load_native_bindings ()

sys .modules ["rlutilities.mechanics"]=mechanics 
sys .modules ["rlutilities.simulation"]=simulation 
sys .modules ["rlutilities.linear_algebra"]=linear_algebra 

asset_dir =Path (__file__ ).parent /"assets"
initialize (asset_dir .as_posix ()+"/")
