"""Things used in tests"""
from dicomgenerator.generators import quick_dataset

from clictree.core import InputType, KeyFile, Link, OutputType, Store, Transformation
from clictree.data_items import InstanceIterator
from clictree.identifiers import DICOMStudyIdentifier, PatientIdentifier, URI, \
    URIReference
from clictree.transformations import DICOMDeidentifier


class SimpleStore(Store[DICOMStudyIdentifier,InstanceIterator]):
    """Returns three datasets for any key you put in"""

    def retrieve(self, key: DICOMStudyIdentifier) -> InstanceIterator:
        return InstanceIterator(data=(quick_dataset(PatientID="Patient_1",
                                                    StudyInstanceUID=key.value,
                                SOPInstanceUID=uid) for uid in "123"))


class PatientChanger(Transformation[InstanceIterator,InstanceIterator]):

    def transform(self, input_data: InstanceIterator) -> InstanceIterator:
        new_patient = PatientIdentifier(value=input_data.patient.value + "_MODIFIED")

        def process(data_in):
            for ds in data_in.data:
                ds.PatientID = ds.PatientID + "_MODIFIED"
                yield ds

        return InstanceIterator(patient=new_patient, data=process(input_data))




class SimpleLink(Link[InstanceIterator, InstanceIterator]):
    """A simple as possible implementation of a Link class.

    Changes PatientID, and performs 'org' -> 'org_CHANGED' mapping
    """


    def __init__(self, key_file:KeyFile):
        self.key_file = key_file

    def transform(self, input_data: InstanceIterator) -> InstanceIterator:
        pass


    def get_original_uri(self, reference: URIReference) -> URI:
        if "CHANGED" not in reference.value:
            raise ValueError(f"Unknown reference '{reference}' "
                             "I only know original URIs for references ending in "
                             "_CHANGED")
        return self #TODO

