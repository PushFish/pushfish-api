PushRocket API [![License](http://img.shields.io/badge/license-BSD-blue.svg?style=flat)](/LICENSE)
==================
This is the core for PushRocket. It manages the whole shebang. 

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