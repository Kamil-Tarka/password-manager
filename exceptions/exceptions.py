"""
Custom exception classes for the Password Manager application.

These exceptions are used to signal specific error conditions in the application logic.
"""


class DatabaseSettingsException(Exception):
    """
    Raised when there is a problem with the database configuration or connection.
    """

    pass


class ToShortPasswordException(Exception):
    """
    Raised when a provided password does not meet the minimum length requirement.
    """

    pass


class NotFoundAccountException(Exception):
    """
    Raised when an account with the specified identifier is not found.
    """

    pass


class NotFoundCustomFieldException(Exception):
    """
    Raised when a custom field with the specified identifier is not found.
    """

    pass
