"""
RAG layer: TF-IDF retrieval over the compatibility rows + an optional IBM watsonx.ai
(Granite) answer written from those rows.

The structured rows are the ground truth; the Granite model only explains them. The
system prompt forbids stating compatibility that is not in the retrieved rows.
If watsonx.ai is not configured, the app simply shows the matching rows.

Environment variables (set as Code Engine secrets / env, never commit them):
  WATSONX_APIKEY      IBM Cloud API key
  WATSONX_PROJECT_ID  watsonx.ai project (or WATSONX_SPACE_ID for a deployment space)
  WATSONX_URL         region endpoint, default https://us-south.ml.cloud.ibm.com
  WATSONX_MODEL_ID    default ibm/granite-3-3-8b-instruct (check your region's model list)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_MODEL_ID = os.environ.get("WATSONX_MODEL_ID", "ibm/granite-3-3-8b-instruct")
DEFAULT_URL = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

SYSTEM_PROMPT = """You are a mainframe (z/OS) product-compatibility assistant for z/OS migrations.
You receive ROWS from a compatibility matrix. They are ground truth:
- 'R3.2', 'z/OS 3.1' and 'z/OS 2.5' are each Yes / No / In Progress / Unverified. Unverified means NO vendor statement was found - never present it as compatible.
- The PTF fields are release-specific: ptf_required is for z/OS 3.2, ptf_required_31 for 3.1, and ptf_required_25 for 2.5.
- Extracted maintenance details are best-effort source-page text. Use them only when present, and never infer that no maintenance is required when details are missing.
Rules:
- Answer ONLY from the rows. If they do not answer the question, say so and point to the vendor link in the rows.
- Never invent products, versions, PTF numbers or dates.
- Group by vendor. Call out products that are Yes on an older z/OS (2.5 or 3.1) but No on a newer one, and any that need PTFs.
- End with one line telling the user to confirm against the live vendor page before production changes, and
  include the source links from the rows you used.
- Be concise: a short intro, then a clean grouped list."""


@dataclass
class RagIndex:
    df: pd.DataFrame
    vectorizer: TfidfVectorizer
    matrix: object

    @classmethod
    def build(cls, df: pd.DataFrame) -> "RagIndex":
        d = df.reset_index(drop=True)
        texts = d.apply(
            lambda r: (f"{r['vendor']} {r['product']} version {r['vrm']} z/OS 3.2 {r['zos32']} z/OS 3.1 {r['zos31']} z/OS 2.5 {r['zos25']} "
                       f"PTF z/OS 3.2 {r['ptf_required']} z/OS 3.1 {r['ptf_required_31']} "
                       f"z/OS 2.5 {r['ptf_required_25']} EOS {r['eos_date']} latest {r['latest_version']} {r['comments']} "
                       f"{r.get('maintenance_details', '')}"),
            axis=1,
        ).tolist()
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        return cls(df=d, vectorizer=vec, matrix=vec.fit_transform(texts))

    def retrieve(self, query: str, top_k: int = 12) -> pd.DataFrame:
        sims = cosine_similarity(self.vectorizer.transform([query]), self.matrix).ravel()
        idx = [i for i in sims.argsort()[::-1][:top_k] if sims[i] > 0]
        return self.df.iloc[idx]


def _rows_text(rows: pd.DataFrame) -> str:
    return "\n".join(
        f"- {r['vendor']} | {r['product']} {r['vrm']} | z/OS 2.5: {r['zos25']} | z/OS 3.1: {r['zos31']} | R3.2: {r['zos32']} | "
        f"PTFs (2.5/3.1/3.2): {r['ptf_required_25']} / {r['ptf_required_31']} / {r['ptf_required']} | "
        f"EOS: {r['eos_date']} | latest: {r['latest_version']} | "
        f"{r['comments']} | maintenance details: {r.get('maintenance_details', 'not fetched')} | "
        f"source: {r['link']} ({r['data_status']})"
        for _, r in rows.iterrows()
    )


def watsonx_configured() -> bool:
    return bool(os.environ.get("WATSONX_APIKEY") and (os.environ.get("WATSONX_PROJECT_ID") or os.environ.get("WATSONX_SPACE_ID")))


def generate_answer(question: str, rows: pd.DataFrame, model_id: str | None = None) -> str:
    """Write an answer from the retrieved rows with a Granite model on watsonx.ai."""
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    creds = Credentials(url=DEFAULT_URL, api_key=os.environ["WATSONX_APIKEY"])
    kwargs = {}
    if os.environ.get("WATSONX_PROJECT_ID"):
        kwargs["project_id"] = os.environ["WATSONX_PROJECT_ID"]
    else:
        kwargs["space_id"] = os.environ["WATSONX_SPACE_ID"]

    model = ModelInference(model_id=model_id or DEFAULT_MODEL_ID, credentials=creds, **kwargs)
    body = _rows_text(rows) if not rows.empty else "(no matching rows)"
    resp = model.chat(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nMATRIX ROWS:\n{body}"},
        ],
        params={"max_tokens": 1200, "temperature": 0},
    )
    return resp["choices"][0]["message"]["content"]
