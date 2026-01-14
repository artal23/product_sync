# -*- coding: utf-8 -*-
"""
Rate Limiter - Control de tasa de peticiones
Implementa algoritmo Token Bucket para limitar requests por segundo
"""

import time
import threading
import logging

_logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Controlador de tasa de peticiones usando Token Bucket Algorithm
    
    Funcionamiento:
    - Bucket tiene capacidad máxima = rate
    - Se genera 'rate' tokens por segundo
    - Cada petición consume 1 token
    - Si no hay tokens disponibles, se espera
    
    Ejemplo:
        limiter = RateLimiter(rate=10)  # 10 peticiones/segundo
        for i in range(100):
            limiter.wait_if_needed()  # Espera si es necesario
            make_api_call()
    """
    
    def __init__(self, rate: int = 10, per_seconds: float = 1.0):
        """
        Inicializa el rate limiter
        
        Args:
            rate: Número de peticiones permitidas
            per_seconds: Ventana de tiempo en segundos
        """
        self.rate = rate
        self.per_seconds = per_seconds
        
        self.tokens = float(rate)
        self.max_tokens = float(rate)
        
        # Timestamp del último refill
        self.last_refill = time.time()
        
        # Lock para thread-safety
        self.lock = threading.Lock()
        
        _logger.info(
            f"RateLimiter initialized: {rate} requests per {per_seconds} seconds"
        )
    
    def _refill_tokens(self):
        """
        Rellena el bucket con tokens según el tiempo transcurrido
        
        Los tokens se generan a una tasa constante:
        tokens_per_second = rate / per_seconds
        """
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calcular tokens a agregar
        tokens_to_add = elapsed * (self.rate / self.per_seconds)
        
        # Actualizar tokens (sin exceder el máximo)
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        
        # Actualizar timestamp
        self.last_refill = now
        
        _logger.debug(f"Tokens refilled: {self.tokens:.2f}/{self.max_tokens}")
    
    def _wait_time(self) -> float:
        """
        Calcula el tiempo de espera necesario para obtener un token
        
        Returns:
            Segundos a esperar (0 si hay tokens disponibles)
        """
        if self.tokens >= 1.0:
            return 0.0
        
        # Calcular cuánto tiempo toma generar 1 token
        time_per_token = self.per_seconds / self.rate
        
        # Calcular tokens faltantes
        tokens_needed = 1.0 - self.tokens
        
        # Tiempo de espera
        wait_time = tokens_needed * time_per_token
        
        return wait_time
    
    def wait_if_needed(self):
        """
        Espera si es necesario para respetar el rate limit
        
        Este método es thread-safe y puede ser llamado concurrentemente
        """
        with self.lock:
            # Rellenar bucket
            self._refill_tokens()
            
            # Calcular tiempo de espera
            wait_time = self._wait_time()
            
            if wait_time > 0:
                _logger.debug(f"Rate limit reached, waiting {wait_time:.3f}s")
                time.sleep(wait_time)
                
                # Refill después de esperar
                self._refill_tokens()
            
            # Consumir un token
            self.tokens -= 1.0
            
            _logger.debug(f"Token consumed, remaining: {self.tokens:.2f}")
    
    def try_acquire(self) -> bool:
        """
        Intenta adquirir un token sin esperar
        
        Returns:
            True si se obtuvo el token, False si no hay tokens disponibles
        """
        with self.lock:
            self._refill_tokens()
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                _logger.debug(f"Token acquired, remaining: {self.tokens:.2f}")
                return True
            
            _logger.debug("No tokens available")
            return False
    
    def get_tokens(self) -> float:
        """
        Retorna el número de tokens actualmente disponibles
        
        Returns:
            Número de tokens disponibles
        """
        with self.lock:
            self._refill_tokens()
            return self.tokens
    
    def reset(self):
        """Resetea el rate limiter a su estado inicial"""
        with self.lock:
            self.tokens = self.max_tokens
            self.last_refill = time.time()
            _logger.info("RateLimiter reset")
    
    def __enter__(self):
        """Context manager entry"""
        self.wait_if_needed()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        pass


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate Limiter Adaptativo
    
    Ajusta automáticamente la tasa según las respuestas de la API:
    - Disminuye tasa si detecta 429 (Too Many Requests)
    - Aumenta gradualmente si todo va bien
    """
    
    def __init__(self, rate: int = 10, min_rate: int = 1, max_rate: int = 50):
        """
        Inicializa el rate limiter adaptativo
        
        Args:
            rate: Tasa inicial de peticiones/segundo
            min_rate: Tasa mínima permitida
            max_rate: Tasa máxima permitida
        """
        super().__init__(rate=rate)
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.initial_rate = rate
        
        # Contador de peticiones exitosas consecutivas
        self.success_count = 0
        
        _logger.info(
            f"AdaptiveRateLimiter initialized: "
            f"rate={rate}, range=[{min_rate}, {max_rate}]"
        )
    
    def report_success(self):
        """
        Reporta una petición exitosa
        
        Después de N peticiones exitosas, aumenta la tasa gradualmente
        """
        with self.lock:
            self.success_count += 1
            
            # Cada 10 peticiones exitosas, aumentar tasa en 1
            if self.success_count >= 10:
                old_rate = self.rate
                self.rate = min(self.max_rate, self.rate + 1)
                self.max_tokens = float(self.rate)
                self.success_count = 0
                
                if old_rate != self.rate:
                    _logger.info(f"Rate increased: {old_rate} -> {self.rate}")
    
    def report_rate_limit_error(self):
        """
        Reporta un error 429 (Too Many Requests)
        
        Reduce la tasa a la mitad inmediatamente
        """
        with self.lock:
            old_rate = self.rate
            self.rate = max(self.min_rate, self.rate // 2)
            self.max_tokens = float(self.rate)
            self.success_count = 0
            
            _logger.warning(
                f"Rate limit error detected, reducing rate: {old_rate} -> {self.rate}"
            )
    
    def reset_to_initial(self):
        """Resetea a la tasa inicial"""
        with self.lock:
            self.rate = self.initial_rate
            self.max_tokens = float(self.rate)
            self.tokens = self.max_tokens
            self.success_count = 0
            self.last_refill = time.time()
            
            _logger.info(f"Rate limiter reset to initial rate: {self.rate}")
