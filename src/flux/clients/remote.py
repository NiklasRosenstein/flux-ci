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
import requests


@implements(BuildClient)
class RemoteBuildClient(object):

  def __init__(self, base_url, token):  # type: (str, str)
    self._base_url = base_url
    self._token = token
    self._session = requests.Session()
    self._session.headers['Authorization'] = 'Bearer ' + token
    self._session.headers['Content-Type'] = 'application/json'
    self._session.headers['Accept'] = 'application/json'

  def _request(self, method, url, *args, **kwargs):
    if url.startswith('/'):
      url = self._base_url + url
    response = self._session.request(method, url, *args, **kwargs)
    response.raise_for_status()
    return response

  @classmethod
  def from_build_data(cls, build_data):  # type: (BuildData) -> RemoteBuildClient
    return cls(build_data.build_api_url, build_data.build_token)

  def get_status(self, build_id):
    return self._request(
      'GET',
      '/build/{}/status').json()

  def set_status(self, build_id, status):
    return self._request(
      'POST',
      '/build/{}/status'.format(build_id),
      json=status).json()

  def start_section(self, build_id, description):
    return self._request(
      'PUT',
      '/build/{}/section'.format(build_id),
      json=description).json()

  def append_output(self, build_id, data):
    return self._request(
      'POST',
      '/build/{}/output/append'.format(build_did),
      data=data,
      headers={'Content-type': 'application/octet-stream'}).json()

  def set_revision_info(self, build_id, ref, commit_sha):
    return self._request(
      'POST',
      '/build/{}/revision-info'.format(build_id),
      json={'ref': ref, 'commit_sha': commit_sha}).json()

  def list_overrides(self, build_id):
    return self._request(
      'GET',
      '/build/{}/overrides'.format(build_id)).json()

  def get_override(self, build_id, filename):
    class ResponseFile(object):
      def __init__(self, response):
        self._response = response
      def read(self, n=None):
        return self._response.raw.read(n)
      def __enter__(self):
        return self
      def __exit__(self, *args):
        self._response.raw.close()
    return ResponseFile(self._request(
      'GET',
      '/build/{}/overrides/{}'.format(build_id, filename),
      stream=True))
