import os.path
import re


__all__ = [ "resub_string_iterator", "resub_basename_iterator" ]


def normalize_pattern(pattern, flags=0):
    if isinstance(pattern, str):
        return re.compile(pattern, flags)
    # otherwise assume it's already a compiled pattern
    return pattern


def resub_string_iterator(pattern, replace, string_iter, flags=0):
    pattern = normalize_pattern(pattern, flags)
    for string in string_iter:
        yield (string, pattern.sub(replace, string))


def resub_basename_iterator(pattern, replace, path_string_iter, flags=0):
    pattern = normalize_pattern(pattern, flags)
    for path in path_string_iter:
        container, name = os.path.split(path)
        yield (path, os.path.join(container, pattern.sub(replace, name)))
