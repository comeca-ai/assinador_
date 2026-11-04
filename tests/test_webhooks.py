import unittest
from backend.webhooks import sign,verify

class WebhookHelperTests(unittest.TestCase):
    def test_signature_covers_id_time_body_and_expiry(self):
        key=b'test-secret-not-for-production'
        signature=sign(key,'event-id',1000,b'{}')
        self.assertTrue(verify(key,'event-id',1000,b'{}',signature,now=1001))
        self.assertFalse(verify(key,'event-id',1000,b'{"changed":true}',signature,now=1001))
        self.assertFalse(verify(key,'other',1000,b'{}',signature,now=1001))
        self.assertFalse(verify(key,'event-id',1000,b'{}',signature,now=1400))
