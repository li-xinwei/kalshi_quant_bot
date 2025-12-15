from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Literal

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


HttpMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH"]


@dataclass(frozen=True)
class KalshiSigner:
    api_key_id: str
    private_key_pem: str

    @staticmethod
    def from_pem_file(api_key_id: str, pem_path: str) -> "KalshiSigner":
        with open(pem_path, "r", encoding="utf-8") as f:
            pem = f.read()
        return KalshiSigner(api_key_id=api_key_id, private_key_pem=pem)

    def sign(self, timestamp_ms: int, method: HttpMethod, path: str) -> str:
        """
        Kalshi signature: base64(RSA-PSS-SHA256( timestamp + METHOD + path ))
        IMPORTANT: sign **path without query parameters**.
        """
        message = f"{timestamp_ms}{method.upper()}{path}".encode("utf-8")

        private_key = serialization.load_pem_private_key(
            self.private_key_pem.encode("utf-8"),
            password=None,
        )

        signature = private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")
