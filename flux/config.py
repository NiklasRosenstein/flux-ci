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

def prepend_path(path):
  ''' Prepend *path* to the ``PATH`` environment variable. '''

  path = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
  os.environ['PATH'] = path + os.pathsep + os.environ['PATH']

from flux_config import *

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
