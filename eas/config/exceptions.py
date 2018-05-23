# -*- coding: utf-8 -*-

__all__ = ["ConfigError", "InvalidConfigError",
           "InvalidEncryptedDataError", "WrongMasterKeyError"]

class ConfigError(Exception):
    pass

class InvalidConfigError(ConfigError):
    pass

class InvalidEncryptedDataError(ConfigError):
    pass

class WrongMasterKeyError(ConfigError):
    pass
