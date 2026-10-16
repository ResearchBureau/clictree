"""Things used in tests"""
from dicomgenerator.generators import quick_dataset

from clictree.core import Link, Store, Transformation
from clictree.data_items import InstanceIterator
from clictree.identifiers import DICOMStudyIdentifier, PatientIdentifier, URI, \
    ResultReference


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
    """A simple as possible implementation of a Link class. For testing

    Changes PatientID, and performs 'org' -> 'org_CHANGED' mapping
    """


    def transform(self, input_data: InstanceIterator) -> InstanceIterator:
        return input_data  # don't change


    def get_original_uri(self, reference: ResultReference) -> URI:
        if "CHANGED" not in reference.value:
            raise ValueError(f"Unknown reference '{reference}' "
                             "I only know original URIs for references ending in "
                             "_CHANGED")
        return URI(context_name=None,domain_name=self.data_source_container.domain_name,
                   container_name=self.data_source_container.container_name,
                   data_item_uid=reference.value.replace("_CHANGED",""))


