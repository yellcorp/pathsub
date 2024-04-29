import os.path

from pathsub.agents import Executive, HistoryAgent, Mkdir, Move, Rmdir, RollbackError
from tests.utils_for_testing import FixtureDirTestCase, read_file, write_file

TEST_CONTENT_1 = b"Test fixture 1 TTLOmpmgPPeblKWrXhvmn0Bz1wPf67ZUFTk-a1e5uN4"
TEST_CONTENT_2 = b"Test fixture 2 kYtSpdv1OMSyF4MRvww3dPBURBRhDNxfCbTj4XYrkwg"
TEST_CONTENT_3 = b"Test fixture 3 1cWB5dl_TtWYcSqz8lD4CRLvsdIIZwtR69pdsyMf-Bc"


class TestExecutive(FixtureDirTestCase):
    def test_move(self):
        agent = Executive()

        start = os.path.join(self._fixture_dir.name, "start")
        end = os.path.join(self._fixture_dir.name, "end")

        write_file(start, TEST_CONTENT_1)

        assert os.path.isfile(start)
        assert not os.path.exists(end)

        agent.move(start, end)

        self.assertFalse(os.path.exists(start))
        self.assertTrue(os.path.isfile(end))
        self.assertEqual(read_file(end), TEST_CONTENT_1)

    def test_mkdir(self):
        agent = Executive()

        the_dir = os.path.join(self._fixture_dir.name, "foo")

        assert not os.path.exists(the_dir)
        agent.mkdir(the_dir)
        self.assertTrue(os.path.isdir(the_dir))

    def test_rmdir(self):
        agent = Executive()

        the_dir = os.path.join(self._fixture_dir.name, "foo")
        os.mkdir(the_dir)
        assert os.path.isdir(the_dir)

        agent.rmdir(the_dir)
        self.assertFalse(os.path.exists(the_dir))


class TestOperations(FixtureDirTestCase):
    def test_move_operation(self):
        agent = Executive()
        start = os.path.join(self._fixture_dir.name, "start")
        end = os.path.join(self._fixture_dir.name, "end")
        write_file(start, TEST_CONTENT_1)

        operation = Move(start, end)
        operation.execute(agent)

        self.assertFalse(os.path.exists(start))
        self.assertTrue(os.path.isfile(end))
        self.assertEqual(read_file(end), TEST_CONTENT_1)

        undo_op = operation.get_undo()
        undo_op.execute(agent)
        self.assertTrue(os.path.isfile(start))
        self.assertFalse(os.path.exists(end))
        self.assertEqual(read_file(start), TEST_CONTENT_1)

    def test_move_operation_doesnt_overwrite(self):
        agent = Executive()
        start = os.path.join(self._fixture_dir.name, "start")
        end = os.path.join(self._fixture_dir.name, "end")
        write_file(start, TEST_CONTENT_1)
        write_file(end, TEST_CONTENT_2)

        operation = Move(start, end)
        self.assertRaises(FileExistsError, operation.execute, agent)
        self.assertEqual(read_file(start), TEST_CONTENT_1)
        self.assertEqual(read_file(end), TEST_CONTENT_2)

    def test_mkdir_operation(self):
        agent = Executive()
        the_dir = os.path.join(self._fixture_dir.name, "foo")
        assert not os.path.exists(the_dir)
        operation = Mkdir(the_dir)
        operation.execute(agent)
        self.assertTrue(os.path.isdir(the_dir))
        operation.get_undo().execute(agent)
        self.assertFalse(os.path.exists(the_dir))

    def test_rmdir_operation(self):
        agent = Executive()
        the_dir = os.path.join(self._fixture_dir.name, "foo")
        os.mkdir(the_dir)
        assert os.path.isdir(the_dir)
        operation = Rmdir(the_dir)
        operation.execute(agent)
        self.assertFalse(os.path.exists(the_dir))
        operation.get_undo().execute(agent)
        self.assertTrue(os.path.isdir(the_dir))


class TestHistoryAgent(FixtureDirTestCase):
    def test_full_rollback(self):
        agent = Executive()
        history = HistoryAgent(agent)

        start = os.path.join(self._fixture_dir.name, "start")
        container = os.path.join(self._fixture_dir.name, "container")
        end = os.path.join(container, "end")
        write_file(start, TEST_CONTENT_1)

        history.mkdir(container)
        history.move(start, end)

        self.assertFalse(os.path.exists(start))
        self.assertTrue(os.path.isdir(container))
        self.assertTrue(os.path.isfile(end))
        self.assertEqual(read_file(end), TEST_CONTENT_1)

        history.rollback()

        self.assertTrue(os.path.isfile(start))
        self.assertFalse(os.path.exists(container))
        self.assertFalse(os.path.exists(end))
        self.assertEqual(read_file(start), TEST_CONTENT_1)

    def test_partial_rollback(self):
        agent = Executive()
        history = HistoryAgent(agent)

        start = os.path.join(self._fixture_dir.name, "start")
        container = os.path.join(self._fixture_dir.name, "container")
        intermediate = os.path.join(container, "intermediate")
        end = os.path.join(container, "end")

        write_file(start, TEST_CONTENT_1)
        os.mkdir(container)
        write_file(end, TEST_CONTENT_2)

        history.move(start, intermediate)
        self.assertRaises(FileExistsError, history.move, intermediate, end)

        history.rollback()

        self.assertTrue(os.path.isfile(start))
        self.assertTrue(os.path.isfile(end))
        self.assertFalse(os.path.exists(intermediate))
        self.assertEqual(read_file(start), TEST_CONTENT_1)
        self.assertEqual(read_file(end), TEST_CONTENT_2)

    def test_file_swap(self):
        agent = Executive()
        history = HistoryAgent(agent)

        file1 = os.path.join(self._fixture_dir.name, "foo")
        file2 = os.path.join(self._fixture_dir.name, "bar")
        intermediate = os.path.join(self._fixture_dir.name, "intermediate")

        write_file(file1, TEST_CONTENT_1)
        write_file(file2, TEST_CONTENT_2)

        history.move(file1, intermediate)
        history.move(file2, file1)
        history.move(intermediate, file2)

        self.assertEqual(read_file(file1), TEST_CONTENT_2)
        self.assertEqual(read_file(file2), TEST_CONTENT_1)

        history.rollback()

        self.assertEqual(read_file(file1), TEST_CONTENT_1)
        self.assertEqual(read_file(file2), TEST_CONTENT_2)

    def test_non_critically_failed_rollback(self):
        agent = Executive()
        history = HistoryAgent(agent)

        start = os.path.join(self._fixture_dir.name, "start")
        container = os.path.join(self._fixture_dir.name, "container")
        end = os.path.join(container, "end")
        rollback_blocker = os.path.join(container, "blocker")

        write_file(start, TEST_CONTENT_1)

        history.mkdir(container)
        history.move(start, end)

        self.assertFalse(os.path.exists(start))
        self.assertEqual(read_file(end), TEST_CONTENT_1)

        # Now prevent `container` from being removed by creating a file in there
        # that HistoryAgent isn't aware of
        write_file(rollback_blocker, TEST_CONTENT_2)

        # The rollback should still complete because failure to undo a
        # mkdir is not considered critical.
        errors = history.rollback()
        self.assertEqual(len(errors), 1)
        (path_and_exc,) = errors
        error_path, error_exc = path_and_exc
        self.assertEqual(error_path, container)
        self.assertIsInstance(error_exc, OSError)

        self.assertFalse(os.path.exists(end))
        self.assertEqual(read_file(start), TEST_CONTENT_1)

    def test_failed_rollback(self):
        agent = Executive()
        history = HistoryAgent(agent)

        start = os.path.join(self._fixture_dir.name, "start")
        intermediate = os.path.join(self._fixture_dir.name, "intermediate")
        end = os.path.join(self._fixture_dir.name, "end")

        write_file(start, TEST_CONTENT_1)

        history.move(start, intermediate)
        history.move(intermediate, end)

        # block the rollback
        write_file(intermediate, TEST_CONTENT_2)

        self.assertRaises(RollbackError, history.rollback)

        # Do it again so we can run tests on the exception as well.
        rollback_error = None
        try:
            history.rollback()
        except RollbackError as caught_rollback_error:
            rollback_error = caught_rollback_error

        self.assertIsInstance(rollback_error, RollbackError)
        self.assertIsInstance(rollback_error.remaining_operations, list)
        self.assertEqual(len(rollback_error.remaining_operations), 2)
        move_end_to_int, move_int_to_start = rollback_error.remaining_operations

        self.assertIsInstance(move_end_to_int, Move)
        self.assertEqual(move_end_to_int.src, end)
        self.assertEqual(move_end_to_int.dest, intermediate)

        self.assertIsInstance(move_int_to_start, Move)
        self.assertEqual(move_int_to_start.src, intermediate)
        self.assertEqual(move_int_to_start.dest, start)
