#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shlex

from .common import make_config, show_error, recognize_path, make_size_readable
from ..common import validate_folder_name, parse_size
from ..constants import FILENAME_ENCODINGS
from .prompter import LoopedPrompter
from .parse_choice import interpret_choice
from ..storage import Storage

from .set_master_password import set_master_password
from .set_key import set_key

__all__ = ["configure"]

def quit_prompt(prompter):
    prompter.quit = True

def return_on_interrupt(f):
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (KeyboardInterrupt, EOFError):
            print()

    return wrapped

class YesNoPrompter(LoopedPrompter):
    def __init__(self, message="", yes=("yes",), no=("no",), case_sensitive=False):
        LoopedPrompter.__init__(self, message)

        self.yes = yes
        self.no = no
        self.case_sensitive = case_sensitive

    def postinput(self):
        if not self.case_sensitive and self.response is not None:
            self.response = self.response.lower()

        if self.response in self.yes:
            self.response = True
            self.quit = True
        elif self.response in self.no:
            self.response = False
            self.quit = True

class ExistingFolderPrompter(LoopedPrompter):
    def __init__(self, config, message=""):
        LoopedPrompter.__init__(self, message)

        self.config = config

    def postinput(self):
        if not validate_folder_name(self.response):
            show_error("Invalid folder name: %r" % (self.response,))
        elif self.response not in self.config.folders:
            show_error("Unknown folder name: %r" % (self.response,))
        else:
            self.quit = True

class NewFolderPrompter(LoopedPrompter):
    def __init__(self, config, message=""):
        LoopedPrompter.__init__(self, message)

        self.config = config

    def postinput(self):
        if not validate_folder_name(self.response):
            show_error("Invalid folder name: %r" % (self.response,))
        elif self.response in self.config.folders:
            show_error("Duplicate folder name: %r" % (self.response,))
        else:
            self.quit = True

class RenameFolderPrompter(LoopedPrompter):
    def __init__(self, config, original, message=""):
        LoopedPrompter.__init__(self, message)

        self.config = config
        self.original = original

    def postinput(self):
        if not self.response or self.response == self.original:
            self.quit = True
            return

        if not validate_folder_name(self.response):
            show_error("Invalid folder name: %r" % (self.response,))
        elif self.response in self.config.folders:
            show_error("Duplicate folder name: %r" % (self.response,))
        else:
            self.quit = True

class ChangePathPrompter(LoopedPrompter):
    def __init__(self, original, message=""):
        LoopedPrompter.__init__(self, message)

        self.original = original

    def postinput(self):
        if not self.response:
            self.response = self.original
            self.quit = True
            return

        path, path_type = recognize_path(self.response)

        if path_type not in Storage.registered_storages:
            show_error("Unknown storage: %r" % (path_type,))
        else:
            self.quit = True

class PathPrompter(LoopedPrompter):
    def postinput(self):
        path, path_type = recognize_path(self.response)

        if path_type not in Storage.registered_storages:
            show_error("Unknown storage: %r" % (path_type,))
        elif not path:
            show_error("Path must not be empty")
        else:
            self.quit = True

class FilenameEncodingPrompter(LoopedPrompter):
    def __init__(self, message="", default=None, title=None):
        LoopedPrompter.__init__(self, message)

        self.default = default

        if title is None:
            title = self.message

        self.title = title

    def preinput(self):
        print(self.title)
        for i, v in enumerate(FILENAME_ENCODINGS):
            if v == self.default:
                print("  %d) %s [default]" % (i + 1, v))
            else:
                print("  %d) %s" % (i + 1, v))
        print()

    def postinput(self):
        self.response = self.response.strip()

        if not self.response and self.default is not None:
            self.response = self.default
            self.quit = True
            return

        try:
            self.response = int(self.response)

            if self.response not in range(1, len(FILENAME_ENCODINGS) + 1):
                raise ValueError
        except ValueError:
            show_error("Invalid choice: %r" % (self.response,))
            return

        self.response = FILENAME_ENCODINGS[self.response - 1]
        self.quit = True

class PositiveIntegerPrompter(LoopedPrompter):
    def __init__(self, message="", default=None):
        LoopedPrompter.__init__(self, message)

        self.default = default

    def postinput(self):
        self.response = self.response.strip()

        if not self.response and self.default is not None:
            self.response = self.default
            self.quit = True
            return

        try:
            self.response = int(self.response)

            if self.response < 1:
                raise ValueError
        except ValueError:
            show_error("%r is not a positive integer" % (self.response,))
            return
        else:
            self.quit = True

class NaturalNumberPrompter(LoopedPrompter):
    def __init__(self, message="", default=None):
        LoopedPrompter.__init__(self, message)

        self.default = default

    def postinput(self):
        self.response = self.response.strip()

        if not self.response and self.default is not None:
            self.response = self.default
            self.quit = True
            return

        try:
            self.response = int(self.response)
        except ValueError:
            show_error("%r is not an integer" % (self.response,))
            return

        if self.response < 0:
            show_error("%r must not be negative" % (self.response,))
            return

        self.quit = True

class NonNegativeFloatPrompter(LoopedPrompter):
    def __init__(self, message="", default=None, allow_nan=False, allow_inf=True):
        LoopedPrompter.__init__(self, message)

        self.default = default
        self.allow_nan = allow_nan
        self.allow_inf = allow_inf

    def postinput(self):
        self.response = self.response.strip()

        if not self.response and self.default is not None:
            self.response = self.default
            self.quit = True
            return

        try:
            self.response = float(self.response)
        except ValueError:
            show_error("%r is not a valid number" % (self.response,))
            return

        if not self.allow_nan and self.response != self.response:
            show_error("The number must not be NaN")
            return

        if not self.allow_inf and abs(self.response) == float("inf"):
            show_error("The number must not be infinity")
            return

        if self.response < 0.0:
            show_error("The number must not be negative")
            return

        self.quit = True

class SizePrompter(LoopedPrompter):
    def __init__(self, message="", default=None):
        LoopedPrompter.__init__(self, message)

        self.default = default

    def postinput(self):
        self.response = self.response.strip()

        if not self.response and self.default is not None:
            self.response = self.default
            self.quit = True
            return

        try:
            self.response = parse_size(self.response)
        except ValueError as e:
            show_error("Invalid size: %r: %s" % (self.response, e))
        else:
            self.quit = True

class ActionPrompter(LoopedPrompter):
    def __init__(self, message="", actions=None):
        LoopedPrompter.__init__(self, message)

        if actions is None:
            actions = {}

        self.actions = actions

    def print_action(self, action_name, action):
        print("  %s) %s" % (action_name, action["description"]))

    def preinput(self):
        print()
        print("Available actions:")

        for action_name, action in sorted(self.actions.items(), key=lambda x: int(x[0])):
            self.print_action(action_name, action)

        print()

    def input(self):
        try:
            LoopedPrompter.input(self)
        except EOFError:
            print()
            self.response = None
            self.quit = True
        except KeyboardInterrupt:
            print()
            self.response = None

    def postinput(self):
        if self.response is not None:
            self.response = self.response.strip()

        if not self.response:
            return

        try:
            action = self.actions[self.response]
        except KeyError:
            show_error("Unknown action: %r" % (self.response,))
            return

        action["function"](self)

class ConfigurePrompter(ActionPrompter):
    def __init__(self, env, message="> "):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.edit_config,
                                       "description": "edit the configuration interactively"},
                                 "2": {"function": self.set_master_password,
                                       "description": "change master password"},
                                 "3": {"function": self.set_key,
                                       "description": "change encryption key"},
                                 "4": {"function": quit_prompt,
                                       "description": "quit"}})

        self.env = env

    @return_on_interrupt
    def edit_config(self, prompter):
        config, ret = make_config(self.env, load_encrypted_data=False, raw=True)

        if ret:
            return

        EditConfigPrompter(self.env, config)()

    @return_on_interrupt
    def set_master_password(self, prompter):
        set_master_password(self.env)

    @return_on_interrupt
    def set_key(self, prompter):
        set_key(self.env)

class EditConfigPrompter(ActionPrompter):
    def __init__(self, env, config, message="> "):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.edit_folders,
                                       "description": "edit folders"},
                                 "2": {"function": self.edit_targets,
                                       "description": "edit sync targets"},
                                 "3": {"function": self.edit_exclude,
                                       "description": "edit exclude"},
                                 "4": {"function": self.edit_other,
                                       "description": "edit other settings"},
                                 "5": {"function": self.save_config,
                                       "description": "save configuration"},
                                 "6": {"function": quit_prompt,
                                       "description": "go back"}})

        self.env = env
        self.config = config

    @return_on_interrupt
    def edit_folders(self, prompter):
        EditFoldersPrompter(self.config)()

    @return_on_interrupt
    def edit_targets(self, prompter):
        EditTargetsPrompter(self.config)()

    @return_on_interrupt
    def edit_exclude(self, prompter):
        EditExcludePrompter(self.config)()

    @return_on_interrupt
    def edit_other(self, prompter):
        EditOtherPrompter(self.config)()

    @return_on_interrupt
    def save_config(self, prompter):
        dump = dump_config(self.config)

        with open(self.env["config_path"], "w") as f:
            f.write(dump)

        print("Successfully saved the configuration")

class EditFoldersPrompter(ActionPrompter):
    def __init__(self, config, message="> "):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.add_folder,
                                       "description": "add folder"},
                                 "2": {"function": self.remove_folders,
                                       "description": "remove folders"},
                                 "3": {"function": self.list_folders,
                                       "description": "list folders"},
                                 "4": {"function": self.show_folder_info,
                                       "description": "show folder info"},
                                 "5": {"function": self.edit_folder,
                                       "description": "edit folder"},
                                 "6": {"function": quit_prompt,
                                       "description": "go back"}})

        self.config = config

    @return_on_interrupt
    def add_folder(self, prompter):
        folder_name = NewFolderPrompter(self.config, "Folder name: ").prompt()

        path = PathPrompter("Folder path: ").prompt()
        path, path_type = recognize_path(path)

        is_encrypted = YesNoPrompter("Enable encryption y/[n]: ", ["y"], ["n", ""]).prompt()

        if is_encrypted:
            filename_encoding = FilenameEncodingPrompter("Filename encoding:",
                                                         "base32").prompt()
        else:
            filename_encoding = "base32"

        if path_type == "local":
            avoid_rescan = YesNoPrompter("Avoid rescan y/[n]: ", ["y"], ["n", ""]).prompt()
        else:
            avoid_rescan = YesNoPrompter("Avoid rescan [y]/n: ", ["y", ""], ["n"]).prompt()

        folder = {"name": folder_name,
                  "type": path_type,
                  "path": path,
                  "encrypted": is_encrypted,
                  "filename_encoding": filename_encoding,
                  "avoid_rescan": avoid_rescan}

        self.config.folders[folder["name"]] = folder

    @return_on_interrupt
    def remove_folders(self, prompter):
        folder_names = sorted(self.config.folders.keys())
        for i, folder_name in enumerate(folder_names):
            print("[%d] %s" % (i + 1, folder_name))
       
        while True:
            choice = input("Numbers of folders to remove [default: none]: ").strip() or "none"

            try:
                to_remove = interpret_choice(choice, folder_names)
            except (ValueError, IndexError) as e:
                show_error("Error: %s" % (e,))
            else:
                break

        sure = bool(to_remove)

        if sure:
            sure = YesNoPrompter("Are you sure? y/[n] ", ["y"], ["n", ""]).prompt()

        if not sure:
            print("No folders were removed")
            return

        for i in to_remove:
            self.config.folders.pop(i)
            print("Removed folder: %s" % (i,))

    @return_on_interrupt
    def list_folders(self, prompter):
        for name in sorted(self.config.folders.keys()):
            print("%s" % (name,))

    @return_on_interrupt
    def show_folder_info(self, prompter):
        folder_name = ExistingFolderPrompter(self.config, "Folder: ").prompt()

        folder = self.config.folders[folder_name]

        if folder["type"] != "local":
            path = "%s://%s" % (folder["type"], folder["path"])
        else:
            path = folder["path"]

        print("Name: %s" % (folder_name,))
        print("Path: %s" % (path,))
        print("Storage: %s" % (folder["type"]))
        print("Encrypted: %s" % (str(folder["encrypted"]).lower()),)

        if folder["encrypted"]:
            print("Filename encoding: %s" % (folder["filename_encoding"],))

        print("Avoid rescan: %s" % (str(folder["avoid_rescan"]).lower()),)

    @return_on_interrupt
    def edit_folder(self, prompter):
        folder_name = ExistingFolderPrompter(self.config, "Folder to edit: ").prompt()

        EditFolderPrompter(self.config, folder_name, "> ").prompt()

class EditFolderPrompter(ActionPrompter):
    def __init__(self, config, folder_name, message=""):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.change_name,
                                       "description": "name"},
                                 "2": {"function": self.change_path,
                                       "description": "path"},
                                 "3": {"function": self.change_encryption,
                                       "description": "encryption"},
                                 "4": {"function": self.change_avoid_rescan,
                                       "description": "avoid rescan"},
                                 "5" : {"function": self.change_exclude,
                                        "description": "exclude"},
                                 "6": {"function": quit_prompt,
                                       "description": "go back"}})

        self.config = config
        self.folder = config.folders[folder_name]

    @return_on_interrupt
    def change_name(self, prompter):
        folder_name = self.folder["name"]
        msg = "New folder name [%s]: " % (folder_name,)
        new_folder_name = RenameFolderPrompter(self.config, folder_name, msg)()
        new_folder_name = new_folder_name or folder_name

        if new_folder_name != folder_name:
            self.folder["name"] = new_folder_name
            self.config.folders[new_folder_name] = self.config.folders.pop(folder_name)
            print("Renamed folder: %s to %s" % (folder_name, new_folder_name))

    @return_on_interrupt
    def change_path(self, prompter):
        path, path_type = self.folder["path"], self.folder["type"]
        msg = "New folder path [%s://%s]: " % (path_type, path)
        new_path = ChangePathPrompter(path_type + "://" + path, msg).prompt()

        new_path, new_path_type = recognize_path(new_path)
        self.folder["path"] = new_path
        self.folder["type"] = new_path_type

        print("Changed folder path: %s://%s to %s://%s" % (path_type, path,
                                                           new_path_type, new_path))

    @return_on_interrupt
    def change_encryption(self, prompter):
        encrypted = self.folder["encrypted"]

        if encrypted:
            msg = "Enable encryption [y]/n: "
            yes = ["y", ""]
            no = ["n"]
        else:
            msg = "Enable encryption y/[n]: "
            yes = ["y"]
            no = ["n", ""]

        new_encrypted = YesNoPrompter(msg, yes, no)()

        self.folder["encrypted"] = new_encrypted

        if new_encrypted != encrypted:
            if new_encrypted:
                print("Enabled encryption")
            else:
                print("Disabled encryption")

        if new_encrypted:
            filename_encoding = self.folder["filename_encoding"]
            if filename_encoding == "base64":
                msg = "Filename encoding [base64]/base41: "
            else:
                msg = "Filename encoding base64/[base41]: "

            new_filename_encoding = FilenameEncodingPrompter("Filename encoding: ",
                                                             default=filename_encoding)()

            self.folder["filename_encoding"] = new_filename_encoding

            print("Changed filename encoding: %s to %s" % (filename_encoding,
                                                           new_filename_encoding))

    @return_on_interrupt
    def change_avoid_rescan(self, prompter):
        avoid_rescan = self.folder["avoid_rescan"]

        if avoid_rescan:
            msg = "Avoid rescan [y]/n: "
            yes = ["y", ""]
            no = ["n"]
        else:
            msg = "Avoid rescan y/[n]: "
            yes = ["y"]
            no = ["n", ""]

        new_avoid_rescan = YesNoPrompter(msg, yes, no).prompt()

        self.folder["avoid_rescan"] = new_avoid_rescan

        if new_avoid_rescan != avoid_rescan:
            if new_avoid_rescan:
                print("Now avoiding rescan")
            else:
                print("No longer avoiding rescan")

    @return_on_interrupt
    def change_exclude(self, prompter):
        EditExcludePrompter(self.config, self.folder)()

class EditTargetsPrompter(ActionPrompter):
    def __init__(self, config, message="> "):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.add_target,
                                       "description": "add sync target"},
                                 "2": {"function": self.remove_targets,
                                       "description": "remove sync targets"},
                                 "3": {"function": self.list_targets,
                                       "description": "list sync targets"},
                                 "4": {"function": quit_prompt,
                                       "description": "go back"}})

        self.config = config

    @return_on_interrupt
    def add_target(self, prompter):
        source = ExistingFolderPrompter(self.config, "Source folder: ")()
        destination = ExistingFolderPrompter(self.config, "Destination folder: ")()

        self.config.sync_targets.append((source, destination))

        print("Added target: %s -> %s" % (source, destination))

    @return_on_interrupt
    def remove_targets(self, prompter):
        for i, target in enumerate(self.config.sync_targets):
            source, destination = target

            print("[%d] %s -> %s" % (i + 1, source, destination))
       
        while True:
            choice = input("Numbers of targets to remove [default: none]: ").strip() or "none"

            try:
                to_remove = interpret_choice(choice, self.config.sync_targets)
            except (ValueError, IndexError) as e:
                show_error("Error: %s" % (e,))
            else:
                break

        sure = bool(to_remove)

        if sure:
            sure = YesNoPrompter("Are you sure? y/[n] ", ["y"], ["n", ""])()

        if not sure:
            print("No sync targets were removed")
            return

        for i in to_remove:
            self.config.sync_targets.remove(i)
            print("Removed sync target: %s -> %s" % (i[0], i[1]))

    @return_on_interrupt
    def list_targets(self, prompter):
        for source, destination in self.config.sync_targets:
            print("%s -> %s" % (source, destination))

class EditExcludePrompter(ActionPrompter):
    def __init__(self, config, folder=None, message="> "):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.add_pattern,
                                       "description": "add pattern"},
                                 "2": {"function": self.remove_patterns,
                                       "description": "remove patterns"},
                                 "3": {"function": self.list_patterns,
                                       "description": "list patterns"},
                                 "4": {"function": quit_prompt,
                                       "description": "go back"}})

        self.config = config
        self.folder = folder

    @return_on_interrupt
    def add_pattern(self, prompter):
        pattern = PathPrompter("Pattern: ").prompt()
        pattern, path_type = recognize_path(pattern)

        if self.folder is not None:
            self.folder["allowed_paths"].setdefault(path_type, [])
            allowed_paths = self.folder["allowed_paths"][path_type]
        else:
            self.config.allowed_paths.setdefault(path_type, [])
            allowed_paths = self.config.allowed_paths[path_type]

        if not allowed_paths or allowed_paths[-1][0] != "e":
            allowed_paths.append(["e", []])

        exclude_block = allowed_paths[-1]

        exclude_block[1].append(pattern)

        print("Added exclude pattern: %r" % (path_type + "://" + pattern,))

    @return_on_interrupt
    def remove_patterns(self, prompter):
        pass

    @return_on_interrupt
    def list_patterns(self, prompter):
        if self.folder is not None:
            allowed_paths = self.folder["allowed_paths"]
        else:
            allowed_paths = self.config.allowed_paths

        for storage_name, blocks in allowed_paths.items():
            for block_type, patterns in blocks:
                if block_type != "e":
                    continue

                for pattern in patterns:
                    if storage_name != "local":
                        print("%s://%s" % (storage_name, pattern))
                    else:
                        print(pattern)

class EditOtherPrompter(ActionPrompter):
    def __init__(self, config, message="> "):
        ActionPrompter.__init__(self, message,
                                {"1": {"function": self.set_sync_threads,
                                       "description": "set number of sync threads"},
                                 "2": {"function": self.set_scan_threads,
                                       "description": "set number of scan threads"},
                                 "3": {"function": self.set_download_threads,
                                       "description": "set number of download threads"},
                                 "4": {"function": self.set_upload_limit,
                                       "description": "set upload speed limit"},
                                 "5": {"function": self.set_download_limit,
                                       "description": "set download speed limit"},
                                 "6": {"function": self.set_temp_encrypt_buffer_limit,
                                       "description": "set temporary encryption buffer size"},
                                 "7": {"function": self.set_ignore_unreachable,
                                       "description": "set ignore unreachable files"},
                                 "8": {"function": self.set_n_retries,
                                       "description": "set number of retries"},
                                 "9": {"function": self.set_connect_timeout,
                                       "description": "set connect timeout"},
                                 "10": {"function": self.set_read_timeout,
                                       "description": "set read timeout"},
                                 "11": {"function": self.set_upload_connect_timeout,
                                       "description": "set upload connect timeout"},
                                 "12": {"function": self.set_upload_read_timeout,
                                        "description": "set upload read timeout"},
                                 "13": {"function": self.set_temp_dir,
                                        "description": "set temporary directory path"},
                                 "14": {"function": quit_prompt,
                                       "description": "go back"}})

        self.config = config

    @return_on_interrupt
    def set_sync_threads(self, prompter):
        sync_threads = self.config.sync_threads

        msg = "Number of sync threads [default: %d]: " % (sync_threads,)
        new_sync_threads = PositiveIntegerPrompter(msg, sync_threads)()

        self.config.sync_threads = new_sync_threads

        print("Sync threads: %d" % (new_sync_threads,))

    @return_on_interrupt
    def set_scan_threads(self, prompter):
        scan_threads = self.config.scan_threads

        msg = "Number of scan threads [default: %d]: " % (scan_threads,)
        new_scan_threads = PositiveIntegerPrompter(msg, scan_threads)()

        self.config.scan_threads = new_scan_threads

        print("Scan threads: %d" % (new_scan_threads,))

    @return_on_interrupt
    def set_download_threads(self, prompter):
        download_threads = self.config.download_threads

        msg = "Number of download threads [default: %d]: " % (download_threads,)
        new_download_threads = PositiveIntegerPrompter(msg, download_threads)()

        self.config.download_threads = new_download_threads

        print("Download threads: %d" % (new_download_threads,))

    @return_on_interrupt
    def set_upload_limit(self, prompter):
        upload_limit = self.config.upload_limit

        readable_limit = make_size_readable(upload_limit, ["", "K", "M"])

        msg = "Upload limit [default: %s]: " % (readable_limit,)
        new_upload_limit = SizePrompter(msg, upload_limit)()

        self.config.upload_limit = new_upload_limit

        print("Upload limit: %s" % (make_size_readable(new_upload_limit, ["", "K", "M"]),))

    @return_on_interrupt
    def set_download_limit(self, prompter):
        download_limit = self.config.download_limit

        readable_limit = make_size_readable(download_limit, ["", "K", "M"])

        msg = "Download limit [default: %s]: " % (readable_limit,)
        new_download_limit = SizePrompter(msg, download_limit)()

        self.config.download_limit = new_download_limit

        print("Download limit: %s" % (make_size_readable(new_download_limit, ["", "K", "M"]),))

    @return_on_interrupt
    def set_temp_encrypt_buffer_limit(self, prompter):
        temp_encrypt_buffer_limit = self.config.temp_encrypt_buffer_limit

        readable_limit = make_size_readable(temp_encrypt_buffer_limit, ["", "K", "M", "G"])

        msg = "Temporary encryption buffer limit [default: %s]: " % (readable_limit,)
        new_temp_encrypt_buffer_limit = SizePrompter(msg, temp_encrypt_buffer_limit)()

        self.config.temp_encrypt_buffer_limit = new_temp_encrypt_buffer_limit

        print("Download limit: %s" % (make_size_readable(new_temp_encrypt_buffer_limit, ["", "K", "M", "G"])))

    @return_on_interrupt
    def set_ignore_unreachable(self, prompter):
        ignore_unreachable = self.config.ignore_unreachable

        if ignore_unreachable:
            msg = "Ignore unreachable files during scan [y]/n: "
            yes = ["y", ""]
            no = ["n"]
        else:
            msg = "Ignore unreachable files during scan y/[n]: "
            yes = ["y"]
            no = ["n", ""]

        new_ignore_unreachable = YesNoPrompter(msg, yes, no)()

        self.config.ignore_unreachable = new_ignore_unreachable

        if new_ignore_unreachable:
            print("Ignore unreachable files during scan: yes")
        else:
            print("Ignore unreachable files during scan: no")

    @return_on_interrupt
    def set_n_retries(self, prompter):
        n_retries = self.config.n_retries

        msg = "Number of retries [default: %d]: " % (n_retries,)
        new_n_retries = NaturalNumberPrompter(msg, n_retries)()

        self.config.n_retries = new_n_retries

        print("Number of retries: %d" % (new_n_retries,))

    @return_on_interrupt
    def set_connect_timeout(self, prompter):
        if isinstance(self.config.timeout, (tuple, list)):
            connect_timeout, read_timeout = self.config.timeout
        else:
            connect_timeout = self.config.timeout or float("inf")
            read_timeout = connect_timeout

        if connect_timeout is None:
            connect_timeout = float("inf")

        msg = "Connect timeout [default: %r]: " % (connect_timeout,)
        new_connect_timeout = NonNegativeFloatPrompter(msg, connect_timeout)()

        print("Connect timeout: %r" % (new_connect_timeout,))

        if new_connect_timeout == float("inf"):
            new_connect_timeout = None

        self.config.timeout = (new_connect_timeout, read_timeout)

    @return_on_interrupt
    def set_read_timeout(self, prompter):
        if isinstance(self.config.timeout, (tuple, list)):
            connect_timeout, read_timeout = self.config.timeout
        else:
            read_timeout = self.config.timeout
            connect_timeout = read_timeout

        if read_timeout is None:
            read_timeout = float("inf")

        msg = "Read timeout [default: %r]: " % (read_timeout,)
        new_read_timeout = NonNegativeFloatPrompter(msg, read_timeout)()

        print("Read timeout: %r" % (new_read_timeout,))

        if new_read_timeout == float("inf"):
            new_read_timeout = None

        self.config.read_timeout = (connect_timeout, new_read_timeout)

    @return_on_interrupt
    def set_upload_connect_timeout(self, prompter):
        if isinstance(self.config.upload_timeout, (tuple, list)):
            upload_connect_timeout, upload_read_timeout = self.config.timeout
        else:
            upload_connect_timeout = self.config.upload_timeout or float("inf")
            upload_read_timeout = upload_connect_timeout

        if upload_connect_timeout is None:
            upload_connect_timeout = float("inf")

        msg = "Upload connect timeout [default: %r]: " % (upload_connect_timeout,)
        new_upload_connect_timeout = NonNegativeFloatPrompter(msg, upload_connect_timeout)()

        print("Upload connect timeout: %r" % (new_upload_connect_timeout,))

        if new_upload_connect_timeout == float("inf"):
            new_upload_connect_timeout = None

        self.config.upload_timeout = (new_upload_connect_timeout, upload_read_timeout)

    @return_on_interrupt
    def set_upload_read_timeout(self, prompter):
        if isinstance(self.config.upload_timeout, (tuple, list)):
            upload_connect_timeout, upload_read_timeout = self.config.timeout
        else:
            upload_read_timeout = self.config.upload_timeout or float("inf")
            upload_connect_timeout = upload_read_timeout

        if upload_read_timeout is None:
            upload_read_timeout = float("inf")

        msg = "Upload read timeout [default: %r]: " % (upload_read_timeout,)
        new_upload_read_timeout = NonNegativeFloatPrompter(msg, upload_read_timeout)()

        print("Upload read timeout: %r" % (new_upload_read_timeout,))

        if new_upload_read_timeout == float("inf"):
            new_upload_read_timeout = None

        self.config.upload_timeout = (upload_connect_timeout, new_upload_read_timeout)

    @return_on_interrupt
    def set_temp_dir(self, prompter):
        new_path = input("Temporary directory path [default: %s]: " % (self.config.temp_dir or "-",))

        if new_path == "-":
            new_path = None

        if new_path:
            self.config.temp_dir = new_path

        print("Temporary directory path: %s" % (self.config.temp_dir,))
 
def configure(env):
    print("Interactive Encrypt & Sync configuration")

    ConfigurePrompter(env)()

    return 0

def quote(s):
    return shlex.quote(s).replace("\\", "\\\\")

def dump_config(config):
    indent = " " * 4
    output = ""

    output += "# Number of threads for synchronizer, scanner and downloader respectively\n"
    output += "sync-threads %d\n" % (config.sync_threads,)
    output += "scan-threads %d\n" % (config.scan_threads,)
    output += "download-threads %d\n\n" % (config.download_threads,)
    output += """\
# Upload/Download speed limits
# inf means infinity or no speed limit
# 8192 means 8912 Bytes
# 1.2m means 1.2 MiB
# 500k means 500 KiB
"""
    output += "upload-limit %s\n" % (make_size_readable(config.upload_limit, ["", "K", "M"]),)
    output += "download-limit %s\n\n" % (make_size_readable(config.download_limit, ["", "K", "M"]),)

    output += "temp-encrypt-buffer-limit %s\n\n" % (make_size_readable(config.temp_encrypt_buffer_limit, ["", "K", "M", "G"]))

    output += "n-retries %d\n\n" % (config.n_retries,)

    if isinstance(config.timeout, (tuple, list)):
        connect_timeout, read_timeout = config.timeout
    else:
        connect_timeout = read_timeout = config.timeout

    if connect_timeout is None:
        connect_timeout = float("inf")

    if read_timeout is None:
        read_timeout = float("inf")

    output += "connect-timeout %r\n" % (connect_timeout,)
    output += "read-timeout %r\n\n" % (read_timeout,)

    if isinstance(config.upload_timeout, (tuple, list)):
        upload_connect_timeout, upload_read_timeout = config.upload_timeout
    else:
        upload_connect_timeout = upload_read_timeout = config.upload_timeout

    if upload_connect_timeout is None:
        upload_connect_timeout = float("inf")

    if upload_read_timeout is None:
        upload_read_timeout = float("inf")

    output += "upload-connect-timeout %r\n" % (upload_connect_timeout,)
    output += "upload-read-timeout %r\n\n" % (upload_read_timeout,)

    output += "scan-ignore-unreachable %s\n\n" % (str(config.ignore_unreachable).lower(),)

    if config.temp_dir is not None:
        output += "temp-dir %s\n\n" % (quote(config.temp_dir))
    
    output += "folders {"

    for folder_name, folder in config.folders.items():
        output += "\n"
        output += indent + "%s %s://%s {\n" % (quote(folder_name), folder["type"],
                                              quote(folder["path"]))
        output += indent * 2 + "encrypted %s\n" % (repr(folder["encrypted"]).lower(),)
        output += indent * 2 + "filename-encoding %s\n" % (quote(folder["filename_encoding"]))
        output += indent * 2 + "avoid-rescan %s\n" % (repr(folder["avoid_rescan"]).lower(),)

        for path_type, blocks in folder["allowed_paths"].items():
            for block_type, block in blocks:
                assert(block_type in ["i", "e"])

                output += "\n"

                if block_type == "e":
                    output += indent * 2 + "exclude {\n"
                else:
                    output += indent * 2 + "include {\n"

                for pattern in block:
                    output += indent * 3 + "%s\n" % (quote(pattern),)

                output += indent * 2 + "}\n"

        output += indent + "}\n"

    output += "}\n\n"

    output += "targets {\n"

    for source, destination in config.sync_targets:
        output += indent + "%s -> %s\n" % (quote(source), quote(destination))

    output += "}\n\n"

    output += """\
# List of patterns to exclude when performing local scan
# The synchronizer will think they don't exist
# You can have multiple include/exclude blocks
# They will be interpreted in specified order
"""

    if not config.allowed_paths:
        output += "exclude {}\n"
        output += "include {}\n"

    for path_type, blocks in config.allowed_paths.items():
        for block_type, block in blocks:
            assert(block_type in ["i", "e"])
            if block_type == "e":
                output += "exclude {\n"
            else:
                output += "include {\n"

            for pattern in block:
                output += indent + "%s://%s\n" % (path_type, quote(pattern))

            output += "}\n\n"

    return output.rstrip("\n")
