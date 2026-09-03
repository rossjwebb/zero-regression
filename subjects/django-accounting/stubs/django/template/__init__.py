# SPDX-License-Identifier: Apache-2.0


class Library:
    def filter(self, name=None, **kwargs):
        def decorator(func):
            return func

        if callable(name):
            return name
        return decorator
