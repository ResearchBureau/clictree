"""Everything that can serve as a unique identifier for something in CLICTree

Location Hierarchy
------------------
To point to a data item, 4 levels are important:
DataTtem <-  Collection <- Domain <- Context

* A DataItem represents one piece of data
* A Collection contains references to data items
* A Domain can contain multiple collections, and represents a pseudonymization domain
* A Context is linked to authentication. The context determines which resources,
  credentials are available.

"""
from dataclasses import dataclass
from enum import IntEnum
from itertools import dropwhile
from typing import Optional


@dataclass(frozen=True)
class Identifier:
    """A key to identify a single thing. Is frozen data class so any instance with
    the same value will be seen as the same thing.

    Should always be serializable to string"""

    value: str

    def __str__(self):
        return f"{type(self).__name__} : {self.value}"


class ResultReference(Identifier):
    """A key referencing a transformation of a single DataItem.

    Allows the 'naming' of any Transformation result, making it possible to create a
    uri that points to a second uri. Important for linking, referencing and chaining"""
    pass

class URIScope(IntEnum):
    """How broad is a URI's area of validity? Does it only reference a local DataItem
    (small scope), or does it also define which container, domain, context this is in
    (large scope)?

    Important for permissions management. Only high-level operations can use broad-scope
    urls
    """
    DATA_ITEM = 0
    CONTAINER = 1
    DOMAIN = 2
    CONTEXT = 3

class URIReferenceLevel(IntEnum):
    """At which level does this URI refence an object? Does it reference a DataItem
    (low reference level), an entire context (high reference level),
    or something in between?
    """
    DATA_ITEM = 0
    CONTAINER = 1
    DOMAIN = 2
    CONTEXT = 3

class URI:
    """Identifies a location or object.

    format: /<context>/<domain>/<container>/<uid>

    * '/a/b/c/d' fully locates a uid 'a' in a container 'b', domain 'c', context 'd'

    You can leave off the root indicator to create a relative reference:
    * 'a'/'b' is a valid URI for a data item 'a' within a domain 'b'

    The root indicator (slash) is important in interpreting a URL.
    Without root indicator, location elements are read from right to left:

    * 'a/b' means 'b' is the left-most location element <uid>,
       meaning 'a/b' refers to uid 'b' in container 'a'
    With root indicator, location elements are read from left to right:

    * '/a/b' means 'a' is the right-most location element <context>,
       meaning '/a/b' refers to domain 'b' in context 'a'

    You can use empty values to create relative links at any level:
    *  '//a/b' is a valid reference to a container 'b' in domain 'a'

    Location elements can be empty, but have to be consecutive:

    * 'a/b' is a valid reference to DataItem 'b' in container 'a'

    * '///a/b' means the same and is also valid

    * '//a//b' is not consecutive and thus invalid. DataItem 'b' in domain 'a' is
      meaningless without knowing the container in between.

    Properties
    ----------
    A URI should be serializable to string
    """

    SEPARATOR = ":"
    ROOT_INDICATOR = "/"

    def __init__(self, context_name: Optional[str]=None, domain_name:Optional[str]=None,
                 container_name:Optional[str]=None,
                 data_item_uid:Optional[str]=None):
        self.context_name = context_name
        self.domain_name = domain_name
        self.container_name = container_name
        self.data_item_uid = data_item_uid

    def __eq__(self, other):
        if not hasattr(other, "as_tuple"):
            return False
        else:
            return self.as_tuple() == other.as_tuple()

    def __hash__(self):
        """A URI is fully described by its string value"""
        return hash(self.to_string())


    @classmethod
    def is_root(cls, string_in):
        """This string denotes a URI starting at root. It is not relative"""
        return string_in.startswith(cls.ROOT_INDICATOR)

    @classmethod
    def from_string(cls, string_in):
        """Parse UID from string

        Format
        ------
        /<context>/<domain>/<container>/<uid>
        Slash-separated. Initial slash denotes root level.
        uri without root is assumed to be partial, and filled from right to left.
        For example "boo/faz" is a partial URI for a container 'boo' containing item
        'faz', while "/boo/faz" is absolute, denoting a context 'boo' containing a
        domain 'faz'

        Raises
        ------
        ValueError
            If string cannot be parsed
        """

        if cls.is_root(string_in):
            # this is an absolute path. Fill context from left to right.
            # Could not think of an elegant way to do this.
            to_parse = string_in[1:]
            params = (to_parse.split(cls.SEPARATOR) + [""] * 4)[:4]
        else:
            # this is relative. Fill context from right to left
            params = (([""] * 4) + string_in.split(cls.SEPARATOR))[-4:]

        params = tuple(None if x is "" else x for x in params)
        return cls.from_tuple(params)

    @classmethod
    def from_tuple(cls, tuple_in):
        """Expects exactly size-4 tuple. None values allowed
        Raises
        ------
        ValueError
            If the tuple results in an invalid URI
        """
        context, domain, container, uid = tuple_in
        created = cls(context, domain, container, uid)
        if created.is_valid():
            return created
        else:
            raise ValueError(f"Cannot create valid URL from tuple {tuple_in}")

    def scope(self) -> URIScope:
        # get highest filled in element
        if self.context_name:
            return URIScope.CONTEXT
        elif self.domain_name:
            return URIScope.DOMAIN
        elif self.container_name:
            return URIScope.CONTAINER
        elif self.data_item_uid:
            return URIScope.DATA_ITEM
        raise ValueError("Could not determine scope. Is this URI empty?")


    def reference_level(self) -> URIReferenceLevel:
        """At which level does this URI refence an object? Does it reference a DataItem
        (low reference level), an entire context (high reference level),
        or something in between?
        """
        # get lowest filled in element
        if self.data_item_uid:
            return URIScope.DATA_ITEM
        elif self.container_name:
            return URIScope.CONTAINER
        elif self.domain_name:
            return URIScope.DOMAIN
        elif self.context_name:
            return URIScope.CONTEXT

        raise ValueError("Could not determine reference level. Is this URI empty?")

    def to_string(self) -> str:
        uri = self.SEPARATOR.join("" if x is None else x for x in self.as_tuple())
        if self.reference_level() > URIScope.DATA_ITEM:
            # if this does not reference a data item we need to make it absolute
            # also removing trailing separators because they are ugly and hold no info
            uri = (self.ROOT_INDICATOR + uri).rstrip(self.SEPARATOR)
        elif self.reference_level() == URIScope.DATA_ITEM:
            # if you are referencing a data item then you don't need any leading
            # separators
            uri = uri.lstrip(self.SEPARATOR)

        return uri


    def as_tuple(self):
        return (self.context_name, self.domain_name, self.container_name,
                self.data_item_uid)

    def is_absolute(self) -> bool:
        """This URI starts at the widest location level: context. Is not relative to
        context"""
        return bool(self.context_name)

    def is_consecutive(self) -> bool:
        """Running through location hierarchy from left to right, they form a
        consecutive block without holes
        """
        return any(x for x in trim_none(self.as_tuple()) if x is None)

    def is_valid(self):
        """Check whether this uri points to either a location or a data item"""
        if self.is_consecutive:
            return True
        else:
            return False


    def __str__(self):
        return self.to_string()

    def __repr__(self):
        # a URI with the same string value really should be the same object. There
        # are no hidden variables.
        return self.to_string()


def trim_none(tuple_in):
    """Remove any None values from both sides of a tuple"""
    tuple_in = tuple(dropwhile(lambda x: x is None, tuple_in))  # trim left
    return tuple(dropwhile(lambda x: x is None, reversed(tuple_in)))[::-1]  # trim right

class DICOMStudyIdentifier(Identifier):
    """A key to identify a single DICOM study"""
    pass

class StudyInstanceUID(DICOMStudyIdentifier):
    pass

class AccessionNumber(DICOMStudyIdentifier):
    pass

class PatientIdentifier(Identifier):
    pass

UNKNOWN_PATIENT = PatientIdentifier(value='Unknown')  # Default patient