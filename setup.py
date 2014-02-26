#!/usr/bin/env python
from setuptools import setup, find_packages
import platform

TEST_REQUIRES = [
    'flexmock>=0.9.7',
    'nose',
    'coverage',
    'unittest2'
]

INSTALL_REQUIRES = [
    'requests>=1.0.0',
]
INSTALL_REQUIRES_CPYTHON = [
    'lxml>=3.0',
]

# lxml 3.3.x is broken with pypy. lets see how this plays out...
INSTALL_REQUIRES_PYPY = [
    'lxml>3.0,<3.3.beta'
]

if platform.python_implementation().lower() != 'pypy':
    INSTALL_REQUIRES += INSTALL_REQUIRES_CPYTHON
else:
    INSTALL_REQUIRES += INSTALL_REQUIRES_PYPY


setup(
    name='box.py',
    version='1.2.8',
    author='Sookasa',
    author_email='dev@sookasa.com',
    url='http://github.com/sookasa/box.py',
    description='Python client for Box',
    long_description=__doc__,
    packages=find_packages(exclude=("tests", "tests.*",)),
    zip_safe=False,
    extras_require={
        'tests': TEST_REQUIRES,
    },
    license='BSD',
    tests_require=TEST_REQUIRES,
    install_requires=INSTALL_REQUIRES,
    test_suite='tests',
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
