import pandas as pd 
import csv
import os
from datetime import date, datetime, timedelta
from typing import Dict, List

#rol y permisos
#para admistracion anurlar alertas debe ser true
ROLES_PERMISOS = {
    'ESTUDIANTE': {'ver_notas': True, 'llenar_campos': False, 'publicar_notas': False, 'editar_7dias': False, 'modificar_final': False, 'admin_usuarios': False,
                   'anular_alertas': False},
    
    'PROFESOR':{'ver_notas': True, 'llenar_campos': True, 'publicar_notas': False, 'editar_7dias': False, 'modificar_final': False, 'admin_usuarios': False,
                'anular_alertas': False},
    
    'ADMINISTRACION': {'ver_notas': True, 'llenar_campos': False, 'publicar_notas': False, 'editar_7dias': False, 'modificar_final':  False, 'admin_usuarios': True, 'anular_alertas': False},

    'ENCARGADA_REGISTRO': {'ver_notas': True, 'llenar_campos': False, 'publicar_notas': False, 'editar_7dias': True, 'modificar_final': True, 'admin_usuarios': False, 'anular_alertas': False},

    'DIRECTOR': {'ver_notas': True, 'llenar_campos': True, 'publicar_notas': True, 'editar_7dias': True, 'modificar_final': True, 'admin_usuarios': True, 'anular_alertas': True},
}


ESCALA_LETRA = {
    (97, 100): "A+", (93,96): "A", (90,92): "A-",
    (87, 89): "B+", (83,86): "B", (80,82): "B-",
    (77, 79): "C+", (73,76): "C", (70,72): "C-",
    (67, 69): "D+", (63,66): "D", (60,62): "D-",
    (0, 59): "F+"
}

#NOTA: Usamos esta estructura simple en memoria hasta que implementemos la base de datos real

USUARIOS_SIMULADOS = [
    {'USUARIO_ID': 1001, 'usuario_nombre': 'Ana', 'usuario_apellido': 'Bermudez', 'usuario_rol': 'ESTUDIANTE' },
    {'USUARIO_ID': 2005, 'usuario_nombre': 'Pedro', 'usuario_apellido': 'Gomez', 'usuario_rol': 'PROFESOR' },
    {'USUARIO_ID': 3001, 'usuario_nombre': 'Carmen', 'usuario_apellido': 'Duarte', 'usuario_rol': 'DIRECTOR' },
    {'USUARIO_ID': 4002, 'usuario_nombre': 'Raquel', 'usuario_apellido': 'Perez', 'usuario_rol': 'ADMINISTRACION' },
    {'USUARIO_ID': 5003, 'usuario_nombre': 'Jose', 'usuario_apellido': 'Martinez', 'usuario_rol': 'ENCARGADA_REGISTRO' }
]

#Funciones
from typing import Any
def gestionar_permisos(user_id: int) -> dict[str, list[Any]]:
    
    try:
        usuario_encontrado = None
        for usuario in USUARIOS_SIMULADOS:
            if usuario['USUARIO_ID'] == user_id:
                usuario_encontrado = usuario
                break
        if usuario_encontrado:
            rol = usuario_encontrado['usuario_rol']

            if rol in ROLES_PERMISOS:
                permisos = ROLES_PERMISOS[rol]

                resultado = {
                    'autenticado': True,
                    'datos': usuario_encontrado,
                    'permisos': permisos
                }
                return resultado
            else:
                return {'autenticado': False, 'mensaje': f"ERROR: Rol '{rol}' no definido en el sistema de permisos."}
        else:
            return {'autenticado': False, 'mensaje': "ERROR: Usuario no encontrado"}
        
    except Exception as e:
        return {'autenticado': False, 'mensaje': f"ERROR interno al gestionar permisos: {e}"}
    
    
#director_permisos = gestionar_permisos(3001)
#print(director_permisos)
#estudiantes_permisos = gestionar_permisos(1001)
#print(estudiantes_permisos)
#error_permisos = gestionar_permisos(9999)
#print(error_permisos)
