import os,sys,tempfile,subprocess,unittest,threading
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sandbox
import restore_apps as core
from restore_gui import apple
from restore_gui.tasks import TasksMixin

class Engines(unittest.TestCase):
    def setUp(self):
        self.old=(core.ENGINE,core.IPATOOL_HOME,core.SESSION_PASSPHRASE)
        core.SESSION_PASSPHRASE='test-key'
    def tearDown(self):
        core.ENGINE,core.IPATOOL_HOME,core.SESSION_PASSPHRASE=self.old
    def test_go_engine_is_rejected(self):
        with self.assertRaises(ValueError):core.configure_engine('go')
    def test_cpp_arguments_and_executable(self):
        core.configure_engine('cpp')
        self.assertEqual(core.engine_binary(),'ipatool-cpp')
        self.assertEqual(core.keychain_args(),['--keychain-passphrase','test-key'])
    def test_secret_values_are_masked(self):
        out=core.masked(['ipatool-cpp.exe','auth','login','--password','secret-password','--auth-code','123456','--keychain-passphrase','test-key'])
        for secret in ('secret-password','123456','test-key'):self.assertNotIn(secret,out)
    def test_cpp_purchase_shape_filters_non_ios_items(self):
        import json
        text=json.dumps({'count':3,'apps':[{'id':'42','name':'App','kind':'iOS App'},{'id':'43','name':'Book','kind':'Book'},{'id':'44','name':'Mac App','kind':'Mac App'}]})
        self.assertEqual(apple.parse_purchases(text),({42:'App'},3))
    def test_cpp_two_factor_round_trip(self):
        core.configure_engine('cpp');calls=[];logs=[];responses=iter([(1,'two-factor auth code required. Retry with --auth-code CODE'),(0,'success=true')])
        def stream(cmd):calls.append(cmd);return next(responses)
        b=SimpleNamespace(stop_flag=False,stream=stream,session_ok=lambda tool:True,log=logs.append,post=lambda fn:fn(),on_login_result=mock.Mock(),ask_main=lambda *a:'123456',hint=mock.Mock())
        TasksMixin.task_login(b,'ipatool-cpp.exe','example@example.com','test-password')
        self.assertEqual(len(calls),2)
        self.assertNotIn('--non-interactive',calls[0])
        self.assertIn('--auth-code',calls[1]);b.on_login_result.assert_called_with(True,'example@example.com')
    def test_cpp_purchase_list_is_fetched_once_with_all(self):
        core.configure_engine('cpp');calls=[]
        def stream(cmd,quiet_json=False):calls.append(cmd);return 0,'{"apps":[{"id":"42","name":"App","kind":"iOS App"}],"count":1}'
        b=SimpleNamespace(stop_flag=False,stream=stream,log=lambda *a:None,post=lambda fn:fn(),on_purchases_result=mock.Mock())
        with mock.patch('restore_gui.tasks.fetch_available',return_value=set()):TasksMixin.task_purchases(b,'ipatool-cpp.exe')
        self.assertEqual(len(calls),1);self.assertIn('--all',calls[0]);self.assertNotIn('--page',calls[0])
        b.on_purchases_result.assert_called_once_with({42:'App'},set())
    def test_packaged_cpp_commands_without_account(self):
        exe=Path(__file__).resolve().parents[1]/'build/res/ipatool-cpp.exe'
        if not exe.exists():self.skipTest('Build binary unavailable')
        with tempfile.TemporaryDirectory() as td:
            core.configure_engine('cpp');env=core.ipatool_env(Path(td))
            for command in [['auth','info'],['auth','login'],['list-versions','-i','650377962','--format','json'],['download','-i','650377962','-o',str(Path(td,'test.ipa'))]]:
                r=subprocess.run([str(exe),'--keychain-passphrase','test',*command],env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(r.returncode,1)
                self.assertRegex(r.stdout+r.stderr,r'Not logged in|email is required')
            self.assertFalse(Path(td,'test.ipa').exists())
