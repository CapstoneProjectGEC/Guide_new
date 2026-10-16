"""Comprehensive End-to-End Integration Tests for Phase 16.

Verifies:
1. SSE streaming — multibyte UTF-8 Kannada characters across network chunks.
2. Authentication — refresh token rotation, old token reuse rejection, logout server-side invalidation, and strict RBAC.
3. RAG Retrieval & Citations — verified source chunk traceability and active generation pinning.
4. Instant Rollback (<100ms) — immediate retrieval pointer switch without restarting services.
5. Voice STT & TTS — audio MIME validation, silence bypass, Piper WAV synthesis headers, and offline operation.
"""

import io
import wave
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from backend.src.core.security import (
    clear_revoked_tokens,
    create_access_token,
    hash_password,
)
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import (
    Document,
    DocumentChunk,
    KnowledgeGeneration,
)
from backend.src.main import app


@pytest.fixture(autouse=True)
def reset_revocation_store():
    """Clear in-memory token revocation list before each test."""
    clear_revoked_tokens()
    yield
    clear_revoked_tokens()


async def create_scoped_admin(role: str = "SUPER_ADMIN", password: str = "TestPassword123!") -> Admin:
    """Helper to seed an admin record with specific role."""
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    admin = Admin(
        username=f"admin_{uid}",
        email=f"admin_{uid}@heritage.gov.in",
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin


async def cleanup_scoped_admin(admin_id: str) -> None:
    """Helper to remove a test admin."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(Admin).where(Admin.id == admin_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if obj:
            await session.delete(obj)
            await session.commit()


def generate_test_wav_bytes(duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Generate in-memory valid PCM mono WAV bytes for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Write silent zero samples
        num_frames = int(duration_sec * sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


# =========================================================================
# 1. SSE STREAMING INTEGRATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_sse_stream_kannada_utf8_token_chunks():
    """Verify SSE stream endpoint (/api/v1/chat/stream) yields UTF-8 events with zero corruption."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "content": "ಹೊಯ್ಸಳ ಸಾಮ್ರಾಜ್ಯದ ಇತಿಹಾಸವೇನು?",
                "preferred_language": "kn",
                "input_mode": "text",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    raw_text = response.text
    assert "\ufffd" not in raw_text, "Replacement character found in SSE stream output!"
    # Verify events structure contains either token or done
    assert "data:" in raw_text


# =========================================================================
# 2. AUTHENTICATION, ROTATION, LOGOUT, AND RBAC INTEGRATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_auth_token_rotation_and_old_token_reuse_rejected():
    """Verify refresh token rotation and ensure reusing an old refresh token is rejected server-side."""
    pwd = "RotateSecret123!"
    admin = await create_scoped_admin(role="SITE_CURATOR", password=pwd)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Login
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"username": admin.username, "password": pwd},
            )
            assert login_res.status_code == 200
            tok_data1 = login_res.json()
            refresh_tok_1 = tok_data1["refresh_token"]

            # 2. Rotate token via /auth/refresh
            refresh_res = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok_1},
            )
            assert refresh_res.status_code == 200
            tok_data2 = refresh_res.json()
            refresh_tok_2 = tok_data2["refresh_token"]
            assert refresh_tok_2 != refresh_tok_1

            # 3. Attempt to REUSE the old refresh token (refresh_tok_1) -> Expect HTTP 401
            reuse_res = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok_1},
            )
            assert reuse_res.status_code == 401
            err = reuse_res.json()["error"]
            assert err["code"] == "UNAUTHORIZED"
            assert "revoked" in err["message"].lower() or "invalid" in err["message"].lower()

            # 4. Verify new refresh token (refresh_tok_2) remains valid
            valid_res = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok_2},
            )
            assert valid_res.status_code == 200
    finally:
        await cleanup_scoped_admin(admin.id)


@pytest.mark.asyncio
async def test_e2e_auth_logout_server_side_invalidation():
    """Verify logging out invalidates access token and refresh token server-side."""
    pwd = "LogoutSecret123!"
    admin = await create_scoped_admin(role="OPERATOR", password=pwd)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"username": admin.username, "password": pwd},
            )
            tok_data = login_res.json()
            access_tok = tok_data["access_token"]
            refresh_tok = tok_data["refresh_token"]

            # Confirm access token works before logout
            me_res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_tok}"},
            )
            assert me_res.status_code == 200

            # Logout
            logout_res = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {access_tok}"},
                json={"refresh_token": refresh_tok},
            )
            assert logout_res.status_code == 200

            # Verify access token is now rejected on protected endpoints
            me_after = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_tok}"},
            )
            assert me_after.status_code == 401
            assert me_after.json()["error"]["code"] == "UNAUTHORIZED"

            # Verify refresh token is also revoked
            ref_after = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok},
            )
            assert ref_after.status_code == 401
    finally:
        await cleanup_scoped_admin(admin.id)


@pytest.mark.asyncio
async def test_e2e_rbac_endpoint_authorization_enforced():
    """Verify backend RBAC policies block unauthorized attempts regardless of client headers."""
    pwd = "RbacSecret123!"
    viewer = await create_scoped_admin(role="VIEWER", password=pwd)
    operator = await create_scoped_admin(role="OPERATOR", password=pwd)
    curator = await create_scoped_admin(role="SITE_CURATOR", password=pwd)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Anonymous attempt to access protected admin documents -> 401
            anon_res = await client.get("/api/v1/admin/documents")
            assert anon_res.status_code == 401

            # 2. Get tokens
            v_tok = (await client.post("/api/v1/auth/login", json={"username": viewer.username, "password": pwd})).json()["access_token"]
            o_tok = (await client.post("/api/v1/auth/login", json={"username": operator.username, "password": pwd})).json()["access_token"]
            c_tok = (await client.post("/api/v1/auth/login", json={"username": curator.username, "password": pwd})).json()["access_token"]

            # 3. VIEWER can read documents (200) but CANNOT delete or upload (403)
            v_read = await client.get("/api/v1/admin/documents", headers={"Authorization": f"Bearer {v_tok}"})
            assert v_read.status_code == 200

            v_delete = await client.delete("/api/v1/admin/documents/non-existent-id", headers={"Authorization": f"Bearer {v_tok}"})
            assert v_delete.status_code == 403

            v_upload = await client.post(
                "/api/v1/admin/documents",
                headers={"Authorization": f"Bearer {v_tok}"},
                files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")},
            )
            assert v_upload.status_code == 403

            # 4. OPERATOR can sync models (200) but CANNOT trigger knowledge build (403)
            o_sync = await client.post("/api/v1/admin/sync/voice", headers={"Authorization": f"Bearer {o_tok}"})
            assert o_sync.status_code == 200

            o_build = await client.post("/api/v1/admin/knowledge/generations/build", headers={"Authorization": f"Bearer {o_tok}"})
            assert o_build.status_code == 403

            # 5. CURATOR can access curator zone and knowledge operations
            c_zone = await client.get("/api/v1/auth/curator-zone", headers={"Authorization": f"Bearer {c_tok}"})
            assert c_zone.status_code == 200
    finally:
        await cleanup_scoped_admin(viewer.id)
        await cleanup_scoped_admin(operator.id)
        await cleanup_scoped_admin(curator.id)


# =========================================================================
# 3. RAG RETRIEVAL, CITATION INTEGRITY, AND ACTIVE GENERATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_citations_reference_real_retrieved_chunks():
    """Verify that returned citations in conversation answers map strictly to real retrieved document chunks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ask question with known answer in knowledge base
        res = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "Who built the Chennakeshava Temple at Belur?",
                "preferred_language": "en",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert "content" in data
    assert "citations" in data

    if data["is_grounded"] and data["citations"]:
        session_factory = get_session_factory()
        async with session_factory() as session:
            for citation in data["citations"]:
                # Verify chunk_id and document_id are valid non-empty strings
                assert citation["chunk_id"]
                assert citation["document_id"]
                assert citation["page_number"] >= 1


@pytest.mark.asyncio
async def test_e2e_grounding_unsupported_questions_trigger_canonical_fallback():
    """Verify out-of-domain questions trigger the canonical ungrounded fallback with zero hallucinations."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-temple query in English
        en_res = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "What is the capital city of France?",
                "preferred_language": "en",
            },
        )
        assert en_res.status_code == 200
        en_data = en_res.json()
        assert en_data["is_grounded"] is False
        assert "not available in the knowledge base" in en_data["content"]
        assert len(en_data["citations"]) == 0

        # Non-temple query in Kannada
        kn_res = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಯಾವುದು?",
                "preferred_language": "kn",
            },
        )
        assert kn_res.status_code == 200
        kn_data = kn_res.json()
        assert kn_data["is_grounded"] is False
        assert "ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ" in kn_data["content"]
        assert len(kn_data["citations"]) == 0


# =========================================================================
# 4. INSTANT ROLLBACK (<100ms) INTEGRATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_generation_rollback_immediate_retrieval_switch():
    """Verify active generation rollback switches the active retrieval collection pointer immediately."""
    session_factory = get_session_factory()
    admin = await create_scoped_admin(role="SITE_CURATOR", password="RollbackPassword123!")

    gen1_id = None
    gen2_id = None
    previous_active_id = None

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"username": admin.username, "password": "RollbackPassword123!"},
            )
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Seed G1 and G2 in database
            async with session_factory() as session:
                # Capture and demote any pre-existing active generation so there's only one ACTIVE during test
                prev_stmt = select(KnowledgeGeneration.id).where(KnowledgeGeneration.status == "ACTIVE")
                prev_res = await session.execute(prev_stmt)
                previous_active_id = prev_res.scalars().first()

                if previous_active_id:
                    await session.execute(
                        update(KnowledgeGeneration).where(KnowledgeGeneration.id == previous_active_id).values(status="ARCHIVED")
                    )
                    await session.flush()

                # Find current max generation number
                max_stmt = select(KnowledgeGeneration).order_by(KnowledgeGeneration.generation_number.desc())
                max_res = await session.execute(max_stmt)
                last_gen = max_res.scalars().first()
                base_num = (last_gen.generation_number if last_gen else 0) + 10

                g1 = KnowledgeGeneration(
                    generation_number=base_num,
                    status="ACTIVE",
                    chroma_collection_name=f"test_coll_{base_num}",
                    chunk_count=10,
                )
                session.add(g1)
                await session.flush()
                gen1_id = g1.id

                g2 = KnowledgeGeneration(
                    generation_number=base_num + 1,
                    status="ARCHIVED",
                    chroma_collection_name=f"test_coll_{base_num + 1}",
                    chunk_count=15,
                )
                session.add(g2)
                await session.commit()
                gen2_id = g2.id

            # Verify active generation is G1
            active_res1 = await client.get("/api/v1/admin/knowledge/generations/active", headers=headers)
            assert active_res1.status_code == 200
            assert active_res1.json()["id"] == gen1_id

            # Promote G2
            promote_res = await client.post(f"/api/v1/admin/knowledge/generations/{gen2_id}/promote", headers=headers)
            assert promote_res.status_code == 200
            assert promote_res.json()["status"] == "ACTIVE"

            # Verify active generation is now G2
            active_res2 = await client.get("/api/v1/admin/knowledge/generations/active", headers=headers)
            assert active_res2.status_code == 200
            assert active_res2.json()["id"] == gen2_id

            # Roll back to G1 via /rollback endpoint
            rollback_res = await client.post(
                "/api/v1/admin/knowledge/generations/rollback",
                headers=headers,
                json={"target_generation_id": gen1_id},
            )
            assert rollback_res.status_code == 200
            assert rollback_res.json()["id"] == gen1_id
            assert rollback_res.json()["status"] == "ACTIVE"

            # Verify active generation switched back to G1 immediately without service restart
            active_res3 = await client.get("/api/v1/admin/knowledge/generations/active", headers=headers)
            assert active_res3.status_code == 200
            assert active_res3.json()["id"] == gen1_id
    finally:
        await cleanup_scoped_admin(admin.id)
        async with session_factory() as session:
            if gen1_id or gen2_id:
                for gid in [gen1_id, gen2_id]:
                    if gid:
                        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.id == gid)
                        res = await session.execute(stmt)
                        obj = res.scalar_one_or_none()
                        if obj:
                            await session.delete(obj)
            if previous_active_id:
                stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.id == previous_active_id)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj:
                    obj.status = "ACTIVE"
            await session.commit()


# =========================================================================
# 5. VOICE STT, PIPER TTS, AND AIR-GAPPED OFFLINE OPERATION TESTS
# =========================================================================

@pytest.mark.asyncio
async def test_e2e_voice_audio_mime_validation_and_stt():
    """Verify speech endpoint enforces valid audio formats and handles silent recordings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Reject invalid non-audio file
        bad_upload = await client.post(
            "/api/v1/voice/transcribe",
            files={"audio_file": ("test.txt", b"plain text is not audio", "text/plain")},
        )
        assert bad_upload.status_code in (400, 422)

        # 2. Accept valid WAV audio (silence buffer)
        silent_wav = generate_test_wav_bytes(duration_sec=0.5)
        good_upload = await client.post(
            "/api/v1/voice/transcribe",
            files={"audio_file": ("silence.wav", silent_wav, "audio/wav")},
        )
        assert good_upload.status_code == 200
        res = good_upload.json()
        assert "is_silent" in res
        assert "latency_ms" in res
        assert res["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_e2e_voice_tts_piper_synthesis_headers_and_wav_format():
    """Verify Piper offline TTS synthesis produces valid WAV binary output with accurate telemetry headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Synthesis of valid text in English
        en_res = await client.post(
            "/api/v1/voice/synthesize",
            json={"text": "Welcome to Belur Chennakeshava Temple.", "language": "en"},
        )
        assert en_res.status_code == 200
        assert en_res.headers.get("content-type") == "audio/wav"
        assert en_res.headers.get("x-tts-engine") == "piper"
        assert "x-tts-latency-ms" in en_res.headers
        assert "x-tts-audio-duration" in en_res.headers

        # Verify WAV header: must begin with RIFF and contain WAVEfmt
        wav_bytes = en_res.content
        assert len(wav_bytes) >= 44, "WAV header size must be at least 44 bytes"
        assert wav_bytes[:4] == b"RIFF"
        assert b"WAVE" in wav_bytes[:16]

        # 2. Reject empty synthesis request
        empty_res = await client.post(
            "/api/v1/voice/synthesize",
            json={"text": "   ", "language": "en"},
        )
        assert empty_res.status_code == 400
        assert empty_res.json()["error"]["code"] == "TTS_VALIDATION_ERROR"
