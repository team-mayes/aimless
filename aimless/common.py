from abc import ABCMeta, abstractmethod
from datetime import datetime
import inspect
import logging
import os

class JobSlaveError(Exception): pass
class SubmissionError(JobSlaveError): pass
class StatusError(JobSlaveError): pass
class OutputParsingError(JobSlaveError): pass
class PersistenceError(JobSlaveError): pass
class NotFoundError(JobSlaveError): pass
class InvalidDataError(JobSlaveError): pass

logger = logging.getLogger("jslave_common")


class NonStringIterable:
    """Iterable check ABC that distinguishes Iterables minus str.
    The Iterable check explicitly adds str, so this class uses the
    same check minus the "str" registration.
    From http://stackoverflow.com/a/1055540

    isinstance([1,2,3], NonStringIterable) will be True.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __iter__(self):
        while False:
            yield None

    @classmethod
    def __subclasshook__(cls, C):
        if cls is NonStringIterable:
            if any("__iter__" in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented

def cmakedir(tgt_dir):
    """
    Creates the given directory and its parent directories if it
    does not already exist.

    Keyword arguments:
    tgt_dir -- The directory to create
    
    """
    if not os.path.exists(tgt_dir):
        os.makedirs(tgt_dir)
    elif not os.path.isdir(tgt_dir):
        raise NotFoundError("Resource %s exists and is not a dir" % 
                        tgt_dir)

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

def to_datetime(raw_val):
    "Attempts to coerce the given value into a datetime instance."
    if raw_val == None:
        return raw_val
    if isinstance(raw_val, datetime):
        return raw_val
    try:
        return datetime.fromtimestamp(float(raw_val))
    except ValueError:
        return datetime.strptime(raw_val, "%Y-%m-%dT%H:%M:%S")
    except TypeError, e:
        raise InvalidDataError("Type %s can't be made a datetime: %s", (type(raw_val), e))

def as_not_falsy(val, msg="Object evaluates to False"):
    """Test that the value does not evaluate to false; raises InvalidDataError
    if the data is False."""
    if val:
        return val
    else:
        raise InvalidDataError(msg)

def scalarize(val):
    """If val is an iterable, returns the first element or None. Non-iterables
    are returned unmodified.
    """
    if (isinstance(val, NonStringIterable)):
        return next(iter(val), None)
    else:
        return val

## StructEq and AutoRepr are from 
## http://qinsb.blogspot.com/2009/03/automatic-repr-and-eq-for-data.html

class StructEq(object):

    """A simple mixin that defines equality based on the objects attributes.

    This class is especially useful if you're in a situation where one object
    might not have all the attributes of the other, and your __eq__ method
    would otherwise have to remember to deal with that.

    Classes extending StructEq should only be used in hash tables if all of the
    class members are also hashable.

    Also, classes extending StructEq should not create a cyclic graph where all
    nodes in the cycle extend StructEq, or there will be an infinite loop.
    Cycles are allowed, but objects creating cycles should have their own
    __eq__ methods that prevent the infinite loop.

    To designate certain attributes that shouldn't be checked for equality,
    override the class level variable NONEQ_ATTRS with the set of attrs you
    don't want to check.

    """

    NONEQ_ATTRS = frozenset()

    def __eq__(self, other):
        """Return True if of the same type and all attributes are equal."""
        if self is other:
            return True
        if type(self) != type(other):
            return False
        if len(self.__dict__) != len(other.__dict__):
            return False
        keys = ((frozenset(self.__dict__.iterkeys()) |
                 frozenset(other.__dict__.iterkeys())) - self.NONEQ_ATTRS)
        for key in keys:
            left_elt = self.__dict__.get(key)
            right_elt = other.__dict__.get(key)
            if not (left_elt == right_elt):
                return False
        return True

    def __ne__(self, other):
        """Return False if of different types or any attributes are unequal."""
        return not (self == other)

    def __hash__(self):
        """Return a reasonable hash value that uses all object attributes."""
        # We use frozenset here, because if we used tuple, the order of the
        # items in the tuple would be determined by the order in which the items
        # were returned, which depends on the order in which they were added to
        # __dict__.  Using frozenset fixes this, because it imposes an ordering
        # based on the items themselves, rather than the keys.
        return hash(frozenset(self.__dict__.iteritems()))


class AutoRepr(object):

    """A mixin that defines __repr__ by introspecting on the constructor.

    If the constructor for a class Quux of the form::
      def __init__(self, foo, bar, baz):
    Then __repr__ will return something like::
      "%s(%r, %r, %r)" % (type(self).__name__, self.foo, self.bar, self.baz)

    This is useful when you are defining classes that are basically just
    structs, and you want them to print out a valid repr.  This is especially
    useful in combination with StructEq when writing tests, because you can copy
    and paste the actual value into the expected value and it will be valid
    Python.

    """

    def __repr__(self):
        pieces = []
        class_ = type(self)
        module = inspect.getmodule(class_)
        short_module_name = os.path.basename(module.__file__).split('.')[0]
        pieces.append(short_module_name)
        pieces.append('.')
        pieces.append(class_.__name__)
        pieces.append("(")
        if inspect.ismethod(self.__init__):
            (args, varargs, kwargs, defaults) = inspect.getargspec(self.__init__)
        else:
            # This means that the class has the default __init__ method with no
            # arguments.
            (args, varargs, kwargs, defaults) = ([], None, None, [])
        if defaults is None:
            defaults = []
        def special_getattr(jfld):
            # The idiom described in PEP 8 for avoiding collisions with reserved
            # words and buitins is to append '_' to to an identifier.  However,
            # since attributes can't collide with builtins, you see code like:
            # `self.type = type_`, which we allow for by checking for both
            # cases.
            if hasattr(self, jfld):
                value = getattr(self, jfld)
            elif jfld.endswith('_') and hasattr(self, jfld[:-1]):
                value = getattr(self, jfld[:-1])
            else:
                raise TypeError("AutoRepr can't find a jfld corresponding to "
                                "the __init__ argument %r." % arg)
            return value
        arg_strs = []
        # Deal with regular positional arguments.
        for arg in args[1:-len(defaults) if defaults else None]:
            arg_strs.append(repr(special_getattr(arg)))
        # Deal with optional keyword or default value arguments.
        for (default, arg) in zip(defaults, args[len(args) - len(defaults):]):
            value = special_getattr(arg)
            if value != default:
                arg_strs.append("%s=%r" % (arg, value))
        pieces.append(", ".join(arg_strs))
        pieces.append(")")
        return "".join(pieces)

# PENDING, SAVED, and SUBMITTED are non-Torque states
STATES = enum(COMPLETED='completed', EXITING='exiting', HELD='held',
      QUEUED='queued', RUNNING='running', MOVED='moved', WAITING='waiting',
      SUSPENDED='suspended', PENDING='pending', SAVED='saved',
      SUBMITTED='submitted')

