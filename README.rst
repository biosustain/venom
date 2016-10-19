=========
Venom RPC
=========

.. image:: https://img.shields.io/travis/biosustain/venom/master.svg?style=flat-square
    :target: https://travis-ci.org/biosustain/venom

.. image:: https://img.shields.io/pypi/v/venom.svg?style=flat-square
    :target: https://pypi.python.org/pypi/venom

.. image:: https://img.shields.io/pypi/l/venom.svg?style=flat-square
    :target: https://pypi.python.org/pypi/venom

.. role:: strike
    :class: strike


Venom is an upcoming RPC framework for Python.

So far, Venom RPC supports unary requests & responses that are defined as methods on services. The framework is designed to support different server implementations. The first implementation is a HTTP/1 protocol implementation using "aiohttp".


Installation
============

Venom RPC alpha requires Python 3.5. The final version will likely require Python 3.6.

To install Venom using 'pip', enter:

::

    pip install venom==1.0.0a1[aiohttp]


Road map
========

A list of major features required for the first release:

 - Schema validation
 - Documentation

An unordered list of potential future features:

 - Streaming requests & responses with ZMQ
 - Unary HTTP/1 implementation with "flask"
 - WebSocket implementation with "aiohttp"

   This would be the only solution that fully supports streaming and can be used in the browser today.

 - gRPC (HTTP/2) implementation with e.g. "hyper-h2"
 
   There's already an experimental gRPC implentation based on "grpcio", but without true support for asynchronous calls because that is not supported by the official Python library.
   
 - MsgPack serialization support
 - Protocol Buffer support
 - JSON Hyper-Schema service
 - OpenAPI (Swagger) schema service
 - Client generation from schema

Streamed responses would use Python 3.6 asynchronous generators

