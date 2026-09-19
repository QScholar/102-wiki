#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from builder import SiteRenderer, WikiRepository


ROOT = Path(__file__).resolve().parents[1]


def write_page(output: Path, relative: Path, html: str) -> None:
    target = output / relative / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def build(output: Path, base_url: str, custom_domain: str | None = None) -> None:
    repository = WikiRepository(ROOT)
    catalog = repository.load()
    renderer = SiteRenderer(repository, base_url=base_url)

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    write_page(output, Path(), renderer.render_catalog())

    for wiki in catalog["wikis"]:
        slug = wiki["slug"]
        write_page(output, Path(slug), renderer.render_wiki(slug))
        for section in wiki["sections"]:
            write_page(output, Path(slug) / section["id"], renderer.render_section(slug, section["id"]))
        shutil.copytree(wiki["path"] / "media", output / slug / "media", dirs_exist_ok=True)

    shutil.copytree(ROOT / "static", output / "static", dirs_exist_ok=True)
    (output / ".nojekyll").touch()
    if custom_domain:
        (output / "CNAME").write_text(custom_domain.strip() + "\n", encoding="utf-8")
    print(f"Built {len(catalog['wikis'])} Wiki(s) in {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the YUNA102 Wiki static site")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--base-url", default="/")
    parser.add_argument("--custom-domain")
    args = parser.parse_args()
    build(args.output.resolve(), args.base_url, args.custom_domain)


if __name__ == "__main__":
    main()
