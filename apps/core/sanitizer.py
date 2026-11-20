"""Санитайзер HTML для защиты от XSS на стандартной библиотеке Python."""

from html.parser import HTMLParser

ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}

ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel", "class"},
    "img": {"src", "alt", "title", "class", "width", "height"},
    "*": {"class", "id"},
}

DISALLOWED_SCHEMES = ("javascript:", "vbscript:", "data:")


class _SafeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result: list[str] = []
        self._skip_tag: bool = False

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in {"script", "style", "iframe", "object", "embed"}:
            self._skip_tag = True
            return

        if tag_lower not in ALLOWED_TAGS:
            return

        safe_attrs = []
        for attr, val in attrs:
            attr_lower = attr.lower()
            if attr_lower.startswith("on"):
                continue

            val_str = (val or "").strip()
            if any(val_str.lower().startswith(s) for s in DISALLOWED_SCHEMES):
                continue

            tag_allowed = ALLOWED_ATTRS.get(tag_lower, set())
            wildcard_allowed = ALLOWED_ATTRS.get("*", set())
            if attr_lower in tag_allowed or attr_lower in wildcard_allowed:
                safe_attrs.append(f'{attr_lower}="{val_str}"')

        attr_str = f" {' '.join(safe_attrs)}" if safe_attrs else ""
        self.result.append(f"<{tag_lower}{attr_str}>")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in {"script", "style", "iframe", "object", "embed"}:
            self._skip_tag = False
            return

        if tag_lower in ALLOWED_TAGS:
            self.result.append(f"</{tag_lower}>")

    def handle_data(self, data):
        if not self._skip_tag:
            self.result.append(data)


def sanitize_html(text: str) -> str:
    """Очищает HTML от опасных тегов (script, iframe, on-обработчики, javascript-схемы)."""
    if not text:
        return ""
    parser = _SafeHTMLParser()
    parser.feed(text)
    return "".join(parser.result)
