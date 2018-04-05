# -*- coding: utf-8 -*-

__all__ = ["AuthenticatorError", "LoginError", "LogoutError"]

class AuthenticatorError(Exception):
    pass

class LoginError(AuthenticatorError):
    pass

class LogoutError(AuthenticatorError):
    pass
