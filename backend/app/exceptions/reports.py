class ReportTargetNotFoundError(Exception):
    pass


class ReportAlreadyOpenError(Exception):
    pass


class ReportDetailsRequiredError(Exception):
    pass


class ReportLimitReachedError(Exception):
    def __init__(self, max_reports: int) -> None:
        super().__init__(max_reports)
        self.max_reports = max_reports


class ReportsNotOpenError(Exception):
    pass
