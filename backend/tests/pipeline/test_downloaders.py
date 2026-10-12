"""Downloader failure handling with stubbed HTTP (no network)."""

from datetime import date

import pytest
import requests

from app.data_pipeline.downloaders.base import DownloadContext, DownloadError
from app.data_pipeline.downloaders.fund_nav import download_amfi_nav
from app.data_pipeline.downloaders.risk_free import download_rbi_tbill_auctions
from app.data_pipeline.source_registry import BY_ID


class _Response:
    def __init__(self, text: str, status: int = 200) -> None:
        self.text = text
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class _Session:
    def __init__(self, responses: list[_Response]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}

    def request(self, method: str, url: str, **kwargs) -> _Response:
        if not self.responses:
            raise requests.ConnectionError("no route to host")
        return self.responses.pop(0)


def _ctx(responses: list[_Response]) -> DownloadContext:
    ctx = DownloadContext(date(2024, 1, 1), date(2024, 1, 31), 5, 0, "test")
    ctx._session = _Session(responses)  # type: ignore[assignment]
    return ctx


def test_http_error_is_a_download_failure() -> None:
    with pytest.raises(DownloadError, match="403"):
        download_amfi_nav(BY_ID["GSEC"], _ctx([_Response("Forbidden", 403)]))


def test_network_error_is_a_download_failure() -> None:
    with pytest.raises(DownloadError, match="no route"):
        download_amfi_nav(BY_ID["GSEC"], _ctx([]))


def test_amfi_response_without_header_is_rejected() -> None:
    with pytest.raises(DownloadError, match="no NAV header"):
        download_amfi_nav(BY_ID["GSEC"], _ctx([_Response("<html>maintenance</html>")]))


def test_amfi_response_without_scheme_rows_is_rejected() -> None:
    header = (
        "Scheme Code;NAV Name;Plan;Option;ISIN Div Payout/ISIN Growth;"
        "ISIN Div Reinvestment;Net Asset Value;Date\n"
    )
    with pytest.raises(DownloadError, match="no NAV rows"):
        download_amfi_nav(
            BY_ID["GSEC"], _ctx([_Response(header + "999;Other;;;;;1.0;01-Jan-2024\n")])
        )


def test_rbi_bot_challenge_page_is_not_mistaken_for_data() -> None:
    index = '<html>Handbook of Statistics<input name="__VIEWSTATE" value="x"/></html>'
    listing = (
        '<a class="link2" href=PublicationsView.aspx?id=1>'
        "Table 1 : Auctions of 91-Day Government of India Treasury Bills</a>"
    )
    captcha = (
        "<html>Please enable JavaScript to view the page content. What code is in the image?</html>"
    )
    spec = BY_ID["RF_TBILL_91D"]
    with pytest.raises(DownloadError, match="did not contain the expected table"):
        download_rbi_tbill_auctions(
            spec, _ctx([_Response(index), _Response(listing), _Response(captcha)])
        )
