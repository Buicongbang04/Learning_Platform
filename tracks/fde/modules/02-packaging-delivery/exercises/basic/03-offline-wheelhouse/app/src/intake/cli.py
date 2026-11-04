import json
import platform
import sys
from importlib.metadata import version

import yaml
from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    title: str
    pages: int = Field(ge=1)
    tags: list[str] = []


def summarize(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        documents = [Document.model_validate(item) for item in yaml.safe_load(handle) or []]
    return {
        "documents": len(documents),
        "pages": sum(doc.pages for doc in documents),
        "tags": sorted({tag for doc in documents for tag in doc.tags}),
        "versions": {
            "python": platform.python_version(),
            "pydantic": version("pydantic"),
            "pyyaml": version("pyyaml"),
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Cách dùng: intake <documents.yaml>", file=sys.stderr)
        return 2
    print(json.dumps(summarize(sys.argv[1]), ensure_ascii=False))
    return 0
