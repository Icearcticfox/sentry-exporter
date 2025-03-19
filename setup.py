#!/usr/bin/env python
import os
import setuptools

try:
    import criteo_build

    _CRITEO_BUILD = True
except ImportError:
    _CRITEO_BUILD = False

with open(os.path.join(os.path.dirname(__file__), "README.md")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))


def _read_reqs(relpath):
    fullpath = os.path.join(os.path.dirname(__file__), relpath)
    with open(fullpath) as f:
        return [
            s.strip() for s in f.readlines() if (s.strip() and not s.startswith("#"))
        ]


_REQUIREMENTS_TXT = _read_reqs("requirements.txt")
_INSTALL_REQUIRES = [req for req in _REQUIREMENTS_TXT if "://" not in req]

setup_common_args = {
    "long_description_content_type": "text/markdown",
    "long_description": README + "\n",
    "include_package_data": True,
    "entry_points": {
        "console_scripts": [
            "sentry-exporter = sentry_exporter.cmd:main",
        ]
    },
    "packages": setuptools.find_packages(),
}

if _CRITEO_BUILD:
    setuptools.setup(distclass=criteo_build.Distribution, **setup_common_args)
else:
    setuptools.setup(
        name="sentry-exporter",
        version="0.1",
        description="Sentry metric exporter",
        install_requires=_INSTALL_REQUIRES,
        **setup_common_args,
    )
