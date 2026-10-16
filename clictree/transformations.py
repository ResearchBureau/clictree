"""Classes that transform a data item"""

from midom.validation import Deidentifier
from clictree.core import Transformation
from clictree.data_items import Instance


class DICOMDeidentifier(Transformation[Instance, Instance]):

    def __init__(self, deidentifier: Deidentifier):
        self.deidentifier = deidentifier

    def transform(self, input_data: Instance) -> Instance:
        return self.deidentifier.deidentify(input_data)



