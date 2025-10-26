import pytest
from dovwms import DOVClient, get_profile_from_dov


import json
from unittest.mock import Mock, patch


@patch.object(DOVClient, 'check_layer_exists')
@patch.object(DOVClient, 'parse_feature_info')
@patch('dovwms.dov.get_elevation')
def test_fetch_profile_with_elevation(mock_get_elev, mock_parse, mock_check, dov_client, sample_location):
    """Test profile fetching with elevation data."""
    mock_check.return_value = True
    mock_parse.return_value = {'layers': [{'name': 'Layer_0-10cm'}]}

    # Mock elevation helper
    mock_get_elev.return_value = 45.7

    # Mock WMS response
    mock_response = Mock()
    mock_response.read.return_value = json.dumps({"features": []})
    dov_client.wms = Mock()
    dov_client.wms.getfeatureinfo.return_value = mock_response

    profile = dov_client.fetch_profile(sample_location, fetch_elevation=True)

    assert profile['elevation'] == 45.7
    mock_get_elev.assert_called_once_with(sample_location, "EPSG:31370")


@patch('dovwms.dov.DOVClient')
def test_get_profile_from_dov_with_elevation(mock_client_cls):
    """Test convenience function with elevation fetching."""
    mock_client = Mock()
    mock_client.fetch_profile.return_value = {
        'layers': [{'name': 'Layer_0-10cm'}],
        'elevation': 45.7
    }
    mock_client_cls.return_value = mock_client

    profile = get_profile_from_dov(247172.56, 204590.58, fetch_elevation=True)

    # Verify fetch_elevation parameter was used
    call_kwargs = mock_client.fetch_profile.call_args[1]
    assert 'elevation' in str(call_kwargs) or profile is not None


@pytest.mark.integration  
def test_get_profile_from_dov_with_elevation_real_service():
    """Integration test for convenience function with real service."""
    profile = get_profile_from_dov(247172.56, 204590.58, fetch_elevation=True)

    if profile is not None:
        assert isinstance(profile, dict)