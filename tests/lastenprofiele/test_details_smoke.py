# tests/lastenprofiele/test_details_smoke.py

import pytest
from dash.testing.application_runners import import_app

@pytest.fixture
def dash_app():
    return import_app("dashboard.app")

def test_details_header_exists(dash_duo, dash_app):
    # Start server and go straight to /details
    dash_duo.start_server(dash_app)
    dash_duo.wait_for_page(f"{dash_duo.server_url}/details", timeout=5)

    # Try to find ALL <h2>s on the page
    headers = dash_duo.find_elements("h2")
    texts = [h.text for h in headers]

    # Print them so pytest log shows what actually got rendered
    print("\n<H2> tags found:", texts)

    assert headers, "❌ No <h2> elements were found on /details – this is why your other tests time out."