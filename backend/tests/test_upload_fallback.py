"""Verifies the local-disk fallback used on self-hosted servers (no EMERGENT_LLM_KEY)."""
import asyncio
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import UploadFile  # noqa: E402
from routes import upload as up  # noqa: E402


class FakeUser:
    userId = "test-user"


async def main():
    os.environ["EMERGENT_LLM_KEY"] = ""
    data = b"%PDF-1.4 fake pdf bytes"
    f = UploadFile(filename="fallback.pdf", file=io.BytesIO(data))
    res = await up.upload_media(file=f, media_type="document", current_user=FakeUser())
    print("response:", res)
    assert res["url"].startswith("/api/uploads/documents/"), res
    saved = up.UPLOAD_DIR / "documents" / res["url"].split("/")[-1]
    assert saved.exists() and saved.read_bytes() == data
    print("PASS: local fallback saved", saved)
    saved.unlink()


if __name__ == "__main__":
    asyncio.run(main())
