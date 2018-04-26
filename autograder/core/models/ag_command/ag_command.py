from .ag_command_base import AGCommandBase


class AGCommand(AGCommandBase):
    """
    Contains the core information needed to run a command during grading.
    """
    # Since this class is most commonly used in transparent -to-one relationships,
    # we leave out pk from serialization.
    SERIALIZABLE_FIELDS = [
        'name',
        'cmd',
        'time_limit',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',
    ]

    EDITABLE_FIELDS = [
        'name',
        'cmd',
        'time_limit',
        'stack_size_limit',
        'virtual_memory_limit',
        'process_spawn_limit',
    ]

    SERIALIZE_RELATED = [
        'stdin_instructor_file',
    ]
