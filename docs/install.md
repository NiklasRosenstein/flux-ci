+++
title = "Installation"
ordering = 1
+++

## Requirements

* Python 3
* Git 2.3 (for `GIT_SSH_COMMAND`)
* [Flask][]
* [SQLAlchemy][]

[Flask]: http://flask.pocoo.org/
[SQLAlchemy]: http://www.sqlalchemy.org/

## Manual Installation

    $ git clone https://github.com/NiklasRosenstein/flux.git -b stable && cd stable
    $ virtualenv .venv
    $ .venv/bin/pip install -r requirements.txt
    # Update the secret key and root account credentials in flux_config.py
    $ $(EDITOR) flux_config.py
    $ .venv/bin/python flux_run.py

Visit http://localhost:4042. Also check out the [Configuration](../config) page.

Depending on the database you want to use, you may need to install additional
modules into the virtual environment, like `psycopg2` for PostgreSQL. The
default database uses an SQLite database file in the current working directory.

For security reasons, you should place the Flux CI server behind an SSL
encrypted proxy pass server. This is an example configuration for nginx:

```nginx
server {
  listen 80;
  listen 443;
  ssl on;
  server_name flux.example.com;

  if ($scheme = http) {
    return 301 https://$host$request_uri;
  }

  location / {
    proxy_pass http://0.0.0.0:4042$request_uri;
    proxy_set_header Host $host;
  }
}
```

## Docker Setup

*TODO ...*

## Manage the server

To run Flux on a specific user or simply for using daemon manager, I recommend
using the [nocrux][] daemon manager.

```
$ pip install --user nocrux
$ cat nocrux_config.py
register_daemon(
  name = 'flux',
  prog = '/home/flux/flux/.env/bin/python',
  args = ['flux_run.py'],
  cwd  = '/home/flux/flux',
  user = 'flux',
  group = 'flux'
)
$ nocrux flux start
[nocrux]: (flux) starting "/home/flux/flux/.env/bin/python flux_run.py"
[nocrux]: (flux) started. (pid: 30747)
```

[nocrux]: https://github.com/NiklasRosenstein/nocrux
