from setuptools import setup, Command, find_packages

version = '0.1.0'

#
# call setup
#
setup(
    name                 = 'baiocas',
    version              = version,
    description          = 'A simple Bayeux client for Python following the Comet paradigm.',
    long_description     = None,
    classifiers          = [],
    keywords             = '',
    author               = 'Yoann Roman',
    author_email         = 'silentsound@gmail.com',
    url                  = 'http://github.com/silentsound/baiocas',
    license              = '',
    packages             = find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data = True,
    zip_safe             = False,
    install_requires     = [
        'mock >= 0.7.2',
        'pycurl >= 7.19.0',
        'pytest >= 2.1.3',
        'simplejson >= 2.2.1',
        'tornado >= 2.2.0'
    ],
    entry_points         = '',
)
