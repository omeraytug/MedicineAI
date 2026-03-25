"""WHO ICD-11 API client (OAuth2 client credentials + MMS search)."""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
DEFAULT_RELEASE = "2024-01"


class ICD11Error(Exception):
    pass


def _auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def get_access_token(client_id: str, client_secret: str, client: httpx.Client) -> str:
    resp = client.post(
        TOKEN_URL,
        headers={
            "Authorization": _auth_header(client_id, client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": "icdapi_access"},
    )
    if resp.status_code >= 400:
        raise ICD11Error(f"Token request failed: {resp.status_code} {resp.text[:500]}")
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ICD11Error("Token response missing access_token")
    return str(token)


def search_mms(
    query: str,
    *,
    token: str,
    release_id: str,
    client: httpx.Client,
    limit: int = 10,
) -> list[dict[str, Any]]:
    q = query.strip()
    if not q:
        return []
    url = f"https://id.who.int/icd/release/11/{release_id}/mms/search"
    resp = client.get(
        url,
        params={"q": q},
        headers={
            "Authorization": f"Bearer {token}",
            "API-Version": "v2",
            "Accept": "application/json",
            "Accept-Language": "en",
        },
    )
    if resp.status_code >= 400:
        raise ICD11Error(f"Search failed for {query!r}: {resp.status_code} {resp.text[:500]}")
    payload = resp.json()
    return _normalize_search_hits(payload)[:limit]


def _normalize_search_hits(payload: Any) -> list[dict[str, Any]]:
    """Flatten common ICD API search JSON shapes into small dicts."""
    out: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return out
    entities = (
        payload.get("destinationEntities")
        or payload.get("entities")
        or payload.get("results")
        or []
    )
    if not isinstance(entities, list):
        return out
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        title = ent.get("title") or ent.get("name") or ent.get("label")
        if isinstance(title, dict):
            title = title.get("@value") or title.get("value") or json.dumps(title, ensure_ascii=False)
        uri = ent.get("id") or ent.get("uri") or ent.get("code")
        code = ent.get("theCode") or ent.get("code")
        if title or uri:
            out.append(
                {
                    "title": str(title) if title else "",
                    "uri": str(uri) if uri else "",
                    "code": str(code) if code else "",
                }
            )
    return out


def build_icd_context_for_queries(
    queries: list[str],
    *,
    max_queries: int = 5,
    per_query: int = 6,
) -> str:
    """Run ICD MMS search for each query and return a compact text block for prompts."""
    cid = os.getenv("ICD_CLIENT_ID", "").strip()
    csec = os.getenv("ICD_CLIENT_SECRET", "").strip()
    release = os.getenv("ICD_RELEASE_ID", DEFAULT_RELEASE).strip() or DEFAULT_RELEASE
    if not cid or not csec:
        return ""
    lines: list[str] = []
    with httpx.Client(timeout=45.0) as client:
        try:
            token = get_access_token(cid, csec, client)
        except ICD11Error as e:
            return f"(ICD-11 API unavailable: {e})"
        for q in queries[:max_queries]:
            try:
                hits = search_mms(q, token=token, release_id=release, client=client, limit=per_query)
            except ICD11Error as e:
                lines.append(f"Query {q!r}: error {e}")
                continue
            lines.append(f"Query {q!r}:")
            if not hits:
                lines.append("  (no hits)")
                continue
            for h in hits:
                t = h.get("title") or "?"
                uri = h.get("uri") or ""
                code = h.get("code") or ""
                extra = f" [{code}]" if code else ""
                lines.append(f"  - {t}{extra} ({uri})")
    return "\n".join(lines)
