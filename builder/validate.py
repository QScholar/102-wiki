#!/usr/bin/env python3
from pathlib import Path

from builder import SiteRenderer, WikiRepository


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    repository = WikiRepository(root)
    catalog = repository.load()
    renderer = SiteRenderer(repository)
    renderer.render_catalog()
    renderer.render_guide()
    for wiki in catalog["wikis"]:
        renderer.render_wiki(wiki["slug"])
        for section in wiki["sections"]:
            renderer.render_section(wiki["slug"], section["id"])
    print(f"Validated {len(catalog['wikis'])} Wiki(s) and all configured sections")


if __name__ == "__main__":
    main()
