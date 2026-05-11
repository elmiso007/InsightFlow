import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path
import configparser

# Adicionar o diretório do script ao path
sys.path.insert(0, str(Path(__file__).parent))

from api import load_config, get_user, scalarize, clean_str

class TestLoadConfig:
    @patch('api.configparser.ConfigParser')
    def test_load_config_success(self, mock_config_parser):
        mock_config = MagicMock()
        mock_config.get.return_value = 'https://api.test.com'
        mock_config.getboolean.return_value = True
        mock_config.getint.return_value = 80
        mock_config_parser.return_value = mock_config

        config = load_config()
        assert config['TRAY_DDL_URL'] == 'https://api.test.com'
        assert config['TRAY_VERIFY_SSL'] is True
        assert config['TIME_WINDOW_MINUTES'] == 80

    @patch('api.configparser.ConfigParser')
    def test_load_config_missing_var(self, mock_config_parser):
        mock_config = MagicMock()
        mock_config.get.side_effect = configparser.NoOptionError('TRAY_DDL_URL', 'DEFAULT')
        mock_config_parser.return_value = mock_config

        with pytest.raises(ValueError, match="Variável TRAY_DDL_URL não definida no config.ini"):
            load_config()

class TestGetUser:
    @patch('api.requests.get')
    def test_get_user_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 123}
        mock_get.return_value = mock_response

        result = get_user('https://api.test.com', 'token', 123)
        assert result == {'id': 123}

    @patch('api.requests.get')
    def test_get_user_no_retry_on_500(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        result = get_user('https://api.test.com', 'token', 123)
        assert result is None
        assert mock_get.call_count == 1

class TestHelpers:
    def test_scalarize_dict(self):
        assert scalarize({'login': 'user'}) == 'user'
        assert scalarize({'value': 123}) == 123
        assert scalarize({'unknown': 'val'}) == 'val'

    def test_scalarize_list(self):
        assert scalarize([1, 2, 3]) == 1

    def test_scalarize_primitive(self):
        assert scalarize('string') == 'string'
        assert scalarize(42) == 42
        assert scalarize(None) is None

    def test_clean_str(self):
        assert clean_str('  test  ') == 'test'
        assert clean_str('') is None
        assert clean_str(None) is None
        assert clean_str('long_string', maxlen=5) == 'long_'