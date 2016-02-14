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
* [ ] Support for generating build artifacts

### Setup

Say you have an instance of [Gogs][] running on your local machine.
Install Flux into a virtual environment and update the `flux_config.py`

```python
ssh_identity_file = os.path.expanduser('~/.ssh/id_rsa_nopw')
repos = {
  'owner/repository': {
    'secret': 'mysecretkey',
    'clone_url': 'localhost:owner/repository.git',
  },
}
```

Next, add the following webhook to your repository:

    http://localhost:4042/hook/push?api=gogs

And start Flux with `./flux_run.py`.

> Note: For deployment on a production server, you should make use of
> NGinx or Apache with an SSL certificate and then do a proxy pass to
> the local Flux server for secure exchange of the repository secret.

  [Flask]: http://flask.pocoo.org/
  [Gogs]: https://gogs.io/
