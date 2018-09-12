PushRocket API [![License](http://img.shields.io/badge/license-BSD-blue.svg?style=flat)](/LICENSE)
==================
This is the core for PushRocket. It manages the whole shebang. 


## Configuration
The pushrocket API server reads various options from a configuration file. This configuration file can be specified by setting the environment variable `PUSHROCKET_CONFIG`. If this variable is not set, then the file is searched for in a default path.

```
     ~/.config/pushrocket-api/pushrocket-api.cfg # on Linux 
     %APPDATA%\pushrocket-api\pushrocket-api.cfg # on Windows
     ~/Library/Application Support/pushrocket-api/pushrocket-api.cfg # on OSX
```

where the value for "user" will be changed to your current username. If this file does not exist, then the API server will generate a default configuration, which looks like this:

```
[database]
#for mysql, use something like:
#uri = 'mysql+pymysql://pushrocket@localhost/pushrocket_api?charset=utf8mb4'

#for sqlite (the default), use something like:
uri = sqlite:////home/pushrocket/.local/share/pushrocket-api/pushrocket-api.db

[dispatch]
google_api_key = 
google_gcm_sender_id = 509878466986
#point this at the pushrocket-connectors zeroMQ pubsub socket
zeromq_relay_uri = 

[server]
#set to 0 for production mode
debug = 1

```

the format of the database URI is an SQLAlchemy URL as [described here](http://docs.sqlalchemy.org/en/latest/core/engines.html)

Docker
------------------
Build the image:

```
docker build -t pushrocket-api:latest .
```

Run:

```
docker run pushrocket-api:latest 
```

Run tests.py:

```
docker run pushrocket-api:latest python tests.py
```
