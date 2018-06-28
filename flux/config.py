# Copyright (c) 2016  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
'''
Processes the ``flux_config.py`` module.
'''

import os
import importlib
import sys

def prepend_path(path, envvar='PATH'):
  ''' Prepend *path* to the ``PATH`` environment variable. '''

  path = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
  os.environ[envvar] = path + os.pathsep + os.environ[envvar]
  return os.environ[envvar]

# Import config file more failsafe, without user getting python exception if missing
if importlib.util.find_spec("flux_config") is None and 'FLUX_ROOT' in os.environ:
  sys.path.append(os.environ['FLUX_ROOT'])
if importlib.util.find_spec("flux_config") is None and os.path.isfile(os.path.join(os.getcwd(), 'data', 'flux_config.py')):
  sys.path.append(os.path.join(os.getcwd(), 'data'))
if importlib.util.find_spec("flux_config") is not None:
  from flux_config import *
else:
  msg = "Error: File 'flux_config.py' not found. Looked in working directory and FLUX_ROOT."
  print(msg, file=sys.stderr)
  sys.exit(1)

for dirvar in ['root_dir', 'build_dir', 'override_dir']:
  if dirvar in globals():
    if not os.path.exists(globals()[dirvar]):
        os.makedirs(globals()[dirvar])

# Backwards-compatibility for the db_url that we used with SQLAlchemy.
# We only support parsing the sqlite:// schema here.
if 'db_url' in globals():
  if not db_url.startswith('sqlite://'):
    raise EnvironmentError('The db_url backwards compatibility is only '
                           'implemented for sqlite:// schema.')
  database = {
    'provider': 'sqlite',
    'filename': db_url[9:].lstrip('/'),
  }
