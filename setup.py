# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import codecs
from setuptools import setup, find_packages

setup(
    name='venom',
    version='2.0.0',
    packages=find_packages(exclude=['*tests*']),
    url='https://github.com/biosustain/venom',
    license='MIT',
    author='Lars Schöning',
    author_email='lays@biosustain.dtu.dk',
    description='Venom is an upcoming RPC framework for Python',
    long_description=codecs.open('README.rst', encoding='utf-8').read(),
    test_suite='nose.collector',
    tests_require=[
        'aiohttp>=2.0.1',
        'ujson',
        'nose'
    ],
    install_requires=[
        'blinker>=1.4.0',
        'aniso8601>=1.2.1'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    zip_safe=False,
    extras_require={
        'docs': ['Sphinx>=1.5.5'],
        'aiohttp': ['aiohttp>=1.2.0', 'ujson'],
        'grpc': ['grpcio'],
    }
)
