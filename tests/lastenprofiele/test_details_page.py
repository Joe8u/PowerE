import pytest
from dash.testing.application_runners import import_app


@pytest.fixture
def dash_app():
    """Import and return the Dash app."""
    return import_app("dashboard.app")


def go_to_details(dash_duo):
    # 1) Wait for the summary page’s header to appear (client-side hydration)
    dash_duo.wait_for_element("h2", timeout=10)

    # 2) Click the Details nav-link (client-side router)
    link = dash_duo.find_element("a.nav-link[href='/details']")
    link.click()

    # 3) Finally wait for the Details page header
    return dash_duo.wait_for_element("h2", timeout=10)


def test_details_layout_smoke(dash_duo, dash_app):
    """Smoke‐test that the Details page layout renders its static controls."""
    dash_duo.start_server(dash_app)
    header = go_to_details(dash_duo)
    assert header.text.startswith("Detail-Analyse")

    # Static controls
    assert dash_duo.find_element("#appliance-dropdown")
    assert dash_duo.find_element("#date-picker")
    assert dash_duo.find_element("#time-series-graph")


def test_details_callback_updates_graph(dash_duo, dash_app):
    """Verify that changing the dropdown triggers the time-series callback."""
    dash_duo.start_server(dash_app)
    go_to_details(dash_duo)

    # Trigger the callback by selecting the 2nd appliance
    dash_duo.select_dcc_dropdown("#appliance-dropdown", index=1)

    # Wait for the Plotly figure to render
    plot = dash_duo.wait_for_element(".js-plotly-plot", timeout=10)
    assert "plotly" in plot.get_attribute("class")


def test_nav_to_details_uses_client_router(dash_duo, dash_app):
    """Ensure that we’re using the client‐side router to navigate to Details."""
    dash_duo.start_server(dash_app)

    # Wait for summary to load, then click into Details
    dash_duo.wait_for_element("h2", timeout=10)
    nav = dash_duo.find_element("a.nav-link[href='/details']")
    nav.click()

    # Should immediately render the Details header without a full reload
    header = dash_duo.wait_for_element("h2", timeout=5)
    assert header.text.startswith("Detail-Analyse")