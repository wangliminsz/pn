# -*- coding: utf-8 -*-
"""
Tencent COS(S3 兼容) 文件存储层
- 开关: settings.COS_ENABLED (conf/env 里默认 True); 关闭时回退本地 MEDIA_ROOT
- 私有桶: 下载一律用预签名 URL(默认 10 分钟)
- 提供:
    cos_storage.get_client()            调试/运维用
    cos_storage.save_file(rel, bytes)    写文件(COS 或本地)
    cos_storage.delete_file(rel)         删文件(忽略不存在)
    cos_storage.file_exists(rel)         是否存在
    cos_storage.file_url(rel)            下载地址(COS=签名URL / 本地=MEDIA_URL)
    MediaStorage                         作为 Django STORAGES['default'], 兼容 FileField(如头像)
"""
import os
import threading
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

COS_ENABLED = bool(getattr(settings, "COS_ENABLED", False))

_client = None
_lock = threading.Lock()


def get_client():
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                from qcloud_cos import CosConfig, CosS3Client
                config = CosConfig(
                    Region=settings.COS_REGION,
                    SecretId=settings.COS_SECRET_ID,
                    SecretKey=settings.COS_SECRET_KEY,
                    Scheme="https",
                )
                _client = CosS3Client(config)
    return _client


def _key(rel: str) -> str:
    """相对路径 → COS key(统一用 / 并去掉起始斜杠)"""
    return str(rel).lstrip("/").replace("\\", "/")


def _local_path(rel: str) -> str:
    return os.path.join(settings.MEDIA_ROOT, _key(rel))


def cos_save(rel: str, data: bytes):
    get_client().put_object(Bucket=settings.COS_BUCKET, Key=_key(rel), Body=data)


def cos_delete(rel: str):
    try:
        get_client().delete_object(Bucket=settings.COS_BUCKET, Key=_key(rel))
    except Exception:
        pass


def cos_read(rel: str) -> bytes:
    resp = get_client().get_object(Bucket=settings.COS_BUCKET, Key=_key(rel))
    stream = resp["Body"].get_raw_stream()
    return stream.read()


def cos_exists(rel: str) -> bool:
    try:
        get_client().head_object(Bucket=settings.COS_BUCKET, Key=_key(rel))
        return True
    except Exception:
        return False


def cos_signed_url(rel: str, expire: int = 600) -> str:
    return get_client().get_presigned_url(
        Method="GET", Bucket=settings.COS_BUCKET, Key=_key(rel), Expired=expire)


def cos_list_objects(prefix: str):
    """
    分页列出 COS 对象(带 Prefix), 返回 [{'rel','size','mtime'}] (mtime=epoch秒)
    """
    out = []
    marker = None
    while True:
        kw = {"Bucket": settings.COS_BUCKET, "Prefix": prefix, "MaxKeys": 1000}
        if marker:
            kw["Marker"] = marker
        r = get_client().list_objects(**kw)
        for o in (r.get("Contents") or []):
            lm = o.get("LastModified")
            try:
                mtime = int(lm.timestamp()) if hasattr(lm, "timestamp") else int(time.mktime(lm.timetuple()))
            except Exception:
                mtime = 0
            out.append({"rel": o["Key"], "size": int(o.get("Size") or 0), "mtime": mtime})
        if not r.get("IsTruncated"):
            break
        marker = r.get("NextMarker")
        if not marker:
            break
    return out


# ---------- 统一入口(业务代码用这个, 不直接摸文件系统) ----------

def save_file(rel: str, data: bytes):
    """保存字节流到 COS(或本地)"""
    if COS_ENABLED:
        cos_save(rel, data)
    else:
        local = _local_path(rel)
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as out:
            out.write(data)


def read_file(rel: str) -> bytes:
    if COS_ENABLED:
        return cos_read(rel)
    with open(_local_path(rel), "rb") as f:
        return f.read()


def delete_file(rel: str):
    if COS_ENABLED:
        cos_delete(rel)
    else:
        try:
            os.remove(_local_path(rel))
        except OSError:
            pass


def file_exists(rel: str) -> bool:
    if COS_ENABLED:
        return cos_exists(rel)
    return os.path.isfile(_local_path(rel))


def file_url(rel: str, expire: int = 600) -> str:
    """下载用 URL: COS=私有桶预签名(10分钟), 本地=MEDIA_URL"""
    if COS_ENABLED:
        return cos_signed_url(rel, expire)
    return f"{settings.MEDIA_URL}{_key(rel)}"


# ---------- Django Storage 后端(给 FileField / avator 等用) ----------

@deconstructible
class MediaStorage(Storage):
    """
    全局默认存储: COS_ENABLED=True 用 COS 私有桶; 否则回退本地 FileSystemStorage
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cos = COS_ENABLED
        self._local = FileSystemStorage(
            location=settings.MEDIA_ROOT,
            base_url=settings.MEDIA_URL,
        )

    def _open(self, name, mode="rb"):
        if self._cos:
            return ContentFile(cos_read(name))
        return self._local.open(name, mode)

    def _save(self, name, content):
        if self._cos:
            cos_save(name, content.read())
            return name
        return self._local.save(name, content)

    def delete(self, name):
        if self._cos:
            cos_delete(name)
        else:
            self._local.delete(name)

    def exists(self, name):
        if self._cos:
            return cos_exists(name)
        return self._local.exists(name)

    def size(self, name):
        if self._cos:
            from qcloud_cos.cos_exception import CosServiceError
            try:
                head = get_client().head_object(Bucket=settings.COS_BUCKET, Key=_key(name))
                return int(head["Content-Length"])
            except CosServiceError:
                return 0
        return self._local.size(name)

    def url(self, name):
        return file_url(name)