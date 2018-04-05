# -*- coding: utf-8 -*-

__all__ = ["UnknownAuthenticatorError", "AuthenticatorError", "LoginError", "LogoutError"]

class UnknownAuthenticatorError(Exception):
    pass

class AuthenticatorError(Exception):
    pass

class LoginError(AuthenticatorError):
    pass

class LogoutError(AuthenticatorError):
    pass
