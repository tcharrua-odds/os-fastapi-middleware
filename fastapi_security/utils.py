"""Funções utilitárias para a biblioteca."""

import ipaddress
from typing import List


def is_ip_in_network(ip: str, networks: List[str]) -> bool:
    """
    Verifica se um IP está em uma lista de redes (suporta CIDR).
    
    Args:
        ip: Endereço IP a verificar
        networks: Lista de IPs ou redes em notação CIDR
        
    Returns:
        True se o IP está permitido
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        for network in networks:
            try:
                # Tenta como rede CIDR
                if "/" in network:
                    network_obj = ipaddress.ip_network(network, strict=False)
                    if ip_obj in network_obj:
                        return True
                # Tenta como IP único
                else:
                    if ip_obj == ipaddress.ip_address(network):
                        return True
            except ValueError:
                continue
        
        return False
    except ValueError:
        return False


def hash_api_key(api_key: str) -> str:
    """
    Gera hash de uma API key para armazenamento seguro.
    
    Args:
        api_key: API key em texto plano
        
    Returns:
        Hash SHA-256 da API key
    """
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(length: int = 32) -> str:
    """
    Gera uma API key aleatória.
    
    Args:
        length: Comprimento da chave
        
    Returns:
        API key gerada
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))