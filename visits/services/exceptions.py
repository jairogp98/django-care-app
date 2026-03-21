class CaregiverScheduleConflictError(Exception):
    pass


class VisitTaskAlreadyCompletedError(Exception):
    pass


class VisitHasPendingMandatoryTasksError(Exception):
    pass


class VisitAlreadyCancelledError(Exception):
    pass