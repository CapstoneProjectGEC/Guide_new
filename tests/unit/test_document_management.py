"""Unit and integration tests for Phase 5: PDF Document Management."""

import io
import uuid
import fitz  # PyMuPDF
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from backend.src.core.security import hash_password
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import Document
from backend.src.infrastructure.models.system import AuditLog
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def create_sample_pdf(title: str = "Belur Chennakeshava Temple Guide", pages: int = 2) -> bytes:
    """Generate a valid in-memory PDF document using PyMuPDF."""
    doc = fitz.open()
    for p in range(pages):
        page = doc.new_page(width=595, height=842)
        text = (
            f"{title}\n"
            f"Page {p + 1}\n"
            f"The Chennakeshava Temple at Belur, commissioned by King Vishnuvardhana in 1117 CE, "
            f"is a premier example of Hoysala architecture built from fine-grained chloritic schist (soapstone)."
        )
        page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def create_curator_admin() -> tuple[Admin, str]:
    """Seed a test curator administrator."""
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    pwd = "CuratorPassword123!"
    admin = Admin(
        username=f"curator_{uid}",
        email=f"curator_{uid}@karnatakagov.in",
        password_hash=hash_password(pwd),
        role="SITE_CURATOR",
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin, pwd


async def create_viewer_admin() -> tuple[Admin, str]:
    """Seed a test viewer administrator."""
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    pwd = "ViewerPassword123!"
    admin = Admin(
        username=f"viewer_{uid}",
        email=f"viewer_{uid}@karnatakagov.in",
        password_hash=hash_password(pwd),
        role="VIEWER",
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin, pwd


async def cleanup_admin(admin_id: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(Admin).where(Admin.id == admin_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if obj:
            await session.delete(obj)
            await session.commit()


@pytest.mark.asyncio
async def test_pdf_upload_metadata_and_audit():
    """Verify uploading a valid PDF document records metadata, hash, and audit log."""
    curator, pwd = await create_curator_admin()
    pdf_bytes = create_sample_pdf(title="Belur Temple Official Document", pages=2)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Login
            login_res = await client.post("/api/v1/auth/login", json={"username": curator.username, "password": pwd})
            token = login_res.json()["access_token"]

            # 2. Upload PDF
            files = {"file": ("Temple_info.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            upload_res = await client.post(
                "/api/v1/admin/documents",
                files=files,
                headers={"Authorization": f"Bearer {token}"},
            )

        assert upload_res.status_code == 201
        data = upload_res.json()
        doc_id = data["id"]
        assert data["filename"] == "Temple_info.pdf"
        assert data["page_count"] == 2
        assert len(data["sha256_hash"]) == 64
        assert data["file_size_bytes"] == len(pdf_bytes)

        # Verify database record
        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(Document).where(Document.id == doc_id)
            res = await session.execute(stmt)
            doc_record = res.scalar_one_or_none()
            assert doc_record is not None
            assert doc_record.filename == "Temple_info.pdf"

            # Verify audit log
            audit_stmt = select(AuditLog).where(AuditLog.resource_id == doc_id, AuditLog.action == "DOC_UPLOAD")
            audit_res = await session.execute(audit_stmt)
            audit_record = audit_res.scalar_one_or_none()
            assert audit_record is not None
            assert audit_record.action == "DOC_UPLOAD"

        # Cleanup created doc
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.delete(f"/api/v1/admin/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    finally:
        await cleanup_admin(curator.id)


@pytest.mark.asyncio
async def test_sha256_deduplication_conflict():
    """Verify uploading identical content is rejected with HTTP 409 Conflict."""
    curator, pwd = await create_curator_admin()
    pdf_bytes = create_sample_pdf(title="Unique Duplicate Test", pages=1)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post("/api/v1/auth/login", json={"username": curator.username, "password": pwd})
            token = login_res.json()["access_token"]

            # First upload
            files = {"file": ("Doc1.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            first_res = await client.post("/api/v1/admin/documents", files=files, headers={"Authorization": f"Bearer {token}"})
            assert first_res.status_code == 201
            doc_id = first_res.json()["id"]

            # Second upload with identical bytes
            files_dup = {"file": ("Doc2.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            dup_res = await client.post("/api/v1/admin/documents", files=files_dup, headers={"Authorization": f"Bearer {token}"})

            assert dup_res.status_code == 409
            assert dup_res.json()["error"]["code"] == "CONFLICT"

            # Cleanup
            await client.delete(f"/api/v1/admin/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    finally:
        await cleanup_admin(curator.id)


@pytest.mark.asyncio
async def test_invalid_magic_bytes_rejected():
    """Verify uploading non-PDF content is rejected with validation error."""
    curator, pwd = await create_curator_admin()
    fake_content = b"This is a text file masquerading as a PDF."

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post("/api/v1/auth/login", json={"username": curator.username, "password": pwd})
            token = login_res.json()["access_token"]

            files = {"file": ("Fake.pdf", io.BytesIO(fake_content), "application/pdf")}
            res = await client.post("/api/v1/admin/documents", files=files, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 422
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        await cleanup_admin(curator.id)


@pytest.mark.asyncio
async def test_rbac_viewer_cannot_upload_or_delete():
    """Verify VIEWER role is blocked from uploading or deleting documents."""
    viewer, pwd = await create_viewer_admin()
    pdf_bytes = create_sample_pdf(title="Rbac Doc", pages=1)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post("/api/v1/auth/login", json={"username": viewer.username, "password": pwd})
            token = login_res.json()["access_token"]

            # Attempt upload
            files = {"file": ("ViewerTest.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            upload_res = await client.post("/api/v1/admin/documents", files=files, headers={"Authorization": f"Bearer {token}"})
            assert upload_res.status_code == 403

            # Attempt delete
            del_res = await client.delete("/api/v1/admin/documents/nonexistent-id", headers={"Authorization": f"Bearer {token}"})
            assert del_res.status_code == 403
    finally:
        await cleanup_admin(viewer.id)


@pytest.mark.asyncio
async def test_document_download_and_deletion_lifecycle():
    """Verify full document download and deletion lifecycle."""
    curator, pwd = await create_curator_admin()
    pdf_bytes = create_sample_pdf(title="Download Lifecycle Test", pages=3)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post("/api/v1/auth/login", json={"username": curator.username, "password": pwd})
            token = login_res.json()["access_token"]

            # 1. Upload
            files = {"file": ("DownloadTest.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
            upload_res = await client.post("/api/v1/admin/documents", files=files, headers={"Authorization": f"Bearer {token}"})
            doc_id = upload_res.json()["id"]

            # 2. Get metadata
            get_res = await client.get(f"/api/v1/admin/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
            assert get_res.status_code == 200
            assert get_res.json()["page_count"] == 3

            # 3. Download bytes
            dl_res = await client.get(f"/api/v1/admin/documents/{doc_id}/download", headers={"Authorization": f"Bearer {token}"})
            assert dl_res.status_code == 200
            assert dl_res.content == pdf_bytes

            # 4. Delete
            del_res = await client.delete(f"/api/v1/admin/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
            assert del_res.status_code == 200

            # 5. Verify 404 after deletion
            get_after = await client.get(f"/api/v1/admin/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
            assert get_after.status_code == 404
    finally:
        await cleanup_admin(curator.id)
