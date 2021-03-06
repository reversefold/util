import os
import sys
import subprocess

from colorama import Fore, Style

from reversefold.util import multiproc


def escape_double_quotes(val):
    return val.replace('"', '''"'"'"''')


def escape_single_quotes(val):
    return val.replace("'", """'"'"'""")


class SSHException(Exception):
    pass


class SSHHost(object):
    # Used to know when no value is passed into stdin as None is a valid value
    __SENTINEL = object()

    def __init__(
        self,
        host,
        port=None,
        user=None,
        output_prefix="",
        prefix_pad_length=28,
        connect_timeout=5,
        # Default to no specific cipher to allow the client and server to negotiate one.
        # Can be used to force a specific cipher.
        cipher=None,
        # Default to not checking host keys as cloud servers make it super annoying.
        # Also default log level to ERROR so we don't see output about the host keys.
        check_host_keys=False,
        ssh_log_level="ERROR",
        identity=None,
        use_color=True,
        quiet=True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.prefix = output_prefix
        self.connect_timeout = connect_timeout
        self.cipher = cipher
        self.check_host_keys = check_host_keys
        self.ssh_log_level = ssh_log_level
        if identity is None:
            self.identity = os.environ.get("IDENTITY", None)
        else:
            self.identity = identity
        self.use_color = use_color
        self.quiet = quiet
        self.host_prefix = "%s[%s%s%s%s%s%s%s]%s" % (
            Style.BRIGHT if self.use_color else "",
            Style.NORMAL if self.use_color else "",
            Fore.LIGHTBLUE_EX if self.use_color else "",
            "%s@" % (user,) if user is not None else "",
            host,
            ":%s" % (port,) if port is not None else "",
            Fore.RESET if self.use_color else "",
            Style.BRIGHT if self.use_color else "",
            Style.NORMAL if self.use_color else "",
        )
        text_len = (
            len(self.host_prefix)
            - len(Style.BRIGHT) * 2
            - len(Style.NORMAL) * 2
            - len(Fore.LIGHTBLUE_EX)
            - len(Fore.RESET)
        )
        if text_len < prefix_pad_length:
            self.host_prefix += " " * (prefix_pad_length - text_len)
        self.full_prefix = "%s%s" % (self.prefix, self.host_prefix)

    def puts(self, line=None):
        """
        Write line to stdout prefixed by host
        """
        if line is None:
            line = ""
        elif not isinstance(line, str):
            line = line.decode(errors="backslashreplace")

        sys.stdout.write("%s %s" % (self.full_prefix, line))
        sys.stdout.flush()

    def _get_ssh_options(self, force_tty=False):
        ssh_options = [
            # compress
            "-C",
            # Don't even try to ask for a password if key auth fails
            "-o",
            "BatchMode=yes",
            # Send a null packet every 5 seconds to make sure our connection stays
            # open as long as needed.
            "-o",
            "ServerAliveInterval=5",
            # Explicitly set ControlMaster and ControlPath to make sure that scripted SSH sessions don't accidentally
            # clobber each other. (Imagine one SSH to a host starts, then a second one starts and the first ssh is
            # stopped by the script before the second is finished. The first SSH session being terminated will terminate
            # the second while it may still be running a command.)
            "-o",
            "ControlMaster=no",
            "-o",
            "ControlPath=none",
        ]

        if not self.check_host_keys:
            ssh_options.extend(
                ["-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no"]
            )

        if self.ssh_log_level is not None:
            ssh_options.extend(["-o", "LogLevel=%s" % (self.ssh_log_level,)])

        if self.cipher is not None:
            ssh_options.extend(["-c", str(self.cipher)])

        if self.port is not None:
            ssh_options.extend(["-p", str(self.port)])

        if self.user is not None:
            ssh_options.extend(["-l", str(self.user)])

        if self.connect_timeout is not None:
            ssh_options.extend(["-o", "ConnectTimeout=%s" % (self.connect_timeout,)])

        if force_tty:
            ssh_options.extend(["-t", "-t"])

        if self.identity is not None:
            ssh_options.extend(["-o", "IdentityFile=%s" % (self.identity,)])

        if self.quiet:
            ssh_options.append("-q")

        return ssh_options

    def _get_ssh_cmd(self, force_tty=False):
        """Get the array needed to run subprocess.Popen with ssh"""

        sshcmd = ["ssh"]
        sshcmd.extend(self._get_ssh_options(force_tty))
        sshcmd.append(str(self.host))

        return sshcmd

    def _start(
        self,
        executable,
        command,
        cwd=None,
        output_running=False,
        stdin=__SENTINEL,
        close_stdin=True,
        force_tty=False,
    ):
        cmds = []
        if cwd is not None:
            cmds.append("cd '%s'" % (escape_single_quotes(cwd),))

        cmds.append(command)

        run_cmd = "; ".join(cmds)

        if output_running:
            self.puts(run_cmd)

        sshcmd = self._get_ssh_cmd(force_tty)
        sshcmd.append("%s '%s'" % (executable, escape_single_quotes(run_cmd)))

        stdin_type = (
            subprocess.PIPE
            if stdin is SSHHost.__SENTINEL or isinstance(stdin, str)
            else stdin
        )

        ssh = subprocess.Popen(
            sshcmd, stdin=stdin_type, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        if stdin_type == subprocess.PIPE:
            if isinstance(stdin, str):
                ssh.stdin.write(stdin)
            if close_stdin:
                ssh.stdin.close()
        return ssh

    def start(
        self,
        command,
        cwd=None,
        output_running=False,
        stdin=__SENTINEL,
        close_stdin=True,
        force_tty=False,
        capture_output=False,
    ):
        proc = self._start(
            "/bin/bash -c", command, cwd, output_running, stdin, close_stdin, force_tty
        )
        (stdout, stderr, threads) = multiproc.run_subproc(
            proc,
            output_func=self.puts,
            wait=False,
            capture_output=capture_output,
            use_color=self.use_color,
        )
        return (proc, threads, stdout, stderr)

    def _run(
        self,
        executable,
        command,
        cwd=None,
        output_running=False,
        stdin=__SENTINEL,
        capture_output=False,
    ):
        """
        Runs command via ssh and executable.
        """
        ssh = self._start(executable, command, cwd, output_running, stdin)
        (stdout, stderr) = multiproc.run_subproc(
            ssh,
            output_func=self.puts,
            capture_output=capture_output,
            use_color=self.use_color,
        )

        if ssh.returncode:
            raise SSHException("ssh return code was %r" % (ssh.returncode,))

        return (stdout, stderr)

    def run(
        self,
        command,
        cwd=None,
        output_running=False,
        stdin=__SENTINEL,
        capture_output=True,
    ):
        return self._run(
            "/bin/bash -c", command, cwd, output_running, stdin, capture_output
        )

    def sudo(
        self,
        command,
        cwd=None,
        output_running=False,
        stdin=__SENTINEL,
        capture_output=True,
    ):
        return self._run(
            "sudo /bin/bash -c", command, cwd, output_running, stdin, capture_output
        )
