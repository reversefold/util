import unittest

import mock
import psutil

from reversefold.util import proc


class TestException(Exception):
    pass


class TestProc(unittest.TestCase):
    def setUp(self):
        self.psutil_Process = mock.patch('psutil.Process').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_process_tree_no_children(self):
        mock_proc = mock.MagicMock()
        self.psutil_Process.return_value = mock_proc
        mock_proc.children.return_value = []

        result = proc.get_process_tree(123)

        self.psutil_Process.assert_called_once_with(123)
        mock_proc.children.assert_called_once_with(recursive=True)

        self.assertEquals(result, [mock_proc])

    def test_get_process_tree_with_children(self):
        mock_proc = mock.MagicMock()
        mock_procs = [mock.MagicMock() for _ in xrange(3)]
        self.psutil_Process.return_value = mock_proc
        mock_proc.children.return_value = mock_procs

        result = proc.get_process_tree(123)

        self.psutil_Process.assert_called_once_with(123)
        mock_proc.children.assert_called_once_with(recursive=True)

        self.assertEquals(result, [mock_proc] + mock_procs)

    def test_get_process_tree_NoSuchProcess(self):
        self.psutil_Process.side_effect = psutil.NoSuchProcess('')

        result = proc.get_process_tree(123)

        self.psutil_Process.assert_called_once_with(123)

        self.assertEquals(result, [])

    def test__signal_processes_empty(self):
        proc._signal_processes([], '')

    def test__signal_processes(self):
        mock_procs = [mock.MagicMock() for _ in xrange(4)]
        mock_procs[0].is_running.return_value = False
        mock_procs[1].is_running.return_value = True
        mock_procs[1].signal_func.side_effect = psutil.NoSuchProcess('')
        mock_procs[2].is_running.return_value = True
        mock_procs[2].signal_func.side_effect = Exception('')
        mock_procs[3].is_running.return_value = True

        proc._signal_processes(mock_procs, 'signal_func')

        mock_procs[1].signal_func.assert_called_once()
        mock_procs[2].signal_func.assert_called_once()
        mock_procs[3].signal_func.assert_called_once()

    def test_signalling(self):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 123
        mock_ps_proc = mock.MagicMock()
        self.psutil_Process.return_value = mock_ps_proc
        mock_ps_proc.is_running.return_value = True

        with proc.signalling(mock_proc, 'signal_func') as mock_proc_as:
            self.assertEqual(mock_proc_as, mock_proc)

        self.psutil_Process.assert_called_once_with(123)
        mock_ps_proc.signal_func.assert_called_once()

    def test_signalling_exc_in_with_block(self):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 123
        mock_ps_proc = mock.MagicMock()
        self.psutil_Process.return_value = mock_ps_proc
        mock_ps_proc.is_running.return_value = True

        try:
            with proc.signalling(mock_proc, 'signal_func') as mock_proc_as:
                self.assertEqual(mock_proc_as, mock_proc)
                raise TestException()
        except TestException:
            pass

        mock_ps_proc.is_running.assert_called_once()
        self.psutil_Process.assert_called_once_with(123)
        mock_ps_proc.signal_func.assert_called_once()

    def test_nested(self):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 123
        mock_ps_proc = mock.MagicMock()
        self.psutil_Process.return_value = mock_ps_proc
        mock_ps_proc.is_running.return_value = True

        try:
            with proc.killing(mock_proc) as mock_proc_as:
                self.assertEqual(mock_proc_as, mock_proc)
                try:
                    with proc.terminating(mock_proc_as) as mock_proc_as_as:
                        self.assertEqual(mock_proc_as_as, mock_proc)
                        raise TestException()
                finally:
                    mock_proc.pid = 321
        except TestException:
            pass

        self.psutil_Process.assert_has_calls([mock.call(123), mock.call(321)], any_order=True)
        mock_ps_proc.is_running.assert_has_calls([mock.call(), mock.call()], any_order=True)
        mock_ps_proc.terminate.assert_called_once()
        mock_ps_proc.kill.assert_called_once()

    def test_dead(self):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 123
        mock_ps_proc = mock.MagicMock()
        self.psutil_Process.return_value = mock_ps_proc
        mock_ps_proc.is_running.return_value = True

        with proc.dead(mock_proc) as mock_proc_as:
            self.assertEqual(mock_proc_as, mock_proc)

        self.psutil_Process.assert_has_calls([mock.call(123), mock.call(123)], any_order=True)
        mock_ps_proc.is_running.assert_has_calls([mock.call(), mock.call()], any_order=True)
        mock_ps_proc.terminate.assert_called_once()
        mock_ps_proc.kill.assert_called_once()

    def test_dead_kills_abandoned_children(self):
        mock_proc = mock.MagicMock()
        mock_proc.pid = 123
        mock_ps_proc = mock.MagicMock()
        mock_child_ps_proc = mock.MagicMock()
        mock_child_ps_proc.is_running.return_value = True
        get_process_tree = mock.patch('reversefold.util.proc.get_process_tree').start()
        get_process_tree.side_effect = [[mock_ps_proc, mock_child_ps_proc], []]
        mock_ps_proc.is_running.return_value = True

        with proc.dead(mock_proc, recursive=True) as mock_proc_as:
            self.assertEqual(mock_proc_as, mock_proc)

        mock_ps_proc.terminate.assert_called_once()
        mock_child_ps_proc.terminate.assert_called_once()
        mock_child_ps_proc.kill.assert_called_once()
