"""Places you can get data from"""
from os import PathLike
from typing import Iterator

from dicomtrolley.core import DICOMObjectReference, Query, StudyReference
from dicomtrolley.trolley import Trolley

from clictree.core import OutputType, Repository, Instance, Source
from clictree.identifiers import AccessionNumber, DICOMStudyIdentifier, StudyInstanceUID


class DICOMWebSource(Repository[DICOMStudyIdentifier,Iterator[Instance]]):

    def __init__(self, trolley: Trolley):
        self.trolley = trolley

    def retrieve(self, key: DICOMStudyIdentifier) -> Iterator[Instance]:
        """All instances belonging to the given study"""
        yield from self.trolley.fetch_all_datasets([self.resolve_identifier(key)])  # obtain Dataset for each instance


    def resolve_identifier(self, key:DICOMStudyIdentifier) -> DICOMObjectReference:
        """Obtain a valid dicomtrolley reference for given key. Query if needed"""

        if isinstance(key, StudyInstanceUID):
            # StudyInstanceUID can be used as is
            return StudyReference(study_uid=key.value)
        elif isinstance(key, AccessionNumber):
            # AccessionNumber is not globally unique. We need to query
            study = self.trolley.find_study(Query(AccessionNumber=key.value))
            return StudyReference(study_uid=study.uid)
        else:
            raise ValueError(f'Unknown key type {type(key)}')

class AccessionNumberList(Source[AccessionNumber]):
    """A file with an accession number on each line"""

    def __init__(self, path: PathLike):
        self.path = path

    def __iter__(self):
        with open(self.path,'r') as f:
            for line in f:
                yield AccessionNumber(line.strip('\n\r'))



