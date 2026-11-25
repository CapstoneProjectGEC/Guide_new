"""Asynchronous Ollama client adapter with streaming, connection pooling, and cancellation."""

import asyncio
from functools import lru_cache
import json
from typing import Any, AsyncGenerator
import httpx
from backend.src.core.config import get_settings
from backend.src.core.errors import ServiceUnavailableError
from backend.src.core.logging import get_logger

logger = get_logger("infrastructure.llm.ollama_client")


class OllamaClient:
    """Async adapter for local Ollama server with connection pooling and SSE streaming."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        connect_timeout: float | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout_seconds or settings.OLLAMA_TIMEOUT_SECONDS
        self.connect_timeout = connect_timeout or settings.OLLAMA_CONNECT_TIMEOUT_SECONDS

        # Bounded connection pool for local inference
        self._limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self._timeouts = httpx.Timeout(
            timeout=self.timeout,
            connect=self.connect_timeout,
            read=self.timeout,
            write=self.connect_timeout,
        )
        self._client: httpx.AsyncClient | None = None

    async def get_http_client(self) -> httpx.AsyncClient:
        """Lazily initialize or return the pooled async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._timeouts,
                limits=self._limits,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client session cleanly."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            logger.info("ollama_http_client_closed")

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
        temperature: float | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        keep_alive: str | None = None,
        stop: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream generation tokens from local Ollama /api/generate endpoint."""
        settings = get_settings()
        target_model = model or settings.OLLAMA_MODEL
        client = await self.get_http_client()

        ka_raw = keep_alive or settings.OLLAMA_KEEP_ALIVE
        ka_val: Any = -1 if str(ka_raw).strip() == "-1" else ka_raw

        stop_sequences = stop if stop is not None else [
            "Tourist Question:",
            "\nTourist:",
            "\nTourist Question",
            "\nHuman:",
            "\nUser:",
            "\nContext:",
        ]

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": ka_val,
            "options": {
                "num_ctx": num_ctx or settings.OLLAMA_NUM_CTX,
                "num_predict": num_predict or settings.OLLAMA_NUM_PREDICT,
                "temperature": temperature if temperature is not None else settings.OLLAMA_TEMPERATURE,
                "top_k": top_k or settings.OLLAMA_TOP_K,
                "top_p": top_p if top_p is not None else settings.OLLAMA_TOP_P,
                "stop": stop_sequences,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        logger.info(
            "ollama_stream_request_started",
            model=target_model,
            prompt_chars=len(prompt),
            num_ctx=payload["options"]["num_ctx"],
            num_predict=payload["options"]["num_predict"],
        )

        try:
            req = client.build_request("POST", "/api/generate", json=payload)
            response = await client.send(req, stream=True)

            if response.status_code != 200:
                err_text = await response.aread()
                logger.error("ollama_server_error", status_code=response.status_code, body=err_text.decode("utf-8", errors="replace"))
                raise ServiceUnavailableError(f"Ollama server returned error status {response.status_code}: {err_text.decode('utf-8', errors='replace')}")

            try:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as exc:
                        logger.warning("ollama_stream_json_decode_error", line=line[:60], error=str(exc))
                        continue

                    token = data.get("response", "")
                    if token:
                        yield token

                    if data.get("done", False):
                        logger.info(
                            "ollama_stream_completed",
                            total_duration_ns=data.get("total_duration"),
                            eval_count=data.get("eval_count"),
                            eval_duration_ns=data.get("eval_duration"),
                        )
                        break

            except asyncio.CancelledError:
                logger.info("ollama_stream_cancelled_by_client")
                raise
            finally:
                await response.aclose()

        except httpx.ConnectError as exc:
            logger.error("ollama_connection_refused", error=str(exc), base_url=self.base_url)
            raise ServiceUnavailableError(
                f"Local Ollama service unreachable at {self.base_url}. Ensure Ollama is running and bound to localhost.",
                details={"host": self.base_url, "error": str(exc)},
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("ollama_request_timeout", error=str(exc))
            raise ServiceUnavailableError(
                "Ollama inference timed out. Consider reducing num_predict or context tokens.",
                details={"error": str(exc)},
            ) from exc

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
    ) -> str:
        """Non-streaming generate helper accumulating tokens from stream_generate."""
        tokens: list[str] = []
        async for token in self.stream_generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            num_ctx=num_ctx,
            num_predict=num_predict,
        ):
            tokens.append(token)
        return "".join(tokens).strip()

    async def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        """Fetch details of an installed model via /api/show."""
        settings = get_settings()
        target_model = model or settings.OLLAMA_MODEL
        client = await self.get_http_client()

        try:
            resp = await client.post("/api/show", json={"model": target_model})
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Model '{target_model}' not found in Ollama registry (status {resp.status_code})."}
        except Exception as exc:
            logger.warning("ollama_show_model_failed", model=target_model, error=str(exc))
            return {"error": str(exc)}


@lru_cache(maxsize=1)
def get_ollama_client() -> OllamaClient:
    """Return cached OllamaClient singleton."""
    return OllamaClient()
