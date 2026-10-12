"""RBI Handbook of Statistics: 'Auctions of 91-Day Government of India Treasury Bills'.

Each annual Handbook edition publishes roughly one fiscal year of weekly auctions as
an HTML table on www.rbi.org.in. The edition index is navigated exactly as a browser
does (ASP.NET year postback), then each edition's table page is stored verbatim.
rbidocs.rbi.org.in file downloads are not used: they sit behind a CAPTCHA challenge.
"""

import html
import re

from app.data_pipeline.downloaders.base import (
    DownloadContext,
    DownloadError,
    checked_get,
    checked_post,
    utc_now,
)
from app.data_pipeline.raw_store import RawFile, RawSnapshot
from app.data_pipeline.source_registry import DatasetSpec

_PAGE_URL = "https://www.rbi.org.in/Scripts/PublicationsView.aspx?id={id}"
_HIDDEN_INPUT = re.compile(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', re.I)
_BUTTON = re.compile(r'<input[^>]+name="([^"]+)"[^>]+id="btn"', re.I)


def _link_pattern(title: str) -> re.Pattern[str]:
    return re.compile(
        r"href=PublicationsView\.aspx\?id=(\d+)>\s*(Table\s+\d+\s*:\s*"
        + re.escape(title)
        + r")\s*<",
        re.I,
    )


def _form_fields(page: str) -> dict[str, str]:
    fields = {m.group(1): html.unescape(m.group(2)) for m in _HIDDEN_INPUT.finditer(page)}
    button = _BUTTON.search(page)
    if button:
        fields[button.group(1)] = ""
    return fields


def download_rbi_tbill_auctions(spec: DatasetSpec, ctx: DownloadContext) -> RawSnapshot:
    title = spec.source.expected_name
    years = [y.strip() for y in spec.source.params["edition_years"].split(",") if y.strip()]
    index_url = spec.source.url
    index_page = checked_get(ctx, index_url).text
    if "Handbook of Statistics" not in index_page:
        raise DownloadError("RBI Handbook index page did not load (unexpected content)")

    pattern = _link_pattern(title)
    files: list[RawFile] = []
    editions: list[dict[str, object]] = []
    missing: list[str] = []
    for year in years:
        ctx.pause()
        fields = _form_fields(index_page)
        fields["hdnYear"] = year
        listing = checked_post(ctx, index_url, data=fields).text
        match = pattern.search(listing)
        if not match:
            missing.append(year)
            continue
        page_id = match.group(1)
        ctx.pause()
        page = checked_get(ctx, _PAGE_URL.format(id=page_id)).text
        if title not in page or "Implicit Yield" not in page:
            # e.g. a bot-challenge page served with HTTP 200
            raise DownloadError(f"RBI table page id={page_id} did not contain the expected table")
        files.append(RawFile(f"rbi_hbs_{year}_pv{page_id}.html", page.encode("utf-8")))
        editions.append(
            {
                "edition_year": year,
                "page_id": page_id,
                "table": match.group(2),
                "url": _PAGE_URL.format(id=page_id),
            }
        )
    if not files:
        raise DownloadError("No RBI Handbook edition of the 91-day T-bill table was found")
    return RawSnapshot(
        dataset_id=spec.dataset_id,
        source_kind=spec.source.kind.value,
        retrieved_at=utc_now(),
        files=files,
        request={"index_url": index_url, "edition_years": years, "table_title": title},
        source_metadata={"editions": editions, "missing_editions": missing},
    )
