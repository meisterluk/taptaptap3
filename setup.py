#!/usr/bin/env python

"""
    taptaptap
    ~~~~~~~~~

    TAP file handling for cats \*rawwr*

    To install *taptaptap* use pip:

    .. code:: bash

        $ pip install taptaptap

    (C) 2014, Lukas Prokop, BSD 3-clause
"""

setup(
    name='taptaptap',
    version='1.0.0-stable',
    url='http://lukas-prokop.at/proj/taptaptap/',
    license='BSD',
    author='Lukas Prokop',
    author_email='admin@lukas-prokop.at',
    description='Test Anything Protocol handling for cats',
    long_description=__doc__,
    packages=['taptaptap'],
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Documentation',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Logging',
        'Topic :: System :: Systems Administration'
    ],
    test_suite='taptaptap.tests.run'
)