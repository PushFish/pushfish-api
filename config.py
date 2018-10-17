""" setting and getting the persistent configuration for pushrocket-api server"""
import sys
import configparser
import os
import logging
from typing import Type, TypeVar
from collections import namedtuple
import warnings

import appdirs

ConfigOption = namedtuple("ConfigOption", ["default", "type", "required",
                                           "envvar", "comment"])

APPNAME = "pushrocket-api"
_LOGGER = logging.getLogger(APPNAME)

T = TypeVar("T", bound="Config")


def construct_default_db_uri() -> str:
    dbpath = os.path.join(appdirs.user_data_dir(APPNAME), "pushrocket-api.db")
    return "sqlite:///" + dbpath


db_uri_comment = """#for mysql, use something like:
#uri = 'mysql+pymysql://pushrocket@localhost/pushrocket_api?charset=utf8mb4'"""
dispatch_zmq_comment = """#point zeromq_relay_uri at the zeromq pubsub socket for
#the pushrocket connectors """
server_debug_comment = """#set debug to 0 for production mode """

DEFAULT_VALUES = {
    "database": {"uri": ConfigOption(construct_default_db_uri, str, True, "PUSHROCKET_DB", db_uri_comment)},
    "dispatch": {"mqtt_broker_address": ConfigOption("", str, False, "MQTT_ADDRESS", None),
                 "google_api_key": ConfigOption("", str, False, "PUSHROCKET_GOOGLE_API_KEY", None),
                 "google_gcm_sender_id": ConfigOption(123456789012, bool, True, "PUSHROCKET_GCM_SENDER_ID", None),
                 "zeromq_relay_uri": ConfigOption("", str, False, "PUSHROCKET_ZMQ_RELAY_URI", dispatch_zmq_comment)},
    "server": {"debug": ConfigOption(0, bool, False, "PUSHROCKET_DEBUG", server_debug_comment)}}


def call_if_callable(v, *args, **kwargs):
    """ if v is callable, call it with args and kwargs. If not, return v itself """
    return v(*args, **kwargs) if callable(v) else v


def get_config_file_path() -> str:
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

    # check environment variable first
    cfile = os.getenv("PUSHROCKET_CONFIG")
    if not cfile:
        _LOGGER.info("PUSHROCKET_CONFIG is not set, using default config file location")
    elif not os.path.exists(cfile):
        _LOGGER.warning("PUSHROCKET_CONFIG file path does not exist, it will be created: %s", cfile)
        return cfile
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
            _LOGGER.error(errstr)
            raise RuntimeError(errstr)
        else:
            _LOGGER.warning("overwriting existing config file %s with default", path)

    cfg = configparser.ConfigParser(allow_no_value=True)

    for section, settings in DEFAULT_VALUES.items():
        cfg.add_section(section)
        for setting, value in settings.items():
            v = call_if_callable(value.default)
            if value.comment is not None:
                cfg.set(section, value.comment)
            cfg[section][setting] = str(v)

    cfgdir = os.path.dirname(path)
    if not os.path.exists(cfgdir):
        if cfgdir:
            os.mkdir(cfgdir)
        with open(path, "x") as f:
            cfg.write(f)
    else:
        with open(path, "w") as f:
            cfg.write(f)


class Config:
    """ reader for pushrocket config file """
    GLOBAL_INSTANCE = None
    GLOBAL_BACKTRACE_ENABLE = False

    @classmethod
    def get_global_instance(cls: Type[T]) -> T:
        """ returns the a global instance of the Config object.
        If one has not yet been defined, raises a RuntimeError"""
        if cls.GLOBAL_INSTANCE is None:
            raise RuntimeError("no global config instance exists. Construct a \
                               Config instance somewhere in the application")

        return cls.GLOBAL_INSTANCE

    def __init__(self, path: str = None, create: bool = False,
                 overwrite: bool = False) -> None:
        """
        arguments:
            path: path for config file. If not specified, calls get_default_config_path()
            create: create a default config file if it doesn't exist
            overwrite: overwrite the config file with the default even if it
            does already exist
        """
        if not path:
            path = get_config_file_path()

        if not os.path.exists(path):
            if not create:
                errstr = "config file doesn't exist, and didn't pass create=True"
                _LOGGER.error(errstr)
                raise RuntimeError(errstr)

            _LOGGER.info("config file doesn't exist, creating it...")
            write_default_config(path=path, overwrite=False)
        elif overwrite:
            _LOGGER.warning("config file already exists, overwriting...")
            write_default_config(path=path, overwrite=True)

        self._cfg = configparser.ConfigParser()
        with open(path, "r") as f:
            self._cfg.read_file(f)

        # HACK: this is purely here so that the tests can override the global app
        # config
        if hasattr(self, "INJECT_CONFIG"):
            warnings.warn("running with injected config. If you see this \
                          whilst not running tests it IS AN ERROR")
            self = Config.GLOBAL_INSTANCE
        else:
            Config.GLOBAL_INSTANCE = self

        if self.debug:
            Config.GLOBAL_BACKTRACE_ENABLE = True

        self._check_spurious_keys()
        self._load_from_env_vars()

    def _load_from_env_vars(self):
        for section, optdict in DEFAULT_VALUES.items():
            for name, opt in optdict.items():
                envval = os.getenv(opt.envvar)
                if envval:
                    _LOGGER.info("overriding config setting %s from environment variable %s", name, opt.envvar)
                    try:
                        self._cfg[section][name] = envval
                    except ValueError as err:
                        errstr = "couldn't get value of type %s for setting %s"
                        fatal_error_exit_or_backtrace(err, errstr, _LOGGER, opt.type, name)
                    except Exception as err:
                        errstr = "failed to set value of setting %s from environment"
                        fatal_error_exit_or_backtrace(err, errstr, _LOGGER, name)

    def _check_spurious_keys(self):
        for section in self._cfg.sections():
            if section not in DEFAULT_VALUES:
                _LOGGER.critical("spurious section [%s] found in config file. ", section)
                _LOGGER.critical("don't know how to handle this, exiting...")
                sys.exit(1)

            for key in self._cfg[section].keys():
                if key not in DEFAULT_VALUES[section]:
                    _LOGGER.critical("spurious key %s in section [%s] found in config file. ", key, section)
                    _LOGGER.critical("don't know how to handle this, exiting...")
                    sys.exit(1)

    def _safe_get_cfg_value(self, section: str, key: str):
        opt = DEFAULT_VALUES[section][key]
        try:
            return opt.type(self._cfg[section][key])
        except KeyError as err:
            reportstr = "no value for REQUIRED configuration option: %s in section [%s] defined" % (key, section)
            if opt.required:
                fatal_error_exit_or_backtrace(err, reportstr, _LOGGER)
            else:
                _LOGGER.warning(reportstr)
                defvalue = call_if_callable(opt.default)
                _LOGGER.warning("using default value of %s", str(defvalue))
                return opt.type(defvalue)

    @property
    def database_uri(self) -> str:
        """ returns the database connection URI"""
        # HACK: create directory to run db IF AND ONLY IF it's identical to
        # default and doesn't exist. Please get rid of this with something
        # better soon
        val = self._safe_get_cfg_value("database", "uri")
        if val == construct_default_db_uri():
            datadb = os.path.dirname(val).split("sqlite:///")[1]
            if not os.path.exists(datadb):
                try:
                    os.mkdir(datadb)
                except PermissionError as err:
                    errstr = "can't create default database directory. Exiting..."
                    fatal_error_exit_or_backtrace(err, errstr, _LOGGER)
        return val

    @property
    def mqtt_broker_address(self) -> str:
        """ returns MQTT server address"""
        return self._safe_get_cfg_value("dispatch", "mqtt_broker_address")

    @property
    def google_api_key(self) -> str:
        """ returns google API key for gcm"""
        return self._safe_get_cfg_value("dispatch", "google_api_key")

    @property
    def google_gcm_sender_id(self) -> int:
        """ returns sender id for gcm"""
        return self._safe_get_cfg_value("dispatch", "google_gcm_sender_id")

    @property
    def zeromq_relay_uri(self) -> str:
        """ returns relay URI for zeromq dispatcher"""
        return self._safe_get_cfg_value("dispatch", "zeromq_relay_uri")

    @property
    def debug(self) -> bool:
        """ returns desired debug state of application.
        Overridden by the value of environment variable FLASK_DEBUG """
        if int(os.getenv("FLASK_DEBUG", "0")):
            return True
        return self._safe_get_cfg_value("server", "debug")


def fatal_error_exit_or_backtrace(err: Exception,
                                  msg: str,
                                  logger: logging.Logger,
                                  *logargs, **logkwargs):
    """ standard handling of fatal errors. Logs a critical error, then, if
    debug mode is enabled, rethrows the error (to get a backtrace or debug),
    and if not, exits the program with return code 1

    arguments:
        err: the exception that caused this situation. Can be None, in which case
        will not be re-raised

        msg: the message you want to log
        logger: the logger to log to. Can be None, in which case a default logger
        will be obtained

        logargs, logkwargs: arguments to pass on to the logging function

    """
    if logger is None:
        logger = logging.getLogger("pushrocket-api")

    logger.critical(msg, *logargs, **logkwargs)
    logger.critical("exiting...")
    if Config.GLOBAL_BACKTRACE_ENABLE:
        if err is not None:
            raise err
    sys.exit(1)
