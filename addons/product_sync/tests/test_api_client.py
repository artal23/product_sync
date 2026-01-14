# -*- coding: utf-8 -*-
"""
Tests para APIClient
Verifica reintentos, timeouts y manejo de errores HTTP
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import requests

# Import del módulo
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.api_client import APIClient, APIClientError


class TestAPIClient:
    """Test suite para APIClient"""
    
    def setup_method(self):
        self.base_url = "http://test-api:8000"
        self.client = APIClient(
            base_url=self.base_url,
            timeout=5,
            max_retries=3
        )
    
    def test_initialization(self):
        """Test: Cliente se inicializa correctamente"""
        assert self.client.base_url == self.base_url
        assert self.client.timeout == 5
        assert self.client.max_retries == 3
        assert self.client.session is not None
    
    def test_successful_get_request(self):
        """Test: GET request exitoso"""
        with patch.object(self.client.session, 'request') as mock_request:
            # Mock de respuesta exitosa
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'test'}
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_request.return_value = mock_response
            
            result = self.client.get('/test')
            
            assert result == {'data': 'test'}
            mock_request.assert_called_once()
    
    def test_successful_post_request(self):
        """Test: POST request exitoso"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {'id': 1, 'created': True}
            mock_response.elapsed.total_seconds.return_value = 0.3
            mock_request.return_value = mock_response
            
            data = {'name': 'Test Product'}
            result = self.client.post('/products', data=data)
            
            assert result == {'id': 1, 'created': True}
            mock_request.assert_called_once_with(
                method='POST',
                url=f'{self.base_url}/products',
                timeout=5,
                json=data
            )
    
    def test_retry_on_500_error(self):
        """Test: Reintentos automáticos en error 500"""
        with patch.object(self.client.session, 'request') as mock_request:
            # Primera llamada: 500 error
            # Segunda llamada: 500 error
            # Tercera llamada: 200 OK
            mock_responses = [
                Mock(status_code=500, elapsed=Mock(total_seconds=Mock(return_value=0.1))),
                Mock(status_code=500, elapsed=Mock(total_seconds=Mock(return_value=0.1))),
                Mock(status_code=200, json=Mock(return_value={'success': True}), 
                     elapsed=Mock(total_seconds=Mock(return_value=0.1)))
            ]
            mock_request.side_effect = mock_responses
            
            with patch('time.sleep'):  # Mock sleep para no esperar realmente
                result = self.client.get('/test')
            
            assert result == {'success': True}
            assert mock_request.call_count == 3  # 3 intentos
    
    def test_retry_on_429_rate_limit(self):
        """Test: Reintentos en rate limit (429)"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_responses = [
                Mock(status_code=429, elapsed=Mock(total_seconds=Mock(return_value=0.1))),
                Mock(status_code=200, json=Mock(return_value={'data': 'ok'}),
                     elapsed=Mock(total_seconds=Mock(return_value=0.1)))
            ]
            mock_request.side_effect = mock_responses
            
            with patch('time.sleep'):
                result = self.client.get('/test')
            
            assert result == {'data': 'ok'}
            assert mock_request.call_count == 2
    
    def test_no_retry_on_400_error(self):
        """Test: NO reintenta en errores 4xx (excepto 429)"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_request.return_value = mock_response
            
            with pytest.raises(APIClientError) as exc_info:
                self.client.get('/test')
            
            assert 'Client error: 400' in str(exc_info.value)
            assert mock_request.call_count == 1  # Solo 1 intento
    
    def test_max_retries_exceeded(self):
        """Test: Falla después de max_retries"""
        with patch.object(self.client.session, 'request') as mock_request:
            # Todos los intentos fallan con 500
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_request.return_value = mock_response
            
            with patch('time.sleep'):
                with pytest.raises(APIClientError) as exc_info:
                    self.client.get('/test')
            
            assert 'Request failed after 3 attempts' in str(exc_info.value)
            assert mock_request.call_count == 3
    
    def test_exponential_backoff(self):
        """Test: Backoff exponencial funciona correctamente"""
        client = APIClient(base_url=self.base_url, max_retries=5)
        
        # Verificar cálculo de backoff
        assert client._calculate_backoff(1) == 1   # 2^0
        assert client._calculate_backoff(2) == 2   # 2^1
        assert client._calculate_backoff(3) == 4   # 2^2
        assert client._calculate_backoff(4) == 8   # 2^3
        assert client._calculate_backoff(5) == 16  # 2^4
        
        # Máximo es 60 segundos
        assert client._calculate_backoff(10) == 60
    
    def test_timeout_handling(self):
        """Test: Manejo de timeout"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout("Timeout")
            
            with patch('time.sleep'):
                with pytest.raises(APIClientError) as exc_info:
                    self.client.get('/test')
            
            assert 'Request failed after 3 attempts' in str(exc_info.value)
    
    def test_connection_error_handling(self):
        """Test: Manejo de error de conexión"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")
            
            with patch('time.sleep'):
                with pytest.raises(APIClientError) as exc_info:
                    self.client.get('/test')
            
            assert mock_request.call_count == 3  # Reintenta
    
    def test_health_check_success(self):
        """Test: Health check exitoso"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'healthy'}
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_request.return_value = mock_response
            
            result = self.client.health_check()
            
            assert result is True
    
    def test_health_check_failure(self):
        """Test: Health check falla"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError()
            
            result = self.client.health_check()
            
            assert result is False
    
    def test_patch_request(self):
        """Test: PATCH request"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'updated': True}
            mock_response.elapsed.total_seconds.return_value = 0.2
            mock_request.return_value = mock_response
            
            result = self.client.patch('/products/1', data={'price': 99.99})
            
            assert result == {'updated': True}
    
    def test_delete_request(self):
        """Test: DELETE request"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 204  # No Content
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_request.return_value = mock_response
            
            result = self.client.delete('/products/1')
            
            assert result is None  # 204 retorna None
    
    def test_invalid_json_response(self):
        """Test: Manejo de respuesta JSON inválida"""
        with patch.object(self.client.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_request.return_value = mock_response
            
            result = self.client.get('/test')
            
            assert result is None  


if __name__ == '__main__':
    pytest.main([__file__, '-v'])