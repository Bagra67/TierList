from sqlalchemy.exc import OperationalError


class UnreachableDatabaseSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
