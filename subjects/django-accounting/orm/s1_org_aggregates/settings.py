# SPDX-License-Identifier: Apache-2.0
"""Isolated Django settings for the org-aggregates scaffold.

This is not the pin's project settings. The frozen slice has none.
"""

SECRET_KEY = "s1-org-aggregates-scaffold-not-a-secret"
DEBUG = True
INSTALLED_APPS = ["s1_org_aggregates"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = False
TIME_ZONE = "UTC"
