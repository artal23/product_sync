# -*- coding: utf-8 -*-
"""
Cliente HTTP para comunicación con API externa
Incluye reintentos con backoff exponencial y manejo robusto de errores
"""

import requests
import time
import logging
from typing import Optional, Dict, Any

_logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Excepción personalizada para errores del cliente API"""
    pass


class APIClient:
    """
    Cliente HTTP robusto para comunicación con API externa
    
    Características:
    - Reintentos automáticos con backoff exponencial
    - Timeout configurable
    - Logging estructurado
    - Manejo de errores HTTP
    """
    
    def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 5):
        """
        Inicializa el cliente API
        
        Args:
            base_url: URL base de la API (ej: http://mock-api:8000)
            timeout: Timeout en segundos para cada petición
            max_retries: Número máximo de reintentos
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Headers por defecto
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Odoo-ProductSync/1.0',
        })
        
        _logger.info(f"APIClient initialized: {base_url} (timeout={timeout}s, retries={max_retries})")
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calcula tiempo de espera con backoff exponencial
        
        Args:
            attempt: Número de intento actual (1-based)
            
        Returns:
            Segundos a esperar antes del siguiente intento
        """
        # Backoff exponencial: 2^(attempt-1) segundos
        # Intento 1: 1s, Intento 2: 2s, Intento 3: 4s, Intento 4: 8s, etc.
        base_delay = 2 ** (attempt - 1)
        
        # Máximo 60 segundos de espera
        return min(base_delay, 60)
    
    def _should_retry(self, response: requests.Response, attempt: int) -> bool:
        """
        Determina si se debe reintentar la petición
        
        Args:
            response: Respuesta HTTP recibida
            attempt: Número de intento actual
            
        Returns:
            True si se debe reintentar, False en caso contrario
        """
        # No reintentar si ya alcanzamos el máximo
        if attempt >= self.max_retries:
            return False
        
        # Reintentar en errores del servidor (5xx)
        if 500 <= response.status_code < 600:
            return True
        
        # Reintentar en rate limiting (429)
        if response.status_code == 429:
            return True
        
        # Reintentar en timeout del servidor (408)
        if response.status_code == 408:
            return True
        
        # No reintentar errores del cliente (4xx excepto 429)
        return False
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Realiza una petición HTTP con reintentos
        
        Args:
            method: Método HTTP (GET, POST, PATCH, DELETE)
            endpoint: Endpoint de la API (ej: /products)
            **kwargs: Argumentos adicionales para requests (params, json, etc.)
            
        Returns:
            Diccionario con la respuesta JSON o None si falla
            
        Raises:
            APIClientError: Si la petición falla después de todos los reintentos
        """
        url = f"{self.base_url}{endpoint}"
        attempt = 0
        last_exception = None
        
        while attempt < self.max_retries:
            attempt += 1
            
            try:
                _logger.debug(f"[Attempt {attempt}/{self.max_retries}] {method} {url}")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Log de respuesta
                _logger.debug(
                    f"Response: {response.status_code} "
                    f"(time: {response.elapsed.total_seconds():.2f}s)"
                )
                
                # Manejar respuestas exitosas (2xx)
                if 200 <= response.status_code < 300:
                    try:
                        return response.json()
                    except ValueError:
                        # Si no hay JSON, retornar None para status 204 (No Content)
                        if response.status_code == 204:
                            return None
                        _logger.warning(f"Invalid JSON response from {url}")
                        return None
                
                # Verificar si debemos reintentar
                if self._should_retry(response, attempt):
                    backoff = self._calculate_backoff(attempt)
                    
                    _logger.warning(
                        f"Request failed with status {response.status_code}, "
                        f"retrying in {backoff}s... (attempt {attempt}/{self.max_retries})"
                    )
                    
                    time.sleep(backoff)
                    continue
                
                # Error del cliente (4xx) - no reintentar
                error_msg = f"Client error: {response.status_code} - {response.text}"
                _logger.error(error_msg)
                raise APIClientError(error_msg)
            
            except requests.exceptions.Timeout as e:
                last_exception = e
                _logger.warning(f"Request timeout, retrying... (attempt {attempt}/{self.max_retries})")
                
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                    continue
            
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                _logger.warning(
                    f"Connection error, retrying... (attempt {attempt}/{self.max_retries})"
                )
                
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                    continue
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                _logger.error(f"Request exception: {str(e)}")
                
                if attempt < self.max_retries:
                    backoff = self._calculate_backoff(attempt)
                    time.sleep(backoff)
                    continue
        
        # Si llegamos aquí, todos los reintentos fallaron
        error_msg = f"Request failed after {self.max_retries} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"
        
        _logger.error(error_msg)
        raise APIClientError(error_msg)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Realiza petición GET
        
        Args:
            endpoint: Endpoint de la API
            params: Parámetros de query string
            
        Returns:
            Respuesta JSON
        """
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Realiza petición POST
        
        Args:
            endpoint: Endpoint de la API
            data: Datos a enviar como JSON
            
        Returns:
            Respuesta JSON
        """
        return self._make_request('POST', endpoint, json=data)
    
    def patch(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Realiza petición PATCH
        
        Args:
            endpoint: Endpoint de la API
            data: Datos a actualizar como JSON
            
        Returns:
            Respuesta JSON
        """
        return self._make_request('PATCH', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Realiza petición DELETE
        
        Args:
            endpoint: Endpoint de la API
            
        Returns:
            Respuesta JSON
        """
        return self._make_request('DELETE', endpoint)
    
    def health_check(self) -> bool:
        """
        Verifica que la API esté disponible
        
        Returns:
            True si la API responde correctamente
        """
        try:
            response = self.get('/health')
            return response is not None and response.get('status') == 'healthy'
        except APIClientError:
            return False
    
    def close(self):
        """Cierra la sesión HTTP"""
        self.session.close()
        _logger.info("APIClient session closed")
