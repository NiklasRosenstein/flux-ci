# Flux &ndash; Lightweight private build server

Flux is a simple, [Flask] based build server that responds to Git
push events as triggered by GitHub, GitLab, BitBucket or Gogs.
While it is cross-platform and can on Windows, Linux and Mac OS,
it does not provide any kind of virtualization or container
management.

__Flux is__

* [x] Lightweight and easy to deploy
* [x] Operational on Windows, Linux and Mac OS
* [x] Supporting Gogs, GitHub, GitLab and BitBucket

__Flux is not__

* [ ] Secure as in "deployable for the public"!

__Todo__

* [ ] Support for GitLab and BitBucket
* [ ] Actually run builds

  [Flask]: http://flask.pocoo.org/
