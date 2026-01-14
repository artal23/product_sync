# -*- coding: utf-8 -*-
"""
Tests para RateLimiter
Verifica control de tasa de peticiones
"""

import pytest
import time
import threading
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.rate_limiter import RateLimiter, AdaptiveRateLimiter


class TestRateLimiter:
    """Test suite para RateLimiter"""
    
    def test_initialization(self):
        """Test: RateLimiter se inicializa correctamente"""
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        
        assert limiter.rate == 10
        assert limiter.per_seconds == 1.0
        assert limiter.tokens == 10.0
        assert limiter.max_tokens == 10.0
    
    def test_single_request_no_wait(self):
        """Test: Primera petición no espera"""
        limiter = RateLimiter(rate=10)
        
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # No debe esperar (< 0.1s de overhead)
        assert elapsed < 0.1
        assert limiter.tokens == 9.0  # Consumió 1 token
    
    def test_rate_limiting_enforced(self):
        """Test: Rate limit es respetado"""
        limiter = RateLimiter(rate=5, per_seconds=1.0)  # 5 req/s
        
        # Consumir todos los tokens
        for _ in range(5):
            limiter.wait_if_needed()
        
        # El 6to request debe esperar
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Debe esperar ~0.2s (tiempo para generar 1 token a 5 tokens/s)
        assert 0.15 < elapsed < 0.3
    
    def test_token_refill(self):
        """Test: Tokens se rellenan con el tiempo"""
        limiter = RateLimiter(rate=10)
        
        # Consumir 5 tokens
        for _ in range(5):
            limiter.wait_if_needed()
        
        assert limiter.tokens == 5.0
        
        # Esperar 0.5 segundos
        time.sleep(0.5)
        
        # Forzar refill
        limiter._refill_tokens()
        
        # Debe tener ~10 tokens (5 restantes + 5 generados)
        assert 9.5 <= limiter.tokens <= 10.0
    
    def test_try_acquire_success(self):
        """Test: try_acquire retorna True cuando hay tokens"""
        limiter = RateLimiter(rate=10)
        
        result = limiter.try_acquire()
        
        assert result is True
        assert limiter.tokens == 9.0
    
    def test_try_acquire_failure(self):
        """Test: try_acquire retorna False cuando NO hay tokens"""
        limiter = RateLimiter(rate=2)
        
        # Consumir todos los tokens
        limiter.try_acquire()
        limiter.try_acquire()
        
        # No debería adquirir
        result = limiter.try_acquire()
        
        assert result is False
    
    def test_get_tokens(self):
        """Test: get_tokens retorna cantidad correcta"""
        limiter = RateLimiter(rate=10)
        
        limiter.wait_if_needed()  # Consume 1
        tokens = limiter.get_tokens()
        
        assert tokens == 9.0
    
    def test_reset(self):
        """Test: Reset restaura tokens a máximo"""
        limiter = RateLimiter(rate=10)
        
        # Consumir tokens
        for _ in range(5):
            limiter.wait_if_needed()
        
        assert limiter.tokens == 5.0
        
        # Reset
        limiter.reset()
        
        assert limiter.tokens == 10.0
    
    def test_context_manager(self):
        """Test: Context manager funciona"""
        limiter = RateLimiter(rate=10)
        
        initial_tokens = limiter.tokens
        
        with limiter:
            pass  # Usa context manager
        
        # Debe haber consumido 1 token
        assert limiter.tokens == initial_tokens - 1
    
    def test_thread_safety(self):
        """Test: RateLimiter es thread-safe"""
        limiter = RateLimiter(rate=10)
        results = []
        
        def worker():
            for _ in range(5):
                limiter.wait_if_needed()
                results.append(1)
        
        # Crear 3 threads
        threads = [threading.Thread(target=worker) for _ in range(3)]
        
        # Iniciar todos
        for t in threads:
            t.start()
        
        # Esperar a que terminen
        for t in threads:
            t.join()
        
        # Debe haber procesado 15 requests (3 threads * 5 requests)
        assert len(results) == 15
    
    def test_high_rate_limit(self):
        """Test: Rate limit alto funciona correctamente"""
        limiter = RateLimiter(rate=100)  # 100 req/s
        
        start = time.time()
        
        # Hacer 50 requests
        for _ in range(50):
            limiter.wait_if_needed()
        
        elapsed = time.time() - start
        
        # Debe ser muy rápido (< 1 segundo)
        assert elapsed < 1.0
    
    def test_wait_time_calculation(self):
        """Test: Cálculo de tiempo de espera es correcto"""
        limiter = RateLimiter(rate=5, per_seconds=1.0)
        
        # Consumir todos los tokens
        for _ in range(5):
            limiter.wait_if_needed()
        
        # Calcular tiempo de espera
        wait_time = limiter._wait_time()
        
        # Debe ser ~0.2s (tiempo para generar 1 token a 5 tokens/s)
        assert 0.15 <= wait_time <= 0.25


class TestAdaptiveRateLimiter:
    """Test suite para AdaptiveRateLimiter"""
    
    def test_initialization(self):
        """Test: AdaptiveRateLimiter se inicializa correctamente"""
        limiter = AdaptiveRateLimiter(rate=10, min_rate=1, max_rate=50)
        
        assert limiter.rate == 10
        assert limiter.min_rate == 1
        assert limiter.max_rate == 50
        assert limiter.initial_rate == 10
        assert limiter.success_count == 0
    
    def test_rate_increase_on_success(self):
        """Test: Tasa aumenta después de N éxitos"""
        limiter = AdaptiveRateLimiter(rate=10, min_rate=1, max_rate=50)
        
        initial_rate = limiter.rate
        
        # Reportar 10 éxitos
        for _ in range(10):
            limiter.report_success()
        
        # Tasa debe haber aumentado
        assert limiter.rate == initial_rate + 1
        assert limiter.success_count == 0  # Se reinicia
    
    def test_rate_decrease_on_rate_limit_error(self):
        """Test: Tasa disminuye en error de rate limit"""
        limiter = AdaptiveRateLimiter(rate=10, min_rate=1, max_rate=50)
        
        initial_rate = limiter.rate
        
        # Reportar error de rate limit
        limiter.report_rate_limit_error()
        
        # Tasa debe haberse reducido a la mitad
        assert limiter.rate == initial_rate // 2
        assert limiter.success_count == 0  # Se reinicia
    
    def test_rate_not_below_minimum(self):
        """Test: Tasa no baja del mínimo"""
        limiter = AdaptiveRateLimiter(rate=2, min_rate=1, max_rate=50)
        
        # Reportar múltiples errores
        limiter.report_rate_limit_error()
        limiter.report_rate_limit_error()
        
        # No debe bajar de min_rate
        assert limiter.rate == 1
    
    def test_rate_not_above_maximum(self):
        """Test: Tasa no sube del máximo"""
        limiter = AdaptiveRateLimiter(rate=49, min_rate=1, max_rate=50)
        
        # Reportar múltiples éxitos
        for _ in range(50):
            limiter.report_success()
        
        # No debe subir de max_rate
        assert limiter.rate <= 50
    
    def test_reset_to_initial(self):
        """Test: Reset restaura a tasa inicial"""
        limiter = AdaptiveRateLimiter(rate=10, min_rate=1, max_rate=50)
        
        # Cambiar tasa
        for _ in range(10):
            limiter.report_success()
        
        # Reset
        limiter.reset_to_initial()
        
        assert limiter.rate == 10
        assert limiter.success_count == 0


class TestRateLimiterPerformance:
    """Tests de performance para RateLimiter"""
    
    def test_actual_rate_enforcement(self):
        """Test: Rate limit real es respetado"""
        target_rate = 10  # 10 req/s
        limiter = RateLimiter(rate=target_rate)
        
        requests_made = 0
        start_time = time.time()
        test_duration = 2.0  # 2 segundos
        
        # Hacer requests durante 2 segundos
        while time.time() - start_time < test_duration:
            limiter.wait_if_needed()
            requests_made += 1
        
        elapsed = time.time() - start_time
        actual_rate = requests_made / elapsed
        
        # El rate real debe estar cerca del target
        # Permitir 10% de margen
        assert target_rate * 0.9 <= actual_rate <= target_rate * 1.1
        
        print(f"Target rate: {target_rate} req/s")
        print(f"Actual rate: {actual_rate:.2f} req/s")
        print(f"Requests made: {requests_made} in {elapsed:.2f}s")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])