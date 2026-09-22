"""
Local Edge Inference Engine for Laya Decision Model using ONNX Runtime.
Enables:
1. 0 Server Cost & Unlimited Concurrency on client PC.
2. 0ms Network Latency: CPU inference in ~15-30ms with AVX2/AVX-512 optimization.
3. Offline Capability: Works without internet (e.g. traveling, airplane mode).
4. Structured typed predictions: choice (classification), score (ranking), and noul (binary probability).
"""
import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("LocalLayaEngine")

class LocalLayaEngine:
    def __init__(
        self,
        model_path: str = "models/laya_int8.onnx",
        tokenizer_path: str = "models/tokenizer.json",
        num_threads: int = 2
    ):
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        self.num_threads = num_threads

        self.session = None
        self.tokenizer = None

        self._load_engine()

    def _load_engine(self):
        """Loads ONNX Runtime InferenceSession and Tokenizer if files are present."""
        if not os.path.exists(self.model_path) or not os.path.exists(self.tokenizer_path):
            logger.info(
                f"Local model files not found (model: {self.model_path}, tokenizer: {self.tokenizer_path}). "
                f"Local engine will remain inactive until files are provided."
            )
            return

        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = self.num_threads
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self.session = ort.InferenceSession(
                self.model_path,
                sess_options,
                providers=["CPUExecutionProvider"]
            )
            self.tokenizer = Tokenizer.from_file(self.tokenizer_path)
            logger.info(f"Local Laya ONNX engine initialized successfully from {self.model_path}!")
        except Exception as e:
            logger.error(f"Failed to load local ONNX engine: {e}")
            self.session = None
            self.tokenizer = None

    def is_available(self) -> bool:
        """Returns True if the local ONNX engine is loaded and ready."""
        return self.session is not None and self.tokenizer is not None

    def format_state_text(self, state: Dict[str, Any]) -> str:
        """Serializes game state dictionary into concise structured text for encoder embedding."""
        parts = []
        if "character" in state:
            parts.append(f"Class: {state['character']}")
        if "floor" in state:
            parts.append(f"Floor: {state['floor']}")
        if "act" in state:
            parts.append(f"Act: {state['act']}")
        if "hp" in state and "max_hp" in state:
            parts.append(f"HP: {state['hp']}/{state['max_hp']}")
        if "deck_size" in state:
            parts.append(f"Deck: {state['deck_size']} cards")
        if "deck_sample" in state:
            sample_str = ", ".join(state["deck_sample"][:8])
            parts.append(f"DeckSample: [{sample_str}]")
        if "relics" in state:
            relic_str = ", ".join(state["relics"][:6])
            parts.append(f"Relics: [{relic_str}]")
        if "act_boss" in state:
            parts.append(f"Boss: {state['act_boss']}")
        if "boss_context" in state and state["boss_context"]:
            parts.append(f"BossNote: {state['boss_context']}")

        # Fallback if dictionary has arbitrary keys
        if not parts:
            for k, v in state.items():
                if isinstance(v, (str, int, float, bool)):
                    parts.append(f"{k}: {v}")

        return " | ".join(parts)

    def predict(self, state: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes local ONNX inference on questions given current state.
        Returns a dict conforming to Laya API response schema.
        """
        if not self.is_available():
            raise RuntimeError("LocalLayaEngine is not available. Please ensure model files exist.")

        start_time = time.time()
        state_text = self.format_state_text(state)

        # Detect whether the loaded ONNX model is Laya multi-head (requires marker_pos, qtype)
        required_inputs = [inp.name for inp in self.session.get_inputs()]
        is_laya_multihead = "marker_pos" in required_inputs

        answers = {}

        for q_key, q_data in questions.items():
            q_type = q_data.get("type", "choice")
            instructions = q_data.get("instructions", "")

            if is_laya_multihead:
                # 1. Real Laya 421M Multi-Head Architecture
                if q_type == "choice":
                    criteria = q_data.get("criteria", {})
                    if isinstance(criteria, dict):
                        choices = list(criteria.keys())
                    elif isinstance(criteria, list):
                        choices = list(criteria)
                    else:
                        choices = ["Option A", "Option B"]

                    if len(choices) < 2:
                        choices = list(choices) + ["Skip"]

                    qtype_val = 0
                    options_to_format = choices

                elif q_type == "noul":
                    qtype_val = 2
                    options_to_format = ["否", "是"]

                elif q_type == "score":
                    qtype_val = 1
                    criteria = q_data.get("criteria", [])
                    if isinstance(criteria, list) and len(criteria) >= 2:
                        options_to_format = criteria
                    elif isinstance(criteria, dict) and len(criteria) >= 2:
                        options_to_format = list(criteria.keys())
                    else:
                        options_to_format = ["差", "中", "良", "优"]

                # Build prompt with options and track marker token positions
                prompt_prefix = f"[STATE] {state_text} [QUESTION] {instructions}\n"
                prefix_tokens = self.tokenizer.encode(prompt_prefix).ids
                all_tokens = list(prefix_tokens)
                marker_positions = []

                for idx, opt in enumerate(options_to_format):
                    marker_positions.append(len(all_tokens))
                    opt_str = f"Option {idx}: {opt}\n"
                    all_tokens.extend(self.tokenizer.encode(opt_str).ids)

                input_ids = np.array([all_tokens], dtype=np.int64)
                attention_mask = np.ones_like(input_ids, dtype=np.int64)
                marker_pos = np.array([marker_positions], dtype=np.int64)
                marker_mask = np.ones((1, len(options_to_format)), dtype=bool)
                qtype = np.array([qtype_val], dtype=np.int64)

                feed_dict = {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "marker_pos": marker_pos,
                    "marker_mask": marker_mask,
                    "qtype": qtype
                }
                outputs = self.session.run(None, feed_dict)
                logits = outputs[0][0]  # Shape [num_options]

                if q_type == "choice":
                    exp_logits = np.exp(logits - np.max(logits))
                    probs = exp_logits / np.sum(exp_logits)
                    prob_dict = {
                        c_name: round(float(p), 4)
                        for c_name, p in zip(options_to_format, probs)
                    }
                    best_idx = int(np.argmax(probs))
                    best_choice = options_to_format[best_idx]
                    confidence = round(float(probs[best_idx]), 4)
                    answers[q_key] = {
                        "type": "choice",
                        "choice": best_choice,
                        "confidence": confidence,
                        "probabilities": prob_dict
                    }

                elif q_type == "noul":
                    exp_logits = np.exp(logits - np.max(logits))
                    probs = exp_logits / np.sum(exp_logits)
                    yes_prob = round(float(probs[1]), 4) if len(probs) > 1 else 0.5
                    answers[q_key] = {
                        "type": "noul",
                        "noul": yes_prob
                    }

                elif q_type == "score":
                    exp_logits = np.exp(logits - np.max(logits))
                    probs = exp_logits / np.sum(exp_logits)
                    N = len(options_to_format)
                    expected_idx = sum(i * p for i, p in enumerate(probs))
                    score_val = round(float(expected_idx / max(1, N - 1) * 4.0 + 1.0), 2)
                    answers[q_key] = {
                        "type": "score",
                        "score": score_val
                    }

            else:
                # 2. Simple Linear Graph Fallback (e.g. dummy test model)
                full_prompt = f"[STATE] {state_text} [QUESTION] {instructions}"
                encoded = self.tokenizer.encode(full_prompt)
                input_ids = np.array([encoded.ids], dtype=np.int64)
                attention_mask = np.array([encoded.attention_mask], dtype=np.int64)

                if input_ids.shape[1] == 0:
                    input_ids = np.array([[0]], dtype=np.int64)
                    attention_mask = np.array([[1]], dtype=np.int64)

                outputs = self.session.run(None, {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask
                })
                logits = outputs[0][0]

                if q_type == "choice":
                    criteria = q_data.get("criteria", {})
                    if isinstance(criteria, dict):
                        choices = list(criteria.keys())
                    elif isinstance(criteria, list):
                        choices = list(criteria)
                    else:
                        choices = ["Option A", "Option B"]

                    if not choices:
                        choices = ["Skip"]

                    num_choices = len(choices)
                    choice_logits = logits[:num_choices] if len(logits) >= num_choices else np.resize(logits, num_choices)
                    exp_logits = np.exp(choice_logits - np.max(choice_logits))
                    probs = exp_logits / np.sum(exp_logits)
                    prob_dict = {c: round(float(p), 4) for c, p in zip(choices, probs)}
                    best_idx = int(np.argmax(probs))
                    answers[q_key] = {
                        "type": "choice",
                        "choice": choices[best_idx],
                        "confidence": round(float(probs[best_idx]), 4),
                        "probabilities": prob_dict
                    }

                elif q_type == "noul":
                    val = float(logits[0]) if len(logits) > 0 else 0.0
                    sig = 1.0 / (1.0 + np.exp(-val))
                    answers[q_key] = {
                        "type": "noul",
                        "noul": round(float(sig), 4)
                    }

                elif q_type == "score":
                    val = float(logits[0]) if len(logits) > 0 else 0.0
                    sig = 1.0 / (1.0 + np.exp(-val))
                    answers[q_key] = {
                        "type": "score",
                        "score": round(float(sig * 4.0 + 1.0), 2)
                    }

        elapsed_ms = round((time.time() - start_time) * 1000, 1)

        return {
            "answers": answers,
            "latency_ms": elapsed_ms,
            "engine": "local_onnx"
        }
