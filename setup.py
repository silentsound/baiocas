from __future__ import absolute_import
from __future__ import unicode_literals

from setuptools import find_packages
from setuptools import setup

version = '1.0.0'

#
# call setup
#
setup(
    name='baiocas',
    version=version,
    description='A simple Bayeux client for Python following the Comet paradigm.',
    long_description=None,
    classifiers=[],
    keywords='',
    author='Yoann Roman',
    author_email='silentsound@gmail.com',
    url='http://github.com/silentsound/baiocas',
    license='',
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
