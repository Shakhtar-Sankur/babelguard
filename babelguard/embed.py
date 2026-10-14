"""Multilingual sentence embeddings, for linking the same scam across languages by meaning.

Character matching cannot see that "Su paquete está retenido en aduanas" and "Your parcel is held
at customs" are one lure, and it fails completely across scripts (Hindi, Thai, Arabic ...). A
multilingual encoder maps both to nearby vectors. `Encoder` wraps a Hugging Face model with mean
pooling and returns unit vectors, so `campaigns.link(..., embed=Encoder())` links by meaning.

torch and transformers are imported only when an Encoder is created, so the rest of Babelguard
keeps its numpy-only footprint.
"""
import numpy as np

DEFAULT_MODEL = "intfloat/multilingual-e5-small"


class Encoder:
    def __init__(self, model=DEFAULT_MODEL, batch_size=64, max_length=128, prefix=None, device="cpu"):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model)
        self.model = AutoModel.from_pretrained(model).to(device).eval()
        self.batch_size, self.max_length, self.device = batch_size, max_length, device
        # E5 models are trained with a role prefix; symmetric similarity uses "query: " on both sides
        self.prefix = prefix if prefix is not None else ("query: " if "e5" in model.lower() else "")

    def __call__(self, texts):
        out = []
        with self.torch.inference_mode():
            for i in range(0, len(texts), self.batch_size):
                batch = [self.prefix + (t or "") for t in texts[i:i + self.batch_size]]
                enc = self.tok(batch, padding=True, truncation=True, max_length=self.max_length,
                               return_tensors="pt").to(self.device)
                hidden = self.model(**enc).last_hidden_state
                mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                v = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
                out.append(self.torch.nn.functional.normalize(v, dim=-1).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 1), dtype=np.float32)


def top_k(queries, corpus, k=10, chunk=2048):
    """Indices of the k most similar corpus rows for each query row (both unit vectors)."""
    q = np.asarray(queries, dtype=np.float32)
    c = np.asarray(corpus, dtype=np.float32)
    k = min(k, len(c))
    out = np.empty((len(q), k), dtype=np.int64)
    for i in range(0, len(q), chunk):
        s = q[i:i + chunk] @ c.T
        idx = np.argpartition(-s, k - 1, axis=1)[:, :k]
        order = np.take_along_axis(s, idx, axis=1).argsort(axis=1)[:, ::-1]
        out[i:i + chunk] = np.take_along_axis(idx, order, axis=1)
    return out
