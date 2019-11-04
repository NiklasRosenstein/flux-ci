# Copyright (c) 2019  Niklas Rosenstein
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

from nr.types.interface import implements
from ..core.build_manager import BuildClient, BuildData
from ..models import orm, Build
import os


@implements(BuildClient)
class LocalBuildClient(object):

  @orm.db_session
  def get_status(self, build_id):
    return Build[build_id].status

  @orm.db_session
  def set_status(self, build_id, status):
    Build[build_id].transition(status)

  @orm.db_session
  def start_section(self, build_id, description):
    Build[build_id]
    # TODO (@NiklasRosenstein)

  @orm.db_session
  def append_output(self, build_id, data):
    Build[build_id]
    # TODO (@NiklasRosenstein)

  @orm.db_session
  def set_revision_info(self, build_id, ref, commit_sha):
    build = Build[build_id]
    build.ref = ref or build.ref
    build.commit_sha = commit_sha

  @orm.db_session
  def list_overrides(self, build_id):
    build = Build[build_id]
    overrides_path = build.path(Build.Data_OverrideDir)
    if not os.path.isdir(overrides_path):
      return []
    filenames = []
    for root, dirs, files in os.walk(overrides_path):
      filenames.extend(files)
    print('@@@@', filenames)
    return filenames

  @orm.db_session
  def get_override(self, build_id, filename):
    build = Build[build_id]
    overrides_path = build.path(Build.Data_OverrideDir)
    # TODO (@NiklasRosenstein): Ensure that the filename is not outside
    #    of the overrides_path directory.
    filename = os.path.join(overrides_path, filename)
    return open(filename, 'rb')
