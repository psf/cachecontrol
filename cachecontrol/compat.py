# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

# Handle the case where the requests module has been patched to not have
# urllib3 bundled as part of its source.
try:
    from requests.packages.urllib3.response import HTTPResponse
except ImportError:
    from urllib3.response import HTTPResponse

try:
    from requests.packages.urllib3.util import is_fp_closed
except ImportError:
    from urllib3.util import is_fp_closed
