# Flux &ndash; Lightweight CI Server ![](http://i.imgur.com/A0PsiQs.png) ![](http://i.imgur.com/uuTtLzU.png)

Flux is a simple, [Flask][] based continuous integration server
that responds to push events triggered by [Gogs][] and GitHub. It
is licensed under the MIT license.

For security reasons, Flux should be deployed over an SSL
encrypted proxy pass server (eg. via NGinx) and only for
internal purpose since it does not provide any mechanism
to prevent bad code from being executed.

__Screenshots__

<table><tr>
  <td><p align="center">Dashboard</p><a href="http://i.imgur.com/67dTFgb.png"><img src="http://i.imgur.com/67dTFgb.png"/></a></td>
  <td><p align="center">Repository Overview</p><a href="http://i.imgur.com/UuUIIvy.png"><img src="http://i.imgur.com/UuUIIvy.png"/></a></td>
  <td><p align="center">Repository Settings</p><a href="http://i.imgur.com/jt1SZZ6.png"><img src="http://i.imgur.com/jt1SZZ6.png"/></a></td>
  <td><p align="center">Build Details</p><a href="http://i.imgur.com/hWe3xD2.png"><img src="http://i.imgur.com/hWe3xD2.png"/></a></td>
  <td><p align="center">User Settings</p><a href="http://i.imgur.com/bgbqZDD.png"><img src="http://i.imgur.com/bgbqZDD.png"/></a></td>
</tr></table>

__Features__

* [x] Lightweight and easy to deploy
* [x] Operational on Windows, Linux and Mac OS
* [x] Supports [Gogs][] & GitHub
* [x] Stop & Restart builds
* [x] View and download build logs and artifacts
* [x] User access control

__Todo__

* [ ] Support for GitLab and BitBucket [#12](https://github.com/NiklasRosenstein/flux/issues/11)
* [ ] Distributed/multi-platform builds with build slaves [#9](https://github.com/NiklasRosenstein/flux/issues/9)

__Requirements__

* Python 3
* Git 2.3 (for `GIT_SSH_COMMAND`)
* [Flask][]
* [SQLAlchemy][]

__Configuration__

Check out [`flux_config.py`](flux_config.py) for the configuration
template and the parameter documentation.

__Installation__

```
$ git clone https://github.com/NiklasRosenstein/flux.git -b stable && cd flux
$ virtualenv --python python3 .env
$ source .env/bin/activate
(.env) $ pip install -r requirements.txt
(.env) $ nohup ./flux_run.py &
```

__Additional Links__

* [Gogs Webhook](https://gogs.io/docs/features/webhook)
* [GitHub Push](https://developer.github.com/v3/activity/events/types/#pushevent)
* [GitLab Push](https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#push-events)
* [BitBucket Push](https://confluence.atlassian.com/bitbucket/event-payloads-740262817.html#EventPayloads-Push)

  [Flask]: http://flask.pocoo.org/
  [SQLAlchemy]: http://www.sqlalchemy.org/
  [Gogs]: https://gogs.io/
