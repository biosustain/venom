from typing import Union, List, Mapping, NewType

_JSONArray = List['_JSONValue']
_JSONObject = Mapping[str, '_JSONValue']
_JSONValue = Union[None, bool, str, int, float, '_JSONObject', '_JSONArray']

JSONArray = NewType('JSONArray', _JSONArray)
JSONObject = NewType('JSONObject', _JSONObject)
JSONValue = NewType('JSONValue', _JSONValue)
