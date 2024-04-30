pathsub
=======

Provides the command-line utility ``submv`` for renaming files and
directories with find-and-replace.

Paths can be matched by literal text, or by regular expressions. When
regular expressions are used, the replacement text can reference numbered
or named capturing groups. The find-replace can apply to the file's entire
path, or just its name. If a file's new path would place it in a directory
that doesn't exist, that directory and any necessary parent directories
are created.

If an error occurs, a rollback is performed, undoing all the rename/move
operations completed before the error. Existing files are never
overwritten - renames that would cause two files to have the same name are
considered errors. Your operating system and file system determine whether
two names are considered the same - NTFS, HFS+ and APFS are all
case-insensitive by default. `HFS+ is also normalization-insensitive
<https://developer.apple.com/library/archive/technotes/tn/tn1150.html#UnicodeSubtleties>`_.

Usage
-----

``submv [-h] [-b] [-l] [-i] [-n] [--version] SEARCH REPLACE PATH [PATH ...]``

Rename or move files by performing find-replace operations on their paths.

.. list-table:: Positional arguments
   :widths: 14 56

   * - ``SEARCH``
     - The regular expression to match, unless ``-l/--literal`` is
       specified, in which case this is interpreted as the literal text to
       match.

   * - ``REPLACE``
     - The replacement string. If ``SEARCH`` is a regular expression (that
       is, if ``-l/--literal`` is not specified), capturing groups can be
       referenced by index with ``\N`` or ``\g<N>``, where ``N`` is the
       group's 1-based index, or by name with ``\g<NAME>``. For more
       detail see the `Python documentation
       <https://docs.python.org/3/library/re.html>`_ for ``re.sub``,
       specifically the ``repl`` argument.

   * - ``PATH``
     - The files or directories to rename or move.

.. list-table:: Options
   :widths: 14 56

   * - ``-h, --help``
     - Show help message and exit.

   * - ``-b, --basename``
     - Change only the basename of the file - that is, the part of the
       path after the last path separator.

   * - ``-l, --literal``
     - Match the search string as specified, rather than interpreting it
       as a regular expression.

   * - ``-i, --ignore-case`` 
     - Case-insensitive matching of strings or regular expressions.

   * - ``-n, --dry-run``     
     - Show the intended changes without making them. Different files that
       would end up with identical paths are reported as conflicts. This
       does not query the file system, so only exactly identical paths
       count as conflicts - your OS and file system may apply further
       restrictions such as case insensitivity or Unicode normalization.
       Such conflicts are only detected when trying to actually rename the
       files.

   * - ``--version``     
     - Show program's version number and exit.
