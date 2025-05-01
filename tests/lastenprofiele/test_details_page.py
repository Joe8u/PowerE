import datetime
import dash
import pytest
from dash.testing.application_runners import import_app
from plotly.graph_objs import Figure

# fixture to spin up the Dash app
@pytest.fixture
def dash_app():
    app = import_app("dashboard.app").app
    return dash.Dash(__name__, server=app.server, routes_pathname_prefix="/test/")

def test_details_layout_and_callback(dash_duo, dash_app):
    dash_duo.start_server(dash_app)
    dash_duo.wait_for_text("h2", "Detail-Analyse", timeout=5)

    # Dropdown existiert
    dropdown = dash_duo.find_element("#appliance-dropdown")
    assert dropdown is not None

    # DatePicker existiert
    datepicker = dash_duo.find_element("#date-picker")
    assert datepicker is not None

    # Graph existiert
    graph = dash_duo.find_element("#time-series-graph")
    assert graph is not None

    # Callback auslösen: wähle eine Appliance und Datum
    dropdown.send_keys("Computer")
    # Warte auf initiale Figure
    dash_duo.wait_for_element(".js-plotly-plot", timeout=10)
    # Prüfe, dass die Figure Klasse 'plotly' enthält
    assert "plotly" in dash_duo.find_element(".js-plotly-plot").get_attribute("class")