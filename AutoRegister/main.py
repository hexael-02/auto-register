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

#PESOS DE CALIFICACION (DEBE SUMAR 100)
PESOS_CALIFICACION = {
    'participacion': 20,
    'cuaderno': 15,
    'practica': 20,
    'exposicion':20,
    'prueba_mensual':25
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

def obtener_calificacion_letas(notas_numericas: float) -> str:
    for (min_nota, max_nota),  letra in ESCALA_LETRA.items():
        if min_nota <= notas_numericas <= max_nota:
            return letra
    return "N/A"

def calcular_calificacion_periodo(campo_detallado: dict[str, float]) -> dict [str, Any]:

    nota_final_numerica = 0 

    if not PESOS_CALIFICACION:
        return {'error': True, 'mensaje': "error: la constante PESOS_CALIFICACION no esta definida"}
    
    try:
        for campo, puntuacion_obtenida in campo_detallado.items():
            peso_campo = PESOS_CALIFICACION.get(campo)

            if peso_campo is None:
                raise ValueError(f" el campo '{campo}' no tiene un peso definido en PESOS_CALIFICACION. ")
            nota_final_numerica += puntuacion_obtenida
            
            nota_final_numerica = round (nota_final_numerica, 2)

            if nota_final_numerica > 100:
                nota_final_numerica = 100.0
            
            nota_final_letras = obtener_calificacion_letas(nota_final_numerica)

            return {
                'error': False,
                'calificacion_numerica': nota_final_numerica,
                'calificacion_letras': nota_final_letras
            }
    except (ValueError, TypeError) as e:
        return {'error': True, 'mensaje': f"error de calculo. verifique los tipos de datos: {e}" }
    except Exception as e:
        return {'error': True, 'mensaje':f"error inesperado al calcular la califciacion: {e}"}
    


