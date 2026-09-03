# SPDX-License-Identifier: Apache-2.0


def get_language():
    return "en-us"


def to_locale(language):
    return language.replace("-", "_")


def ugettext_lazy(message):
    return message


def gettext_lazy(message):
    return message
