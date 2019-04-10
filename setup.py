import setuptools
import re

VERSION = None
with open('nutshell/__init__.py') as f:
    VERSION = re.search(r"^__version__\s*=\s*'(\d+\.\d+\.\d+\w*)'", f.read(), re.MULTILINE).group(1)

if VERSION is None:
    raise RuntimeError('Missing or invalid version number')

setuptools.setup(
  name='whatgif',
  author='github/supposedly',
  license='MIT',
  version=VERSION,
  packages=setuptools.find_packages(),
  include_package_data=True,
  url='https://github.com/supposedly/whatgif',
  description='Python GIF-creation stuff',
  python_requires='>=3.3'
)
