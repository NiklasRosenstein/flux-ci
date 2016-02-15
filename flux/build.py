# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
This module implements the Flux worker queue. Flux will start one or
more threads (based on the ``parallel_builds`` configuration value)
that will process the queue.
'''

import subprocess

from .models import Session, Build
from datetime import datetime


def start_queue():
  pass


def stop_queue():
  pass


def do_build(session, build):
  pass
