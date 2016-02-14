# Flux &ndash; Lightweight private build server

Flux is a simple, [Flask][] based build server that responds to
push events triggered by [Gogs][] and GitHub.

For security reasons, Flux should be deployed over an SSL
encrypted proxy pass server (eg. via NGinx) and only for
internal purpose since it does not provide any mechanism
to prevent bad code from being executed.

![screenshot](http://i.imgur.com/91p3ZNX.png)

__Features__

* [x] Lightweight and easy to deploy
* [x] Operational on Windows, Linux and Mac OS
* [x] Supports [Gogs][] & GitHub
* [ ] Web interface to view realtime build queue, build logs
      and download artifacts with user access control

__Todo__

* [ ] Support for GitLab and BitBucket
* [ ] Support for generating build artifacts

__Requirements__

* Git 2.3 (for `GIT_SSH_COMMAND`)
* [Flask][]

__Configuration__

Check out [`flux_config.py`](flux_config.py) for the configuration
template and the parameter documentation.

__Callbacks__

* `/hook/push?api=(gogs|github)` &ndash; the push event callback

__Additional Links__

* [Gogs Webhook](https://gogs.io/docs/features/webhook)
* [GitHub Push](https://developer.github.com/v3/activity/events/types/#pushevent)
* [GitLab Push](https://gitlab.com/gitlab-org/gitlab-ce/blob/master/doc/web_hooks/web_hooks.md#push-events)
* [BitBucket Push](https://confluence.atlassian.com/bitbucket/event-payloads-740262817.html#EventPayloads-Push)

  [Flask]: http://flask.pocoo.org/
  [Gogs]: https://gogs.io/
