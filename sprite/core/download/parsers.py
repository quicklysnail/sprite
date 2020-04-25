# # -*- coding:utf-8 -*-
# __author__ = 'liyong'
# __date__ = '2019-08-25 13:14'
#
# from .headers import Headers
# from .response import Response
#
# HTTP_PARSE_ENCODING = 'utf-8'
#
# """
# http response parser
# """
#
# """HttpRequestParser
#
#         protocol -- a Python object with the following methods
#         (all optional):
#
#           - on_message_begin()
#           - on_url(url: bytes)
#           - on_header(name: bytes, value: bytes)
#           - on_headers_complete()
#           - on_body(body: bytes)
#           - on_message_complete()
#           - on_chunk_header()
#           - on_chunk_complete()
#           - on_status(status: bytes)
# """
#
#
# class HttpToolsProtocol:
#     def __init__(self, response:Response,  expected_content_length: int = 1024 * 1024):
#         self._response= response
#         self._status = 0
#         self._content = b''
#         self._headers = Headers()
#         # Response state
#         self._response_started = False
#         self._response_complete = False
#         self._headers_complete = False
#         self._chunked_encoding = None
#         self._expected_content_length = expected_content_length
#
#     def on_message_begin(self):
#         self._response_started = True
#
#     def on_url(self, url: bytes):
#         pass
#
#     def on_header(self, name: bytes, value: bytes):
#         self._headers[name.decode(HTTP_PARSE_ENCODING)] = value.decode(HTTP_PARSE_ENCODING)
#
#     def on_headers_complete(self):
#         self._headers_complete = True
#         self._response.headers = self._headers
#
#     def on_body(self, body: bytes):
#         self._content += body
#
#     def on_message_complete(self):
#         self._response_complete = True
#
#     def on_chunk_header(self):
#         self._chunked_encoding = True
#
#     def on_chunk_complete(self):
#         self._response_complete = True
#
#     def on_status(self, status: bytes):
#         self._status = status.decode(HTTP_PARSE_ENCODING)
#
#     @property
#     def headers(self):
#         return self._headers
#
#     @property
#     def content(self):
#         return self._content
#
#     def __str__(self):
#         return f'{self._status}   {self._headers}   {self._content}'
