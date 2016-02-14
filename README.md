# Flux &ndash; Lightweight private build server

Flux is a simple, [Flask] based build server that responds to Git
push events as triggered by GitHub, GitLab, BitBucket or Gogs.
While it is cross-platform and can on Windows, Linux and Mac OS,
it does not provide any kind of virtualization or container
management. Thus, flux is not secure to be deployed as a public
service!

__Flux is__

* [x] Lightweight and easy to deploy
* [x] Operational on Windows, Linux and Mac OS
* [x] Tested for the GitHub and Gogs PUSH webhook
* [ ] A simple web interface to view build logs and download
      build artifacts with user access control

__Todo__

* [ ] Support for GitLab and BitBucket

  [Flask]: http://flask.pocoo.org/
