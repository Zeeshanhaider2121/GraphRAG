"""Document enrichment: chapter detection, section extraction, formula parsing."""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import mistune

# Try to import optional libraries
try:
    from pylatexenc.latex2text import LatexNodes2Text
    PYLATEXENC_AVAILABLE = True
    latex_converter = LatexNodes2Text()
except ImportError:
    PYLATEXENC_AVAILABLE = False
    latex_converter = None

try:
    from TexSoup import TexSoup
    TEXSOUP_AVAILABLE = True
except ImportError:
    TEXSOUP_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════
# Unicode Subscript / Superscript Maps
# ══════════════════════════════════════════════════════════════════════════

SUBSCRIPT_MAP: Dict[str, str] = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'h': 'ₕ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ',
    's': 'ₛ', 't': 'ₜ', 'i': 'ᵢ', 'j': 'ⱼ', 'r': 'ᵣ',
    'u': 'ᵤ', 'v': 'ᵥ',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
}

SUPERSCRIPT_MAP: Dict[str, str] = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
}

GREEK_MAP: Dict[str, str] = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\epsilon': 'ε', r'\varepsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η',
    r'\theta': 'θ', r'\vartheta': 'ϑ', r'\iota': 'ι', r'\kappa': 'κ',
    r'\lambda': 'λ', r'\mu': 'μ', r'\nu': 'ν', r'\xi': 'ξ',
    r'\pi': 'π', r'\varpi': 'ϖ', r'\rho': 'ρ', r'\varrho': 'ϱ',
    r'\sigma': 'σ', r'\varsigma': 'ς', r'\tau': 'τ', r'\upsilon': 'υ',
    r'\phi': 'φ', r'\varphi': 'φ', r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    r'\Gamma': 'Γ', r'\Delta': 'Δ', r'\Theta': 'Θ', r'\Lambda': 'Λ',
    r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Sigma': 'Σ', r'\Upsilon': 'Υ',
    r'\Phi': 'Φ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
}

OPERATOR_MAP: Dict[str, str] = {
    r'\leq': '≤', r'\geq': '≥', r'\le': '≤', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\sim': '∼',
    r'\equiv': '≡', r'\cong': '≅', r'\propto': '∝', r'\simeq': '≃',
    r'\times': '×', r'\cdot': '·', r'\div': '÷', r'\pm': '±', r'\mp': '∓',
    r'\infty': '∞', r'\partial': '∂', r'\nabla': '∇',
    r'\sum': 'Σ', r'\prod': 'Π', r'\int': '∫',
    r'\sqrt': '√', r'\ldots': '…', r'\cdots': '⋯',
    r'\rightarrow': '→', r'\leftarrow': '←', r'\leftrightarrow': '↔',
    r'\Rightarrow': '⇒', r'\Leftarrow': '⇐', r'\Leftrightarrow': '⇔',
    r'\forall': '∀', r'\exists': '∃', r'\in': '∈', r'\notin': '∉',
    r'\subset': '⊂', r'\supset': '⊃', r'\cup': '∪', r'\cap': '∩',
    r'\emptyset': '∅', r'\varnothing': '∅',
    r'\perp': '⊥', r'\parallel': '∥', r'\angle': '∠',
    r'\degree': '°', r'\circ': '°',
}

# ── Helpers ────────────────────────────────────────────────────────────

def to_subscript(s: str) -> str:
    return ''.join(SUBSCRIPT_MAP.get(c, c) for c in s)

def to_superscript(s: str) -> str:
    return ''.join(SUPERSCRIPT_MAP.get(c, c) for c in s)

def strip_font_commands(s: str) -> str:
    font_cmds = (
        r'\\mathrm', r'\\mathbf', r'\\mathit', r'\\mathsf', r'\\mathtt',
        r'\\text', r'\\textbf', r'\\textit', r'\\textrm', r'\\textsf',
        r'\\texttt', r'\\boldsymbol', r'\\bm', r'\\mathcal', r'\\mathbb',
        r'\\operatorname', r'\\mbox',
    )
    pattern = r'(?:' + '|'.join(font_cmds) + r')\s*\{([^{}]*)\}'
    prev = None
    while prev != s:
        prev = s
        s = re.sub(pattern, r'\1', s)
    return s

def parse_braced(s: str, pos: int) -> Tuple[str, int]:
    if pos >= len(s) or s[pos] != '{':
        if pos < len(s):
            return s[pos], pos + 1
        return '', pos
    depth = 0
    start = pos + 1
    i = pos
    while i < len(s):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    return s[start:], len(s)

def latex_subscript_superscript(latex: str) -> str:
    result = []
    i = 0
    while i < len(latex):
        c = latex[i]
        if c == '_':
            i += 1
            while i < len(latex) and latex[i] == ' ':
                i += 1
            if i >= len(latex):
                result.append('_')
                break
            content, i = parse_braced(latex, i)
            content = strip_font_commands(content)
            result.append(to_subscript(content))
        elif c == '^':
            i += 1
            while i < len(latex) and latex[i] == ' ':
                i += 1
            if i >= len(latex):
                result.append('^')
                break
            content, i = parse_braced(latex, i)
            content = strip_font_commands(content)
            result.append(to_superscript(content))
        else:
            result.append(c)
            i += 1
    return ''.join(result)

def convert_latex_to_unicode(latex: str) -> str:
    latex = re.sub(r'^\$\$?|\$\$?$|^\\\[|\\\]$', '', latex).strip()
    frac_pattern = r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}'
    latex = re.sub(frac_pattern, r'(\1/\2)', latex)
    latex = strip_font_commands(latex)
    for cmd, char in GREEK_MAP.items():
        latex = latex.replace(cmd, char)
    for cmd, char in OPERATOR_MAP.items():
        latex = latex.replace(cmd, char)
    latex = latex_subscript_superscript(latex)
    latex = re.sub(r'\\([a-zA-Z]+)', r'\1', latex)
    latex = re.sub(r'\s+', ' ', latex)
    latex = re.sub(r'[{}]', '', latex)
    return latex.strip()

def clean_markdown_latex(markdown: str) -> str:
    def replace_display_with_tag(match):
        content = match.group(1)
        tag = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        cleaned = convert_latex_to_unicode(content)
        return f"{cleaned} ({tag})" if tag else cleaned

    markdown = re.sub(
        r'\$\$(.+?)\s*\\tag\{([^}]+)\}\s*\$\$',
        replace_display_with_tag,
        markdown,
        flags=re.DOTALL
    )
    markdown = re.sub(
        r'\$\$(.+?)\$\$',
        lambda m: convert_latex_to_unicode(m.group(1)),
        markdown,
        flags=re.DOTALL
    )
    markdown = re.sub(
        r'\$(.+?)\$',
        lambda m: convert_latex_to_unicode(m.group(1)),
        markdown
    )
    return markdown

def extract_tag_from_formula_soup(latex: str) -> Optional[str]:
    if not TEXSOUP_AVAILABLE:
        return None
    try:
        parsed = TexSoup(latex)
        for cmd in parsed.find_all('tag'):
            return str(cmd.args[0]).strip() if cmd.args else None
    except Exception:
        return None

def extract_tag_from_formula_regex(latex: str) -> Optional[str]:
    match = re.search(r'\\tag\s*\{([^}]+)\}', latex)
    return match.group(1).strip() if match else None

def extract_tag_from_formula(latex: str) -> Optional[str]:
    tag = extract_tag_from_formula_soup(latex)
    if tag is None:
        tag = extract_tag_from_formula_regex(latex)
    return tag

def extract_formulas_with_conversion(markdown: str) -> List[Dict]:
    formulas = []
    for match in re.finditer(r'\$\$(.+?)\$\$', markdown, re.DOTALL):
        latex = match.group(1).strip()
        tag = extract_tag_from_formula(latex)
        plain_text = latex_converter.latex_to_text(latex) if PYLATEXENC_AVAILABLE else latex
        formulas.append({'latex': latex, 'plain_text': plain_text, 'tag': tag})
    for match in re.finditer(r'\$(.+?)\$', markdown):
        latex = match.group(1).strip()
        plain_text = latex_converter.latex_to_text(latex) if PYLATEXENC_AVAILABLE else latex
        formulas.append({'latex': latex, 'plain_text': plain_text, 'tag': None})
    return formulas

def parse_number_title(raw_text: str) -> Tuple[Optional[str], str]:
    match = re.match(r'^([\d.]+)\s+(.+)$', raw_text.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return None, raw_text.strip()

def normalize_header(h: str) -> str:
    return " ".join(h.strip().lower().split())

# ── Section/chapter detection helpers (from final_json.py) ──────────────

BOOK_TITLE_PATTERNS = ["handbuch eurocode", "normen-handbuch", "handbook", "manual", "normen-download"]
FRONT_MATTER_KW = {"vorwort", "vorwort en", "nationales vorwort", "inhalt", "einführung", "benutzerhinweise",
                   "preface", "foreword", "contents", "introduction"}
IGNORE_PATTERNS = re.compile(
    r"leerseite|blank page|vorteils-code|dieser titel steht|^\s*$|"
    r"^(january|february|march|april|may|june|july|august|september|oktober|november|december|"
    r"januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\s+\d{4}$|"
    r"^bauwesen\b|^din\s*$", re.IGNORECASE)
APPENDIX_PATTERN = re.compile(r"^(a\s+)?(anhang|appendix|annex)\s+[a-z]+", re.IGNORECASE)

def classify_header(header: str) -> str:
    raw = header.strip()
    if not raw or IGNORE_PATTERNS.search(raw):
        return "ignore"
    normalized = normalize_header(raw)
    if any(kw in normalized for kw in BOOK_TITLE_PATTERNS):
        return "book_title"
    if normalized in FRONT_MATTER_KW or any(kw in normalized for kw in ["vorwort", "inhalt", "preface", "contents"]):
        return "front_matter"
    if APPENDIX_PATTERN.match(raw):
        return "appendix"
    if re.match(r"^\d{2,3}\s*$", raw):
        return "book_title"
    return "chapter"

def is_likely_repeating_norm_header(header: str, current_chapter: str) -> bool:
    if not header or not current_chapter:
        return False
    norm = normalize_header(header)
    curr = normalize_header(current_chapter)
    if len(set(norm.split()) & set(curr.split())) >= 2:
        return True
    if re.compile(r'\b(din|en|iso|astm|bs|ansi|jis|gb)\b.*?\b\d{3,5}\b', re.IGNORECASE).search(header):
        return True
    return False

def extract_book_title_generic(header: str) -> Optional[str]:
    if not header:
        return None
    normalized = header.strip().upper()
    patterns = [
        r'(.+?)\s+(?:BAND|VOLUME|VOL\.?|TEIL|PART)\s+\d+',
        r'((?:HANDBUCH|HANDBOOK|MANUAL|NORMEN-HANDBUCH)[^:]+?)(?:\s+BAND|\s+VOLUME|$)',
        r'(.+?)\s+(?:BAND|VOLUME)',
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'\s+\d+$', '', title)
            return title
    if not re.match(r'^\d{2,3}\s*$', normalized):
        parts = normalized.split()
        if parts and len(parts[0]) > 2:
            title_parts = [p for p in parts[:5] if not re.match(r'^\d+$', p)]
            if title_parts:
                return ' '.join(title_parts)
    return None

def extract_band_number_generic(header: str) -> Optional[int]:
    if not header:
        return None
    normalized = header.strip().upper()
    for pattern in [r'BAND\s+(\d+)', r'VOLUME\s+(\d+)', r'VOL\.?\s+(\d+)', r'TEIL\s+(\d+)', r'PART\s+(\d+)']:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))
    return None

class HeaderExtractor:
    def __init__(self):
        self.markdown = mistune.create_markdown(renderer=None)

    def extract_all_headers(self, text: str) -> List[Dict]:
        if not text:
            return []
        try:
            tokens = self.markdown(text)
        except Exception:
            return []
        headers = []
        self._walk_tokens(tokens, headers)
        return headers

    def _walk_tokens(self, tokens: List, headers: List):
        for token in tokens:
            if token.get('type') == 'heading':
                attrs = token.get('attrs', {})
                level = attrs.get('level', 0)
                children = token.get('children', [])
                raw_text = self._extract_text(children)
                number, title = parse_number_title(raw_text)
                headers.append({'level': level, 'raw_text': raw_text, 'number': number, 'title': title})
            if 'children' in token:
                self._walk_tokens(token['children'], headers)

    def _extract_text(self, tokens: List) -> str:
        parts = []
        for token in tokens:
            if token.get('type') == 'text':
                parts.append(token.get('raw', ''))
            elif 'children' in token:
                parts.append(self._extract_text(token['children']))
        return ''.join(parts).strip()

def verify_main_chapter_against_header(chapter_title: str, running_header: str) -> bool:
    if not chapter_title or not running_header:
        return False
    norm_title = normalize_header(chapter_title)
    norm_header = normalize_header(running_header)
    if norm_title == norm_header or norm_title in norm_header or norm_header in norm_title:
        return True
    stop_words = {'der', 'die', 'das', 'und', 'von', 'für', 'im', 'an', 'auf', 'the', 'and', 'of', 'in', 'on'}
    common = (set(norm_title.split()) & set(norm_header.split())) - stop_words
    return len(common) >= 2

def enrich_images_with_captions(markdown: str, images: List[Dict]) -> List[Dict]:
    captions = []
    for match in re.finditer(r'!\[([^\]]*)\]\([^\)]+\)', markdown):
        caption_text = match.group(1).strip()
        if caption_text:
            captions.append(caption_text)
    enriched = []
    for i, img in enumerate(images):
        enriched_img = dict(img)
        if i < len(captions):
            enriched_img['caption'] = captions[i]
        enriched.append(enriched_img)
    return enriched

def extract_section_boundaries(markdown: str, page_index: int) -> List[Dict]:
    boundaries = []
    lines = markdown.split('\n')
    for line_idx, line in enumerate(lines):
        if line.startswith('#'):
            match = re.match(r'^(#+)\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                raw_text = match.group(2).strip()
                number, title = parse_number_title(raw_text)
                boundaries.append({'level': level, 'number': number, 'title': title, 'start_line': line_idx})
                continue
        if re.match(r'^\s*(\d+(?:\.\d+){1,10})\s*$', line):
            number = line.strip()
            boundaries.append({'level': 0, 'number': number, 'title': number, 'start_line': line_idx})
    return boundaries

def extract_sections_with_content(markdown: str, page_index: int,
                                   page_images: List[Dict], page_tables: List[Dict]) -> List[Dict]:
    boundaries = extract_section_boundaries(markdown, page_index)
    if not boundaries:
        return []
    lines = markdown.split('\n')
    sections = []
    for i, boundary in enumerate(boundaries):
        start_line = boundary['start_line']
        if i + 1 < len(boundaries):
            end_line = boundaries[i + 1]['start_line']
        else:
            end_line = len(lines)
        content_lines = lines[start_line + 1:end_line]
        raw_content = '\n'.join(content_lines).strip()
        clean_content = raw_content
        sections.append({
            'level': boundary['level'],
            'number': boundary['number'],
            'title': boundary['title'],
            'start_page': page_index,
            'end_page': page_index,
            'content': clean_content,
            'images': [],
            'tables': [],
        })
    if sections:
        sections[-1]['images'] = page_images or []
        sections[-1]['tables'] = page_tables or []
    return sections

# ══════════════════════════════════════════════════════════════════════════
# Main processing function (from final_json.py)
# ══════════════════════════════════════════════════════════════════════════

def process_document(pages: List[Dict], metadata: Dict) -> Dict:
    header_extractor = HeaderExtractor()
    current_book_title = None
    current_band = 0
    current_chapter = ""
    current_chapter_type = "front_matter"
    chapter_index = []
    active_chapter_entry = None
    enriched_pages = []
    all_sections = []

    for page in pages:
        page_index = page.get('index', 0)
        header = (page.get('header') or '').strip()
        raw_markdown = page.get('markdown') or ''
        page_images = enrich_images_with_captions(raw_markdown, page.get('images', []))
        page_tables = page.get('tables', [])
        clean_md = clean_markdown_latex(raw_markdown)

        book_title = extract_book_title_generic(header)
        if book_title:
            current_book_title = book_title
        band = extract_band_number_generic(header)
        if band:
            current_band = band

        all_headers = header_extractor.extract_all_headers(raw_markdown)
        header_type = classify_header(header)

        main_chapter_headers = [h for h in all_headers if h['level'] == 1]
        detected_main_chapter = False

        if len(main_chapter_headers) == 1:
            main_h = main_chapter_headers[0]
            chapter_title = main_h['title']
            is_verified = verify_main_chapter_against_header(chapter_title, header)
            if is_verified:
                detected_main_chapter = True
                if active_chapter_entry:
                    active_chapter_entry["end_page"] = page_index - 1
                    chapter_index.append(active_chapter_entry)
                if header_type == 'appendix' or APPENDIX_PATTERN.match(chapter_title):
                    chapter_type = "appendix"
                elif header_type == 'front_matter' or any(kw in normalize_header(chapter_title) for kw in FRONT_MATTER_KW):
                    chapter_type = "front_matter"
                else:
                    chapter_type = "main_chapter"
                current_chapter = chapter_title
                current_chapter_type = chapter_type
                active_chapter_entry = {
                    "chapter": chapter_title,
                    "chapter_type": chapter_type,
                    "band": current_band,
                    "start_page": page_index,
                    "end_page": None,
                }

        if not detected_main_chapter:
            if header_type in ("chapter", "appendix", "front_matter"):
                is_repeating = is_likely_repeating_norm_header(header, current_chapter)
                is_different = (normalize_header(header) != normalize_header(current_chapter))
                if not is_repeating and is_different:
                    if active_chapter_entry:
                        active_chapter_entry["end_page"] = page_index - 1
                        chapter_index.append(active_chapter_entry)
                    current_chapter = header
                    current_chapter_type = header_type
                    active_chapter_entry = {
                        "chapter": header,
                        "chapter_type": header_type,
                        "band": current_band,
                        "start_page": page_index,
                        "end_page": None,
                    }

        if active_chapter_entry:
            active_chapter_entry["end_page"] = page_index

        sections = extract_sections_with_content(raw_markdown, page_index, page_images, page_tables)
        page_formulas = extract_formulas_with_conversion(raw_markdown)

        for sec in sections:
            all_sections.append({'section': sec, 'chapter': current_chapter, 'page_index': page_index})

        enriched_pages.append({
            'index': page_index,
            'markdown': clean_md,
            'header': header,
            'book_title': current_book_title,
            'band': current_band,
            'chapter': current_chapter or None,
            'chapter_type': current_chapter_type,
            'sections': sections,
            'formulas': page_formulas,
            'images': page_images,
            'tables': page_tables,
        })

    if active_chapter_entry:
        active_chapter_entry["end_page"] = pages[-1].get("index", 0) if pages else 0
        chapter_index.append(active_chapter_entry)

    # Merge consecutive duplicate chapters
    merged_chapters = []
    i = 0
    while i < len(chapter_index):
        current = chapter_index[i]
        if i + 1 < len(chapter_index):
            next_ch = chapter_index[i + 1]
            if (normalize_header(current['chapter']) == normalize_header(next_ch['chapter'])
                    and current['band'] == next_ch['band']):
                merged_name = next_ch['chapter'] if len(next_ch['chapter']) >= len(current['chapter']) else current['chapter']
                merged_type = ('main_chapter'
                               if current['chapter_type'] == 'main_chapter' or next_ch['chapter_type'] == 'main_chapter'
                               else current['chapter_type'])
                merged_chapters.append({
                    'chapter': merged_name,
                    'chapter_type': merged_type,
                    'band': current['band'],
                    'start_page': current['start_page'],
                    'end_page': next_ch['end_page'],
                })
                i += 2
                continue
        merged_chapters.append(current)
        i += 1
    chapter_index = merged_chapters

    # Refine section end_pages
    chapter_end_map = {c["chapter"]: c["end_page"] for c in chapter_index}
    for idx, entry in enumerate(all_sections):
        section = entry["section"]
        level = section["level"]
        chapter = entry["chapter"]
        end = chapter_end_map.get(chapter, section["start_page"])
        for j in range(idx + 1, len(all_sections)):
            next_entry = all_sections[j]
            if next_entry["chapter"] != chapter:
                break
            if 0 < next_entry["section"]["level"] <= level:
                end = next_entry["page_index"] - 1
                break
        section["end_page"] = max(section["start_page"], end)

    return {
        "metadata": {
            **metadata,
            "book_title": current_book_title,
            "pylatexenc_enabled": PYLATEXENC_AVAILABLE,
            "texsoup_enabled": TEXSOUP_AVAILABLE,
        },
        "chapter_index": chapter_index,
        "pages": enriched_pages,
    }

# ══════════════════════════════════════════════════════════════════════════
# EnrichmentService class
# ══════════════════════════════════════════════════════════════════════════

class EnrichmentService:
    """Service that performs the same logic as final_json.py."""

    def enrich(self, ocr_payload: dict) -> dict:
        pages = ocr_payload.get("pages", [])
        metadata = {
            "model": ocr_payload.get("model"),
            "usage_info": ocr_payload.get("usage_info"),
            "document_annotation": ocr_payload.get("document_annotation"),
        }
        return process_document(pages, metadata)