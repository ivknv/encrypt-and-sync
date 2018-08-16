# -*- coding: utf-8 -*-

from getpass import getpass
import os

import paramiko
import pysftp

from .authenticator import Authenticator
from .exceptions import LoginError, LogoutError

from ..storage import Storage
from ..cli.common import show_error
from ..cli.prompter import LoopedPrompter
from .. import pathm

__all__ = ["SFTPAuthenticator"]

def load_ssh_key(path, password=None):
    key_classes = [paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey, paramiko.Ed25519Key]
    error = None

    for key_class in key_classes:
        key = None

        try:
            key = key_class.from_private_key_file(path, password)
        except paramiko.ssh_exception.PasswordRequiredException as e:
            raise e
        except paramiko.ssh_exception.SSHException as e:
            error = e
        else:
            return key

    if error is not None:
        raise error

class SSHKeyPrompter(LoopedPrompter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1st stage: get the key path
        # 2nd stage: get the key password if necessary
        self.stage = 1

        self.key_path = None
        self.password = None
        self.key = None

    def input(self):
        assert(self.stage in (1, 2))

        if self.stage == 1:
            super().input()
        elif self.stage == 2:
            try:
                self.response = getpass("Key passphrase: ")
            except (KeyboardInterrupt, EOFError):
                self.response = None
                self.stage = 1

    def postinput(self):
        assert(self.stage in (1, 2))

        if self.stage == 1:
            if self.response is None:
                return

            self.key_path = os.path.expanduser(self.response)
            self.key_path = os.path.abspath(self.key_path)

            if not os.path.exists(self.key_path):
                show_error("Error: file not found: %r" % (self.key_path,))
                return

            if not os.path.isfile(self.key_path):
                show_error("Error: %r is not a file" % (self.key_path,))
                return

            try:
                self.key = load_ssh_key(self.key_path)
            except paramiko.ssh_exception.PasswordRequiredException as e:
                self.stage = 2
            except IOError as e:
                show_error("I/O error: %s" % (e,))
            else:
                self.quit = True
        elif self.stage == 2:
            self.password = self.response

            try:
                self.key = load_ssh_key(self.key_path, self.password)
            except paramiko.ssh_exception.SSHException as e:
                if str(e).startswith("not a valid "):
                    show_error("Authentication error: invalid private key %r" % (self.key_path,))
                    self.stage = 1
                else:
                    show_error("Invalid password. Try again")
            except IOError as e:
                show_error("I/O error: %s" % (e,))
            else:
                self.quit = True

class SSHPasswordPrompter(LoopedPrompter):
    def __init__(self, username, host, port, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.username, self.host, self.port = username, host, port

    def input(self):
        self.response = getpass(self.message)

    def postinput(self):
        password = self.response

        try:
            authenticate_using_password(self.username, self.host, self.port, password)
        except paramiko.ssh_exception.BadAuthenticationType as e:
            raise e
        except paramiko.ssh_exception.AuthenticationException as e:
            show_error("Authentication error: %s" % (e,))
            show_error("Try again")
        else:
            self.quit = True

class SFTPConnection(pysftp.Connection):
    def __init__(self, *args, **kwargs):
        # Fix for AttributeError on self.__del__()
        self._sftp_live = False
        self._transport = None
        self._cnopts = pysftp.CnOpts()

        pysftp.Connection.__init__(self, *args, **kwargs)

def get_host_address(path):
    host_address, separator, path = path.lstrip("/").partition("/")
    path = pathm.join_properly("/", path) or "/"

    return host_address

def split_host_address(address):
    username, user_separator, rest = address.partition("@")
    hostname, port_separator, port = rest.partition(":")

    if not username:
        raise ValueError("SFTP username must not be empty")

    if not hostname:
        raise ValueError("SFTP hostname cannot be empty")

    if port and not port_separator:
        raise ValueError("Invalid SFTP address: %r" % (address,))

    port = "22" if not port else port
    port = int(port)

    return username, hostname, port

def authenticate_using_agent(username, host, port):
    agent = paramiko.Agent()
    keys = agent.get_keys()

    error = None

    if not keys:
        raise paramiko.ssh_exception.AuthenticationException("No keys available")

    for key in keys:
        try:
            connection = SFTPConnection(host, port=port, username=username,
                                        private_key=key)
            return
        except paramiko.ssh_exception.AuthenticationException as e:
            error = e

    if error is not None:
        raise error

def authenticate_using_key(username, host, port, key):
    connection = SFTPConnection(host, port=port, username=username, private_key=key)

def authenticate_using_password(username, host, port, password):
    connection = SFTPConnection(host, port=port, username=username, password=password)

class SFTPAuthenticator(Authenticator):
    name = "sftp"

    def get_auth_id(self, config, path, env, *args, **kwargs):
        try:
            username, host, port = split_host_address(get_host_address(path))
        except ValueError as e:
            raise LoginError("invalid SFTP address %r: %s" % (path, e))

        return ("sftp", username, host, port)

    def login(self, config, path, env, *args, **kwargs):
        try:
            username, host, port = split_host_address(get_host_address(path))
        except ValueError as e:
            raise LoginError("invalid SFTP address %r: %s" % (path, e))

        storage = Storage.get_storage("sftp")(config)

        ssh_auth = config.encrypted_data.setdefault("ssh_auth", {})

        k = "%s@%s:%d" % (username, host, port)

        host_auth = ssh_auth.setdefault(k, {"method":       None,
                                            "password":     None,
                                            "key_path":     None,
                                            "key_password": None})

        no_auth_check = env.get("no_auth_check", False)

        auth_method = host_auth.get("method")

        if auth_method == "agent":
            try:
                if not no_auth_check:
                    authenticate_using_agent(username, host, port)

                config.storages["sftp"] = storage

                return
            except paramiko.ssh_exception.AuthenticationException:
                pass
        elif auth_method == "key":
            key_path = host_auth.get("key_path")
            key_password = host_auth.get("key_password")

            if key_path is not None:
                try:
                    key = load_ssh_key(key_path, key_password)

                    try:
                        if not no_auth_check:
                            authenticate_using_key(username, host, port, key)

                        config.storages["sftp"] = storage

                        return
                    except paramiko.ssh_exception.AuthenticationException:
                        pass
                except paramiko.ssh_exception.SSHException:
                    pass
        elif auth_method == "password":
            password = host_auth.get("password")

            if password is not None:
                try:
                    if not no_auth_check:
                        authenticate_using_password(username, host, port, password)

                    config.storages["sftp"] = storage

                    return
                except paramiko.ssh_exception.AuthenticationException:
                    pass

        print("Choose the authentication method for sftp://%s@%s:%d: " % (username, host, port))

        AUTH_SSH_AGENT = 1
        AUTH_SSH_KEY = 2
        AUTH_PASSWORD = 3

        while True:
            print("[1]: Using SSH agent (default)")
            print("[2]: Using SSH key")
            print("[3]: Using password")

            choice = input("Authentication method (default: 1): ")

            try:
                choice = choice.strip() or "1"

                if choice not in ("1", "2", "3"):
                    raise ValueError

                choice = int(choice)

                if choice == AUTH_SSH_AGENT:
                    try:
                        authenticate_using_agent(username, host, port)
                    except paramiko.ssh_exception.AuthenticationException as e:
                        show_error("Authentication error: %s" % (e,))
                        show_error("Try another method")
                        continue

                    host_auth["method"] = "agent"
                elif choice == AUTH_SSH_KEY:
                    prompter = SSHKeyPrompter("SSH key path: ")
                    prompter.prompt()

                    key = prompter.key


                    try:
                        authenticate_using_key(username, host, port, key)
                    except paramiko.ssh_exception.AuthenticationException as e:
                        show_error("Authentication error: %s" % (e,))
                        show_error("Try another method")
                        continue

                    host_auth["method"] = "key"
                    host_auth["key_path"] = prompter.key_path
                    host_auth["key_password"] = prompter.password
                elif choice == AUTH_PASSWORD:
                    try:
                        prompter = SSHPasswordPrompter(username, host, port,
                                                       "Password for %s: " % (username,))
                        prompter.prompt()
                    except paramiko.ssh_exception.BadAuthenticationType:
                        show_error("This host does not accept passwords")
                        show_error("Try another method")
                        continue
                    except (KeyboardInterrupt, EOFError):
                        continue

                    host_auth["method"] = "password"
                    host_auth["password"] = prompter.password

                break
            except ValueError:
                show_error("Error: invalid choice %r" % (choice,))

        config.storages["sftp"] = storage

    def logout(self, config, path, env, *args, **kwargs):
        ssh_auth = config.encrypted_data.setdefault("ssh_auth", {})

        if pathm.join_properly("/", path) in ("/", ""):
            ssh_auth.clear()
            print("Successfully logged out of all SFTP hosts")
            return

        username, host, port = split_host_address(get_host_address(path))

        try:
            ssh_auth.pop("%s@%s:%d" % (username, host, port))
            print("Successfully logged out of sftp://%s@%s:%d" % (username, host, port))
        except KeyError:
            print("Not logged in")
