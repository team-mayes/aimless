#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import aimless


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='aimless',
    version=aimless.__version__,
    description='A run script for submitting and processing aimless shooting simulations using Amber.',
    long_description=readme + '\n\n' + history,
    author='Chris Mayes',
    author_email='cmayes@cmayes.com',
    url='https://github.com/cmayes/aimless',
    packages=[
        'aimless',
    ],
    entry_points = {
        'console_scripts': [
            'aimless = aimless.aimless:main',
            'aimless_init = aimless.init_loc:main',
        ],
    },
    package_dir={'aimless': 'aimless'},
    package_data = {
        'aimless': ['skel/*.*', 'skel/tpl/*.*', 'skel/input/*.*'],
    },
    include_package_data=True,
    install_requires=[
    'mock',],
    license="BSD",
    zip_safe=False,
    keywords='aimless',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    test_suite='tests',
)