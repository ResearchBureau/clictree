"""Things that can be referenced and passed around in clictree"""

from typing import Iterator

from clictree.core import DataItem, Instance


class InstanceIterator(DataItem[Iterator[Instance]]):
    pass


