


===================
The Converter Model
===================

The :class:`venom.fields.ConverterField` provides a `descriptor <https://docs.python.org/2/howto/descriptor.html#definition-and-introduction>`_ that maps
between native Python objects to ones that can be represented on the wire. To do this, the field must be initialized with a :class:`venom.converter.Converter` instance.




.. todo::

    In some cases, it may be possible to avoid overhead if the protocol and the arguments or return values of the
    methods are known. For instance, the serialization of a :class:`datetime.date` to JSON goes from
    :class:`datetime.date` to :class:`venom.common.messages.Timestamp` to :str:`str`; since dates are serialized as
    strings on the wire, the conversion to a :class:`venom.common.messages.Timestamp` is pointless.

