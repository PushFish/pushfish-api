""" setting and getting the persistent configuration for pushrocket-api server"""

import configparser
import os
import logging

import appdirs

__LOGGER = logging.getLogger("pushrocket-api")
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
        __LOGGER.info("PUSHROCKET_CONFIG is not set, using default config file location")
    elif not os.path.exists(cfile):
        __LOGGER.error("PUSHROCKET_CONFIG file path is invalid: %s", cfile)
    else:
        return cfile

    configdir = appdirs.user_config_dir(appname=APPNAME)
    return os.path.join(configdir, "pushrocket-api.cfg")


def write_default_config(path: str = None, overwrite: bool = False):
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
            __LOGGER.error(errstr)
            raise RuntimeError(errstr)
        else:
            __LOGGER.warning("overwriting existing config file %s with default", path)

    cfg = configparser.ConfigParser(allow_no_value=True)
    cfg.add_section("database")
    cfg.set("database", "#for mysql, use something like: \
            uri = 'mysql+pymysql://pushrocket@localhost/pushrocket_api?charset=utf8mb4'")
    dbpath = os.path.join(appdirs.user_data_dir(APPNAME), "pushrocket-api.db")
    cfg["database"]["uri"] = dbpath

    cfg.add_section("dispatch")
    cfg["dispatch"]["google_api_key"] = ""
    cfg["dispatch"]["google_gcm_sender_id"] = str(509878466986)
    cfg["dispatch"]["zeromq_relay_uri"] = ""

    cfg.add_section("server")
    cfg["server"]["debug"] = str(int(True))

    cfgdir = os.path.dirname(path)
    if not os.path.exists(cfgdir):
        os.mkdir(cfgdir)    
        with open(path, "x") as f:
            cfg.write(f)
    else:
        with open(path, "w") as f:
            cfg.write(f)


class Config:
    """ reader for pushrocket config file """
    def __init__(self, path=None, create=False):
        """
        arguments:
            path: path for config file. If not specified, calls get_default_config_path()
            create: create a default config file if it doesn't exist
        """
        if not path:
            path = get_config_file_path()

        if not os.path.exists(path):
            if not create:
                errstr = "config file doesn't exist, and didn't pass create=True"
                __LOGGER.error(errstr)
                raise RuntimeError(errstr)

            __LOGGER.info("config file doesn't exist, creating it...")
            write_default_config(path=path, overwrite=False)

        self._cfg = configparser.ConfigParser()
        with open(path, "r") as f:
            self._cfg.read_file(f)

    @property
    def database_uri(self):
        """ returns the database connection URI"""
        return self._cfg["database"]["uri"]

    @property
    def google_api_key(self):
        """ returns google API key for gcm"""
        return self._cfg["dispatch"]["google_api_key"]

    @property
    def google_gcm_sender_id(self):
        """ returns sender id for gcm"""
        return int(self._cfg["dispatch"]["google_gcm_sender_id"])

    @property
    def zeromq_relay_id(self):
        """ returns relay id for zeromq dispatcher"""
        return self._cfg["dispatch"]["zeromq_relay_id"]

    @property
    def debug(self):
        """ returns desired debug state of application"""
        return bool(int(self._cfg["server"]["debug"]))
