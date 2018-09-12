import configparser
import appdirs
import os
import logging

_logger = logging.getLogger("pushrocket-api")
APPNAME = "pushrocket-api"

def get_config_file_path():
    """ 
    gets a configuration file path for pushrocket-api.
        
    First, the environment variable PUSHROCKET_CONFIG will be checked.
    If that variable contains an invalid path, an exception is raised.
        
    If the variable is not set, the config file will be loaded from the 
    platform specific standard config directory, e.g.
    
    on linux: ~/.config/pushrocket-api/pushrocket-api.cfg
    on Windows: C:\\Users\\user\\AppData\\Local\\pushrocket-api\\pushrocket-api.cfg
    on OSX: /Users/user/Library/Application Support/pushrocket-api/pushrocket-api.cfg
    
    The file is not created if it does not exist.
        
    """
     
    #check environment variable first
    cfile = os.getenv("PUSHROCKET_CONFIG")
    if not cfile:
        _logger.info("PUSHROCKET_CONFIG is not set, using default config file location")
    elif not os.path.exists(cfile):
        _logger.error("PUSHROCKET_CONFIG file path is invalid: {}".format(cfile))
    else:
        return cfile
    
    configdir = appdirs.user_config_dir(appname=APPNAME)
    return os.path.join(configdir, "pushrocket-api.cfg")
    

def write_default_config(path=None, overwrite=False):
    """ writes out a config file with default options pre-loaded 
    
    Arguments:
        path: the path for the config file to write. If not specified,
        calls get_config_file_path() to obtain a location
        
        overwrite: whether to overwrite an existing file. If False, and the 
        path already exists, raises a RuntimeError
    
    """
    if path is None:
        path = get_config_file_path()
        
    if os.path.exists(path):
        if not overwrite:
            errstr = "config file {} already exists. Not overwriting".format(path)
            _logger.error(errstr)
            raise RuntimeError(errstr)
        else:
            _logger.warn("overwriting existing config file {} with default".format(path))
        
    cfg = configparser.ConfigParser(allow_no_value=True)
    cfg.add_section("database")
    dbpath = os.path.join(appdirs.user_data_dir(APPNAME),"pushrocket-api.db")
    cfg["database"]["uri"] = dbpath

    cfg.add_section("dispatch")
    cfg["dispatch"]["google_api_key"] = ""
    cfg["dispatch"]["google_gcm_sender_id"] = 509878466986
    cfg["dispatch"]["zeromq_relay_uri"] = ""
    
    cfg.add_section("server")
    cfg["server"]["debug"] = True
    
    with open(path,"w") as f:
        cfg.write(f)
    
        
        
    
    






# Must be a mysql database!
database_uri = 'mysql+pymysql://pushrocket@localhost/pushjet_api?charset=utf8mb4'
#database_uri = 'sqlite:///pushrocket_api.db'

# Are we debugging the server?
# Do not turn this on when in production!
debug = True

# Google Cloud Messaging configuration (required for android!)
google_api_key = ''
google_gcm_sender_id = 509878466986  # Change this to your gcm sender id

# Message Queueing, this should be the relay. A "sane" value
# for this would be something like ipc:///tmp/pushrocket-relay.ipc
zeromq_relay_uri = ''
