"""Database and knowledge base bootstrap / initialization script."""

import asyncio
import hashlib
from pathlib import Path
import sys

# Ensure project root is on sys.path
sys.path.insert(0, ".")

import fitz
from sqlalchemy import select

from backend.src.application.pipeline.generation_manager import KnowledgeGenerationManager
from backend.src.application.translation.translator import TranslationService
from backend.src.application.voice.tts_service import get_tts_service
from backend.src.core.security import hash_password
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import Document, KnowledgeGeneration
from backend.src.infrastructure.models.system import ModelRegistry, SystemSetting
from backend.src.infrastructure.storage.local_storage import LocalStorageService


async def bootstrap():
    print("=== Bootstrapping Karnataka Tourism AI Guide Database & Services ===")
    session_factory = get_session_factory()

    async with session_factory() as session:
        # 1. Admin account
        stmt = select(Admin).where(Admin.username == "admin")
        res = await session.execute(stmt)
        admin = res.scalar_one_or_none()
        if not admin:
            print("Creating default super admin: 'admin' ...")
            admin = Admin(
                username="admin",
                email="admin@karnatakagov.in",
                password_hash=hash_password("AdminPassword123!"),
                role="SUPER_ADMIN",
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            print("Super admin created successfully (username: admin, password: AdminPassword123!)")
        else:
            print(f"Super admin 'admin' already exists (id: {admin.id})")

        # 2. System Settings
        default_settings = [
            ("heritage_mode", "true", "Enable Belur heritage cultural terminology"),
            ("grounding_confidence_threshold", "0.35", "Hybrid RAG reranker cutoff"),
            ("rate_limit_tourist_rpm", "60", "Max requests per minute per tourist"),
        ]
        for key, val, desc in default_settings:
            s_stmt = select(SystemSetting).where(SystemSetting.setting_key == key)
            s_res = await session.execute(s_stmt)
            if not s_res.scalar_one_or_none():
                session.add(SystemSetting(setting_key=key, setting_value=val, description=desc))
        await session.commit()
        print("System settings verified.")

        # 3. Model Registry (Ollama + local embeddings)
        default_models = [
            ("phi3:mini", "ollama", "LLM", 4096, True, True),
            ("all-MiniLM-L6-v2", "sentence-transformers", "EMBEDDING", 384, True, True),
            ("cross-encoder/ms-marco-MiniLM-L-6-v2", "cross-encoder", "RERANKER", 512, True, True),
        ]
        for m_name, provider, m_type, ctx, avail, active in default_models:
            m_stmt = select(ModelRegistry).where(ModelRegistry.model_name == m_name)
            m_res = await session.execute(m_stmt)
            if not m_res.scalar_one_or_none():
                session.add(ModelRegistry(
                    model_name=m_name,
                    model_type=m_type,
                    is_available=avail,
                ))
        await session.commit()
        print("Model registry verified.")

        # 4. Sync voice and translation registries
        tts_service = get_tts_service()
        voices = await tts_service.sync_voice_registry(session=session)
        print(f"Synced {len(voices)} voice records.")

        trans_service = TranslationService()
        translations = await trans_service.sync_translation_registry(session=session)
        print(f"Synced {len(translations)} translation records.")
        await session.commit()

        # 5. Ingest baseline document: Temple_info.pdf
        doc_path = Path("Temple_info.pdf")
        if not doc_path.exists():
            doc_path = Path("data/documents/Temple_info.pdf")

        if doc_path.exists():
            pdf_bytes = doc_path.read_bytes()
            sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

            d_stmt = select(Document).where(Document.sha256_hash == sha256_hash)
            d_res = await session.execute(d_stmt)
            doc_record = d_res.scalar_one_or_none()

            if not doc_record:
                storage = LocalStorageService()
                stored_path, sha_calc, size_bytes, page_count = storage.save_file(pdf_bytes, doc_path.name)

                doc_record = Document(
                    filename=doc_path.name,
                    storage_path=stored_path,
                    file_size_bytes=size_bytes,
                    page_count=page_count,
                    sha256_hash=sha_calc,
                    uploaded_by_id=admin.id,
                )
                session.add(doc_record)
                await session.commit()
                await session.refresh(doc_record)
                print(f"Ingested baseline document: {doc_record.filename} ({page_count} pages)")
            else:
                print(f"Baseline document {doc_record.filename} already present in DB.")

        # 6. Check active knowledge generation
        g_stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.status == "ACTIVE")
        g_res = await session.execute(g_stmt)
        active_gen = g_res.scalar_one_or_none()

        if not active_gen:
            print("No ACTIVE knowledge generation found. Building initial generation...")
            manager = KnowledgeGenerationManager(session=session)
            gen = await manager.build_generation(admin_id=admin.id, auto_promote=True)
            print(f"Successfully built and promoted Generation {gen.generation_number} (ID: {gen.id}) with {gen.chunk_count} chunks!")
        else:
            print(f"Active generation already present: Gen {active_gen.generation_number} (ID: {active_gen.id}) with {active_gen.chunk_count} chunks.")

    print("\n=== Bootstrap Complete! System is fully initialized! ===")


if __name__ == "__main__":
    asyncio.run(bootstrap())
