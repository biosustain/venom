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


Venom is an upcoming RPC framework for Python. It features a simple, testable, composable service model and support for the Python 3 *typing* module. It will support unary (single message) and streaming communication patterns inspired by gRPC. The framework uses a simple message format for communications, compatible with the ProtocolBuffer format. The aim of Venom is to provide a low overhead framework for RPC service development specifically in Python while sticking to language agnostic communication standards. 

So far, Venom RPC supports unary requests & replies that are defined as methods on services. The framework is designed to support different server implementations. 

The currently available implementations are:

- Unary HTTP/1 protocol implementation using *aiohttp* (asynchronous) or *flask* (synchronous only)
- Unary gRPC protocol implementation using *grpcio*
 
 
Documentation currently is minimal! Head to the ``examples/`` folder for more details.

Installation
============

Venom RPC alpha requires Python 3.5. The final version will likely require Python 3.6.

To install Venom using 'pip' for use with *aiohttp*, run:

::

    pip install venom[aiohttp]
    
To install Venom using 'pip' for use with *flask*, run:

::

    pip install flask-venom

Road map
========

A list of major features required for the first release:

- Schema validation
- Documentation
- Message generation from request arguments
- OpenAPI (Swagger) schema service for API reflection
 
An unordered list of potential future features:

- CLI for generating sharable stubs from services
- Streaming WebSocket implementation with *aiohttp*

  This would be the only solution that fully supports streaming and can be used in the browser today.

- Streaming gRPC (HTTP/2) implementation with e.g. *hyper-h2*

  There's already an experimental gRPC implementation based on *grpcio*, but without true support for asynchronous calls because that is not supported by the official Python library.
   
- MsgPack serialization support
- ProtocolBuffer support
   
  The problem with ProtocolBuffer as it stands now is that the official Python library for ProtocolBuffer is not very pythonic, 
  while ease of development in Python is the primary motivator behind Venom.

Streamed responses would use Python 3.6 asynchronous generators.

