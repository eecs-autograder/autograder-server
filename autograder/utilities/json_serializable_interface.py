class JsonSerializable:
    """
    This capability class provides an interface for objects to be
    serialized to and deserialized from JSON objects.
    """
    @classmethod
    def from_json(class_, json):
        raise NotImplementedError('This method must be overridden')

    def to_json(self):
        raise NotImplementedError('This method must be overridden')
