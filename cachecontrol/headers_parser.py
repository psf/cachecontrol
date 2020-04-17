# SPDX-FileCopyrightText: © 2019 The cachecontrol Authors
# SPDX-License-Identifier: Apache-2.0

import functools

from abnf.grammars import rfc7234
from abnf.parser import NodeVisitor, Rule
from requests.structures import CaseInsensitiveDict


@functools.lru_cache(maxsize=1)
def _get_cache_control_rule():
    return rfc7234.Rule("Cache-Control")


@functools.lru_cache(maxsize=1)
def _get_pragma_rule() -> Rule:
    return rfc7234.Rule("Pragma")


class DirectivesVisitor(NodeVisitor):
    def __init__(self):
        super().__init__()
        self.directives = []

    def visit(self, node):
        super().visit(node)

    def visit_cache_control(self, node):
        for child_node in node.children:
            self.visit(child_node)

    def visit_cache_directive(self, node):
        self.directives.append(node.value)

    def visit_pragma(self, node):
        for child_node in node.children:
            self.visit(child_node)

    def visit_pragma_directive(self, node):
        self.directives.append(node.value)


def _tokenize_directives(header_value, rule):
    # We allow a bit of leeway from the RFC, allowing spaces before and after the header
    # value, by stripping the input string.
    header_value = header_value.strip()

    if not header_value:
        return {}

    header_node = rule.parse_all(header_value)
    header_visitor = DirectivesVisitor()
    header_visitor.visit(header_node)

    directives_dict = CaseInsensitiveDict()
    for directive in header_visitor.directives:
        if "=" in directive:
            directive, argument = directive.split("=", 1)
            # RFC7234 requires recognizing quoted-string forms even where they are not
            # recommended. Thankfully the parser will reject invalid half-quoted
            # strings.
            if argument[0] == '"':
                argument = argument[1:-1]
        else:
            argument = None

        if directive in directives_dict:
            logger.debug("Duplicate directive '%s' in header", directive)
        else:
            directives_dict[directive] = argument

    return directives_dict


def tokenize_cache_control(header_value):
    return _tokenize_directives(header_value, _get_cache_control_rule())


def tokenize_pragma(header_value):
    return _tokenize_directives(header_value, _get_pragma_rule())
