# SPDX-License-Identifier: Apache-2.0

EMPTY_VALUES = (None, "", [], (), {})


class MinValueValidator:
    def __init__(self, limit_value):
        self.limit_value = limit_value

    def __call__(self, value):
        return value


class MaxValueValidator:
    def __init__(self, limit_value):
        self.limit_value = limit_value

    def __call__(self, value):
        return value
