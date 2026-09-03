# SPDX-License-Identifier: Apache-2.0


def reverse(viewname, args=None, kwargs=None):
    parts = [str(item) for item in (args or ())]
    return "/" + "/".join([viewname, *parts])
