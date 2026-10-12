"""Things used in tests"""
from dicomgenerator.generators import quick_dataset

from clictree.core import Store, Transformation
from clictree.data_items import InstanceIterator
from clictree.identifiers import DICOMStudyIdentifier, PatientIdentifier


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



