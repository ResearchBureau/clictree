"""Things that can be referenced and passed around in clictree"""

from typing import Iterator

import pydicom

from clictree.core import DataItem


# in clictree all studies are represented by pydicom datasets
Instance = pydicom.Dataset

class InstanceIterator(DataItem[Iterator[Instance]]):
    pass


