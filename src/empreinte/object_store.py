"""Stockage objet des fichiers bruts et images de pages.

Abstrait par un Protocol : ``InMemoryObjectStore`` (demo/tests, hors-ligne) et
``S3ObjectStore`` (production, S3-compatible type MinIO in-VPC). Les binaires ne sont jamais
stockes en base : seules les cles d'objet le sont (cf. ``repositories.py``).
"""

from __future__ import annotations

from typing import Protocol

_DEFAULT_CONTENT_TYPE = "application/octet-stream"


class ObjectStoreError(RuntimeError):
    """Echec d'acces au stockage objet."""


class ObjectStore(Protocol):
    """Contrat minimal d'un stockage objet binaire."""

    async def put(self, key: str, data: bytes, content_type: str = _DEFAULT_CONTENT_TYPE) -> None:
        """Stocke ``data`` sous la cle ``key``."""
        ...

    async def get(self, key: str) -> bytes:
        """Retourne les octets stockes sous ``key`` ou leve ``ObjectStoreError``."""
        ...


class InMemoryObjectStore:
    """Stockage objet en memoire (demo/tests)."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str = _DEFAULT_CONTENT_TYPE) -> None:
        del content_type
        self._objects[key] = data

    async def get(self, key: str) -> bytes:
        try:
            return self._objects[key]
        except KeyError as exc:
            raise ObjectStoreError(f"objet introuvable: {key}") from exc


class S3ObjectStore:  # pragma: no cover - depend de l'extra 'storage'
    """Stockage objet S3-compatible (MinIO/S3) via aioboto3."""

    def __init__(
        self,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ) -> None:
        self._endpoint = endpoint
        self._bucket = bucket
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region

    def _session(self) -> object:
        import aioboto3

        return aioboto3.Session()

    async def put(self, key: str, data: bytes, content_type: str = _DEFAULT_CONTENT_TYPE) -> None:
        session = self._session()
        async with session.client(  # type: ignore[attr-defined]
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
        ) as client:
            await client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )

    async def get(self, key: str) -> bytes:
        session = self._session()
        async with session.client(  # type: ignore[attr-defined]
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            region_name=self._region,
        ) as client:
            try:
                response = await client.get_object(Bucket=self._bucket, Key=key)
                body: bytes = await response["Body"].read()
            except Exception as exc:
                raise ObjectStoreError(f"objet introuvable: {key}") from exc
        return body
