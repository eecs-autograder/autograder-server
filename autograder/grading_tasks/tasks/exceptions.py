class StopGrading(Exception):
    pass


class SubmissionRejected(StopGrading):
    pass


class SubmissionRemovedFromQueue(StopGrading):
    pass
