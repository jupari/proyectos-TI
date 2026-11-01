def division_segura(numerador, denominador):
    """Devuelve `None` (en vez de `ZeroDivisionError`) cuando el denominador
    es cero o nulo, o el numerador es nulo.

    Todo porcentaje o índice de la aplicación pasa por aquí: la UI debe
    mostrar un guion, nunca un 0% engañoso (docs/modelo-datos.md §10).
    """
    if not denominador or numerador is None:
        return None
    return numerador / denominador
