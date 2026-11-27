"""Regression checks for USB selection, trust requests and connection failures."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sandbox
from restore_gui import device

class ConnectionTests(unittest.TestCase):
    def probe(self, *, pair=False, devices=None, error=None, paired=False):
        from pymobiledevice3 import usbmux,lockdown
        ld=SimpleNamespace(all_values={'ProductVersion':'18.0'},display_name='iPhone',paired=paired,close=AsyncMock())
        create=AsyncMock(return_value=ld,side_effect=error)
        listing=AsyncMock(return_value=devices if devices is not None else [SimpleNamespace(serial='usb-test',connection_type='USB')])
        with patch.object(usbmux,'list_devices',listing),patch.object(lockdown,'create_using_usbmux',create):
            result=device.probe_device(pair=pair)
        return result,create,ld

    def test_explicit_connect_requests_trust(self):
        result,create,ld=self.probe(pair=True,paired=True)
        self.assertTrue(create.call_args.kwargs['autopair'])
        self.assertEqual(create.call_args.kwargs['connection_type'],'USB')
        self.assertTrue(result['paired'])
        ld.close.assert_awaited_once()

    def test_poll_does_not_request_trust(self):
        result,create,_=self.probe()
        self.assertFalse(create.call_args.kwargs['autopair'])
        self.assertEqual(result['state'],'trust')

    def test_wifi_device_is_not_selected(self):
        result,create,_=self.probe(devices=[SimpleNamespace(serial='wifi',connection_type='Network')])
        self.assertIsNone(result)
        create.assert_not_called()

    def test_service_failure_is_distinct(self):
        from pymobiledevice3.exceptions import ConnectionFailedToUsbmuxdError
        result,_,_=self.probe(error=ConnectionFailedToUsbmuxdError())
        self.assertEqual(result['state'],'driver')

    def test_trust_denial_is_explained(self):
        from pymobiledevice3.exceptions import UserDeniedPairingError
        result,_,_=self.probe(pair=True,error=UserDeniedPairingError())
        self.assertEqual(result['state'],'trust')
        self.assertIn('отклонено',result['message'])

    def test_timeout_is_explained(self):
        result,_,_=self.probe(pair=True,error=TimeoutError())
        self.assertEqual(result['state'],'trust')
