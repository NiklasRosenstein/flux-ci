
import os
import setuptools
import sys

def package_files(directory):
  paths = []
  for (path, directories, filenames) in os.walk(directory):
    for filename in filenames:
      paths.append(os.path.join('..', path, filename))
  return paths

if sys.version[:3] < '3.4':
  raise EnvironmentError('Flux CI is not compatible with Python {}'
                         .format(sys.version[:3]))

with open('README.md') as fp:
  readme = fp.read()

with open('requirements.txt') as fp:
  requirements = fp.readlines()

setuptools.setup(
  name = 'flux-ci',
  version = '1.1.0',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Flux is your own private CI server.',
  long_description = readme,
  long_description_content_type = 'text/markdown',
  license = 'MIT',
  url = 'https://github.com/NiklasRosenstein/flux-ci',
  install_requires = requirements,
  packages = setuptools.find_packages(),
  include_package_data = True,
)
