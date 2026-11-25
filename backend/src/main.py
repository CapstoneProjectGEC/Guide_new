import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from backend.src.core.config import Settings, get_settings
from backend.src.core.errors import register_exception_handlers
from backend.src.core.limiter import RateLimitMiddleware
from backend.src.core.logging import get_logger, setup_logging
from backend.src.core.middleware import CorrelationIdMiddleware
from backend.src.presentation.api.health import get_health
from backend.src.presentation.router import GATEWAY_TAGS_METADATA, api_v1_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown."""
    settings = get_settings()
    setup_logging(profile=settings.APP_PROFILE, log_level=settings.LOG_LEVEL)
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        profile=settings.APP_PROFILE,
    )

    # Pre-warm all inference models to eliminate cold-start latency for tourists
    try:
        from backend.src.infrastructure.vector.chroma_store import get_embedding_service
        from backend.src.application.rag.reranker import get_cross_encoder_reranker
        from backend.src.infrastructure.translation.nllb_engine import get_nllb_engine
        from backend.src.infrastructure.llm.ollama_client import get_ollama_client

        # 1. Warm MiniLM embedding service
        get_embedding_service().embed_query("Belur Chennakeshava Temple warmup")
        # 2. Warm CrossEncoder reranker
        get_cross_encoder_reranker().rerank("Belur temple warmup", [{"content": "Belur Chennakeshava Temple"}])
        # 3. Warm NLLB-200 CTranslate2 engine
        get_nllb_engine().warmup()
        # 4. Warm Ollama with a keep-alive ping
        await get_ollama_client().generate(prompt="Hello", system_prompt="Warmup", num_predict=2)
        logger.info("all_inference_models_prewarmed_successfully")
    except Exception as exc:
        logger.warning("model_prewarm_exception", error=str(exc))

    yield
    # Clean up pooled HTTP connections and voice resources
    from backend.src.infrastructure.llm.ollama_client import get_ollama_client
    from backend.src.infrastructure.audio.piper_engine import get_piper_engine
    await get_ollama_client().close()
    get_piper_engine().close()
    logger.info("application_stopping")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance with Unified Gateway."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-Powered Smart Tourist Guide Platform for Belur Chennakeshava Temple. "
            "Unified Client Gateway providing grounded multilingual RAG exploration, speech interactions, "
            "and administrative knowledge lifecycle management."
        ),
        lifespan=lifespan,
        openapi_tags=GATEWAY_TAGS_METADATA,
        docs_url="/docs" if settings.DEBUG or settings.APP_PROFILE == "dev" else None,
        redoc_url="/redoc" if settings.DEBUG or settings.APP_PROFILE == "dev" else None,
        openapi_url="/openapi.json" if settings.DEBUG or settings.APP_PROFILE == "dev" else None,
    )

    # 1. Secure CORS Middleware (Disallowing wildcard with credentials)
    allow_credentials = settings.cors_allow_credentials
    sanitized_origins = (
        [o for o in settings.CORS_ORIGINS if o != "*"]
        if allow_credentials
        else settings.CORS_ORIGINS
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sanitized_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Rate Limiting Middleware (Sliding Window per Process)
    app.add_middleware(RateLimitMiddleware)

    # 3. Correlation ID Middleware
    app.add_middleware(CorrelationIdMiddleware)

    # 4. Standardized Exception Handlers
    register_exception_handlers(app)

    # 5. Route Registration via Unified API v1 Gateway Router
    app.include_router(api_v1_router)

    # Root-level health probe for container orchestrators (alias to /api/v1/health)
    @app.get("/health", include_in_schema=False)
    async def root_health_alias(cfg: Settings = Depends(get_settings)):
        return await get_health(cfg)

    # Custom OpenAPI schema generator injecting Bearer security definitions
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=GATEWAY_TAGS_METADATA,
        )
        openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT access token issued by /api/v1/auth/login",
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    cfg = get_settings()
    uvicorn.run("backend.src.main:app", host=cfg.HOST, port=cfg.PORT, reload=cfg.DEBUG)
