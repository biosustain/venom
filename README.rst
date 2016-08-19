=========
Venom RPC
=========

Venom will be an RPC framework for Python.


Road map
========

A list of major features required for the first release:

 - Schema validation
 - Error handling
 - Documentation

An unordered list of future features:

 - Streaming requests & responses with ZMQ
 - Unary HTTP/1 implementation with "aiohttp"
 - Unary HTTP/1 implementation with "flask"
 - WebSocket implementation with "aiohttp"

   This would be the only solution that fully supports streaming and can be used in the browser today.

 - gRPC (HTTP/2) implementation with e.g. "hyper-h2"
 - MsgPack serialization support
 - Protocol Buffer support
 - JSON Hyper-Schema service
 - OpenAPI (Swagger) schema service
 - Remote generation from schema
