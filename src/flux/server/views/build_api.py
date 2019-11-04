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

import json
import flask

from .. import app
from ...clients.local import LocalBuildClient


def json_response(data, code=200, headers=None):
  if headers is None:
    headers = {}
  return json.dumps(data), code, headers


@app.route('/api/internal/build/<build_id>/status', methods=['GET'])
def get_status(build_id):
  return json_response(LocalBuildClient().get_status(build_id))


@app.route('/api/internal/build/<build_id>/status', methods=['POST'])
def set_status(build_id):
  status = flask.request.json
  return json_response(LocalBuildClient().set_status(build_id, status))


@app.route('/api/internal/build/<build_id>/section', methods=['PUT'])
def start_section(build_id):
  description = flask.request.json
  return json_response(LocalBuildClient().start_section(build_id, description))


@app.route('/api/internal/build/<build_id>/output/append', methods=['POST'])
def append_output(build_id):
  return json_response(LocalBuildClient().append_output(build_id, flask.request.data))


@app.route('/api/internal/build/<build_id>/revision-info', methods=['POST'])
def set_revision_info(build_id):
  data = flask.request.json
  ref = data['ref']
  commit_sha = data['commit_sha']
  return json_response(LocalBuildClient().set_revision_info(build_id, ref, commit_sha))


@app.route('/api/internal/build/<build_id>/overrides', methods=['GET'])
def list_overrides(build_id):
  return json_response(LocalBuildClient().list_overrides(build_id))


@app.route('/api/internal/build/<build_id>/overrides/<path:filename>', methods=['GET'])
def get_override(build_id, filename):
  return LocalBuildClient().get_override(build_id, filename).read()   # TODO: stream
