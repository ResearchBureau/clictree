"""Classes that transform a data item"""

from midom.validation import Deidentifier
from clictree.core import Instance, KeyFile, Transformation



class DICOMDeidentifier(Transformation[Instance, Instance]):

    def __init__(self, deidentifier: Deidentifier):
        self.deidentifier = deidentifier

    def transform(self, input_data: Instance) -> Instance:
        return self.deidentifier.deidentify(input_data)



