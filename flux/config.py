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

"""
Loads the Python configuration file for Flux CI.
"""

import os
import sys

loaded = False


def load(filename=None):
  global loaded
  if filename is None:
    filename = os.getenv('FLUX_CONFIG', 'flux_config.py')
  filename = os.path.expanduser(filename)
  if not os.path.isabs(filename):
    for path in [os.getenv('FLUX_ROOT'), '.', 'data']:
      if not path: continue
      if os.path.isfile(os.path.join(path, filename)):
        filename = os.path.join(path, filename)
        break
  filename = os.path.normpath(filename)
  with open(filename) as fp:
    exec(compile(fp.read(), filename, 'exec'), globals())
  loaded = True


def prepend_path(path, envvar='PATH'):
  ''' Prepend *path* to the ``PATH`` environment variable. '''

  path = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
  os.environ[envvar] = path + os.pathsep + os.environ[envvar]
  return os.environ[envvar]
