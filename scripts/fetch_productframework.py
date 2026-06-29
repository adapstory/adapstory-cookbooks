#!/usr/bin/env python3
"""Archive public Product Architecture Framework materials into this repo."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs" / "productframework"
PAGES_ROOT = DOCS_ROOT / "pages"
EXTERNAL_ROOT = DOCS_ROOT / "external"
ASSETS_ROOT = REPO_ROOT / "assets" / "productframework"
DATA_ROOT = REPO_ROOT / "data" / "productframework"

SITE_ROOT = "https://productframework.ru"
SITEMAP_URL = f"{SITE_ROOT}/sitemap.xml"
REQUEST_HEADERS = {
    "User-Agent": "adapstory-cookbooks-archiver/1.0 (+https://github.com/adapstory/adapstory-cookbooks)"
}
DEFAULT_TIMEOUT_SECONDS = 20

SKIP_TEXT_EXACT = {
    "Методология",
    "Руководство",
    "Лекториум",
    "Навыки [+ИИ]",
    "Game of PAF",
    "Feature Life Cycle",
    "Product Life Cycle",
    "Инструменты",
    "Гипотезы и эксперименты",
    "Библиотеки и шаблоны",
    "Схема жизненного цикла",
    "I этап. Product Discovery",
    "Библиотека бизнес-моделей",
    "Библиотека гипотез и экспериментов",
    "Оценка рынка TAM / SAM / SOM",
    "Экосистема продуктов",
    "Product Requirements Document",
    "Hypothesis Card",
    "To main content",
    "CC BY-SA 4.0 License",
    "Юридическая информация",
    "Обо мне и вопросы сотрудничества",
    'Канал "Борода продакта"',
}

SKIP_TEXT_PREFIXES = (
    "На сайте используются Cookies",
    "Файлы cookie, необходимые",
    "Основные файлы cookie",
    "Аналитические файлы cookie",
    "Рекламные файлы cookie",
    "Список используемых нами",
    "Всегда включены.",
    "Эти файлы cookie",
    "посмотреть здесь",
    "Узнать больше",
    "Смотреть ролики",
)

INTERNAL_HOSTS = {"productframework.ru", "www.productframework.ru"}
SUPPORTED_EXTERNAL_HOSTS = {
    "miro.com": "miro",
    "docs.google.com": "google",
}

ARTIFACT_BRIEFS: dict[str, dict[str, object]] = {
    "https://miro.com/app/board/uXjVK3QPtrU=/": {
        "description": (
            "Каркас Product Architecture Framework: круговая карта продуктовой "
            "системы, которая связывает исследования, маркетинг, продажи, "
            "дизайн решения, разработку, delivery, рост и эксперименты."
        ),
        "covers": [
            "Показывает PAF как единую карту взаимосвязанных продуктовых практик.",
            "Разбивает пространство на шесть крупных доменов: Discovery & Researches, Value & Solution Design, Development & Delivery, Growth & Experiments, Product Marketing, Sales & Economics.",
            "Помогает увидеть, какие артефакты и виды работ соединяют стратегию, гипотезы, реализацию и масштабирование.",
        ],
        "usage": [
            "Использовать как обзорную карту для product ops, обучения и аудита роли команды.",
            "Отмечать на карте, какие практики уже работают, а какие являются пробелами.",
        ],
        "key_pages": ["home.md", "product_life_cycle.md", "product_discovery.md"],
    },
    "https://miro.com/app/board/uXjVOWJXlSQ=/": {
        "description": (
            "Набор шаблонов Business Model Canvas и производных схем для анализа "
            "и перепроектирования бизнес-модели продукта."
        ),
        "covers": [
            "Содержит варианты структурирования сегментов, ценностных предложений, каналов, монетизации и издержек.",
            "Подходит для генерации альтернативных моделей масштабирования и проверки гипотез монетизации.",
        ],
        "usage": [
            "Использовать на этапе Business Model Research и при стратегическом рефакторинге продукта.",
            "Заполнять несколько канвасов параллельно, чтобы сравнить разные модели роста и unit-экономики.",
        ],
        "key_pages": ["activities/business_model_research.md", "hypotheses/business_model.md", "business_goals.md"],
    },
    "https://miro.com/app/board/uXjVOxyyBs0=/": {
        "description": (
            "Библиотека гипотез и экспериментов для проверки спроса, ценности, "
            "каналов привлечения, активации и бизнес-модели."
        ),
        "covers": [
            "Собирает паттерны экспериментов по разным продуктовым зонам: discovery, growth, marketing и monetization.",
            "Помогает быстро подобрать метод валидации под конкретную неопределённость.",
        ],
        "usage": [
            "Использовать как каталог экспериментов при формировании backlog гипотез.",
            "Привязывать выбранный эксперимент к карточке Hypothesis Card и ожидаемой метрике решения.",
        ],
        "key_pages": ["experiment_methodology.md", "hypothesis.md", "activities/acquisition_configuration_research.md"],
    },
    "https://miro.com/app/board/uXjVPLzO7IM=/": {
        "description": (
            "Шаблон оценки объёма рынка TAM / SAM / SOM для перевода общей "
            "рыночной возможности в реалистичный адресуемый сегмент и целевой "
            "объём захвата."
        ),
        "covers": [
            "Разделяет расчёт на полный рынок, доступный сегмент и достижимую долю.",
            "Нужен для проверки, достаточно ли ёмкости рынка под амбиции продукта и бизнеса.",
        ],
        "usage": [
            "Использовать в Market Analysis и Segment Scoring до масштабных инвестиций в решение.",
            "Фиксировать допущения по сегментам, каналам и ограничениям, а затем уточнять расчёт по мере исследований.",
        ],
        "key_pages": ["tam_sam_som.md", "activities/market_analysis.md", "activities/segment_scoring.md"],
    },
    "https://miro.com/app/board/uXjVN-A4MfU=/": {
        "description": (
            "Схема продуктовой экосистемы, которая показывает, как несколько "
            "продуктов и потоков ценности могут усиливать друг друга внутри "
            "общего портфеля."
        ),
        "covers": [
            "Помогает проектировать связи между продуктами, каналами и сценариями перехода пользователя между решениями.",
            "Нужна для thinking beyond single-product growth и поиска синергии в портфеле.",
        ],
        "usage": [
            "Использовать в Product Evolution и Portfolio Formation, когда бизнес выходит за рамки одного продукта.",
            "Отмечать точки cross-sell, shared capabilities и общие каналы acquisition/retention.",
        ],
        "key_pages": ["product_ecosystem_map.md", "product_evolution_cycle.md", "product_market_fit.md"],
    },
    "https://miro.com/app/board/uXjVOs817Gs=/": {
        "description": (
            "Карта навыков и ролей product management, раскладывающая продуктовые "
            "компетенции по доменам исследований, маркетинга, экономики, "
            "дизайна решения, delivery и growth."
        ),
        "covers": [
            "Показывает, какие компетенции нужны менеджеру продукта и как они группируются в разные типы ролей.",
            "Поддерживает обсуждение роли AI в перераспределении продуктовых задач.",
        ],
        "usage": [
            "Использовать для оценки текущей роли product manager и планирования развития команды.",
            "Применять как матрицу для найма, обучения и обсуждения новой ролевой модели с ИИ.",
        ],
        "key_pages": ["skill_map.md", "ai_product_roles.md"],
    },
    "https://docs.google.com/document/d/1I61-3IfI6qqsDQM5Cnvw0aFztQNbRU9CCq9St8Z3vCE/edit": {
        "description": (
            "Шаблон PRD для фиксации продуктовой проблемы, целевого сегмента, "
            "ценностного предложения, требований, ограничений и критериев успеха."
        ),
        "covers": [
            "Переводит исследовательские и стратегические выводы в документ для дизайна и delivery.",
        ],
        "usage": [
            "Заполнять после прохождения discovery и перед детальным проектированием решения.",
        ],
        "key_pages": ["activities/requirements_design.md", "product_documentation.md", "implementation_plan.md"],
    },
    "https://docs.google.com/document/d/1C-9NCwm5_AFssK72OEJK2ujQjuuZVvK-8p1tHverp6s/edit": {
        "description": (
            "Карточка гипотезы для структурирования допущения, метрик проверки, "
            "дизайна эксперимента и критерия принятия решения."
        ),
        "covers": [
            "Служит базовым форматом для управления гипотезами потребителя, ценности, решения и бизнес-модели.",
        ],
        "usage": [
            "Использовать вместе с библиотекой экспериментов и backlog гипотез.",
        ],
        "key_pages": ["hypothesis.md", "hypotheses/customer.md", "experiment_methodology.md"],
    },
    "https://docs.google.com/spreadsheets/d/1DC61vKVcPcxb2OgGZ98hKSlzM1c07YfhAywu1WFy8Eg/edit": {
        "description": (
            "Табличная карта Product Mindset с навыками менеджера продукта, "
            "используемая для диагностики компетенций и обсуждения ролевой модели."
        ),
        "covers": [
            "Фиксирует набор навыков и позволяет смотреть на них как на матрицу развития или оценки роли.",
        ],
        "usage": [
            "Использовать при оценке компетенций, найме и построении плана обучения product-команды.",
        ],
        "key_pages": ["skill_map.md", "ai_product_roles.md"],
    },
}


@dataclass
class LinkRecord:
    text: str
    url: str


class ProductPageParser(HTMLParser):
    """Extract links, images, metadata, and readable text chunks."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=False)
        self.base_url = base_url
        self.title = ""
        self.meta: dict[str, str] = {}
        self.links: list[LinkRecord] = []
        self.images: list[str] = []
        self.text_chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._current_link: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            value = attrs_dict.get("content")
            if key and value:
                self.meta[key] = normalize_space(value)
            return
        if tag == "a":
            href = attrs_dict.get("href")
            if href:
                self._current_link = urllib.parse.urljoin(self.base_url, href)
                self._current_link_text = []
            return
        if tag == "img":
            src = attrs_dict.get("src")
            if src:
                self.images.append(urllib.parse.urljoin(self.base_url, src))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
            return
        if tag == "a" and self._current_link:
            text = normalize_space(" ".join(self._current_link_text))
            self.links.append(LinkRecord(text=text, url=self._current_link))
            self._current_link = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = normalize_space(unescape(data))
        if not text:
            return
        if self._in_title:
            self.title += text
            return
        if self._current_link is not None:
            self._current_link_text.append(text)
        if len(text) >= 20:
            self.text_chunks.append(text)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def ensure_dirs() -> None:
    for path in (DOCS_ROOT, PAGES_ROOT, EXTERNAL_ROOT, ASSETS_ROOT, DATA_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", "ignore")


def parse_sitemap(xml_text: str) -> list[str]:
    return re.findall(r"<loc>(.*?)</loc>", xml_text)


def page_slug(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    return path or "home"


def title_to_slug(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zА-Яа-я._-]+", "-", value, flags=re.UNICODE)
    cleaned = cleaned.strip("-").lower()
    return cleaned or "artifact"


def markdown_relpath(target: Path, source_dir: Path) -> str:
    return os.path.relpath(target, source_dir).replace(os.sep, "/")


def clean_text_chunks(chunks: Iterable[str], title: str, description: str) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        text = normalize_space(chunk)
        if not text or text in seen:
            continue
        if text == title or text == description:
            continue
        if text in SKIP_TEXT_EXACT:
            continue
        if any(text.startswith(prefix) for prefix in SKIP_TEXT_PREFIXES):
            continue
        if text.startswith("http://") or text.startswith("https://"):
            continue
        if "t-btnflex" in text or "background-color:" in text:
            continue
        seen.add(text)
        cleaned.append(text)
    return trim_text_edges(cleaned)


def trim_text_edges(chunks: list[str]) -> list[str]:
    start = 0
    for index, chunk in enumerate(chunks):
        if len(chunk) >= 60 or "." in chunk or chunk.isupper():
            start = index
            break

    end = len(chunks)
    footer_markers = (
        "Product Architecture Framework and all site's materials is distributed under a",
        "Product Architecture Framework and all site materials is distributed under a",
    )
    for index, chunk in enumerate(chunks[start:], start=start):
        if any(chunk.startswith(marker) for marker in footer_markers):
            end = index
            break

    return chunks[start:end]


def filter_links(links: Iterable[LinkRecord]) -> list[LinkRecord]:
    filtered: list[LinkRecord] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        if not link.url.startswith("http"):
            continue
        key = (link.text, link.url)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(link)
    return filtered


def safe_asset_suffix(url: str, content_type: str | None) -> str:
    parsed = urllib.parse.urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".svg", ".gif", ".webp", ".pdf", ".txt"}:
        return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return ".bin"


def infer_suffix_from_bytes(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


def download_asset(url: str, target: Path) -> Path | None:
    if target.exists():
        return target
    try:
        data = fetch_bytes(url)
    except Exception as exc:
        print(f"[warn] asset download failed: {url} ({exc})", file=sys.stderr)
        return None
    final_target = target
    if final_target.suffix == ".bin":
        final_target = final_target.with_suffix(infer_suffix_from_bytes(data))
        if final_target.exists():
            return final_target
    target.parent.mkdir(parents=True, exist_ok=True)
    final_target.write_bytes(data)
    return final_target


def resolve_external_type(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    for supported_host, external_type in SUPPORTED_EXTERNAL_HOSTS.items():
        if host.endswith(supported_host):
            if external_type != "google":
                return external_type
            if "/document/d/" in parsed.path:
                return "google-doc"
            if "/spreadsheets/d/" in parsed.path:
                return "google-sheet"
    return None


def canonicalize_external_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if host.endswith("miro.com") and parsed.path.startswith("/app/board/"):
        return urllib.parse.urlunparse(("https", "miro.com", parsed.path, "", "", ""))
    if host.endswith("docs.google.com"):
        if "/document/d/" in parsed.path:
            doc_id = google_doc_id(url)
            if doc_id:
                return f"https://docs.google.com/document/d/{doc_id}/edit"
        if "/spreadsheets/d/" in parsed.path:
            sheet_id = google_sheet_id(url)
            if sheet_id:
                return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def pandoc_available() -> bool:
    return bool(shutil_which("pandoc"))


def shutil_which(command: str) -> str | None:
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(folder) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def html_to_markdown_excerpt(html_text: str) -> str | None:
    if not pandoc_available():
        return None
    result = subprocess.run(
        ["pandoc", "-f", "html", "-t", "plain"],
        input=html_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    text = normalize_space(result.stdout.decode("utf-8", "ignore"))
    return text or None


def google_doc_id(url: str) -> str | None:
    match = re.search(r"/document/d/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def google_sheet_id(url: str) -> str | None:
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None


def fetch_google_doc_text(url: str) -> str | None:
    doc_id = google_doc_id(url)
    if not doc_id:
        return None
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        return fetch_text(export_url)
    except Exception:
        return None


def fetch_google_sheet_csv(url: str) -> str | None:
    sheet_id = google_sheet_id(url)
    if not sheet_id:
        return None
    parsed = urllib.parse.urlparse(url)
    gid = urllib.parse.parse_qs(parsed.query).get("gid", [None])[0]
    if not gid and parsed.fragment.startswith("gid="):
        gid = parsed.fragment.split("=", 1)[1]
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        export_url += f"&gid={gid}"
    try:
        return fetch_text(export_url)
    except Exception:
        return None


def write_page_markdown(
    page_url: str,
    title: str,
    description: str,
    image_path: Path | None,
    chunks: list[str],
    external_links: list[LinkRecord],
) -> Path:
    slug = page_slug(page_url)
    target = PAGES_ROOT / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    lines.append(f"- Source: [{page_url}]({page_url})")
    if description:
        lines.append(f"- Summary: {description}")
    if image_path:
        rel = markdown_relpath(image_path, target.parent)
        lines.append(f"- Primary diagram asset: [{image_path.name}]({rel})")
    if external_links:
        lines.append("- External artifacts:")
        for link in external_links:
            lines.append(f"  - [{link.text or link.url}]({link.url})")
    lines.append("")
    if description:
        lines.extend(["## Description", "", description, ""])
    if chunks:
        lines.append("## Extracted Text")
        lines.append("")
        for chunk in chunks:
            lines.append(chunk)
            lines.append("")
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def write_external_markdown(
    artifact_type: str,
    artifact_url: str,
    title: str,
    description: str,
    image_path: Path | None,
    page_refs: list[str],
    doc_text: str | None = None,
) -> Path:
    slug = title_to_slug(title or artifact_url)
    target = EXTERNAL_ROOT / artifact_type / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title or artifact_url}", ""]
    lines.append(f"- Source: [{artifact_url}]({artifact_url})")
    lines.append(f"- Type: `{artifact_type}`")
    if description:
        lines.append(f"- Summary: {description}")
    if image_path:
        rel = markdown_relpath(image_path, target.parent)
        lines.append(f"- Preview asset: [{image_path.name}]({rel})")
    brief = ARTIFACT_BRIEFS.get(artifact_url, {})
    effective_description = str(brief.get("description") or description).strip()
    key_pages = select_key_pages(page_refs, brief)
    if key_pages:
        lines.append("- Key related pages:")
        for page_ref in key_pages:
            lines.append(f"  - [{page_ref}]({page_ref})")
    if page_refs:
        lines.append(f"- Referenced from archived pages: {len(sorted(set(page_refs)))}")
    lines.append("")
    if effective_description:
        lines.extend(["## Description", "", effective_description, ""])
    covers = [str(item) for item in brief.get("covers", [])]
    if covers:
        lines.append("## What The Scheme Covers")
        lines.append("")
        for item in covers:
            lines.append(f"- {item}")
        lines.append("")
    usage = [str(item) for item in brief.get("usage", [])]
    if usage:
        lines.append("## How To Use")
        lines.append("")
        for item in usage:
            lines.append(f"- {item}")
        lines.append("")
    if doc_text:
        lines.extend(["## Exported Text", "", doc_text.strip(), ""])
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def select_key_pages(page_refs: list[str], brief: dict[str, object]) -> list[str]:
    unique_refs = sorted(set(page_refs))
    preferred = [str(item) for item in brief.get("key_pages", [])]
    if not preferred:
        return unique_refs[:6]
    preferred_set = set(preferred)
    selected = [page_ref for page_ref in unique_refs if any(page_ref.endswith(suffix) for suffix in preferred_set)]
    if selected:
        return selected
    return unique_refs[:6]


def group_name(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    if not path:
        return "root"
    return path.split("/", 1)[0]


def asset_path_for_page(url: str, image_url: str) -> Path:
    slug = page_slug(url)
    suffix = safe_asset_suffix(image_url, None)
    return ASSETS_ROOT / "pages" / f"{slug}{suffix}"


def asset_path_for_external(artifact_type: str, title: str, image_url: str) -> Path:
    suffix = safe_asset_suffix(image_url, None)
    return ASSETS_ROOT / "external" / artifact_type / f"{title_to_slug(title)}{suffix}"


def archive() -> None:
    ensure_dirs()

    sitemap_urls = parse_sitemap(fetch_text(SITEMAP_URL))
    page_records: list[dict[str, object]] = []
    external_records: dict[str, dict[str, object]] = {}

    for index, page_url in enumerate(sitemap_urls, start=1):
        print(f"[page {index}/{len(sitemap_urls)}] {page_url}")
        html_text = fetch_text(page_url)
        parser = ProductPageParser(page_url)
        parser.feed(html_text)

        title = parser.meta.get("og:title") or parser.title or page_slug(page_url)
        description = parser.meta.get("og:description", "")
        primary_image_url = parser.meta.get("og:image")
        chunks = clean_text_chunks(parser.text_chunks, title, description)
        links = filter_links(parser.links)
        external_links: list[LinkRecord] = []
        for link in links:
            artifact_type = resolve_external_type(link.url)
            if not artifact_type:
                continue
            external_links.append(
                LinkRecord(text=link.text, url=canonicalize_external_url(link.url))
            )

        image_path: Path | None = None
        if primary_image_url:
            image_target = asset_path_for_page(page_url, primary_image_url)
            image_path = download_asset(primary_image_url, image_target)

        markdown_path = write_page_markdown(
            page_url=page_url,
            title=title,
            description=description,
            image_path=image_path,
            chunks=chunks,
            external_links=external_links,
        )

        page_records.append(
            {
                "url": page_url,
                "group": group_name(page_url),
                "title": title,
                "description": description,
                "markdown_path": markdown_path.relative_to(REPO_ROOT).as_posix(),
                "asset_path": image_path.relative_to(REPO_ROOT).as_posix() if image_path else None,
                "external_links": [{"text": link.text, "url": link.url} for link in external_links],
                "text_chunks": chunks,
            }
        )

        for link in external_links:
            artifact_type = resolve_external_type(link.url)
            if not artifact_type:
                continue
            canonical_url = canonicalize_external_url(link.url)
            external_records.setdefault(
                canonical_url,
                {
                    "url": canonical_url,
                    "type": artifact_type,
                    "link_text": link.text or link.url,
                    "pages": [],
                },
            )
            external_records[canonical_url]["pages"].append(
                markdown_path.relative_to(REPO_ROOT).as_posix()
            )

    total_artifacts = len(external_records)
    for index, (artifact_url, record) in enumerate(external_records.items(), start=1):
        print(f"[artifact {index}/{total_artifacts}] {artifact_url}")
        artifact_html = fetch_text(artifact_url)
        parser = ProductPageParser(artifact_url)
        parser.feed(artifact_html)
        title = parser.meta.get("og:title") or parser.title or str(record["link_text"])
        description = parser.meta.get("og:description", "")
        primary_image_url = parser.meta.get("og:image")
        image_path: Path | None = None
        if primary_image_url:
            image_target = asset_path_for_external(str(record["type"]), title, primary_image_url)
            image_path = download_asset(primary_image_url, image_target)

        doc_text = None
        if record["type"] == "google-doc":
            doc_text = fetch_google_doc_text(artifact_url)
        elif record["type"] == "google-sheet":
            doc_text = fetch_google_sheet_csv(artifact_url)

        markdown_path = write_external_markdown(
            artifact_type=str(record["type"]),
            artifact_url=artifact_url,
            title=title,
            description=description,
            image_path=image_path,
            page_refs=list(record["pages"]),
            doc_text=doc_text,
        )
        record["title"] = title
        record["description"] = description
        record["markdown_path"] = markdown_path.relative_to(REPO_ROOT).as_posix()
        record["asset_path"] = image_path.relative_to(REPO_ROOT).as_posix() if image_path else None

    grouped_pages: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in page_records:
        grouped_pages[str(record["group"])].append(record)

    index_lines = ["# Product Architecture Framework Archive", ""]
    index_lines.append(f"- Source sitemap: [{SITEMAP_URL}]({SITEMAP_URL})")
    index_lines.append(f"- Pages archived: {len(page_records)}")
    index_lines.append(f"- External artifacts archived: {len(external_records)}")
    index_lines.append("")

    index_lines.append("## Pages")
    index_lines.append("")
    for group in sorted(grouped_pages):
        index_lines.append(f"### {group}")
        index_lines.append("")
        for record in sorted(grouped_pages[group], key=lambda item: str(item["title"])):
            index_lines.append(
                f"- [{record['title']}]({markdown_relpath(REPO_ROOT / str(record['markdown_path']), DOCS_ROOT)})"
            )
        index_lines.append("")

    if external_records:
        index_lines.append("## External Artifacts")
        index_lines.append("")
        for artifact in sorted(external_records.values(), key=lambda item: str(item.get("title", item["url"]))):
            index_lines.append(
                f"- [{artifact.get('title', artifact['url'])}]({markdown_relpath(REPO_ROOT / str(artifact['markdown_path']), DOCS_ROOT)})"
            )
        index_lines.append("")

    (DOCS_ROOT / "index.md").write_text("\n".join(index_lines).rstrip() + "\n", encoding="utf-8")

    payload = {
        "site_root": SITE_ROOT,
        "sitemap_url": SITEMAP_URL,
        "pages": page_records,
        "external_artifacts": sorted(external_records.values(), key=lambda item: str(item["url"])),
    }
    (DATA_ROOT / "catalog.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    archive()
