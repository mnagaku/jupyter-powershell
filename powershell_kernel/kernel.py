from ipykernel.kernelbase import Kernel

from os import unlink, environ

import base64
import imghdr
import re
import signal
import urllib
import sys
import traceback

from powershell_kernel import subprocess_repl, powershell_proxy
from powershell_kernel.util import get_powershell

__version__ = '0.1.2'

version_pat = re.compile(r'version (\d+(\.\d+)+)')

class PowerShellKernel(Kernel):
    implementation = 'powershell_kernel'
    implementation_version = __version__

    @property
    def language_version(self):
        m = version_pat.search(self.banner)
        return m.group(1)

    _banner = None

    @property
    def banner(self):
        return self._banner

    language_info = {'name': 'powershell',
                     'codemirror_mode': 'shell',
                     'mimetype': 'text/x-sh',
                     'file_extension': '.ps1'}

    proxy = None

    def __createProxy(self):
        # powershell_command env variable is set by the kernel to allow both powershell and pwsh
        # but on python2 we cannot pass it thru env variable, see https://github.com/vors/jupyter-powershell/issues/7
        # TODO(python2): can we pass it somehow differently and still provide user-picked value on python2?
        try:
            powershell_command = environ['powershell_command']
        except:
            powershell_command = get_powershell()

        repl = subprocess_repl.SubprocessRepl([powershell_command, '-noninteractive', '-noprofile', '-File', '-'])
        self.proxy = powershell_proxy.ReplProxy(repl)

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        try:
            if not code.strip():
                return {'status': 'ok', 'execution_count': self.execution_count,
                        'payload': [], 'user_expressions': {}}

            if not self.proxy:
                self.__createProxy()

            output = self.proxy.run_command(code)

            message = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', message)

            return {'status': 'ok', 'execution_count': self.execution_count,
                    'payload': [], 'user_expressions': {}}

        except Exception:
            excInfo = sys.exc_info()
            message = {
                'ename': str(excInfo[0].__name__),
                'evalue': str(excInfo[1]),
                'traceback': [traceback.format_exc()]
            }
            self.send_response(self.iopub_socket, 'error', message)
            message['status'] = 'error'
            return message
