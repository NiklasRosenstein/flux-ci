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

from nr.types.interface import Interface
from nr.types.struct import Field, Struct
from nr.types.struct.contrib.tojson import ToJson


class BuildNotRunningError(Exception):
  pass


class BuildClient(Interface):
  """ Interface for reporting the build status. """

  def get_status(self, build_id):  # type: (int) -> str
    pass

  def set_status(self, build_id, status):  # type: (int, str)
    pass

  def set_revision_info(self, build_id, rev, commit_sha):  # type: (int, str, str)
    pass

  def start_section(self, build_id, description):  # type: (int, str)
    pass

  def append_output(self, build_id, data):  # type: (int, bytes)
    pass

  def list_overrides(self, build_id):  # type: (int) -> List[str]
    pass

  def get_override(self, build_id, filename):  # type: (int, str) -> BinaryIO
    pass


class BuildData(Struct, ToJson):
  identity_file = Field(str, nullable=True)
  repository_id = Field(int)
  repository_name = Field(str)
  repository_clone_url = Field(str)
  build_id = Field(int)
  build_ref = Field(str)
  build_commit_sha = Field(str)
  build_api_url = Field(str)
  build_token = Field(str)


class BuildManager(Interface):

  def init(self):  # type: ()
    pass

  def shutdown(self):  # type: ()
    pass

  def start_build(self, build_data, build_client):  # type: (BuildData, BuildClient)
    """ Kick off a build. This should not block the current thread. """

  def cancel_build(self, build_id, build_client):  # type: (int, BuildClient)
    """ Cancel a build that is currently in progress. """
    # raises: BuildNotRunningError
