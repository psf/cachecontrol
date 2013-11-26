import six

from six.moves.urllib.parse import urljoin

import email

if six.PY3:
    parsedate_tz = email.utils.parsedate_tz
else:
    parsedate_tz = email.Utils.parsedate_tz
