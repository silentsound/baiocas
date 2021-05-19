from os import path

from setuptools import find_packages
from setuptools import setup

version = '1.0.1'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='baiocas',
    version=version,
    description='A simple Bayeux client for Python following the Comet paradigm.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='',
    author='Yoann Roman',
    author_email='silentsound@gmail.com',
    url='http://github.com/silentsound/baiocas',
    license_files=["LICENSE"],
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pycurl >= 7.19.0',
        'tornado > 3.0'
    ],
    entry_points='',
    python_requires='>=3.7',
)
