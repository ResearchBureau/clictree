"""Everything that can serve as a unique identifier for something in CLICTree"""


class DICOMStudyIdentifier:

    def __init__(self, value:str):
        self.value = value

    def __str__(self):
        return f"{type(self).__name__} : {self.value}"

class StudyInstanceUID(DICOMStudyIdentifier):
    pass

class AccessionNumber(DICOMStudyIdentifier):

    pass