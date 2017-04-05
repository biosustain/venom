from typing import Dict, Any, Tuple


# FIXME should be Generic
class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def _meta_obj_to_dict(meta_obj):
    dct = {}
    for k, v in meta_obj.__dict__.items():
        if not k.startswith('__'):
            dct[k] = v
    return dct

# FIXME should be AttributeDict[str, Any]
MetaDict = AttributeDict


def meta(bases, members, meta_name='Meta') -> Tuple[MetaDict, MetaDict]:
    meta_ = AttributeDict()
    for base in bases:
        if hasattr(base, '__meta__') and base.__meta__ is not None:
            meta_.update(base.__meta__)
        elif hasattr(base, meta_name):
            meta_.update(_meta_obj_to_dict(getattr(base, meta_name)))

    changes = {}
    if meta_name in members:
        changes = _meta_obj_to_dict(members[meta_name])
        meta_.update(changes)
    return meta_, AttributeDict(changes)


def upper_camelcase(s: str) -> str:
    return s.title().replace('_', '')


def camelcase(s):
    return s[0].lower() + s.title().replace('_', '')[1:] if s else s


class cached_property(object):
    """
    Descriptor (non-data) for building an attribute on-demand on first use.
    """
    def __init__(self, factory):
        """
        <factory> is called such: factory(instance) to build the attribute.
        """
        self._attr_name = factory.__name__
        self._factory = factory

    def __get__(self, instance, owner):
        # Build the attribute.
        attr = self._factory(instance)

        # Cache the value; hide ourselves.
        setattr(instance, self._attr_name, attr)

        return attr
