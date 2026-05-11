class GsdError(Exception):
    """Base exception for GSD Shared Library"""
    pass

class SchemaValidationError(GsdError):
    """API Response Schema Validation Failed"""
    def __init__(self, message: str, raw_data: dict = None):
        super().__init__(message)
        self.raw_data = raw_data
