"""
Laya Model Exporter & INT8 Dynamic Quantization Tool.
Used to:
1. Export Laya (ModernBERT 421M) from PyTorch to ONNX format.
2. Apply INT8 Dynamic Quantization (reducing model size from ~840MB to ~250MB and accelerating CPU inference by 2-3x).
3. Export tokenizer configuration for fast client-side tokenization.
4. Generate a lightweight dummy model for local testing and pipeline verification.
"""
import os
import sys
import argparse
import json
import numpy as np

def create_dummy_test_model(output_dir: str = "models") -> tuple[str, str]:
    """
    Creates a lightweight, valid ONNX model and tokenizer for local testing.
    This enables full local pipeline verification without requiring the full 250MB weights.
    """
    import onnx
    from onnx import helper, TensorProto
    from tokenizers import Tokenizer, models, pre_tokenizers

    os.makedirs(output_dir, exist_ok=True)
    model_path = os.path.join(output_dir, "laya_int8.onnx")
    tokenizer_path = os.path.join(output_dir, "tokenizer.json")

    # 1. Create a minimal valid ONNX graph:
    # Inputs: input_ids (int64 [batch, seq]), attention_mask (int64 [batch, seq])
    # Operations: Cast input_ids to float -> ReduceMean across seq -> MatMul with weights -> Logits [batch, 8]
    input_ids = helper.make_tensor_value_info('input_ids', TensorProto.INT64, ['batch_size', 'seq_len'])
    attention_mask = helper.make_tensor_value_info('attention_mask', TensorProto.INT64, ['batch_size', 'seq_len'])
    output = helper.make_tensor_value_info('logits', TensorProto.FLOAT, ['batch_size', 8])

    # Weights: 1 x 8 matrix
    weight_data = np.array([
        [0.8, -0.2, 0.5, 0.1, -0.4, 0.3, -0.1, 0.6]
    ], dtype=np.float32)
    weights_init = helper.make_tensor(
        name='fc_weights',
        data_type=TensorProto.FLOAT,
        dims=[1, 8],
        vals=weight_data.flatten().tolist()
    )

    # Nodes:
    # 1. Cast input_ids to FLOAT
    node_cast = helper.make_node(
        'Cast',
        inputs=['input_ids'],
        outputs=['input_float'],
        to=TensorProto.FLOAT
    )
    # 2. ReduceMean over axis 1 (seq_len), keepdims=1 -> [batch, 1]
    node_mean = helper.make_node(
        'ReduceMean',
        inputs=['input_float'],
        outputs=['mean_embed'],
        axes=[1],
        keepdims=1
    )
    # 3. MatMul [batch, 1] * [1, 8] -> [batch, 8]
    node_matmul = helper.make_node(
        'MatMul',
        inputs=['mean_embed', 'fc_weights'],
        outputs=['logits'],
    )

    graph = helper.make_graph(
        nodes=[node_cast, node_mean, node_matmul],
        name='DummyLayaEncoder',
        inputs=[input_ids, attention_mask],
        outputs=[output],
        initializer=[weights_init]
    )

    model = helper.make_model(
        graph,
        producer_name='laya_dummy_exporter',
        opset_imports=[helper.make_opsetid('', 14)],
        ir_version=10
    )
    onnx.save(model, model_path)
    print(f"Created lightweight test ONNX model at: {model_path}")

    # 2. Create a minimal tokenizer with BPE
    vocab = {
        "[PAD]": 0,
        "[UNK]": 1,
        "[CLS]": 2,
        "[SEP]": 3,
        "[MASK]": 4,
        "战斗": 5, "卡牌": 6, "跳过": 7, "推荐": 8, "伤害": 9, "格挡": 10,
        "Strike": 11, "Defend": 12, "Bash": 13, "Skip": 14, "Ironclad": 15,
        "Silent": 16, "Defect": 17, "Watcher": 18
    }
    # Add ASCII letters
    for i in range(256):
        ch = chr(i)
        if ch not in vocab:
            vocab[ch] = len(vocab)

    bpe = models.BPE(vocab=vocab, merges=[])
    tok = Tokenizer(bpe)
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.save(tokenizer_path)
    print(f"Created lightweight tokenizer at: {tokenizer_path}")

    return model_path, tokenizer_path

def export_pytorch_to_onnx_and_quantize(
    model_dir_or_name: str,
    output_dir: str = "models",
    quantize: bool = True
):
    """
    Exports a PyTorch HuggingFace ModernBERT model to ONNX FP32, then dynamically quantizes to INT8.
    Run this script on the server or machine where PyTorch and the model weights reside.
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModel
        import onnxruntime
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError as e:
        print(f"Missing PyTorch or Transformers dependencies on this machine: {e}")
        print("Please run this function on your server/environment where PyTorch is installed.")
        return

    os.makedirs(output_dir, exist_ok=True)
    fp32_path = os.path.join(output_dir, "laya_fp32.onnx")
    int8_path = os.path.join(output_dir, "laya_int8.onnx")
    tokenizer_path = os.path.join(output_dir, "tokenizer.json")

    print(f"Loading model and tokenizer from: {model_dir_or_name} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_dir_or_name)
    model = AutoModel.from_pretrained(model_dir_or_name)
    model.eval()

    # Save tokenizer JSON directly
    tokenizer.save_pretrained(output_dir)
    print(f"Tokenizer saved to: {output_dir}")

    # Prepare dummy input for ONNX tracing
    dummy_text = "Slay the Spire: HP 80/80, Energy 3, Hand: Strike, Defend, Bash"
    inputs = tokenizer(dummy_text, return_tensors="pt", max_length=128, padding="max_length", truncation=True)

    print(f"Exporting FP32 ONNX model to: {fp32_path} ...")
    torch.onnx.export(
        model,
        (inputs["input_ids"], inputs["attention_mask"]),
        fp32_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch_size", 1: "seq_len"},
            "attention_mask": {0: "batch_size", 1: "seq_len"},
            "logits": {0: "batch_size"}
        },
        opset_version=14,
        do_constant_folding=True
    )
    print(f"FP32 ONNX export complete. Size: {os.path.getsize(fp32_path) / (1024*1024):.1f} MB")

    if quantize:
        print(f"Quantizing to INT8 Dynamic: {int8_path} ...")
        quantize_dynamic(
            model_input=fp32_path,
            model_output=int8_path,
            weight_type=QuantType.QInt8,
            per_channel=True
        )
        print(f"INT8 Quantization complete! Size: {os.path.getsize(int8_path) / (1024*1024):.1f} MB")
        # Optionally remove the bulky FP32 file to save disk space
        if os.path.exists(int8_path) and os.path.getsize(int8_path) > 0:
            print("Ready for local client deployment.")

def verify_onnx_model(model_path: str, tokenizer_path: str):
    """Verifies that the ONNX model can run inference successfully with ONNX Runtime."""
    import onnxruntime as ort
    from tokenizers import Tokenizer

    print(f"Verifying ONNX model: {model_path} ...")
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    tokenizer = Tokenizer.from_file(tokenizer_path)

    text = "Slay the Spire test scenario"
    encoded = tokenizer.encode(text)
    input_ids = np.array([encoded.ids], dtype=np.int64)
    attention_mask = np.array([encoded.attention_mask], dtype=np.int64)

    outputs = session.run(None, {
        "input_ids": input_ids,
        "attention_mask": attention_mask
    })
    print("Inference successful! Output shape:", [o.shape for o in outputs])
    print("Output preview:", outputs[0])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Laya Model Exporter & INT8 Quantization Tool")
    parser.add_argument("--model-dir", type=str, help="Path or HuggingFace repo of the Laya model")
    parser.add_argument("--output-dir", type=str, default="models", help="Output directory for ONNX files")
    parser.add_argument("--generate-dummy", action="store_true", help="Generate a lightweight dummy ONNX model for testing")
    parser.add_argument("--verify", action="store_true", help="Verify inference on exported model")

    args = parser.parse_args()

    if args.generate_dummy:
        m_path, t_path = create_dummy_test_model(args.output_dir)
        verify_onnx_model(m_path, t_path)
    elif args.model_dir:
        export_pytorch_to_onnx_and_quantize(args.model_dir, args.output_dir)
        if args.verify:
            verify_onnx_model(os.path.join(args.output_dir, "laya_int8.onnx"), os.path.join(args.output_dir, "tokenizer.json"))
    elif args.verify:
        verify_onnx_model(os.path.join(args.output_dir, "laya_int8.onnx"), os.path.join(args.output_dir, "tokenizer.json"))
    else:
        parser.print_help()
