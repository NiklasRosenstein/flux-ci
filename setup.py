
import io
import re
import setuptools
import sys

with io.open('src/flux/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('.\\README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['Flask>=0.10.1', 'pony>=0.7.3', 'pyOpenSSL>=0.15.1', 'cryptography>=2.0', 'nr.fs<=1.5.0,<1.6.0', 'nr.types>=4.0.0,<5.0.0', 'requests']

setuptools.setup(
  name = 'flux-ci',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Flux-CI is your own lightweight CI server.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/flux-ci',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  include_package_data = True,
  install_requires = requirements,
  python_requires = None,
  entry_points = {}
)
