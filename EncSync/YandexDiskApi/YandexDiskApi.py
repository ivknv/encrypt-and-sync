#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import requests

from . import Exceptions

def parse_date(s):
    return time.strptime(s[:-3] + s[-2:], "%Y-%m-%dT%H:%M:%S%z")

RETRY_CODES = {500, 503}
UPLOAD_RETRY_INTERVAL = 3.0

DEFAULT_MAX_RETRIES = 10
DEFAULT_GET_META_LIMIT = 5000
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 15.0
DEFAULT_UPLOAD_TIMEOUT = (DEFAULT_CONNECT_TIMEOUT, 60.0)
DEFAULT_TIMEOUT = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT)

class YndApi(object):
    def __init__(self, appId="", token="", secret=""):
        self.init(appId, token, secret)

    def make_session(self):
        session = requests.Session()
        if self.token:
            session.headers["Authorization"] = "OAuth " + self.token

        return session

    def init(self, appId, token, secret):
        self.id = appId
        self.token = token
        self.secret = secret

    def get_auth_url(self, **kwargs):
        baseURL = "https://oauth.yandex.ru/authorize"
        kwargs["response_type"] = "code"
        kwargs["client_id"] = self.id
        URL = baseURL + "?" + urlencode(kwargs)

        return URL

    def get_token(self, confirmation_code,
                  max_retries=DEFAULT_MAX_RETRIES,
                  timeout=DEFAULT_TIMEOUT, **kwargs):
        URL = "https://oauth.yandex.ru/token"
        kwargs["grant_type"] = "authorization_code"
        kwargs["code"] = confirmation_code
        kwargs["client_id"] = self.id
        kwargs["client_secret"] = self.secret

        for i in range(max_retries + 1):
            r = requests.post(URL, data=kwargs, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r)

    @staticmethod
    def prepare_error(error_dict):
        error_type = error_dict["error"]
        description = error_dict["description"]

        try:
            return Exceptions.exception_map[error_type](description)
        except KeyError:
            return Exceptions.YandexDiskError(error_type, description)

    @staticmethod
    def prepare_response(response, success_codes=None):
        if success_codes is None:
            success_codes = {200}

        ret = {"response": response,
               "success": response.status_code in success_codes}

        try:
            ret["data"] = response.json()
        except (ValueError, RuntimeError):
            ret["data"] = None

        if not ret["success"]:
            if ret["data"] is not None:
                raise YndApi.prepare_error(ret["data"])
            else:
                msg = "Server returned %d" % response.status_code
                raise Exceptions.UnknownYandexDiskError(msg)

        return ret

    def get_disk_data(self, max_retries=DEFAULT_MAX_RETRIES, timeout=DEFAULT_TIMEOUT):
        for i in range(max_retries + 1):
            r = self.make_session().get("https://cloud-api.yandex.net/v1/disk/",
                                        timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r)

    def get_meta(self, path,
                 max_retries=DEFAULT_MAX_RETRIES,
                 timeout=DEFAULT_TIMEOUT, **kwargs):
        baseURL = "https://cloud-api.yandex.net/v1/disk/resources"
        kwargs.setdefault("offset", 0)
        kwargs.setdefault("limit", DEFAULT_GET_META_LIMIT)
        kwargs.setdefault("sort", "name")
        kwargs["path"] = path
        URL = baseURL + "?" + urlencode(kwargs)

        for i in range(max_retries + 1):
            r = self.make_session().get(URL, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        ret = self.prepare_response(r)

        if ret["data"] is None:
            embedded = {}
        else:
            embedded = ret["data"].get("_embedded", {})

        ret["offset"] = embedded.get("offset", 0)
        ret["total"] = embedded.get("total", 1)

        return ret

    def exists(self, path,
               max_retries=DEFAULT_MAX_RETRIES,
               timeout=DEFAULT_TIMEOUT, **kwargs):
        try:
            r = self.get_meta(path, max_retries, timeout, **kwargs)

            return True
        except Exceptions.DiskNotFoundError:
            return False

    def get_type(self, path,
                 max_retries=DEFAULT_MAX_RETRIES,
                 timeout=DEFAULT_TIMEOUT, **kwargs):
        r = self.get_meta(path, max_retries, timeout, **kwargs)

        if r["success"]:
            return r["data"]["type"]

    def is_file(self, path,
                max_retries=DEFAULT_MAX_RETRIES,
                timeout=DEFAULT_TIMEOUT, **kwargs):
        try:
            return self.get_type(path, max_retries, timeout, **kwargs) == "file"
        except Exceptions.DiskNotFoundError:
            return False

    def is_dir(self, path,
               max_retries=DEFAULT_MAX_RETRIES,
               timeout=DEFAULT_TIMEOUT, **kwargs):
        try:
            return self.get_type(path, max_retries, timeout, **kwargs) == "dir"
        except Exceptions.DiskNotFoundError:
            return False

    def ls(self, path,
           max_retries=DEFAULT_MAX_RETRIES,
           timeout=DEFAULT_TIMEOUT, **kwargs):
        kwargs.setdefault("offset", 0)
        kwargs.setdefault("limit", DEFAULT_GET_META_LIMIT)

        res = self.get_meta(path, max_retries, timeout, **kwargs)

        data = res["data"]

        if not res["success"] or data is None:
            yield res
            return

        if "type" not in data:
            yield res
            return

        if data["type"] == "dir":
            j = 0
            for i in data["_embedded"]["items"]:
                ret = dict(res)
                ret["data"] = i
                ret["offset"] = ret["offset"] + j
                yield ret
                j += 1
        else:
            yield res
            return

        offset = data["_embedded"]["offset"]
        total = data["_embedded"]["total"]

        while True:
            if offset + kwargs["limit"] >= total - 1:
                break

            kwargs["offset"] += kwargs["limit"]
            res = self.get_meta(path, max_retries, timeout, **kwargs)

            data = res["data"]

            if not res["success"] or data is None:
                yield res
                break

            if "type" not in data:
                yield res
                break

            if data["type"] == "dir":
                j = 0
                for i in data["_embedded"]["items"]:
                    ret = dict(res)
                    ret["data"] = i
                    ret["offset"] = ret["offset"] + j
                    yield ret
                    j += 1

                offset = data["_embedded"]["offset"]
                total = data["_embedded"]["total"]
            else:
                yield res
                break

    def get_upload_link(self, out_path,
                        max_retries=DEFAULT_MAX_RETRIES,
                        timeout=DEFAULT_TIMEOUT, **kwargs):
        baseURL = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        kwargs["path"] = out_path
        URL = baseURL + "?" + urlencode(kwargs)

        for i in range(max_retries + 1):
            r = self.make_session().get(URL, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r, {200})

    def upload(self, in_file, out_path,
               max_retries=DEFAULT_MAX_RETRIES,
               timeout=DEFAULT_UPLOAD_TIMEOUT, **kwargs):
        close_in = False

        if isinstance(in_file, str):
            in_file = open(in_file, "rb")
            close_in = True

        fpos = in_file.tell()

        for i in range(max_retries + 1):
            res = self.get_upload_link(out_path, max_retries, timeout, **kwargs)

            if not res["success"]:
                return res

            href = res["data"]["href"]

            try:
                in_file.seek(fpos)
                r = self.make_session().put(href, data=in_file,
                                            timeout=timeout, stream=True)
            finally:
                if close_in:
                    in_file.close()

            if r.status_code not in RETRY_CODES:
                break

            time.sleep(UPLOAD_RETRY_INTERVAL)
        return self.prepare_response(r, {201})

    def get_download_link(self, in_path,
                          max_retries=DEFAULT_MAX_RETRIES,
                          timeout=DEFAULT_TIMEOUT, **kwargs):
        baseURL = "https://cloud-api.yandex.net/v1/disk/resources/download"
        kwargs["path"] = in_path
        URL = baseURL + "?" + urlencode(kwargs)

        for i in range(max_retries + 1):
            r = self.make_session().get(URL, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r)

    def download(self, in_path, out_file,
                 max_retries=DEFAULT_MAX_RETRIES,
                 timeout=DEFAULT_TIMEOUT, **kwargs):
        response = self.get_download_link(in_path, max_retries, timeout, **kwargs)

        if not response["success"]:
            return response

        href = response["data"]["href"]

        close_out = False

        if isinstance(out_file, str):
            out_file = open(out_file, "wb")
            close_out = True

        try:
            fpos = out_file.tell()

            for i in range(max_retries + 1):
                r = self.make_session().get(href, timeout=timeout, stream=True)
                out_file.seek(fpos)

                for chunk in r.iter_content(chunk_size=4096):
                    if len(chunk):
                        out_file.write(chunk)

                if r.status_code not in RETRY_CODES:
                    break

            return self.prepare_response(r)
        finally:
            if close_out:
                out_file.close()

    def rm(self, path,
           max_retries=DEFAULT_MAX_RETRIES,
           timeout=DEFAULT_TIMEOUT, **kwargs):
        baseURL = "https://cloud-api.yandex.net/v1/disk/resources"
        kwargs["path"] = path
        URL = baseURL + "?" + urlencode(kwargs)

        for i in range(max_retries + 1):
            r = self.make_session().delete(URL, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r, {202, 204})

    def mkdir(self, path,
              max_retries=DEFAULT_MAX_RETRIES,
              timeout=DEFAULT_TIMEOUT, **kwargs):
        baseURL = "https://cloud-api.yandex.net/v1/disk/resources"
        kwargs["path"] = path
        URL = baseURL + "?" + urlencode(kwargs)

        for i in range(max_retries + 1):
            r = self.make_session().put(URL, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r, {201})

    def files(self, max_retries=DEFAULT_MAX_RETRIES,
              timeout=DEFAULT_TIMEOUT, **kwargs):
        baseURL = "https://cloud-api.yandex.net/v1/disk/resources/files"
        kwargs.setdefault("limit", DEFAULT_GET_META_LIMIT)
        URL = baseURL + "?" + urlencode(kwargs)

        for i in range(max_retries + 1):
            r = self.make_session().get(URL, timeout=timeout)

            if r.status_code not in RETRY_CODES:
                break

        return self.prepare_response(r)
