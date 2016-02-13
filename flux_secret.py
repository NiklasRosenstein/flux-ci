#!/usr/bin/env python3
# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
This script generates a random sequence of characters that can be
used as webhook secret for webhook registrars that allow to manually
enter the secret.
'''

import random
import string

CHARPOOL = string.ascii_letters + string.digits


def main():
  print(''.join(random.choice(CHARPOOL) for i in range(32)))


if __name__ == '__main__':
  main()
