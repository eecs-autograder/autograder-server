# HACK: There are some places where we need to know if the
# size came from the db or the filesystem (pre- or post-migration).
# Rather than adding extra fields, we'll return this sublclass of int.
class MigratedOutputSize(int):
    pass
