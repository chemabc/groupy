"""
Lo que el módulo «limpieza» necesita de «calendario» (ver calendario/apps.py, apartado «limpiables»): qué
recordatorios ya pasaron.
"""

from django.db.models import Q

from .models import Recordatorio


# Recordatorios cuya fecha (la de fin, si la tienen) es anterior a «antes», sin archivar.
def recordatorios(antes):
    pasados = Q(fin__isnull=True, inicio__lt=antes) | Q(fin__lt=antes)
    return Recordatorio.objects.filter(pasados, archivado__isnull=True)
