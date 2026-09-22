"""
Laya Decision Engine Client.
Interfaces with the deployed 421M Laya decision model via HTTP POST /predict.
Supports typed questions: choice (classification), score (ranking), and noul (binary probability).
Includes SSL bypass for self-signed certificates, caching, and async non-blocking execution.
"""
import json
import ssl
import time
import logging
import threading
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Callable
from config import CONFIG
from local_laya_engine import LocalLayaEngine

logger = logging.getLogger("LayaClient")

class LayaClient:
    def __init__(self, config=None):
        self.config = config or CONFIG.laya
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Local Edge ONNX inference engine
        self.local_engine = LocalLayaEngine(
            model_path=self.config.local_model_path,
            tokenizer_path=self.config.local_tokenizer_path,
            num_threads=self.config.intra_op_threads
        )

        # Configure SSL context for self-signed certificate on SakuraFrp tunnel
        self._ssl_ctx = ssl.create_default_context()
        if not self.config.verify_ssl:
            self._ssl_ctx.check_hostname = False
            self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def check_health(self) -> Dict[str, Any]:
        """Checks if the Laya model service is online and ready (local or remote)."""
        if self.local_engine.is_available():
            return {
                "online": True,
                "engine": "local_onnx",
                "status": "ready",
                "data": {"status": "ready", "engine": "local_onnx"},
                "model_path": self.config.local_model_path
            }
        try:
            req = urllib.request.Request(
                self.config.health_url,
                headers={"User-Agent": "SlayTheSpireTacticalAssistant/1.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec, context=self._ssl_ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"online": True, "engine": "remote_http", "data": data}
        except Exception as e:
            logger.warning(f"Laya health check failed: {e}")
            return {"online": False, "error": str(e)}

    def predict(self, state: Dict[str, Any], questions: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
        """
        Queries Laya with state and typed questions.
        If engine_mode is 'local' or ('auto' with local model available), runs on-device ONNX inference.
        Otherwise falls back to remote /predict HTTP endpoint.
        """
        target_model = model or self.config.model
        payload = {
            "state": state,
            "questions": questions,
            "model": target_model
        }

        # Check cache if enabled
        cache_key = ""
        if self.config.cache_enabled:
            cache_key = json.dumps(payload, sort_keys=True, ensure_ascii=False)
            with self._lock:
                if cache_key in self._cache:
                    return self._cache[cache_key]

        # 1. Try local ONNX inference
        if self.config.engine_mode in ["auto", "local"]:
            if self.local_engine.is_available():
                try:
                    res = self.local_engine.predict(state, questions)
                    if self.config.cache_enabled and cache_key:
                        with self._lock:
                            if len(self._cache) > 200:
                                self._cache.pop(next(iter(self._cache)))
                            self._cache[cache_key] = res
                    return res
                except Exception as ex:
                    logger.warning(f"Local ONNX inference failed: {ex}. Falling back to remote HTTP...")
                    if self.config.engine_mode == "local":
                        return {"error": f"Local inference failed: {ex}", "answers": {}}
            elif self.config.engine_mode == "local":
                return {
                    "error": "Local model not found. Please run export_laya_onnx.py or place laya_int8.onnx in models/.",
                    "answers": {}
                }

        # 2. Remote HTTP fallback
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.config.api_url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "SlayTheSpireTacticalAssistant/1.0"
            },
            method="POST"
        )

        start_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec, context=self._ssl_ctx) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                elapsed_ms = (time.time() - start_time) * 1000
                result["client_latency_ms"] = round(elapsed_ms, 1)

                if self.config.cache_enabled and cache_key:
                    with self._lock:
                        # Simple LRU-style limit
                        if len(self._cache) > 200:
                            self._cache.pop(next(iter(self._cache)))
                        self._cache[cache_key] = result

                return result
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            logger.error(f"HTTP {e.code} from Laya server: {err_body}")
            return {
                "error": f"HTTP {e.code}",
                "detail": err_body,
                "answers": {}
            }
        except Exception as e:
            logger.error(f"Failed to query Laya /predict: {e}")
            return {
                "error": str(e),
                "answers": {}
            }

    def predict_async(
        self,
        state: Dict[str, Any],
        questions: Dict[str, Any],
        callback: Callable[[Dict[str, Any]], None],
        model: Optional[str] = None
    ) -> threading.Thread:
        """
        Asynchronously queries Laya /predict in a background thread
        and invokes callback(result) upon completion.
        """
        def _worker():
            res = self.predict(state, questions, model=model)
            try:
                callback(res)
            except Exception as ex:
                logger.error(f"Error in predict_async callback: {ex}")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return thread
