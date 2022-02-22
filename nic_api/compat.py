"""Python 2.7 compatibility"""

from sys import version_info


XML_ENCODING = "utf-8" if version_info.major < 3 else "unicode"
