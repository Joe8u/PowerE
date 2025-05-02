import datetime
import dash
import pytest
from dash.testing.application_runners import import_app
from plotly.graph_objs import Figure

# Fixture to spin up the Dash app
@pytest.fixture
def dash_app():
    return import_app("dashboard.app")

# Test the Details page layout and callback functionality
def test_details_layout_and_callback(dash_duo, dash_app):
    # Start the Dash app server
    dash_duo.start_server(dash_app)

    # Navigate to the Details page
        # instead build the full URL for the details page
    # Click on the "Details" nav link so that Dash's client-side router loads it
    nav_details = dash_duo.find_element("a[href='/details']")
    nav_details.click()
    # now wait for your Details page's <h2> to appear
    dash_duo.wait_for_element("h2", timeout=10)

    # Wait for the header to appear and verify its text
    header = dash_duo.wait_for_element("h2", timeout=20)
    assert "Detail-Analyse" in header.text

    # Verify the appliance dropdown exists
    dropdown = dash_duo.find_element("#appliance-dropdown")
    assert dropdown is not None

    # Verify the date picker range component exists
    datepicker = dash_duo.find_element("#date-picker")
    assert datepicker is not None

    # Verify the graph component exists
    graph = dash_duo.find_element("#time-series-graph")
    assert graph is not None

    # Trigger the callback by selecting an appliance
    dash_duo.select_dcc_dropdown("#appliance-dropdown", option_index=1)

    # Wait for the Plotly figure to render
    plot = dash_duo.wait_for_element(".js-plotly-plot", timeout=10)
    assert "plotly" in plot.get_attribute("class")
