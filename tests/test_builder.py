from pathlib import Path
import json
import tempfile
import unittest

from builder import ConfigError, SiteRenderer, WikiRepository
from builder.build import build


ROOT = Path(__file__).resolve().parents[1]


class BuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = WikiRepository(ROOT)

    def test_current_repository_validates(self) -> None:
        catalog = self.repository.load()
        self.assertEqual(["jiaoxianting"], [wiki["slug"] for wiki in catalog["wikis"]])
        self.assertEqual(4, len(catalog["wikis"][0]["sections"]))
        self.assertEqual(
            "media/gallery/IMG_20251021_200058.jpg",
            catalog["wikis"][0]["logo"],
        )

    def test_catalog_uses_configured_wiki_media_as_cover(self) -> None:
        rendered = SiteRenderer(self.repository, base_url="/preview/").render_catalog()
        self.assertIn('class="catalog-cover"', rendered)
        self.assertIn('/preview/static/sakuya-logo.svg', rendered)
        self.assertIn(
            "/preview/jiaoxianting/media/gallery/IMG_20251021_200058.jpg",
            rendered,
        )

    def test_urls_support_project_path_and_unicode_media(self) -> None:
        renderer = SiteRenderer(self.repository, base_url="https://example.github.io/yuna-wiki/")
        self.assertEqual(
            "/yuna-wiki/jiaoxianting/media/video/%EF%BC%9F%EF%BC%81%E7%A5%9E%E7%A5%9E%EF%BC%81%EF%BC%9F.mp4",
            renderer.site_url("jiaoxianting", "media", "video/？！神神！？.mp4"),
        )

    def test_static_build_contains_all_routes_and_media(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build(output, "/preview/")
            expected = [
                output / "index.html",
                output / "CNAME",
                output / "jiaoxianting/index.html",
                output / "jiaoxianting/story/index.html",
                output / "jiaoxianting/quotes/index.html",
                output / "jiaoxianting/gallery/index.html",
                output / "jiaoxianting/video/index.html",
                output / "jiaoxianting/media/video/？！神神！？.mp4",
                output / "static/wiki.css",
            ]
            for path in expected:
                self.assertTrue(path.exists(), path)
            rendered = (output / "jiaoxianting/gallery/index.html").read_text(encoding="utf-8")
            self.assertIn("/preview/jiaoxianting/media/gallery/", rendered)
            self.assertNotIn(str(ROOT), rendered)
            self.assertEqual(
                "102wiki.yuna.team\n",
                (output / "CNAME").read_text(encoding="utf-8"),
            )

    def test_new_wiki_needs_only_content_and_registration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "static").mkdir()
            (root / "static/logo.svg").write_text("<svg/>", encoding="utf-8")
            for slug in ("first", "second"):
                wiki_dir = root / "content" / slug
                (wiki_dir / "pages").mkdir(parents=True)
                (wiki_dir / "media").mkdir()
                (wiki_dir / "pages/story.md").write_text(f"# {slug}", encoding="utf-8")
                (wiki_dir / "wiki.json").write_text(json.dumps({
                    "schema_version": 1,
                    "id": slug,
                    "slug": slug,
                    "title": slug.title(),
                    "subtitle": "Test",
                    "description": "Test Wiki",
                    "logo": "/static/logo.svg",
                    "theme": "archive",
                    "sections": [{"id": "story", "name": "Story", "icon": "book", "type": "markdown", "source": "pages/story.md"}],
                }), encoding="utf-8")
            (root / "catalog.json").write_text(json.dumps({
                "schema_version": 1,
                "title": "Test catalog",
                "description": "Test",
                "wikis": [
                    {"id": slug, "directory": f"content/{slug}", "enabled": True, "featured": False}
                    for slug in ("first", "second")
                ],
            }), encoding="utf-8")
            self.assertEqual({"first", "second"}, set(WikiRepository(root).load()["by_slug"]))

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog.json").write_text(json.dumps({
                "schema_version": 1,
                "title": "Test catalog",
                "description": "Test",
                "wikis": [{"id": "bad", "directory": "../outside", "enabled": True}],
            }), encoding="utf-8")
            with self.assertRaises(ConfigError):
                WikiRepository(root).load()

    def test_insecure_markdown_link_is_rejected(self) -> None:
        source = ROOT / "content/jiaoxianting/pages/story.md"
        wiki = self.repository.load()["wikis"][0]
        renderer = SiteRenderer(self.repository)
        html = '<p><a href="http://example.com">insecure</a></p>'
        with self.assertRaises(ConfigError):
            renderer._validate_external_links(html, source)

    def test_oversized_media_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "static").mkdir()
            (root / "static/logo.svg").write_text("<svg/>", encoding="utf-8")
            wiki_dir = root / "content/test"
            (wiki_dir / "pages").mkdir(parents=True)
            (wiki_dir / "media/gallery").mkdir(parents=True)
            (wiki_dir / "pages/story.md").write_text("# Test", encoding="utf-8")
            with (wiki_dir / "media/gallery/too-large.jpg").open("wb") as file:
                file.truncate(100 * 1024 * 1024 + 1)
            (wiki_dir / "wiki.json").write_text(json.dumps({
                "schema_version": 1,
                "id": "test",
                "slug": "test",
                "title": "Test",
                "subtitle": "Test",
                "description": "Test",
                "logo": "/static/logo.svg",
                "theme": "archive",
                "sections": [{"id": "story", "name": "Story", "icon": "book", "type": "markdown", "source": "pages/story.md"}],
            }), encoding="utf-8")
            (root / "catalog.json").write_text(json.dumps({
                "schema_version": 1,
                "title": "Test",
                "description": "Test",
                "wikis": [{"id": "test", "directory": "content/test", "enabled": True}],
            }), encoding="utf-8")
            with self.assertRaises(ConfigError):
                WikiRepository(root).load()


if __name__ == "__main__":
    unittest.main()
