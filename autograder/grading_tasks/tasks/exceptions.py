class StopGrading(Exception):
    pass


class SubmissionRejected(StopGrading):
    pass


class SubmissionRemovedFromQueue(StopGrading):
    pass


class RerunCancelled(StopGrading):
    pass


class TestDeleted(Exception):
    pass
