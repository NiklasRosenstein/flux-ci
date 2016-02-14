'''
This is the Flux configuration file.
'''

import os

host = ''
port = 4042
debug = True

# Available choices of build scripts. The first matching option
# will be executed by Flux.
if os.name == 'nt':
  buildscripts = ['.flux-build.cmd']
else:
  buildscripts = ['.flux-build.sh']

# The number of builds that may run in parallel. Usually 1 is
# a good value since the builds themselfs are usually already
# parallelised.
parallel_builds = 1

# The directory in which all repositories are cloned to
# and the builds are executed in. This can also be overwritten
# on a per-repository basis.
build_dir = os.path.expanduser('~/flux-builds')

# Full path to the SSH identity file, or None to let SSH decide.
# This option can also be overwritten on a per-repository basis.
ssh_identity_file = None

# True if SSH verbose mode should be used.
ssh_verbose = True

# Dictionary to configure accepted repositories. The secret is
# either provided by the webhook registrar or it allows you to
# specify a secret manually. In case of the latter, you can
# generate a new secret with the `flux_secret.py` script.
#
# Example configuration:
#
#   'gildarts/awesome-app': {
#     'secret': 'your-secret-key',
#     'clone_url': 'git@gildarts-web.com:gildarts/awesome-app.git',
#   }
#
# * secret: The secret that is sent by the Git server to authenticate.
# * clone_url: The URL from which Flux will clone the repository.
# * ssh_identity_file: Override for the global ssh_identity_file
#   configuration value.
# * build_dir: Override for the global build_dir configuration value.
# * refs: A list of Git refs on which a build is triggered. Pushes
#   to other refs will be ignored.
#
repos = {
}
