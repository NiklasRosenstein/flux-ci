'''
This is the Flux configuration file.
'''

import os

host = 'localhost'
port = 4042
debug = True

app_title = 'Flux CI'
app_url = 'http://localhost:4042'

# A valid SQLAlchemy database URL. Follow this link for more information:
# http://docs.sqlalchemy.org/en/rel_1_0/core/engines.html#database-urls
db_url = 'sqlite:///' + os.path.expanduser('~/flux/data.db')
db_encoding = 'utf8'

# Root username and password.
root_user = 'root'
root_password = 'alpine'

# Available choices of build scripts. The first matching option
# will be executed by Flux.
if os.name == 'nt':
  buildscripts = ['.flux-build.cmd']
else:
  buildscripts = ['.flux-build.sh']

# The directory in which all repositories are cloned to
# and the builds are executed in. This can also be overwritten
# on a per-repository basis.
build_dir = os.path.expanduser('~/flux/builds')

# Full path to the SSH identity file, or None to let SSH decide.
# This option can also be overwritten on a per-repository basis.
ssh_identity_file = None

# True if SSH verbose mode should be used.
ssh_verbose = False
