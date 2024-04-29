import os.path
import re
import unittest

from pathsub.cli import (
    generate_temp_name,
    make_pattern,
    make_plan,
    resub_basename,
    resub_path,
)


class TestMakePattern(unittest.TestCase):
    def test_make_pattern_literal_false_ignore_case_false(self):
        expect_flags = re.compile("x").flags
        got_pattern = make_pattern("a.b", False, False)

        self.assertEqual(got_pattern.pattern, "a.b")
        self.assertEqual(got_pattern.flags, expect_flags)
        self.assertIsNotNone(got_pattern.match("axb"))
        self.assertIsNone(got_pattern.match("Axb"))

    def test_make_pattern_literal_true_ignore_case_false(self):
        expect_flags = re.compile("x").flags
        got_pattern = make_pattern("a.b", True, False)

        self.assertEqual(got_pattern.pattern, "a\\.b")
        self.assertEqual(got_pattern.flags, expect_flags)
        self.assertIsNotNone(got_pattern.match("a.b"))
        self.assertIsNone(got_pattern.match("axb"))

    def test_make_pattern_literal_false_ignore_case_true(self):
        expect_flags = re.compile("x", re.IGNORECASE).flags
        got_pattern = make_pattern("a.b", False, True)

        self.assertEqual(got_pattern.pattern, "a.b")
        self.assertEqual(got_pattern.flags, expect_flags)
        self.assertIsNotNone(got_pattern.match("axb"))
        self.assertIsNotNone(got_pattern.match("Axb"))
        self.assertIsNone(got_pattern.match("Axc"))

    def test_make_pattern_literal_true_ignore_case_true(self):
        expect_flags = re.compile("x", re.IGNORECASE).flags
        got_pattern = make_pattern("a.b", True, True)

        self.assertEqual(got_pattern.pattern, "a\\.b")
        self.assertEqual(got_pattern.flags, expect_flags)
        self.assertIsNotNone(got_pattern.match("a.b"))
        self.assertIsNotNone(got_pattern.match("A.b"))
        self.assertIsNone(got_pattern.match("axb"))


class TestResubBasename(unittest.TestCase):
    def test_resub_basename_without_sep_match(self):
        pattern = re.compile("foo")
        got = resub_basename(pattern, "bar", "foo")
        self.assertEqual(got, "bar")

    def test_resub_basename_with_sep_match(self):
        pattern = re.compile("foo")
        subject = os.path.join("foo", "foo")
        expect = os.path.join("foo", "bar")
        got = resub_basename(pattern, "bar", subject)
        self.assertEqual(got, expect)

    def test_resub_basename_without_sep_miss(self):
        pattern = re.compile("foo")
        got = resub_basename(pattern, "bar", "baz")
        self.assertEqual(got, "baz")

    def test_resub_basename_with_sep_miss(self):
        pattern = re.compile("foo")
        subject = os.path.join("foo", "baz")
        expect = os.path.join("foo", "baz")
        got = resub_basename(pattern, "bar", subject)
        self.assertEqual(got, expect)


class TestGenerateTempName(unittest.TestCase):
    def test_generate_temp_name_without_sep_without_dot(self):
        subject = "foo"
        got = generate_temp_name(subject)
        self.assertRegex(got, r"^foo__submv\w+$")

    def test_generate_temp_name_without_sep_with_dot(self):
        subject = "foo.txt"
        got = generate_temp_name(subject)
        self.assertRegex(got, r"^foo__submv\w+\.txt$")

    def test_generate_temp_name_without_sep_hidden(self):
        subject = ".foo"
        got = generate_temp_name(subject)
        self.assertRegex(got, r"^\.foo__submv\w+$")

    def test_generate_temp_name_with_sep_without_dot(self):
        subject = os.path.join("foo", "bar")
        got = generate_temp_name(subject)
        self.assertRegex(got, rf"^foo{os.sep}bar__submv\w+$")

    def test_generate_temp_name_with_sep_with_dot(self):
        subject = os.path.join("foo", "bar.txt")
        got = generate_temp_name(subject)
        self.assertRegex(got, rf"^foo{os.sep}bar__submv\w+\.txt$")

    def test_generate_temp_name_with_sep_hidden(self):
        subject = os.path.join("foo", ".bar")
        got = generate_temp_name(subject)
        self.assertRegex(got, rf"^foo{os.sep}\.bar__submv\w+$")


class TestResubPath(unittest.TestCase):
    def test_resub_basename_without_sep_match(self):
        pattern = re.compile("foo")
        got = resub_path(pattern, "bar", "foo")
        self.assertEqual(got, "bar")

    def test_resub_basename_with_sep_match(self):
        pattern = re.compile("foo")
        subject = os.path.join("foo", "foo")
        expect = os.path.join("bar", "bar")
        got = resub_path(pattern, "bar", subject)
        self.assertEqual(got, expect)

    def test_resub_basename_without_sep_miss(self):
        pattern = re.compile("foo")
        got = resub_path(pattern, "bar", "baz")
        self.assertEqual(got, "baz")

    def test_resub_basename_with_sep_dirname_match(self):
        pattern = re.compile("foo")
        subject = os.path.join("foo", "baz")
        expect = os.path.join("bar", "baz")
        got = resub_path(pattern, "bar", subject)
        self.assertEqual(got, expect)

    def test_resub_basename_with_sep_miss(self):
        pattern = re.compile("foo")
        subject = os.path.join("baz", "baz")
        expect = os.path.join("baz", "baz")
        got = resub_basename(pattern, "bar", subject)
        self.assertEqual(got, expect)


class TestMakePlan(unittest.TestCase):
    def test_without_conflicts(self):
        paths = ["a", "b1", "c1"]

        def map_path(x: str):
            return x.replace("1", "2")

        plan = make_plan(map_path, paths)

        self.assertFalse(plan.has_conflicts)
        self.assertEqual(plan.valid_moves, [("b1", "b2"), ("c1", "c2")])
        self.assertEqual(plan.conflicts, [])

    def test_with_conflicts(self):
        paths = ["a", "b1", "b2", "c1"]

        def map_path(x: str):
            return x.replace("1", "3").replace("2", "3")

        plan = make_plan(map_path, paths)

        self.assertTrue(plan.has_conflicts)
        self.assertEqual(plan.valid_moves, [("c1", "c3")])
        self.assertEqual(plan.conflicts, [(["b1", "b2"], "b3")])
