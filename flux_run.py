# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

from flux import app, config


if __name__ == '__main__':
  app.run(host=config.host, port=config.port, debug=config.debug)
