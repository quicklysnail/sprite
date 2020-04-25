# # -*- coding:utf-8 -*-
# __author__ = 'liyong'
# __date__ = '2019-07-21 13:49'
#
# from .url import URL
# from sprite.utils.http.cookies import CookiesJar
# from .connection import Connection
#
#
# class Request:
#     __slots__ = ('method', 'url', 'headers', 'data', 'cookies', 'streaming', 'chunked',
#                  'encoding', 'origin', '_isProxyReq')
#
#     def __init__(self, method: str, url: URL, headers: dict, data, cookies: CookiesJar, origin=None, isProxyReq: bool = False):
#         self.method = method.upper() if method else 'GET'
#         self.url = url
#         self.headers = headers or {}
#         self.data = data or b''
#         self.cookies = cookies
#         self.streaming = True if data and not isinstance(
#             data, (bytes, bytearray)) else False
#         self.chunked = self.streaming
#         self.origin = origin
#         self._isProxyReq = isProxyReq
#
#     def isProxyReq(self) -> bool:
#         return self._isProxyReq
#
#     def is_ssl(self) -> bool:
#         if self.url.schema in ["https"]:
#             return True
#         return False
#
#     async def encode(self, connection: Connection):
#         # 把请求编码成字节类型，并调用connection实例发送请求
#
#         # 在代理模式下
#         #   CONNECT www.python.org:443 HTTP/1.1
#         #   Host: www.python.org
#         path = self.url.netloc
#         method = self.method
#         if self.isProxyReq() and self.is_ssl():
#             method = "CONNECT"
#             path = f'{self.url.schema}:{self.url.host}{self.url.netloc}:443'
#
#         http_request = f'{method} {path} HTTP/1.1\r\n'
#         # Headers
#         for header, value in self.headers.items():
#             http_request += f'{header}: {str(value)}\r\n'
#         # Cookies
#         if self.cookies:
#             cookies = ';'.join([c.name + '=' + c.value for c in self.cookies])
#             http_request += f'Cookie: {cookies}'
#
#         if not self.streaming:
#             http_request += f'Content-Length: {str(len(self.data))}\r\n'
#             await connection.sendall((http_request + '\r\n').encode() + self.data)
#
#         elif self.chunked:
#             http_request += f'Transfer-Encoding: chunked\r\n'
#             await connection.sendall((http_request + '\r\n').encode())
#             for chunk in self.data:
#                 size = hex(len(chunk))[2:].encode('utf-8')
#                 await connection.sendall(size + b'\r\n' + chunk + b'\r\n')
#             await connection.sendall(b'0\r\n\r\n')
