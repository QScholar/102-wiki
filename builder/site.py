from __future__ import annotations

from copy import deepcopy
from html import unescape
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
from urllib.parse import quote, urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown


SCHEMA_VERSION = 1
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IDENTIFIER_RE = SLUG_RE
SUPPORTED_TYPES = {"markdown", "quotes", "gallery", "video"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".webm", ".ogg", ".mov", ".avi"}
MAX_GIT_FILE_BYTES = 100 * 1024 * 1024
RESERVED_SLUGS = {"guide", "static"}
GUIDE_SOURCE = Path("docs/content-guide.md")
SECTION_RENDERERS = {
    "markdown": "_render_markdown",
    "quotes": "_render_quotes",
    "gallery": "_render_gallery",
    "video": "_render_video",
}


class ConfigError(ValueError):
    """A public-content configuration is invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"缺少配置文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 格式错误：{path}:{exc.lineno}:{exc.colno}：{exc.msg}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"配置文件顶层必须是对象：{path}")
    return value


def _required_text(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context} 的 {key!r} 必须是非空字符串")
    return value.strip()


def _safe_path(base: Path, relative: str, context: str) -> Path:
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ConfigError(f"{context} 包含非法路径：{relative!r}")
    resolved_base = base.resolve()
    resolved = (base / Path(*candidate.parts)).resolve()
    try:
        resolved.relative_to(resolved_base)
    except ValueError as exc:
        raise ConfigError(f"{context} 越出允许目录：{relative!r}") from exc
    return resolved


class WikiRepository:
    """Load and validate the repository on every request/build."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()

    def load(self) -> dict[str, Any]:
        catalog_path = self.root / "catalog.json"
        catalog = _read_json(catalog_path)
        if catalog.get("schema_version") != SCHEMA_VERSION:
            raise ConfigError(f"{catalog_path} 仅支持 schema_version={SCHEMA_VERSION}")
        _required_text(catalog, "title", str(catalog_path))
        _required_text(catalog, "description", str(catalog_path))
        registrations = catalog.get("wikis")
        if not isinstance(registrations, list):
            raise ConfigError(f"{catalog_path} 的 'wikis' 必须是数组")

        wiki_ids: set[str] = set()
        slugs: set[str] = set()
        loaded: list[dict[str, Any]] = []
        for index, registration in enumerate(registrations):
            context = f"catalog.wikis[{index}]"
            if not isinstance(registration, dict):
                raise ConfigError(f"{context} 必须是对象")
            wiki_id = _required_text(registration, "id", context)
            if not IDENTIFIER_RE.fullmatch(wiki_id):
                raise ConfigError(f"{context}.id 只能包含小写字母、数字和连字符")
            if wiki_id in wiki_ids:
                raise ConfigError(f"Wiki id 重复：{wiki_id}")
            wiki_ids.add(wiki_id)
            if not isinstance(registration.get("enabled"), bool):
                raise ConfigError(f"{context}.enabled 必须是布尔值")
            if "featured" in registration and not isinstance(registration["featured"], bool):
                raise ConfigError(f"{context}.featured 必须是布尔值")
            directory = _required_text(registration, "directory", context)
            wiki_dir = _safe_path(self.root, directory, f"{context}.directory")
            if not registration["enabled"]:
                continue
            if not wiki_dir.is_dir():
                raise ConfigError(f"Wiki 目录不存在：{directory}")

            config_path = wiki_dir / "wiki.json"
            config = _read_json(config_path)
            self._validate_wiki(config, config_path, wiki_dir, wiki_id)
            slug = config["slug"]
            if slug in slugs:
                raise ConfigError(f"Wiki slug 重复：{slug}")
            slugs.add(slug)
            item = deepcopy(config)
            item["directory"] = directory
            item["featured"] = registration.get("featured", False)
            item["path"] = wiki_dir
            loaded.append(item)

        loaded.sort(key=lambda item: (not item["featured"], item["title"], item["slug"]))
        result = deepcopy(catalog)
        result["wikis"] = loaded
        result["by_slug"] = {item["slug"]: item for item in loaded}
        return result

    def _validate_wiki(
        self,
        config: dict[str, Any],
        config_path: Path,
        wiki_dir: Path,
        registered_id: str,
    ) -> None:
        context = str(config_path)
        if config.get("schema_version") != SCHEMA_VERSION:
            raise ConfigError(f"{context} 仅支持 schema_version={SCHEMA_VERSION}")
        wiki_id = _required_text(config, "id", context)
        if wiki_id != registered_id:
            raise ConfigError(f"{context} 的 id 与 catalog 注册值不一致")
        slug = _required_text(config, "slug", context)
        if not SLUG_RE.fullmatch(slug):
            raise ConfigError(f"{context} 的 slug 只能包含小写字母、数字和连字符")
        if slug in RESERVED_SLUGS:
            raise ConfigError(f"{context} 的 slug 使用了站点保留名称：{slug}")
        for key in ("title", "subtitle", "description", "logo", "theme"):
            _required_text(config, key, context)
        logo = config["logo"]
        if logo.startswith("/static/"):
            logo_file = _safe_path(
                self.root / "static",
                logo.removeprefix("/static/"),
                f"{context}.logo",
            )
        elif logo.startswith("media/"):
            logo_file = _safe_path(wiki_dir, logo, f"{context}.logo")
        else:
            raise ConfigError(
                f"{context} 的 logo 必须指向 /static/ 或当前 Wiki 的 media/ 资源"
            )
        if not logo_file.is_file():
            raise ConfigError(f"Logo 文件不存在：{logo}")
        if logo_file.suffix.lower() not in IMAGE_SUFFIXES | {".svg"}:
            raise ConfigError(f"Logo 必须是受支持的图片：{logo}")
        self._validate_media_files(wiki_dir, context)

        sections = config.get("sections")
        if not isinstance(sections, list) or not sections:
            raise ConfigError(f"{context} 的 sections 必须是非空数组")
        section_ids: set[str] = set()
        for index, section in enumerate(sections):
            section_context = f"{context}.sections[{index}]"
            if not isinstance(section, dict):
                raise ConfigError(f"{section_context} 必须是对象")
            section_id = _required_text(section, "id", section_context)
            if not IDENTIFIER_RE.fullmatch(section_id):
                raise ConfigError(f"{section_context}.id 只能包含小写字母、数字和连字符")
            if section_id in section_ids:
                raise ConfigError(f"{context} 的栏目 id 重复：{section_id}")
            section_ids.add(section_id)
            for key in ("name", "icon", "type", "source"):
                _required_text(section, key, section_context)
            section_type = section["type"]
            if section_type not in SUPPORTED_TYPES:
                raise ConfigError(f"{section_context} 使用不支持的类型：{section_type}")
            source = _safe_path(wiki_dir, section["source"], f"{section_context}.source")
            should_be_file = section_type in {"markdown", "quotes"}
            if should_be_file and not source.is_file():
                raise ConfigError(f"栏目源文件不存在：{section['source']}")
            if not should_be_file and not source.is_dir():
                raise ConfigError(f"栏目源目录不存在：{section['source']}")

    def _validate_media_files(self, wiki_dir: Path, context: str) -> None:
        media_dir = wiki_dir / "media"
        if not media_dir.is_dir():
            raise ConfigError(f"{context} 缺少 media 目录")
        for path in media_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                path.resolve().relative_to(media_dir.resolve())
            except ValueError as exc:
                raise ConfigError(f"媒体文件越出当前 Wiki：{path}") from exc
            if path.stat().st_size > MAX_GIT_FILE_BYTES:
                relative = path.relative_to(wiki_dir).as_posix()
                raise ConfigError(f"媒体文件超过 GitHub 100 MiB 限制：{relative}")

    def wiki(self, slug: str) -> tuple[dict[str, Any], dict[str, Any]]:
        catalog = self.load()
        try:
            return catalog, catalog["by_slug"][slug]
        except KeyError as exc:
            raise KeyError(slug) from exc


class SiteRenderer:
    """Render the same validated content for Flask and static hosting."""

    def __init__(
        self,
        repository: WikiRepository,
        base_url: str = "/",
        home_url: str = "https://102.yuna.team/",
    ):
        self.repository = repository
        parsed = urlparse(base_url)
        base_path = parsed.path if parsed.scheme or parsed.netloc else base_url
        self.base_path = "/" + base_path.strip("/") if base_path.strip("/") else ""
        self.home_url = home_url
        self.environment = Environment(
            loader=FileSystemLoader(repository.root / "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.globals.update(
            asset=self.asset,
            site_url=self.site_url,
            wiki_logo=self._logo_url,
        )

    def site_url(self, *parts: str, trailing: bool = False) -> str:
        encoded_parts: list[str] = []
        for value in parts:
            encoded_parts.extend(quote(part, safe="") for part in str(value).strip("/").split("/") if part)
        path = "/".join([item for item in [self.base_path.strip("/"), *encoded_parts] if item])
        result = f"/{path}" if path else "/"
        if trailing and not result.endswith("/"):
            result += "/"
        return result

    def asset(self, filename: str) -> str:
        return self.site_url("static", filename)

    def render_catalog(self) -> str:
        catalog = self.repository.load()
        return self._template("catalog.html", catalog=catalog, home_url=self.home_url)

    def render_guide(self) -> str:
        catalog = self.repository.load()
        source = self.repository.root / GUIDE_SOURCE
        if not source.is_file():
            raise ConfigError(f"缺少 Wiki 内容维护指南：{source}")
        html = markdown.markdown(
            source.read_text(encoding="utf-8"),
            extensions=["extra"],
        )
        self._validate_external_links(html, source)
        return self._template(
            "guide.html",
            catalog=catalog,
            guide_html=html,
            catalog_url=self.site_url(trailing=True),
            home_url=self.home_url,
        )

    def render_wiki(self, slug: str) -> str:
        catalog, wiki = self.repository.wiki(slug)
        sections = []
        for section in wiki["sections"]:
            item = deepcopy(section)
            item["url"] = self.site_url(slug, section["id"], trailing=True)
            sections.append(item)
        return self._template(
            "wiki.html",
            catalog=catalog,
            wiki=wiki,
            sections=sections,
            logo_url=self._logo_url(wiki),
            home_url=self.home_url,
        )

    def render_section(self, slug: str, section_id: str) -> str:
        catalog, wiki = self.repository.wiki(slug)
        section = next((item for item in wiki["sections"] if item["id"] == section_id), None)
        if section is None:
            raise KeyError(section_id)
        handler = getattr(self, SECTION_RENDERERS[section["type"]])
        body = handler(wiki, section)
        return self._template(
            "section.html",
            catalog=catalog,
            wiki=wiki,
            section=section,
            body=body,
            wiki_url=self.site_url(slug, trailing=True),
            logo_url=self._logo_url(wiki),
        )

    def _render_markdown(self, wiki: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
        source = _safe_path(wiki["path"], section["source"], "section.source")
        html = markdown.markdown(source.read_text(encoding="utf-8"), extensions=["extra"])
        html = self._rewrite_markdown_images(html, source, wiki)
        self._validate_external_links(html, source)
        return {"template": "types/markdown.html", "html": html}

    def _render_quotes(self, wiki: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
        source = _safe_path(wiki["path"], section["source"], "section.source")
        html = markdown.markdown(source.read_text(encoding="utf-8"), extensions=["extra"])
        html = self._rewrite_markdown_images(html, source, wiki)
        self._validate_external_links(html, source)
        html = re.sub(r"<p>(.+?)</p>", r'<div class="quote-item">\1</div>', html, flags=re.DOTALL)
        return {"template": "types/quotes.html", "html": html}

    def _render_gallery(self, wiki: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
        source = _safe_path(wiki["path"], section["source"], "section.source")
        items = [self._media_item(wiki, item) for item in sorted(source.iterdir(), key=lambda p: p.name.casefold()) if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES]
        return {"template": "types/gallery.html", "items": items}

    def _render_video(self, wiki: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
        source = _safe_path(wiki["path"], section["source"], "section.source")
        items = [self._media_item(wiki, item) for item in sorted(source.iterdir(), key=lambda p: p.name.casefold()) if item.is_file() and item.suffix.lower() in VIDEO_SUFFIXES]
        return {"template": "types/video.html", "items": items}

    def _media_item(self, wiki: dict[str, Any], path: Path) -> dict[str, str]:
        relative = path.resolve().relative_to((wiki["path"] / "media").resolve()).as_posix()
        return {"name": path.name, "url": self.site_url(wiki["slug"], "media", relative)}

    def _rewrite_markdown_images(self, html: str, source: Path, wiki: dict[str, Any]) -> str:
        media_root = (wiki["path"] / "media").resolve()

        def replace(match: re.Match[str]) -> str:
            reference = unescape(match.group(2))
            parsed = urlparse(reference)
            if parsed.scheme or parsed.netloc or reference.startswith(("/", "#", "data:")):
                return match.group(0)
            target = (source.parent / parsed.path).resolve()
            try:
                relative = target.relative_to(media_root)
            except ValueError as exc:
                raise ConfigError(f"Markdown 图片必须位于当前 Wiki 的 media 目录：{reference}") from exc
            if not target.is_file():
                raise ConfigError(f"Markdown 图片不存在：{reference}")
            rewritten = self.site_url(wiki["slug"], "media", relative.as_posix())
            return f"{match.group(1)}{rewritten}{match.group(3)}"

        return re.sub(r'(<img\b[^>]*\bsrc=")([^"]+)(")', replace, html, flags=re.IGNORECASE)

    def _validate_external_links(self, html: str, source: Path) -> None:
        if re.search(r"\b(?:href|src)\s*=\s*['\"]http://", html, flags=re.IGNORECASE):
            raise ConfigError(f"外部链接必须使用 HTTPS：{source}")

    def _logo_url(self, wiki: dict[str, Any]) -> str:
        logo = wiki["logo"]
        if logo.startswith("/static/"):
            return self.asset(logo.removeprefix("/static/"))
        return self.site_url(wiki["slug"], logo)

    def _template(self, name: str, **context: Any) -> str:
        return self.environment.get_template(name).render(**context)
