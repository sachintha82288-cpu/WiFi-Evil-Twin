"""Custom exceptions for WiFi-Evil-Twin."""


class WiFiEvilTwinError(Exception):
    """Base error for the project."""


class NotAuthorizedError(WiFiEvilTwinError):
    """Raised when the operator has not acknowledged the legal disclaimer."""


class RootRequiredError(WiFiEvilTwinError):
    """Raised when the tool needs root privileges but is not running as root."""


class MissingDependencyError(WiFiEvilTwinError):
    """Raised when a required external binary is not installed."""


class InterfaceError(WiFiEvilTwinError):
    """Raised when a wireless interface is missing or unusable."""


class ConfigError(WiFiEvilTwinError):
    """Raised on invalid configuration."""
