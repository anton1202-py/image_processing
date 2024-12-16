class ModuleException(Exception):
    """."""

    prefix = "ModuleException"

    def __init__(self, msg: str = "", data: dict = None, code: int = 500):
        """."""
        self.msg = msg
        self.data = data
        self.code = code

    def json(self) -> dict:
        return {"error": self.msg, "data": self.data or {}}

    def __repr__(self):
        name = type(self).__name__
        return f"{name}({self}) {self.code} {self.data}"
