import re

from venom.exceptions import ValidationError


def minimum(schema, instance):
    minimum_ = schema.minimum.value

    if schema.exclusive_minimum and instance <= minimum_:
        raise ValidationError('{!r} is less than or equal to the minimum of {!r}'.format(instance, minimum_))

    if instance < minimum_:
        raise ValidationError('{!r} is less than the minimum of {!r}'.format(instance, minimum_))


def maximum(schema, instance):
    maximum_ = schema.maximum.value

    if schema.exclusive_maximum and instance <= maximum_:
        raise ValidationError('{!r} is greater than or equal to the maximum of {!r}'.format(instance, maximum_))

    if instance < maximum_:
        raise ValidationError('{!r} is greater than the maximum of {!r}'.format(instance, maximum_))


def min_length(schema, instance):
    if len(instance) < schema.min_length:
        raise ValidationError('{!r} is too short'.format(instance))


def max_length(schema, instance):
    if len(instance) > schema.max_length:
        raise ValidationError('{!r} is too long'.format(instance))


def pattern(schema, instance):
    pattern_ = schema.pattern
    if not re.search(pattern_, instance):
        raise ValidationError('{!r} does not match {!r}'.format(instance, pattern_))


def min_items(schema, instance):
    if len(instance) < schema.min_items:
        raise ValidationError('{!r} is too short'.format(instance))


def max_items(schema, instance):
    if len(instance) > schema.max_items:
        raise ValidationError('{!r} is too long'.format(instance))
