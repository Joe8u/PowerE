# tests/lastenprofiele/test_details_dump_source.py

import pytest
from dash.testing.application_runners import import_app

@pytest.fixture
def dash_app():
    return import_app("dashboard.app")

def test_dump_details_page_source(dash_duo, dash_app, tmp_path):
    """Fetch /details and write the full HTML to a file so you can inspect it."""
    dash_duo.start_server(dash_app)
    dash_duo.wait_for_page(f"{dash_duo.server_url}/details", timeout=5)

    page_source = dash_duo.driver.page_source
    out_file = tmp_path / "details.html"
    out_file.write_text(page_source, encoding="utf-8")

    pytest.skip(f"Page source dumped to {out_file}")