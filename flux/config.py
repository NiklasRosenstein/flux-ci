# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
Processes the ``flux_config.py`` module.
'''

from flux_config import *

# Insert the actual repository name into the repo configuration.
for name, config in repos.items():
  config['name'] = name
