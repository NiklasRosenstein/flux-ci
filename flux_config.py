'''
This is the Flux configuration file.
'''

import os
from datetime import timedelta
from flux.config import prepend_path

## If your system does not provide the required Git version (>= 2.3),
## you can compile it by yourself and install it locally (or not install
## it at all and keep all build products in the source tree). Uncomment
## the next line and adjust path to update the PATH environment variable
## so flux can find the newer Git version.
# prepend_path('~/git')

## Root directory where the flux data is stored, repositories are checked
## out and built. Defaults to the flux application directory.
root_dir = os.path.abspath(os.environ.get('FLUX_ROOT', os.path.dirname(__file__)))

## The host address to which the Flux web server should bind to. For
## real world deployment, you should hide Flux behind a NGinx/Apache/etc.
## proxy server with SSL support.
host = os.environ.get('FLUX_HOST', 'localhost')

## Port of the Flux web server.
port = int(os.environ.get('FLUX_PORT', 4042))

## Enable this option to increase the logging output, wich makes it
## easier to find and debug problems with Flux.
debug = True

## The application title displayed in the header of the website.
app_title = 'Flux CI'

## The application URL that is required in various places. Adjust
## if it differs from the HOST:PORT combination.
app_url = os.environ.get('FLUX_APP_URL', 'http://{}:{}'.format(host, port))

## The server name. This is important for redirects, especially when
## behind a proxy eg. via NGinx. Make sure to set the 'Host' header
## to this server name when passing the request to the Flux app.
##
## When deploying flux in a Docker container. you must set this to the
## name that is addressable from the outside of the container, eg.
## "localhost:4042".
server_name = os.environ.get('FLUX_SERVER_NAME', app_url.replace('http://', '').replace('https://', ''))

## Secret key required for HTTP session. Use your own random key
## for deployment! Here's a useful link to quickly get a bunch of
## such random secret strings:
##
## https://api.wordpress.org/secret-key/1.1/salt/
secret_key = 'ThAHy8oxRiNIQDBnVlNjEVY78fXdWHdi'

## The PonyORM database configuration.
## https://ponyorm.com/
database = {
  'provider': 'sqlite',
  'filename': '{}/db.sqlite'.format(root_dir),
  'create_db': True
}

## Username and password of the root user with full access.
root_user = 'root'
root_password = 'alpine'

## The number of builds that may be executed in parallel. One is
## usually a good value since today's builds (depending on the used
## build system) are usually multiprocessed already.
parallel_builds = 1

## Filenames of build scripts in a repository. The first matching
## filename will be used.
if os.name == 'nt':
  build_scripts = ['.flux-build.cmd']
else:
  build_scripts = ['.flux-build.sh']

## The directory in which all repositories are cloned to
## and the builds are executed in. The directory structure that
## is created by flux is <owner>/<repo>/<build_num> .
build_dir = os.path.join(root_dir, 'builds')

## The directory which contain file overrides for repositories.
## Anything in the corresponding repository folder
## will overwrite repository contents after clone.
## This is especially useful, if you want to make sure your
## desired build script and nothing else gets executed
## or to override e.g. an icon.
## -> Example:
## override_dir/<owner>/<repo>/ containing icon.png
## -> gets copied to (after clone)
## build_dir/<owner>/<repo>/<build_num>/icon.png
override_dir = os.path.join(root_dir, 'overrides')

## Full path to the SSH identity file, or None to let SSH decide.
ssh_identity_file = None

## True if SSH verbose mode should be used.
ssh_verbose = False

## The time that a login token should be valid for. Specify "None" to
## prevent login tokens from expiring.
login_token_duration = timedelta(hours=6)
