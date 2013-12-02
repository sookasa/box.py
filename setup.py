#!/usr/bin/env python
from setuptools import setup, find_packages


TEST_REQUIRES = [
    'flexmock>=0.9.7',
    'nose',
    'coverage'
]

INSTALL_REQUIRES = [
    'requests>=1.0.0',
    'lxml>=3.0',
]

setup(
    name='box.py',
    version='1.2',
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
        'Programming Language :: Python :: 2.7',
    ],
)
