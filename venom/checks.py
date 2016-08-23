"""

Checks are constraints for JSON-compatible types. The rationale for calling these "check" rather than "constraint" or
"validator" is that it is shorter to write.

"""
from typing import Union, Generic, TypeVar, Tuple, Iterable
import re


class Check(object):
    def __init__(self, *, type_: Union[type, Tuple[type, ...]] = None) -> None:
        self.type = type_

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def _check(self, instance):
        """
        The implementation of the check that assumes that the value is restricted to the right type.

        :param instance:
        :return:
        """
        return True

    def check(self, instance):
        # ignore any checks not for a specific type.
        if self.type is not None and not isinstance(instance, self.type):
            return False

        return self._check(instance)

    def schema(self):
        """
        A JSON schema object describing this check, if possible.

        :return:
        """
        return {}


# ----------------------------------------------------------------------------------------------------------------------
# JSON PropertySchema validation for any instance type
# ----------------------------------------------------------------------------------------------------------------------

T = TypeVar('T')


class Choice(Generic[T], Check):
    """
    This behaves like an an enumeration and should be used when no :class:`enum.Enum` is available.
    """
    def __init__(self, choices: Iterable[T]) -> None:
        super().__init__(type_=(int, str))
        self.choices = tuple(choices)

    def _check(self, instance):
        return instance in self.choices

    def schema(self):
        return {"enum": self.choices}

# ----------------------------------------------------------------------------------------------------------------------
# JSON PropertySchema validation for "object"
# ----------------------------------------------------------------------------------------------------------------------

# TODO
# class KeyPattern(Check):
#     def __init__(self, pattern: str) -> None:
#         super().__init__(type_=dict)
#         self.pattern = pattern
#
#     @property
#     def pattern(self):
#         return self._pattern
#
#     @pattern.setter
#     def pattern(self, pattern):
#         self._pattern_re = re.compile(pattern)
#         self._pattern = pattern
#
#     def _check(self, instance):
#         for key in instance.values():
#             if self._pattern_re.match(key) is None:
#                 return False
#         return True


class MinProperties(Check):
    def __init__(self, value: int) -> None:
        super().__init__(type_=dict)
        self.value = value

    def schema(self):
        return {"minProperties": self.value}


class MaxProperties(Check):
    def __init__(self, value: int) -> None:
        super().__init__(type_=dict)
        self.value = value

    def schema(self):
        return {"maxProperties": self.value}


MapCheck = Union[MinProperties, MaxProperties]


# ----------------------------------------------------------------------------------------------------------------------
# JSON PropertySchema validation for "number" and "integer"
# ----------------------------------------------------------------------------------------------------------------------

class Between(Check):
    def __init__(self,
                 minimum: Union[int, float],
                 maximum: Union[int, float],
                 *,
                 exclusive_minimum: bool = False,
                 exclusive_maximum: bool = False) -> None:
        super().__init__(type_=(int, float))
        self.minimum = minimum
        self.maximum = maximum
        self.exclusive_minimum = exclusive_minimum
        self.exclusive_maximum = exclusive_maximum

    def schema(self):
        schema = {
            "minimum": self.minimum,
            "maximum": self.maximum
        }

        if self.exclusive_minimum:
            schema["exclusiveMinimum"] = True
        if self.exclusive_maximum:
            schema["exclusiveMaximum"] = True
        return schema


class GreaterThan(Check):
    def __init__(self, value: Union[int, float]) -> None:
        super().__init__(type_=(int, float))
        self.value = value

    def schema(self):
        return {"minimum": self.value, "exclusiveMinimum": True}


class LessThan(Check):
    def __init__(self, value: Union[int, float]) -> None:
        super().__init__(type_=(int, float))
        self.value = value

    def schema(self):
        return {"maximum": self.value, "exclusiveMinimum": True}

class GreaterThanEqual(Check):
    def __init__(self, value: Union[int, float]) -> None:
        super().__init__(type_=(int, float))
        self.value = value

    def schema(self):
        return {"minimum": self.value}


class LessThanEqual(Check):
    def __init__(self, value: Union[int, float]) -> None:
        super().__init__(type_=(int, float))
        self.value = value

    def schema(self):
        return {"maximum": self.value}


GT = GreaterThan
GTE = GreaterThanEqual
LT = LessThan
LTE = LessThanEqual

NumberCheck = Union['FormatCheck', Between, LessThan, LessThanEqual, GreaterThan, GreaterThanEqual]


# ----------------------------------------------------------------------------------------------------------------------
# JSON PropertySchema validation for "string"
# ----------------------------------------------------------------------------------------------------------------------

class MinLength(Check):
    def __init__(self, value: int) -> None:
        super().__init__(type_=str)
        self.value = value

    def schema(self):
        return {"minLength": self.value}


class MaxLength(Check):
    def __init__(self, value: int) -> None:
        super().__init__(type_=str)
        self.value = value

    def schema(self):
        return {"maxLength": self.value}


class PatternCheck(Check):
    def __init__(self, pattern: str) -> None:
        super().__init__(type_=str)
        self.pattern = pattern

    @property
    def pattern(self):
        return self._pattern

    @pattern.setter
    def pattern(self, pattern):
        self._pattern_re = re.compile(pattern)
        self._pattern = pattern

    def schema(self):
        return {"pattern": self.pattern}


class FormatCheck(Check):
    def __init__(self, format_: str) -> None:
        super().__init__(type_=(str, int, float))
        self.format = format_

    def schema(self):
        return {"format": self.format}


StringCheck = Union[FormatCheck, Choice[str], MinLength, MaxLength]


# ----------------------------------------------------------------------------------------------------------------------
# JSON PropertySchema validation for "array"
# ----------------------------------------------------------------------------------------------------------------------

class MinItems(Check):
    def __init__(self, value: int) -> None:
        super().__init__(type_=(tuple, list, set))
        self.value = value

    def schema(self):
        return {"minItems": self.value}


class MaxItems(Check):
    def __init__(self, value: int) -> None:
        super().__init__(type_=(tuple, list, set))
        self.value = value

    def schema(self):
        return {"maxItems": self.value}


class UniqueItems(Check):
    def __init__(self, unique: bool = True) -> None:
        super().__init__(type_=(tuple, list, set))
        self.unique = unique

    def schema(self):
        return {"unique": self.unique}


RepeatCheck = Union[MinItems, MaxItems, UniqueItems]
