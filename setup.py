#!/usr/bin/env python3


import pathsub

from setuptools import setup
import os
import sys


with open(os.path.join(
        os.path.dirname(sys.modules["__main__"].__file__),
        "readme.rst"
    ), "r") as readme_stream:
    readme_text = readme_stream.read()


setup(
    name             = "pathsub",
    version          = pathsub.__version__,
    description      = pathsub.__doc__.strip(),
    long_description = readme_text,
    author           = "Jim Boswell",
    author_email     = "jimb@yellcorp.org",
    license          = "MIT",
    url              = "https://github.com/yellcorp/pathsub",

    packages=[ "pathsub" ],
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Topic :: Utilities'
    ],
    entry_points={
        "console_scripts": [
            "submv = pathsub.cli:submv_main",
            "subcp = pathsub.cli:subcp_main"
        ]
    },
    # test_suite="tests"
)
