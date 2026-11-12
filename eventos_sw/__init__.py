"""
Módulo «eventos_sw»: avisos internos entre los módulos del software.

Cuando en un módulo pasa algo («una consulta se ha cerrado»), lo anuncia con emitir(). Los módulos que
lo escuchan (declarado en su contrato) reaccionan sin que el primero sepa que existen. Así los módulos
funcionales no se importan entre sí (ver docs/diseno.md, apartados 3.2 y 3.7).

- Escuchas síncronas: se ejecutan en el acto, dentro de la misma transacción.
- Escuchas asíncronas: se apuntan en la bandeja de salida (tabla AvisoPendiente) y las procesa después
  la orden «python manage.py procesar_bandeja».
"""
