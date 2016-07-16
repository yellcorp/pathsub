pathsub
=======

Python 3 CLI utilities for performing find-replace operations on file paths.

Paths can be matched by literal text, or regular expressions. Files can be
moved/renamed or copied.

If a problem is encountered, an attempt is made to rollback all the changes
made up to that point. Problems can arise in the form of OS errors, or
conflicts among the new paths. Paths conflict if multiple paths are renamed to
the same path, or names that the filesystem prohibits from coexisting in the
same folder. For example, NTFS and HFS+ volumes don't allow filenames within a
directory to differ only in letter case.

Copyright (c) 2016 Jim Boswell.  Licensed under the Expat MIT license.  See the
file LICENSE for the full text.

TODO
----

Documentation

CLI Usage
---------

submv
~~~~~

usage: submv [-h] [-b] [-l] [-i] [-p] [-t] [-v] [--debug] [-q] [--version]
             SEARCH REPLACE PATH [PATH ...]

Rename or move files by performing find-replace operations on their paths.

positional arguments:
  SEARCH             The regular expression, or string if -l/--literal is
                     specified, to match
  REPLACE            The replacement string. If SEARCH is a regular
                     expression, the content of capturing groups can be used
                     by including \\#, \\g<#>, where # is a number, or \\g<NAME>,
                     where NAME is the name of a named group.
  PATH               The files to rename or move.

optional arguments:
  -h, --help         show this help message and exit
  -b, --basename     Restrict the find/replace to just the file's name - that
                     is, the part of the path after the last path separator.
  -l, --literal      Match the search string as specified, rather than
                     interpreting it as a regular expression.
  -i, --ignore-case  Case-insensitive matching of strings or regular
                     expressions.
  -p, --plan         Show the intended changes without making them. Because
                     this mode doesn't query the filesystem, conflicts can
                     only be detected when files share exact paths. The actual
                     operation may have more conflicts due to pre-existing
                     files, case-insensitivity or unicode normalization.
  -t, --trial        Make changes, but immediately roll them back when
                     complete. This can serve as a more accurate preview than
                     the -p/--plan option.
  -v, --verbose      Show each move, rename or copy as it is performed.
  --debug            Show every filesystem operation as it is performed,
                     including intermediate ones and rollbacks.
  -q, --quiet        Suppress all output, including errors.
  --version          show program's version number and exit

To copy files instead of renaming or moving them, use subcp.
