"""Spotting skills in job postings.

Each skill has regex patterns, matched case-insensitively against title + description.
`(?-i:...)` makes part of a pattern case-sensitive (used for "Go").
"""

import html
import re
from typing import Dict, Iterable, List, Pattern, Set

SKILL_PATTERNS: Dict[str, List[str]] = {
    "Python": [r"\bpython\b"],
    "AWS": [r"\baws\b", r"amazon web services"],
    "LLMs / GenAI": [r"\bllms?\b", r"large language models?", r"generative ai", r"\bgen ?ai\b", r"\bgpt-?\d", r"\bfoundation models?\b"],
    "AI agents": [r"\bai agents?\b", r"\bagentic\b", r"multi-agent", r"langgraph", r"crewai", r"\bautogen\b", r"\bagent (?:framework|workflow|system)s?\b"],
    "CI/CD": [r"\bci ?/ ?cd\b", r"continuous (?:integration|delivery|deployment)", r"github actions", r"gitlab ci", r"\bjenkins\b", r"circleci", r"buildkite"],
    "Kubernetes": [r"kubernetes", r"\bk8s\b", r"\beks\b", r"\bgke\b"],
    "SQL": [r"(?<!no-)(?<!no )\bsql\b"],
    "Azure": [r"\bazure\b"],
    "GCP": [r"\bgcp\b", r"google cloud"],
    "TypeScript": [r"typescript"],
    "Java": [r"\bjava\b(?![ -]?script)"],
    "React": [r"\breact(?:\.?js)?\b(?![ -]native)"],
    "WebSockets / real-time": [r"websockets?", r"\breal-?time\b", r"socket\.io", r"webrtc"],
    "Spark": [r"\bspark\b", r"pyspark"],
    "Terraform / IaC": [r"terraform", r"infrastructure[ -]as[ -]code", r"\biac\b", r"pulumi", r"cloudformation"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
    "Docker": [r"\bdocker\b", r"\bpodman\b"],
    "JavaScript": [r"javascript", r"ecmascript"],
    "C++": [r"\bc\+\+"],
    "Snowflake / BigQuery": [r"snowflake", r"bigquery", r"redshift"],
    "Node.js": [r"\bnode\.?js\b"],
    "RAG / vector DB": [r"\brag\b", r"retrieval[- ]augmented", r"vector (?:db|database|store|search)s?", r"pinecone", r"weaviate", r"pgvector", r"qdrant", r"milvus", r"chromadb"],
    "Microservices": [r"micro-?services?"],
    "Go": [r"\bgolang\b", r"(?-i:(?<=[,/(] )Go\b)", r"(?-i:\bGo\b)(?=\s*[,/)])", r"(?-i:\b(?:in|using|with) Go\b)"],
    "Kafka": [r"\bkafka\b"],
    "Rust": [r"\brust\b"],
    "PyTorch": [r"pytorch", r"\btorch\b"],
    "C#/.NET": [r"(?<!\w)c#", r"(?<![\w.])\.net\b", r"\bdotnet\b", r"asp\.net"],
    "Scala": [r"\bscala\b"],
    "Airflow / dbt": [r"\bairflow\b", r"\bdbt\b", r"\bdagster\b"],
    "Spring": [r"spring boot", r"spring framework", r"\bspring (?:mvc|cloud|data|security)\b"],
    "Redis": [r"\bredis\b"],
    "GraphQL": [r"graphql"],
    "MongoDB": [r"\bmongo(?:db)?\b"],
    "React Native": [r"react[ -]native"],
    "Kotlin": [r"\bkotlin\b"],
    "Ruby": [r"\bruby\b"],
    "Angular": [r"\bangular(?:js)?\b"],
    "Next.js": [r"\bnext\.?js\b"],
    "TensorFlow": [r"tensorflow", r"\bkeras\b"],
    "Vue": [r"\bvue(?:\.?js)?\b"],
    "Pandas / NumPy": [r"\bpandas\b", r"\bnumpy\b", r"\bpolars\b"],
    "Rails": [r"ruby on rails", r"\brails\b"],
    "Swift": [r"\bswift\b"],
    "Express": [r"\bexpress\.?js\b", r"\bnode(?:\.js)?\s*/\s*express\b"],
    "FastAPI": [r"fastapi"],
    "Django": [r"\bdjango\b"],
    "PHP": [r"\bphp\b"],
    "Flutter": [r"\bflutter\b"],
    "Jetpack Compose": [r"jetpack compose"],
    "NestJS": [r"\bnest\.?js\b"],
    "Flask": [r"\bflask\b"],
    "Svelte": [r"\bsvelte(?:kit)?\b"],
    "Firebase": [r"firebase"],
    "SwiftUI": [r"swiftui"],
    "Laravel": [r"laravel"],
    "Elixir": [r"\belixir\b"],
    "Dart": [r"\bdart\b"],
}

TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def plain_text(raw: str) -> str:
    """HTML (possibly escaped twice, as Greenhouse sends it) to plain text."""
    text = html.unescape(html.unescape(raw or ""))
    return SPACE.sub(" ", TAG.sub(" ", text)).strip()


def compile_patterns(patterns: Dict[str, Iterable[str]]) -> Dict[str, Pattern]:
    return {name: re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)
            for name, pats in patterns.items() if pats}


def skills_in(text: str, compiled: Dict[str, Pattern]) -> Set[str]:
    return {name for name, rx in compiled.items() if rx.search(text)}
