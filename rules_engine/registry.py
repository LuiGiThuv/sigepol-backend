"""
PASO 11: Registro de Reglas (Registry)

Sistema que permite registrar reglas de forma decorativa,
independiente del modelo de datos.
"""

# Registry global
_registered_rules = {}


def register_rule(codigo):
    """
    Decorador para registrar una función como regla ejecutable.
    
    Uso:
        @register_rule("POLIZAS_POR_EXPIRAR")
        def rule_polizas_por_expirar(rule_obj):
            # Implementación
            pass
    """
    def decorator(func):
        _registered_rules[codigo] = func
        return func
    return decorator


def get_registered_rules():
    """Retorna todas las reglas registradas"""
    return _registered_rules.copy()


def get_rule(codigo):
    """Obtiene una regla específica por código"""
    return _registered_rules.get(codigo)


def is_rule_registered(codigo):
    """Verifica si una regla está registrada"""
    return codigo in _registered_rules


def list_rule_codes():
    """Lista todos los códigos de reglas registradas"""
    return list(_registered_rules.keys())
