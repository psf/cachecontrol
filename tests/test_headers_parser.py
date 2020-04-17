# SPDX-FileCopyrightText: © 2019 The cachecontrol Authors
# SPDX-License-Identifier: Apache-2.0
import unittest

from cachecontrol.headers_parser import tokenize_cache_control, tokenize_pragma

class TestTokenizer(unittest.TestCase):

    def test_single_pragma(self):
        self.assertEqual({"token": None},
                         tokenize_pragma("token"))

    def test_single_cachecontrol(self):
        self.assertEqual({"token": None},
                         tokenize_cache_control("token"))

    def test_multiple_tokens(self):
        self.assertEqual({"token1": None, "token2": None},
                         tokenize_cache_control("token1,token2"))

    def test_single_token_with_value(self):
        self.assertEqual({"token1": "value1"},
                         tokenize_cache_control("token1=value1"))

    def test_single_token_with_value_quoted(self):
        self.assertEqual({"token1": "value1"},
                         tokenize_cache_control('token1="value1"'))

    def test_single_token_with_value_quoted_with_comma(self):
        self.assertEqual({"token1": "value1,value2"},
                         tokenize_cache_control('token1="value1,value2"'))

    def test_two_tokens_with_value_quoted_with_comma(self):
        self.assertEqual({"token1": "value1,value2", "token2": None},
                         tokenize_cache_control('token1="value1,value2",token2'))
