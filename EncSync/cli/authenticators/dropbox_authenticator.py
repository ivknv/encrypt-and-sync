# -*- coding: utf-8 -*-

from ..common import show_error, make_config
from ...Storage import Storage
from ...constants import DROPBOX_APP_KEY, DROPBOX_APP_SECRET

__all__ = ["authenticate_dropbox"]

def authenticate_dropbox(env):
    config, ret = make_config(env)

    if config is None:
        return ret

    import dropbox

    token = config.encrypted_data.get("dropbox_token", "")

    if not token:
        token_valid = False
    else:
        dbx = dropbox.Dropbox(token)

    no_auth_check = env.get("no_auth_check", False)

    if not no_auth_check and token:
        try:
            dbx.users_get_current_account()
            token_valid = True
        except dropbox.exceptions.BadInputError:
            token_valid = False

    if token_valid:
        config.storages["dropbox"] = Storage.get_storage("dropbox")(config)
        return 0

    try:
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
                show_error("Dropbox error: %s: %s" % (e.__class__.__name__, e,))
                show_error("Failed to get a token. Try again")
                continue

            token = response.access_token
            break

        config.encrypted_data["dropbox_token"] = token
        config.storages["dropbox"] = Storage.get_storage("dropbox")(config)

        return 0
    except (KeyboardInterrupt, EOFError):
        return 130
