class ClictreeError(Exception):
    pass

class TransformationError(ClictreeError):
    """A transformation can not be completed"""
    pass