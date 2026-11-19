# -*- coding: utf-8 -*-
"""Omise webhook 签名验签的单元测试(纯函数, 不依赖 DB)。"""
import base64
import hashlib
import hmac
import time

from django.test import override_settings

from dvadmin.tenant.payment import verify_webhook_signature


def _make_signature(secret: str, raw_body: bytes, timestamp: str) -> str:
    """按 Omise 文档生成 HMAC-SHA256 hex 签名, 便于测试。"""
    key = base64.b64decode(secret)
    signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
    return hmac.new(key, signed_payload, hashlib.sha256).hexdigest()


SECRET = base64.b64encode(b"test-webhook-secret-0123456789").decode("ascii")


class TestVerifyWebhookSignature:
    def test_valid_signature(self):
        body = b'{"key":"charge.complete","data":{"id":"chrg_123","status":"successful"}}'
        ts = str(int(time.time()))
        sig = _make_signature(SECRET, body, ts)
        with override_settings(OMISE_WEBHOOK_SECRET=SECRET):
            ok, reason = verify_webhook_signature(body, sig, ts)
        assert ok is True and reason == "ok"

    def test_tampered_body_rejected(self):
        body = b'{"key":"charge.complete","data":{"id":"chrg_123","status":"successful"}}'
        ts = str(int(time.time()))
        sig = _make_signature(SECRET, body, ts)
        # 篡改 body(把 successful 改成 pending 尝试伪造), 签名必须失效
        tampered = body.replace(b"successful", b"pending")
        with override_settings(OMISE_WEBHOOK_SECRET=SECRET):
            ok, reason = verify_webhook_signature(tampered, sig, ts)
        assert ok is False and reason == "bad_signature"

    def test_replay_rejected_by_timestamp(self):
        body = b'{"key":"charge.complete"}'
        old_ts = str(int(time.time()) - 3600)  # 1 小时前
        sig = _make_signature(SECRET, body, old_ts)
        with override_settings(OMISE_WEBHOOK_SECRET=SECRET):
            ok, reason = verify_webhook_signature(body, sig, old_ts)
        assert ok is False and reason == "bad_timestamp"

    def test_not_configured(self):
        body = b'{"key":"charge.complete"}'
        with override_settings(OMISE_WEBHOOK_SECRET=""):
            ok, reason = verify_webhook_signature(body, "deadbeef", str(int(time.time())))
        assert ok is False and reason == "not_configured"

    def test_missing_headers(self):
        with override_settings(OMISE_WEBHOOK_SECRET=SECRET):
            ok, reason = verify_webhook_signature(b"body", "", "")
        assert ok is False and reason == "missing_headers"

    def test_rotation_multi_signature(self):
        """轮换期间 header 含两个逗号分隔签名, 任一匹配即通过。"""
        secret_new = base64.b64encode(b"new-secret-abcdefghijklmnop").decode("ascii")
        body = b'{"key":"charge.complete"}'
        ts = str(int(time.time()))
        sig_old = _make_signature(SECRET, body, ts)
        sig_new = _make_signature(secret_new, body, ts)
        # 新 secret 生效, header 里新旧两个签名都带, 旧的应仍能验过
        combined = f"{sig_new},{sig_old}"
        with override_settings(OMISE_WEBHOOK_SECRET=secret_new):
            ok, reason = verify_webhook_signature(body, combined, ts)
        assert ok is True and reason == "ok"
