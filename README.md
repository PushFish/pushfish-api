PushFish API [![License](http://img.shields.io/badge/license-BSD-blue.svg?style=flat)](/LICENSE)
==================
This is the core for PushFish. It manages the whole shebang. 


## Configuration
The pushfish API server reads various options from a configuration file. This configuration file can be specified by setting the environment variable `PUSHFISH_CONFIG`. If this variable is not set, then the file is searched for in a default path.

```
     ~/.config/pushfish-api/pushfish-api.cfg # on Linux 
     %APPDATA%\pushfish-api\pushfish-api.cfg # on Windows
     ~/Library/Application Support/pushfish-api/pushfish-api.cfg # on OSX
```

where the value for "user" will be changed to your current username. If this file does not exist, then the API server will generate a default configuration, which looks like this:

```
[database]
#for mysql, use something like:
#uri = 'mysql+pymysql://pushfish@localhost/pushfish_api?charset=utf8mb4'

#for sqlite (the default), use something like:
uri = sqlite:////home/pushfish/.local/share/pushfish-api/pushfish-api.db

[dispatch]
google_api_key = 
google_gcm_sender_id = 509878466986
#point this at the pushfish-connectors zeroMQ pubsub socket
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
docker build -t pushfish-api:latest .
```

Run:

```
docker run pushfish-api:latest 
```

Run tests.py:

```
docker run pushfish-api:latest python tests.py
```
