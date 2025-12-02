import pandas as pd 
import csv
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Any
import uuid

ARCHIVO_CSV = "AutoRegister.csv"
#rol y permisos
#para admistracion anurlar alertas debe ser true
ROLES_PERMISOS = {
    'ESTUDIANTE': {'ver_notas': True, 'llenar_campos': False, 'publicar_nota': False, 'editar_7dias': False, 'modificar_final': False, 'admin_usuarios': False,
                   'anular_alertas': False},
    
    'PROFESOR':{'ver_notas': True, 'llenar_campos': True, 'publicar_nota': True, 'editar_7dias': False, 'modificar_final': False, 'admin_usuarios': False,
                'anular_alertas': False},
    
    'ADMINISTRACION': {'ver_notas': True, 'llenar_campos': False, 'publicar_nota': False, 'editar_7dias': False, 'modificar_final':  False, 'admin_usuarios': True, 'anular_alertas': True},

    'ENCARGADA_REGISTRO': {'ver_notas': True, 'llenar_campos': False, 'publicar_nota': False, 'editar_7dias': True, 'modificar_final': True, 'admin_usuarios': False, 'anular_alertas': False},

    'DIRECTOR': {'ver_notas': True, 'llenar_campos': True, 'publicar_nota': True, 'editar_7dias': True, 'modificar_final': True, 'admin_usuarios': True, 'anular_alertas': True},
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

REGISTROS_CALIFICACION_SIMULADOS: list[dict[str, Any ]] = []

#NOTA: Usamos esta estructura simple en memoria hasta que implementemos la base de datos real

USUARIOS_SIMULADOS = [
    {'USUARIO_ID': 1001, 'usuario_nombre': 'Ana', 'usuario_apellido': 'Bermudez', 'usuario_rol': 'ESTUDIANTE' },
    {'USUARIO_ID': 2005, 'usuario_nombre': 'Pedro', 'usuario_apellido': 'Gomez', 'usuario_rol': 'PROFESOR' },
    {'USUARIO_ID': 3001, 'usuario_nombre': 'Carmen', 'usuario_apellido': 'Duarte', 'usuario_rol': 'DIRECTOR' },
    {'USUARIO_ID': 4002, 'usuario_nombre': 'Raquel', 'usuario_apellido': 'Perez', 'usuario_rol': 'ADMINISTRACION' },
    {'USUARIO_ID': 5003, 'usuario_nombre': 'Jose', 'usuario_apellido': 'Martinez', 'usuario_rol': 'ENCARGADA_REGISTRO' }
]

#Funciones
"""
def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        with open(ARCHIVO_CSV, 'w', newline='', encoding='utf-8') as archivo:
            writer = csv.DictReader(archivo, fieldnames= #ESTE ESPACIO DEBE LLENARSE )
            writer.writeheader()
            print(f"archivo '{ARCHIVO_CSV}' creado con exito.")

"""
# bloque 0

def gestionar_permisos(user_id: int) -> dict[str, list[Any]]:
    
    #inicializar_csv()

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

                permisos_clean = {k: bool (v) for k, v in permisos.items()}

                resultado = {
                    'autenticado': True,
                    'datos': usuario_encontrado,
                    'permisos': permisos_clean
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

#bloque 1
def obtener_calificacion_letas(notas_numericas: float) -> str:
    
    #inicializar_csv()

    for (min_nota, max_nota),  letra in ESCALA_LETRA.items():
        if min_nota <= notas_numericas <= max_nota:
            return letra
    return "N/A"

#bloqeu 2
def calcular_calificacion_periodo(campo_detallado: dict[str, float]) -> dict [str, Any]:

    #inicializar_csv()

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
# bloque 3  
def crear_o_actualizar_registro(
        profesor_id: int,
        estudiante_id: int,
        materia: str,
        periodo_num: int,
        campos: dict[str, float],
        metodologia: str
) -> dict[str,any]:
    
    #inicializar_csv()

    permisos_data = gestionar_permisos(profesor_id)
    if not permisos_data['autenticado'] or not permisos_data['permisos'].get('llenar_campos'):
        return {'exito': False, 'mensaje': "permiso denegado: el usuario no puede llenar campos de calificacion."}
    
    calculo_resultado = calcular_calificacion_periodo(campos)

    if calculo_resultado['error']:
        return{'exito': False, 'mensaje': f"fallo en el calculo: {calculo_resultado['mensaje']}"}
    
    nota_numerica = calculo_resultado['calificacion_numerica']
    nota_letra = calculo_resultado['calificacion_letras']

    registro_existente = None
    indice_registro = -1
    
    for i, registro in enumerate(REGISTROS_CALIFICACION_SIMULADOS):
        if (registro['estudiante_ID'] == estudiante_id and registro['materia'] == materia and registro['periodo_numero'] == periodo_num):
            registro_existente = registro
            indice_registro = i 
            break 
        
        
    if registro_existente and registro_existente['publicado']:
        fecha_limite_str = registro_existente.get('fecha_limite_modificacion')
        fecha_limite = datetime.strptime(fecha_limite_str, '%Y-%m-%d').date()
        fecha_actual = date.today()
        
        # ESTRUCTURA DE CONTROL: Verifica si se excedió el límite de 7 días
        if fecha_actual > fecha_limite:
            # ESTRUCTURA DE CONTROL: Solo el Director o Encargada de Registro pueden modificar después del límite
            permiso_modificar_tardio = permisos_data['permisos'].get('modificar_final') or permisos_data['permisos'].get('editar_7dias')
            if not permiso_modificar_tardio:
                return {'exito': False, 'mensaje': 'Edición Bloqueada: El registro está publicado y ha excedido la fecha límite de modificación.'}
        
    # 5. CREACIÓN O ACTUALIZACIÓN DEL DOCUMENTO
    fecha_hoy = date.today()
    fecha_publicacion_str = fecha_hoy.strftime('%Y-%m-%d')
    fecha_limite_modificacion_str = (fecha_hoy + timedelta(days=7)).strftime('%Y-%m-%d')
    
    nuevo_registro = {
        'estudiante_ID': estudiante_id,
        'profesor_ID': profesor_id,
        'materia': materia,
        'periodo_numero': periodo_num,
        'campos_detallados': campos,
        'calificacion_numerica': nota_numerica, 
        'calificacion_letras': nota_letra,
        'promedio_general': None,
        'metodologia_docente': metodologia,
        'fecha_publicacion': fecha_publicacion_str,
        'publicado': False, # Por defecto, la edición es NO publicada
        'alerta_activa': True,
        'fecha_limite_modificacion': fecha_limite_modificacion_str,
        'apelaciones_activas': []
    }

    # ESTRUCTURA DE CONTROL: Determina si es una creación o una actualización
    if registro_existente:
        # Actualización
        REGISTROS_CALIFICACION_SIMULADOS[indice_registro].update(nuevo_registro)
        # Asegura que el ID original se mantenga
        registro_id_final = registro_existente['registro_ID']
        REGISTROS_CALIFICACION_SIMULADOS[indice_registro]['registro_ID'] = registro_id_final 
        
        # RETORNO CORREGIDO: Incluye el 'registro_ID'
        return {
            'exito': True, 
            'mensaje': f'Registro {registro_id_final} actualizado exitosamente. Nota actual: {nota_numerica}',
            'registro_ID': registro_id_final 
        }
    else:
        # Creación
        registro_id_final = str(uuid.uuid4()) # ID único y corto
        nuevo_registro['registro_ID'] = registro_id_final
        REGISTROS_CALIFICACION_SIMULADOS.append(nuevo_registro)
        
        # RETORNO CORREGIDO: Incluye el 'registro_ID'
        return {
            'exito': True, 
            'mensaje': f'Nuevo registro {registro_id_final} creado exitosamente. Nota: {nota_numerica}',
            'registro_ID': registro_id_final
        }

# bloque 4              
def publicar_registro_calificacion(user_id_publicador: int, registro_id: str,)-> Dict[str, Any]:

    #inicializar_csv()

    permisos_data = gestionar_permisos(user_id_publicador)
    if not permisos_data['autenticado'] or not permisos_data['permisos'].get('publicar_nota'):
        return{'extito': False, 'mensaje': "permisos denegado: El usuario no tiene permiso para publicar calificaciones."}
    
    registro_encontrado = None 
    indice_registro = -1

    for i, registro in enumerate(REGISTROS_CALIFICACION_SIMULADOS):
        if registro['registro_ID'] == registro_id:
            registro_encontrado = registro
            indice_registro = i 
            break
    if not registro_encontrado:
        return {'exito': False, 'mensaje': 'el registro no se encuentra'}
    if registro_encontrado.get('publicado'):
        return {'exito': True, 'mensaje': "El registro ya se encuentra publicado correctamente."}
    
    try:
        fecha_hoy = date.today().strftime('%Y-%m-%d')
        fecha_limite = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')

        REGISTROS_CALIFICACION_SIMULADOS[indice_registro].update({
            'publicado': True,
            'alerta_activa': False, #asume que la publicacion resuelve la alerta
            'fecha_publicacion': fecha_hoy,
            'fecha_limite_modificacion': fecha_limite
        })
        
        return {'exito': True, 'mensaje': f'registro {registro_id} publicado exitosamente. se ha activado la ventana de edicion de 7 dias (hasta {fecha_limite}).'}
    
    except Exception as e:
        return {'exito': False, 'mensaje': f"Error interno al actualizar el estado del registro {e}"}
    

#datos_nota_ejemplo = {'participacion': 19.0, 'cuaderno': 14.5, 'practica': 18.0, 'exposicion': 18.0, 'prueba_mensual': 23.0}

# 1. PRUEBA DE CREACIÓN (Bloque 3)
#print("\n--- 1. Intento de CREACIÓN (Profesor 2005) ---")
#creacion = crear_o_actualizar_registro(
#     profesor_id=2005, 
#    estudiante_id=1001, 
#    materia='Matemáticas', 
#    periodo_num=1, 
#    campos=datos_nota_ejemplo, 
#    metodologia='metodología x'
#)

#registro_id_prueba = None
#    registro_id_prueba = creacion['registro_ID'] 
#    print(creacion['mensaje']) 
#    print(f"Registro creado con ID: {registro_id_prueba}")
#else:
#    print(f"FALLO DE CREACIÓN: {creacion['mensaje']}")

# 2. PRUEBA DE PUBLICACIÓN (Bloque 4)
#if registro_id_prueba:
#    print("\n--- 2. Intento de PUBLICACIÓN (Profesor 2005) ---")
#    resultado_publicacion = publicar_registro_calificacion(
#        user_id_publicador=2005, 
#        registro_id = registro_id_prueba
#    )
#    print(resultado_publicacion)

#print("\n--- Estado Final del Registro (Tras Bloque 4) ---")
# Utilizamos el índice [0] porque solo hemos creado un registro
#if REGISTROS_CALIFICACION_SIMULADOS:
#    print(REGISTROS_CALIFICACION_SIMULADOS[0])
#else:
#    print("No se encontró ningún registro para mostrar.")

# bloque 5
def crear_apelacion(estudiante_id: int, registro_id: str, comentario: str ) -> Dict[str, Any]:

    permisos_data = gestionar_permisos(estudiante_id)
    if not permisos_data['autenticado'] or permisos_data['datos']['usuario_rol'] != 'ESTUDIANTE':
        return {'exito': False, 'mensaje': "permiso denegado: solo los estudiantes autenticados pueden crear apelaciones"}
    
    registro_encontrado = None
    indice_registro = -1

    for i, registro in enumerate(REGISTROS_CALIFICACION_SIMULADOS):
        if registro['registro_ID'] == registro_id:
            registro_encontrado = registro
            indice_registro = i 
            break
    if not registro_encontrado:
        return {'exito': False, 'mensaje': "el registro no se encuentra"}
    
    if not registro_encontrado.get('publicado'):
        return {'exito': False, 'mensaje': "solo se puede apelar registros que han sido publicados."}
    
    if registro_encontrado['estudiante_ID'] != estudiante_id:
        return {'exito': False, 'mensaje': "acceso denegado: no puede apelar a un registro que no sea suyo"}
    
    try:
        nueva_apelacion = {
            'apelacion_id': str(uuid.uuid4()),
            'estudiante_id': estudiante_id,'fecha_creacion': date.today().strftime('%Y-%m-%d'),
            'comentario': comentario,
            'estado': 'pendiente', # Estados posibles: Pendiente, Aceptada, Rechazada
            'respuesta_admin': None
        }

        REGISTROS_CALIFICACION_SIMULADOS[indice_registro] ['apelaciones_activas'].append(nueva_apelacion)

        return {
            'exito': 'true',
            'mensaje': f"esta apelacion se registro exitosamente con el ID {registro_id} espere la respuesta de administracion."
        }
    except Exception as e:
        return{'exito': False, 'mensaje': f"ocurrio un error inesperado intentelo mas tarde: {e}"}
    

"""
REGISTROS_CALIFICACION_SIMULADOS.clear() # Limpiar cualquier registro previo

datos_nota_ejemplo_buena = {'participacion': 18.0, 'cuaderno': 13.0, 'practica': 18.0, 'exposicion': 18.0, 'prueba_mensual': 23.0} # Nota buena (90.0)
datos_nota_ejemplo_vacia = {'participacion': 1.0, 'cuaderno': 1.0, 'practica': 1.0, 'exposicion': 1.0, 'prueba_mensual': 1.0} 

print("\n--- Bloque de PRUEBA 5: Gestión de Apelaciones ---")

# --- ESCENARIO 1: Creación de Apelación Exitosa ---

# 1. CREACIÓN DE REGISTRO BASE (Profesor 2005, Estudiante 1001)
# *DEBE* ejecutarse primero
print("\n[Escenario 1.1] Creación Inicial de Nota (Estudiante 1001)")
registro_base = crear_o_actualizar_registro(
    profesor_id=2005, 
    estudiante_id=1001, 
    materia='Matemáticas', 
    periodo_num=3, 
    campos=datos_nota_ejemplo_buena, 
    metodologia='Basada en Proyectos'
)
registro_id_base = registro_base.get('registro_ID')
print(f"Resultado Creación: {registro_base.get('mensaje')}")

# 2. PUBLICACIÓN DEL REGISTRO (REQUERIDO para Apelar)
# *DEBE* ejecutarse en segundo lugar
print("\n[Escenario 1.2] Publicación del Registro (Activa Apelación)")
publicacion_resultado = publicar_registro_calificacion(user_id_publicador=2005, registro_id=registro_id_base)
print(f"Resultado Publicación: {publicacion_resultado.get('mensaje')}")

# 3. CREACIÓN DE APELACIÓN (Estudiante 1001)
# *DEBE* ejecutarse en tercer lugar
print("\n[Escenario 1.3] Creación de Apelación Exitosa (Estudiante 1001)")
apelacion_resultado = crear_apelacion(
    estudiante_id=1001,
    registro_id=registro_id_base,
    comentario="Solicito revisión de mi nota de exposición. Hubo un error en la suma."
)
print(apelacion_resultado)


# 4. VERIFICACIÓN DEL ESTADO FINAL
print("\n[Escenario 1.4] Verificación del Estado del Registro")
if REGISTROS_CALIFICACION_SIMULADOS and registro_id_base == REGISTROS_CALIFICACION_SIMULADOS[0].get('registro_ID'):
    registro_final = REGISTROS_CALIFICACION_SIMULADOS[0]
    print(f"Nota Final: {registro_final['calificacion_numerica']}")
    print(f"Apelaciones Activas: {len(registro_final['apelaciones_activas'])}")
    if registro_final['apelaciones_activas']:
        print(f" > Estado de la Apelación: {registro_final['apelaciones_activas'][0]['estado']}")
else:
    print("Error: No se encontró el registro base para la verificación final.")


# --- ESCENARIO 2: Pruebas de Fallo ---

# 5. INTENTO DE APELACIÓN SOBRE REGISTRO NO PUBLICADO
print("\n[Escenario 2.1] Intento de Apelación en Registro NO PUBLICADO (Debe Fallar)")
registro_no_publicado = crear_o_actualizar_registro(
    profesor_id=2005, 
    estudiante_id=1001, 
    materia='Ciencias', 
    periodo_num=1, 
    campos=datos_nota_ejemplo_vacia, 
    metodologia='Laboratorio'
)
registro_id_no_publicado = registro_no_publicado.get('registro_ID')

apelacion_fallida_no_publicado = crear_apelacion(
    estudiante_id=1001,
    registro_id=registro_id_no_publicado,
    comentario="Esto no debería funcionar."
)
print(apelacion_fallida_no_publicado) # Debe fallar con "Solo se pueden apelar registros que han sido publicados."

# 6. INTENTO DE APELACIÓN POR UN NO-ESTUDIANTE (DIRECTOR 3001)
print("\n[Escenario 2.2] Intento de Apelación por un Director (3001) (Debe Fallar)")
apelacion_fallida_rol = crear_apelacion(
    estudiante_id=3001, # Director
    registro_id=registro_id_base,
    comentario="El director apelando una nota de estudiante."
)
print(apelacion_fallida_rol) # Debe fallar con "Permiso denegado: Solo los estudiantes autenticados pueden crear apelaciones."
"""

# bloque 6

def gestionar_apelacion_admin(user_id_admin: int, registro_id: str, apelacion_id: str, nuevo_estado: str, respuesta_admin: str) -> Dict[str, Any]:
    
    permisos_data = gestionar_permisos(user_id_admin)
    permisos_gestion = permisos_data['permisos'].get('admin_usuarios') or permisos_data ['permisos'].get('modificar_final') 

    if not permisos_data['autenticado'] or not permisos_gestion:
        return{'EXITO': False, 'mensjae': "permiso denegado: solo roles administrativos pueden gestionar apelaciones." }
    
    registro_encontrado = None
    indice_registro = -1

    for i, registro in enumerate(REGISTROS_CALIFICACION_SIMULADOS):
        if registro['registro_ID'] == registro_id:
            registro_encontrado =  registro
            indice_registro = i 
            break

    if not registro_encontrado:
        return {'exito': False, 'mensaje': "error: el registro de calificacion no se encuentra. " }
    
    apelacion_encontrada = None
    indice_apelacion = -1

    for j, apelacion in enumerate(registro_encontrado.get('apelaciones_activas', [])):
        if apelacion['apelacion_id'] == apelacion_id:
            apelacion_encontrada = apelacion
            indice_apelacion = j
            break
    if not apelacion_encontrada:
        return {'exito': False, 'mensaje': "error: debe elegir una de las opciones que mostradas en pantalla (aceptada o rechazada)"}
    
    try:
        REGISTROS_CALIFICACION_SIMULADOS['indice_registro']['apelaciones_activas']['indice_apelacion']['estado'] = nuevo_estado
        REGISTROS_CALIFICACION_SIMULADOS['indice_registro']['apelaciones_activas']['indice_apelacion']['respuesta_admin'] = respuesta_admin

        mensaje_adicional = ""

        if nuevo_estado == 'aceptada':
            REGISTROS_CALIFICACION_SIMULADOS[indice_registro]['alerta_activa'] = True
            mensaje_adicional = "se ha re-activado la alerta del registro para revision por parte del profesor"
        
        return{
            'exito': True,
            'mensaje': f"apelacion {apelacion_id} ha sido marcada como '{nuevo_estado}' por el usuario {user_id_admin}. {mensaje_adicional} "
        }



    except Exception as e: 
        return {'exito': False, 'mensaje': f"error interno al gesitonar la apelacion: {e}"}
    

REGISTROS_CALIFICACION_SIMULADOS.clear() # Limpiar cualquier registro previo
datos_nota_ejemplo = {'participacion': 18.0, 'cuaderno': 13.0, 'practica': 18.0, 'exposicion': 18.0, 'prueba_mensual': 23.0} # Nota buena (90.0)
datos_nota_ejemplo_vacia = {'participacion': 1.0, 'cuaderno': 1.0, 'practica': 1.0, 'exposicion': 1.0, 'prueba_mensual': 1.0} 

print("\n--- Bloque de PRUEBA 6: Gestión Administrativa de Apelaciones ---")

# 1. CREACIÓN Y PUBLICACIÓN DE REGISTRO BASE (Profesor 2005, Estudiante 1001)
print("\n[Setup 1.1] Creación Inicial de Nota (Estudiante 1001)")
registro_base = crear_o_actualizar_registro(
    profesor_id=2005, 
    estudiante_id=1001, 
    materia='Matemáticas', 
    periodo_num=3, 
    campos=datos_nota_ejemplo, 
    metodologia='Basada en Proyectos'
)
registro_id_base = registro_base.get('registro_ID')

print("[Setup 1.2] Publicación del Registro")
publicacion_resultado = publicar_registro_calificacion(user_id_publicador=2005, registro_id=registro_id_base)

# 2. CREACIÓN DE LA APELACIÓN (Estudiante 1001)
print("[Setup 1.3] Creación de Apelación para el Registro Base")
apelacion_resultado = crear_apelacion(
    estudiante_id=1001,
    registro_id=registro_id_base,
    comentario="Apelo la nota de exposición por un error de 2 puntos."
)
apelacion_id_base = apelacion_resultado.get('apelacion_id')
print(f"Apelación Creada: ID={apelacion_id_base}. Estado inicial: Pendiente.")


# --- ESCENARIO 1: ACEPTACIÓN EXITOSA (ADMINISTRACION 4002) ---
print("\n[Escenario 1. ACEPTAR APELACIÓN]")
resultado_aceptar = gestionar_apelacion_admin(
    user_id_admin=4002, # ADMINISTRACION
    registro_id=registro_id_base,
    apelacion_id=apelacion_id_base,
    nuevo_estado='Aceptada',
    respuesta_admin='Apelación Aceptada. El profesor debe revisar la nota de Exposición.'
)
print(f"Resultado Aceptación: {resultado_aceptar.get('mensaje')}")

# 3. VERIFICACIÓN POST-ACEPTACIÓN
print("\n[Verificación 1. ACEPTACIÓN]")
registro_final = REGISTROS_CALIFICACION_SIMULADOS[0]
apelacion_final = registro_final['apelaciones_activas'][0]
print(f"  > Estado Apelación: {apelacion_final['estado']}")
print(f"  > Respuesta Admin: {apelacion_final['respuesta_admin']}")
print(f"  > Alerta Activa: {registro_final['alerta_activa']} (Debe ser True)")


# --- ESCENARIO 2: RECHAZO EXITOSO (DIRECTOR 3001) ---
# Primero, creamos una nueva apelación para poder rechazarla
print("\n[Setup 2.1] Creación de Segunda Apelación (para rechazar)")
apelacion_resultado_rechazo = crear_apelacion(
    estudiante_id=1001,
    registro_id=registro_id_base,
    comentario="Apelación sin fundamento para probar el rechazo."
)
apelacion_id_rechazo = apelacion_resultado_rechazo.get('apelacion_id')

print("\n[Escenario 2. RECHAZAR APELACIÓN]")
resultado_rechazar = gestionar_apelacion_admin(
    user_id_admin=3001, # DIRECTOR
    registro_id=registro_id_base,
    apelacion_id=apelacion_id_rechazo,
    nuevo_estado='Rechazada',
    respuesta_admin='Apelación sin mérito. No se procede a la revisión.'
)
print(f"Resultado Rechazo: {resultado_rechazar.get('mensaje')}")

# 4. VERIFICACIÓN POST-RECHAZO
print("\n[Verificación 2. RECHAZO]")
registro_final_rechazo = REGISTROS_CALIFICACION_SIMULADOS[0]
apelacion_rechazada = registro_final_rechazo['apelaciones_activas'][1] # La segunda apelación
print(f"  > Estado Apelación: {apelacion_rechazada['estado']}")
print(f"  > Respuesta Admin: {apelacion_rechazada['respuesta_admin']}")


# --- ESCENARIO 3: PRUEBA DE FALLO (PROFESOR 2005) ---
print("\n[Escenario 3. FALLO DE PERMISO]")
resultado_fallo = gestionar_apelacion_admin(
    user_id_admin=2005, # PROFESOR (Sin permiso)
    registro_id=registro_id_base,
    apelacion_id=apelacion_id_base,
    nuevo_estado='Aceptada',
    respuesta_admin='Intento de profesor.'
)
print(f"Resultado Fallo: {resultado_fallo.get('mensaje')}") # Debe fallar por permiso
