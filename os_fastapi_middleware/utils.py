"""Funções utilitárias para a biblioteca."""

import ipaddress
from typing import List


def is_ip_in_network(ip: str, networks: List[str]) -> bool:
    """
    Verify if an IP is in a list of networks.
    
    Args:
        ip: Ip address to verify
        networks: Ip addresses or networks to verify
        
    Returns:
        True if allowed, False otherwise
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        for network in networks:
            try:
                if "/" in network:
                    network_obj = ipaddress.ip_network(network, strict=False)
                    if ip_obj in network_obj:
                        return True
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
    Generate hash of an API key.
    
    Args:
        api_key: Api key to hash
        
    Returns:
        Api key SHA256 hash
    """
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key(length: int = 32) -> str:
    """
    Generate a random API key.
    
    Args:
        length: Key length
        
    Returns:
        Generated API key
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))