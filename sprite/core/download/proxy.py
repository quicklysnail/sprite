# # -*- coding:utf-8 -*-
# __author__ = 'liyong'
# __date__ = '2019/8/26 20:19'
#
# import base64
# from typing import Dict
# from urllib.parse import urlparse, unquote, urlunparse
#
#
# class ProxyHandler:
#
#     @classmethod
#     def get_auth_from_url(cls, url: str):
#         parsed = urlparse(url)
#
#         try:
#             auth = (unquote(parsed.username), unquote(parsed.password))
#         except (AttributeError, TypeError):
#             auth = ('', '')
#
#         return auth
#
#     @classmethod
#     def get_proxy_headers(cls, proxy: str):
#         headers = {}
#         username, password = cls.get_auth_from_url(proxy)
#
#         if username:
#             headers['Proxy-Authorization'] = cls._basic_auth_str(username,
#                                                                  password)
#
#         return headers
#
#     @classmethod
#     def _basic_auth_str(cls, username: str, password: str):
#         if not isinstance(username, str):
#             username = str(username)
#
#         if not isinstance(password, str):
#             password = str(password)
#
#         if isinstance(username, str):
#             username = username.encode('latin1')
#
#         if isinstance(password, str):
#             password = password.encode('latin1')
#
#         proxy_user_pass = f'{username}:{password}'
#         authstr = "Basic " + base64.urlsafe_b64encode(bytes((proxy_user_pass), "ascii")).decode("utf8")
#         return authstr
#
#     @classmethod
#     def select_proxy(cls, url: str, proxies: Dict):
#         proxies = proxies or {}
#         urlparts = urlparse(url)
#         if urlparts.hostname is None:
#             return proxies.get(urlparts.scheme, proxies.get('all'))
#
#         proxy_keys = [
#             urlparts.scheme + '://' + urlparts.hostname,
#             urlparts.scheme,
#             'all://' + urlparts.hostname,
#             'all',
#         ]
#         proxy = None
#         for proxy_key in proxy_keys:
#             if proxy_key in proxies:
#                 proxy = proxies[proxy_key]
#                 break
#
#         return proxy
#
#     @classmethod
#     def prepend_scheme_if_needed(cls, url: str, new_scheme: str):
#
#         scheme, netloc, path, params, query, fragment = urlparse(url)
#         if scheme != new_scheme:
#             scheme = new_scheme
#         return urlunparse((scheme, netloc, path, params, query, fragment))
#
#     @classmethod
#     def parse_proxy(cls, url: str):
#         parse_result = urlparse(url)
#         return parse_result.scheme, parse_result.netloc.split(":")[0], parse_result.port
