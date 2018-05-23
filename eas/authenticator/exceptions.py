# -*- coding: utf-8 -*-

__all__ = ["UnknownAuthenticatorError", "AuthenticatorError", "LoginError", "LogoutError"]

class UnknownAuthenticatorError(KeyError):
    pass

class AuthenticatorError(Exception):
    pass

class LoginError(AuthenticatorError):
    pass

class LogoutError(AuthenticatorError):
    pass
