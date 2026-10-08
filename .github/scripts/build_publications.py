"""_data/publication_dois.yml 의 DOI 목록으로 _data/publications.yml 을 생성한다.

메타데이터는 doi.org content negotiation(CSL-JSON)으로 가져온다.
Crossref DOI(대부분의 저널, medRxiv/bioRxiv)와 DataCite DOI(arXiv, Zenodo) 모두 지원.
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

SRC = Path("_data/publication_dois.yml")
OUT = Path("_data/publications.yml")
MY_NAME = "Dahhay Lee"
USER_AGENT = "DahhayLee.github.io publications builder (https://dahhaylee.github.io)"

HEADER = """\
# 자동 생성 파일이에요. 직접 고치지 말고 _data/publication_dois.yml 을 수정하세요.
# (여기를 고치면 다음 실행 때 덮어써져요.)
"""


def norm_doi(s):
    s = str(s).strip()
    s = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", s, flags=re.I)
    s = re.sub(r"^doi:\s*", "", s, flags=re.I)
    return s


def fetch_csl(doi, retries=3):
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="/:;()._-")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.citationstyles.csl+json",
        "User-Agent": USER_AGENT,
    })
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            err = e
        except Exception as e:  # 네트워크 오류 등
            err = e
        time.sleep(2 * (i + 1))
    raise err


KEEP_TAGS = {"i", "em", "b", "strong", "sub", "sup"}


def clean_title(t):
    if isinstance(t, list):
        t = t[0] if t else ""
    t = html.unescape(t or "")
    # <i>, <sub> 등은 남기고 <scp>, <mml:...> 같은 나머지 태그는 벗겨낸다
    def repl(m):
        name = m.group(2).lower()
        return m.group(0) if name in KEEP_TAGS else ""
    t = re.sub(r"<(/?)([a-zA-Z][\w:.-]*)[^>]*>", repl, t)
    return re.sub(r"\s+", " ", t).strip()


def fix_my_name(name):
    key = re.sub(r"[^a-z]", "", name.lower())
    return MY_NAME if key in ("dahhaylee", "leedahhay") else name


def fmt_authors(authors):
    out = []
    for a in authors or []:
        if a.get("literal") or a.get("name"):
            n = a.get("literal") or a.get("name")
        else:
            n = " ".join(x for x in (a.get("given"), a.get("family")) if x)
        if n:
            out.append(fix_my_name(n.strip()))
    return ", ".join(out)


def year_of(csl):
    # 인쇄판 연도 우선(인용 표기와 일치), 없으면 온라인 → issued
    for k in ("published-print", "journal-issue", "published-online", "issued", "published"):
        v = csl.get(k)
        if isinstance(v, dict) and k == "journal-issue":
            v = v.get("published-print")
        try:
            return int(v["date-parts"][0][0])
        except (TypeError, KeyError, IndexError, ValueError):
            continue
    return None


def from_csl(doi, csl):
    journal = csl.get("container-title") or csl.get("publisher") or ""
    if isinstance(journal, list):
        journal = journal[0] if journal else ""
    vol = str(csl.get("volume") or "").strip()
    iss = str(csl.get("issue") or "").strip()
    volume = f"{vol}({iss})" if vol and iss else vol
    pages = str(csl.get("page") or csl.get("article-number") or "").strip()
    pages = pages.replace("--", "–").replace("-", "–")
    e = {
        "title": clean_title(csl.get("title")),
        "authors": fmt_authors(csl.get("author")),
        "journal": html.unescape(journal),
        "year": year_of(csl),
        "volume": volume,
        "pages": pages,
        "doi": doi,
    }
    return {k: v for k, v in e.items() if v not in ("", None)}


def main():
    items = yaml.safe_load(SRC.read_text(encoding="utf-8")) or []
    prev = {}
    if OUT.exists():
        for p in yaml.safe_load(OUT.read_text(encoding="utf-8")) or []:
            if p.get("doi"):
                prev[p["doi"].lower()] = p

    result, problems = [], []
    for it in items:
        if isinstance(it, (str, int, float)):
            it = {"doi": str(it)}
        if not isinstance(it, dict):
            problems.append(f"알 수 없는 항목 형식: {it!r}")
            continue
        it = dict(it)
        if it.get("hide"):
            continue

        if not it.get("doi"):  # DOI 없는 수동 항목은 그대로 사용
            if not (it.get("title") and it.get("year")):
                problems.append(f"DOI 없는 항목에는 title과 year가 필요해요: {it!r}")
                continue
            result.append(it)
            continue

        doi = norm_doi(it.pop("doi"))
        try:
            entry = from_csl(doi, fetch_csl(doi))
        except Exception as e:
            old = prev.get(doi.lower())
            if old:
                problems.append(f"{doi}: 가져오기 실패({e}) → 이전 값 유지")
                entry = {k: v for k, v in old.items()}
            else:
                problems.append(f"{doi}: 가져오기 실패({e}) → 이번엔 목록에서 빠짐")
                continue
        entry.update({k: v for k, v in it.items() if v is not None})  # 직접 적은 필드가 우선
        if not entry.get("year"):
            problems.append(f"{doi}: 연도를 찾지 못했어요. year: 를 직접 적어 주세요")
            continue
        result.append(entry)
        time.sleep(0.5)

    OUT.write_text(
        HEADER + yaml.safe_dump(result, allow_unicode=True, sort_keys=False, width=1000),
        encoding="utf-8",
    )
    print(f"{len(result)}편 기록 → {OUT}")
    for p in problems:
        print(f"::warning::{p}")


if __name__ == "__main__":
    sys.exit(main())