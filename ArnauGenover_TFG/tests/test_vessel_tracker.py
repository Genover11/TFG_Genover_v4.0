# tests/test_vessel_tracker.py
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from ship_broker.core.vessel_tracker import VesselTracker
from ship_broker.core.matcher import CargoMatcher

@pytest.fixture
def sample_html():
    return """
    <div class="ship-list-row">
        <a class="ship-name">Test Vessel</a>
        <div class="ship-type">Bulk Carrier</div>
        <div class="ship-details">50000 DWT</div>
        <span class="ship-position">Rotterdam</span>
        <div class="ship-eta">2024-12-25 14:00</div>
    </div>
    """

@pytest.fixture
def mock_tracker():
    return VesselTracker(api_key="test_key")

@pytest.fixture
def mock_cargo():
    return Mock(
        id=1,
        cargo_type="IRON ORE",
        quantity=45000,
        load_port="Rotterdam",
        laycan_start=datetime(2024, 12, 26)
    )

def test_vessel_extraction(mock_tracker, sample_html):
    vessels = mock_tracker._extract_vessel_data(sample_html)
    assert len(vessels) == 1
    vessel = vessels[0]
    assert vessel['name'] == "Test Vessel"
    assert vessel['dwt'] == 50000.0
    assert vessel['position'] == "Rotterdam"

@patch('requests.get')
def test_port_scraping(mock_get, mock_tracker, sample_html):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = sample_html
    mock_get.return_value = mock_response

    vessels = mock_tracker.get_vessels_in_port("Rotterdam")
    assert len(vessels) == 1
    assert mock_get.called

def test_vessel_matching(mock_tracker, mock_cargo):
    # Mock vessel data
    vessels = [{
        'name': 'Test Vessel',
        'dwt': 50000,
        'position': 'Rotterdam',
        'eta': datetime(2024, 12, 25, 14, 0)
    }]

    # Mock the tracker
    mock_tracker.get_vessels_in_port = Mock(return_value=vessels)

    # Create matcher with mocked db and tracker
    matcher = CargoMatcher(Mock(), mock_tracker)
    matches = matcher.find_vessels_for_cargo(1)

    assert len(matches) == 1
    assert matches[0]['vessel']['name'] == 'Test Vessel'
    assert matches[0]['score'] > 0.5

def test_no_suitable_vessels(mock_tracker, mock_cargo):
    # Mock empty vessel data
    mock_tracker.get_vessels_in_port = Mock(return_value=[])

    matcher = CargoMatcher(Mock(), mock_tracker)
    matches = matcher.find_vessels_for_cargo(1)

    assert len(matches) == 0

@pytest.mark.asyncio
async def test_api_endpoint(test_client, mock_db):
    # Mock database and vessel tracker
    mock_db.query.return_value.filter.return_value.first.return_value = mock_cargo
    
    response = await test_client.get("/api/v1/match/cargo/1/vessels")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)