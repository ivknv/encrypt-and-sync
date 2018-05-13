# -*- coding: utf-8 -*-

import dropbox
import requests

from .authenticator import Authenticator
from .exceptions import LoginError, LogoutError

from ..storage import Storage
from ..constants import DROPBOX_APP_KEY, DROPBOX_APP_SECRET
from ..cli.common import show_error

__all__ = ["DropboxAuthenticator"]

class DropboxAuthenticator(Authenticator):
    name = "dropbox"

    def login(self, config, env, *args, **kwargs):
        token = config.encrypted_data.get("dropbox_token", "")

        token_valid = True

        if not token:
            token_valid = False
        else:
            dbx = dropbox.Dropbox(token)

        no_auth_check = env.get("no_auth_check", False)

        if not no_auth_check and token:
            try:
                dbx.users_get_current_account()
                token_valid = True
            except (dropbox.exceptions.BadInputError, dropbox.exceptions.AuthError):
                token_valid = False
            except dropbox.exceptions.DropboxException as e:
                raise LoginError("Dropbox error: %s: %s" % (e.__class__.__name__, e))

        if token_valid:
            config.storages["dropbox"] = Storage.get_storage("dropbox")(config)
            return

        if not env.get("ask", False):
            raise LoginError("need user input (disabled) to log in")

        token = None

        while True:
            auth_flow = dropbox.oauth.DropboxOAuth2FlowNoRedirect(DROPBOX_APP_KEY,
                                                                  DROPBOX_APP_SECRET)
            url = auth_flow.start()

            print("Go to the following URL: %s" % (url,))
            code = input("Confirmation code: ")

            try:
                response = auth_flow.finish(code)
            except dropbox.exceptions.DropboxException as e:
                show_error("Dropbox error: %s: %s" % (e.__class__.__name__, e))
                show_error("Failed to get a token. Try again")
                continue
            except requests.exceptions.RequestException as e:
                show_error("Network I/O error: %s: %s" % (e.__class__.__name__, e))
                show_error("Failed to get a token. Try again")
                continue

            token = response.access_token
            break

        config.encrypted_data["dropbox_token"] = token
        config.storages["dropbox"] = Storage.get_storage("dropbox")(config)

    def logout(self, config, env, *args, **kwargs):
        token = config.encrypted_data.get("dropbox_token", "")
        if not token:
            return

        try:
            dropbox.Dropbox(token).auth_token_revoke()
        except dropbox.exceptions.AuthError:
            pass
        except dropbox.exceptions.DropboxException as e:
            raise LogoutError("Dropbox error: %s: %s" % (e.__class__.__name__, e))
        except requests.exceptions.RequestException as e:
            raise LogoutError("Network I/O error: %s: %s" % (e.__class__.__name__, e))

        config.encrypted_data.pop("dropbox_token", None)
