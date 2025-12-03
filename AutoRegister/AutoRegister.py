import pandas as pd
import csv
import os
import json
import hashlib
from datetime import date, datetime, timedelta

# --- 1. CONFIGURACIÓN Y CONSTANTES DEL SISTEMA ---

ARCHIVO_CSV = "AutoRegister.csv"
ID_COUNTER_FILE = "id_counter.txt"
ESTADO_INICIAL_NOTA = "N/A" # Marca para notas no publicadas

# Definición del esquema de columnas (Usado para inicializar DataFrames vacíos)
COLUMNS = [
    'ID_REGISTRO', 'estudiante_ID', 'profesor_ID', 'periodo', 
    'fecha_publicacion', 'estado_publicacion', 'estado_revision', 
    'P_NOTA_FINAL', 'P_METODO_ENS', 'P_DETALLES_JSON', 
    'promedio_general'
]

# Constantes del Ministerio de Educación Dominicano (MINERD)
PERIODOS_DIAS_LECTIVOS = 45 # Usado para calcular la fecha de vencimiento del periodo.

# Definición de pesos ponderados (debe sumar 1.0 o 100%)
PESOS_CALIFICACION = {
    'Participacion': 0.18,   # 18%
    'Cuaderno': 0.135,        # 13.5%
    'Practica': 0.18,        # 18%
    'Exposicion': 0.18,      # 18%
    'prueba_mensual': 0.225,  # 22.5%
    'asistencia': 0.10,      # 10%
}
CALIFICACION_CAMPOS = list(PESOS_CALIFICACION.keys())

# Escala de calificación estándar (Asumida por solicitud del usuario)
ESCALA_CALIFICACION = {
    93: 'A', 90: 'A-',
    87: 'B+', 83: 'B', 80: 'B-',
    77: 'C+', 73: 'C', 70: 'C-',
    60: 'D',
    0: 'F'
}

# Definición de roles y permisos
ROLES = {
    'DIRECTOR': 'Director/a',
    'REGISTRO': 'Encargada de Registro',
    'ADMIN': 'Administración',
    'PROFESOR': 'Profesor/a',
    'ESTUDIANTE': 'Estudiante'
}

PERMISOS_ROLES = {
    # Permisos: 'llenar_notas', 'publicar_notas', 'modificar_publicada', 'administrar_usuarios', 'anular_alerta'
    ROLES['DIRECTOR']: {'ver_todo': True, 'llenar_notas': True, 'publicar_notas': True, 'modificar_publicada': True, 'administrar_usuarios': True, 'anular_alerta': True, 'suspender_expulsar': True, 'modificar_post_7d': False},
    ROLES['REGISTRO']: {'ver_todo': True, 'llenar_notas': False, 'publicar_notas': False, 'modificar_publicada': True, 'administrar_usuarios': False, 'anular_alerta': False, 'suspender_expulsar': False, 'modificar_post_7d': False},
    ROLES['ADMIN']: {'ver_todo': True, 'llenar_notas': False, 'publicar_notas': False, 'modificar_publicada': False, 'administrar_usuarios': True, 'anular_alerta': False, 'suspender_expulsar': False, 'modificar_post_7d': False},
    ROLES['PROFESOR']: {'ver_todo': True, 'llenar_notas': True, 'publicar_notas': True, 'modificar_publicada': False, 'administrar_usuarios': False, 'anular_alerta': False, 'suspender_expulsar': False, 'modificar_post_7d': False},
    ROLES['ESTUDIANTE']: {'ver_todo': False, 'llenar_notas': False, 'publicar_notas': False, 'modificar_publicada': False, 'administrar_usuarios': False, 'anular_alerta': False, 'suspender_expulsar': False, 'modificar_post_7d': False},
}

# Datos de Usuario Mock para probar la jerarquía (ID: Rol)
USUARIOS_MOCK = {
    '0': ROLES['DIRECTOR'],    # Directora (ID 0)
    '1': ROLES['REGISTRO'],    # Encargada de Registro (ID 1)
    '2': ROLES['ADMIN'],       # Administración (ID 2)
    '101': ROLES['PROFESOR'],  # Profesor Juan (ID 101)
    '102': ROLES['PROFESOR'],  # Profesora María (ID 102)
    '2001': ROLES['ESTUDIANTE'], # Estudiante A (ID 2001)
    '2002': ROLES['ESTUDIANTE'], # Estudiante B (ID 2002)
}

# --- 2. CLASE PARA GESTIÓN DE ID's ---

def get_max_mock_id(users_mock):
    """Obtiene el ID numérico más alto de los usuarios mock."""
    max_id = -1
    for user_id in users_mock.keys():
        try:
            # Convertimos a int para comparar. Si no es un número, lo ignoramos.
            current_id = int(user_id)
            if current_id > max_id:
                max_id = current_id
        except ValueError:
            continue
    # Devolvemos el ID más alto. Si no hay, devolvemos -1.
    return max_id

class GeneradorIDs:
    """
    Clase para manejar la generación de IDs numéricos secuenciales
    para usuarios y IDs alfanuméricos hashed para registros.
    """
    def __init__(self, counter_file=ID_COUNTER_FILE, mock_users=USUARIOS_MOCK):
        self.counter_file = counter_file
        self.mock_users = mock_users
        self._initialize_counter()

    def _initialize_counter(self):
        """
        Garantiza que el contador persistente comience en un valor 
        mayor que el ID más alto de los usuarios mock, evitando duplicación.
        """
        max_mock_id = get_max_mock_id(self.mock_users)
        
        # El valor mínimo seguro para empezar a generar nuevos IDs
        min_safe_start = max_mock_id
        
        # Si el archivo existe, leemos su valor
        if os.path.exists(self.counter_file):
            try:
                with open(self.counter_file, 'r') as f:
                    last_id_persisted = int(f.read().strip())
                # Usamos el mayor entre el ID persistido y el ID mock más alto
                # Esto asegura que si el mock ID es 2002 y el persistido es 100,
                # comenzaremos en 2002.
                if last_id_persisted < min_safe_start:
                    print(f"Advertencia: Contador desfasado ({last_id_persisted}). Reiniciando contador a {min_safe_start} para evitar colisiones.")
                    self._save_counter(min_safe_start)
                
            except (ValueError, IOError):
                # Si el archivo está corrupto o vacío, lo reiniciamos al valor seguro
                self._save_counter(min_safe_start)
        else:
            # Si el archivo no existe, lo creamos con el valor seguro
            self._save_counter(min_safe_start)

    def _save_counter(self, value):
        """Guarda el valor actual del contador en el archivo."""
        try:
            with open(self.counter_file, 'w') as f:
                f.write(str(value))
        except IOError as e:
            print(f"Error al escribir en el archivo de contador de IDs: {e}")

    def generar_id_secuencial(self):
        """Genera un ID numérico secuencial que persiste en un archivo."""
        current_id = -1
        try:
            # 1. Leer el último ID
            with open(self.counter_file, 'r') as f:
                current_id = int(f.read().strip())
        except (FileNotFoundError, ValueError, IOError) as e:
            # Si hay algún error, significa que la inicialización falló o el archivo
            # se corrompió, pero como ya se inicializó, esto es un fallback.
            print(f"Error al leer contador, re-inicializando: {e}")
            self._initialize_counter()
            try:
                 with open(self.counter_file, 'r') as f:
                    current_id = int(f.read().strip())
            except Exception:
                # Caso extremo si todo falla, devolver None.
                return None
            
        new_id = current_id + 1
        
        # 2. Guardar el nuevo ID
        self._save_counter(new_id)
            
        return str(new_id)

    @staticmethod
    def generar_id_registro(data_tuple):
        """Genera un ID alfanumérico corto (hash) a partir de los datos."""
        # Unimos los datos clave (ID estudiante, periodo, profesor) en una cadena
        data_str = "".join(map(str, data_tuple))
        # Usamos SHA256 y tomamos los primeros 8 caracteres para un ID corto y único
        return hashlib.sha256(data_str.encode()).hexdigest()[:8]

# Instancia del generador (Ahora se inicializa de forma segura)
id_manager = GeneradorIDs()

# --- 3. FUNCIONES DE GESTIÓN DE DATOS (CSV/Pandas) ---

def inicializar_csv():
    """Crea el archivo CSV con los encabezados si no existe."""
    if not os.path.exists(ARCHIVO_CSV):
        # Usamos la constante COLUMNS definida globalmente
        
        try:
            # Crear un DataFrame vacío y guardarlo para crear el archivo con encabezados
            df_vacio = pd.DataFrame(columns=COLUMNS)
            df_vacio.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8')
            print(f"Archivo de registro '{ARCHIVO_CSV}' inicializado.")
        except Exception as e:
            print(f"Error al inicializar el CSV: {e}")

def cargar_datos():
    """Carga los datos del CSV a un DataFrame de Pandas."""
    try:
        if not os.path.exists(ARCHIVO_CSV):
            inicializar_csv()
            # Si se acaba de inicializar, la lectura del CSV debe realizarse
            
        df = pd.read_csv(ARCHIVO_CSV, encoding='utf-8')
        
        # Validación extra: si el DF está vacío después de la lectura, asegurarse de que tiene las columnas.
        if df.empty and df.shape[1] < len(COLUMNS):
             return pd.DataFrame(columns=COLUMNS)
            
        # FIX CLAVE: Convertir columnas de ID a string para evitar errores de tipo al filtrar
        if 'profesor_ID' in df.columns:
            df['profesor_ID'] = df['profesor_ID'].astype(str)
        if 'estudiante_ID' in df.columns:
            df['estudiante_ID'] = df['estudiante_ID'].astype(str)
            
        # Llenamos valores nulos de las columnas de notas para evitar errores de tipo
        df['P_NOTA_FINAL'] = df['P_NOTA_FINAL'].fillna(ESTADO_INICIAL_NOTA)
        df['promedio_general'] = df['promedio_general'].fillna(ESTADO_INICIAL_NOTA)
        return df
        
    except pd.errors.EmptyDataError:
        print("El archivo CSV está vacío, se cargará un DataFrame vacío.")
        # FIX: Devolver un DataFrame vacío pero con las columnas correctas.
        return pd.DataFrame(columns=COLUMNS)
        
    except Exception as e:
        print(f"Error al cargar los datos: {e}")
        # FIX: Devolver un DataFrame vacío con las columnas correctas como fallback.
        return pd.DataFrame(columns=COLUMNS)

def guardar_datos(df):
    """Guarda el DataFrame en el archivo CSV."""
    try:
        df.to_csv(ARCHIVO_CSV, index=False, encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error al guardar los datos: {e}")
        return False

# --- 4. FUNCIONES DE UTILIDAD Y CÁLCULO ---

def verificar_permiso(user_id, accion):
    """Verifica si el usuario tiene permiso para realizar una acción."""
    if user_id not in USUARIOS_MOCK:
        print("Error: Usuario no encontrado.")
        return False
        
    rol = USUARIOS_MOCK[user_id]
    
    if accion in PERMISOS_ROLES[rol]:
        return PERMISOS_ROLES[rol][accion]
        
    return False

def calcular_nota_final(detalles):
    """Calcula la nota final (0-100) usando los pesos ponderados."""
    nota_final = 0
    for campo, peso in PESOS_CALIFICACION.items():
        try:
            # Asumimos que los valores en detalles están entre 0 y 100
            valor = float(detalles.get(campo, 0)) 
            nota_final += valor * peso
        except ValueError:
            # Manejo de error si el valor no es numérico
            print(f"Advertencia: El valor de '{campo}' no es numérico y se tratará como 0.")
    return round(nota_final, 2)

def convertir_a_letra(nota):
    """Convierte la nota numérica a la escala tradicional (A+, A, F, etc.)."""
    nota = float(nota)
    for limite, letra in sorted(ESCALA_CALIFICACION.items(), reverse=True):
        if nota >= limite:
            return letra
    return 'F' # Fallback

def check_alerts(df, user_id):
    """Verifica y muestra alertas de periodos incompletos o vencidos."""
    rol = USUARIOS_MOCK.get(user_id)
    
    # Solo Profesores, Admin, Director, Registro reciben alertas
    if rol not in [ROLES['PROFESOR'], ROLES['ADMIN'], ROLES['DIRECTOR'], ROLES['REGISTRO']]:
        return
        
    alertas = []
    
    # Simulación del periodo actual (en una app real se obtendría del sistema)
    periodo_actual = 'P1' # Asumimos P1 para el ejemplo
    
    # 1. Alerta de campos obligatorios sin llenar (Metodología/Nota)
    registros_pendientes = df[
        (df['profesor_ID'] == user_id) & 
        (df['periodo'] == periodo_actual) &
        (df['estado_publicacion'] == False) & # En borrador
        (df['P_METODO_ENS'].isnull())
    ]
    
    if not registros_pendientes.empty:
        alertas.append(f"¡ALERTA! Tienes {len(registros_pendientes)} calificaciones en borrador para el {periodo_actual} sin el 'Método de Enseñanza' obligatorio. No se podrán publicar.")

    # 2. Alerta de periodo vencido 
    
    if rol in [ROLES['DIRECTOR'], ROLES['ADMIN']]:
        # Para el ejemplo, alertamos si el periodo P1 no está publicado en general
        if df[(df['periodo'] == 'P1') & (df['estado_publicacion'] == True)].empty:
            alertas.append("¡ALERTA ADMINISTRATIVA! El Periodo P1 no ha sido publicado. Esto debe corregirse para pasar al siguiente periodo.")

    if alertas:
        print("\n" + "="*50)
        print(f"ALERTA DEL SISTEMA - Usuario {rol} ({user_id}):")
        for a in alertas:
            print(f"-> {a}")
        print("="*50 + "\n")


# --- 5. LÓGICA DE INTERACCIÓN POR TERMINAL (MENÚS Y FLUJOS) ---

def menu_login():
    """
    Menú de inicio de sesión.
    Permite salir del sistema escribiendo 'X'.
    """
    print("\n--- Sistema de Calificaciones Académicas ---")
    print("Inicie sesión con su ID de usuario o escriba 'X' para salir.")
    
    while True:
        # Convertir a mayúsculas para manejar 'x' o 'X'
        user_id = input("Ingrese su ID de Usuario: ").strip().upper() 
        
        if user_id == 'X':
            print("Saliendo del sistema.")
            # Retornar None, None para indicar que se debe romper el bucle principal
            return None, None 
            
        if user_id in USUARIOS_MOCK:
            rol = USUARIOS_MOCK[user_id]
            print(f"\nBienvenido/a, {rol} (ID: {user_id}).")
            return user_id, rol
        else:
            print("ID no válido. Intente de nuevo o escriba 'X' para salir.")

def gestionar_calificaciones(df, user_id, periodo='P1'):
    """
    Permite al profesor llenar, guardar y publicar calificaciones para múltiples estudiantes.
    """
    
    if not verificar_permiso(user_id, 'llenar_notas'):
        print("Permiso denegado: No tienes permiso para llenar calificaciones.")
        return df

    print(f"\n--- GESTIÓN DE CALIFICACIONES - PERIODO {periodo} ---")
    
    # Simulación de estudiantes en el curso del profesor (para el ejemplo, todos los estudiantes)
    estudiantes_ids = [k for k, v in USUARIOS_MOCK.items() if v == ROLES['ESTUDIANTE']]
    if not estudiantes_ids:
        print("No hay estudiantes registrados.")
        return df
        
    print(f"Estudiantes a calificar: {', '.join(estudiantes_ids)}")
    
    nuevos_registros = []
    
    for est_id in estudiantes_ids:
        
        # Buscar registro existente (borrador o publicado)
        # Aseguramos que est_id sea string antes de filtrar por si acaso
        registro_existente = df[
            (df['estudiante_ID'] == str(est_id)) & 
            (df['periodo'] == periodo)
        ]
        
        is_published = False
        
        if not registro_existente.empty:
            record = registro_existente.iloc[0]
            is_published = record['estado_publicacion']
            
            # Bloquear si ya está publicado y el usuario no es Director/Registro
            if is_published and not verificar_permiso(user_id, 'modificar_publicada'):
                print(f"-> Estudiante {est_id}: Calificación de {periodo} YA PUBLICADA y bloqueada para usted.")
                continue

            print(f"\n[EDITANDO] Calificación existente para Estudiante {est_id}.")
            # Se asegura que la columna 'P_DETALLES_JSON' contenga un string JSON válido o un diccionario vacío
            detalles_json_str = record['P_DETALLES_JSON']
            if isinstance(detalles_json_str, str):
                try:
                    detalles_previos = json.loads(detalles_json_str)
                except json.JSONDecodeError:
                    detalles_previos = {}
            else:
                detalles_previos = {}
                
            metodo_previo = record['P_METODO_ENS']
        else:
            print(f"\n[NUEVO] Llenando calificación para Estudiante {est_id}.")
            detalles_previos = {}
            metodo_previo = ""


        # Llenado de campos de calificación
        detalles_notas = {}
        for campo in CALIFICACION_CAMPOS:
            prompt = f"Ingrese nota para '{campo}' ({int(PESOS_CALIFICACION[campo]*100)}%): "
            while True:
                try:
                    # Usar valor previo si existe
                    valor_defecto = detalles_previos.get(campo, 0)
                    nota_input = input(f"{prompt} (Actual: {valor_defecto}): ") or str(valor_defecto)
                    nota = float(nota_input)
                    if 0 <= nota <= 100:
                        detalles_notas[campo] = nota
                        break
                    else:
                        print("La nota debe estar entre 0 y 100.")
                except ValueError:
                    print("Entrada no válida. Ingrese un número.")

        # Llenado del Método de Enseñanza (Obligatorio)
        metodo_ens = input(f"Método de Enseñanza (OBLIGATORIO) (Actual: {metodo_previo}): ") or metodo_previo
        if not metodo_ens:
            print("ADVERTENCIA: El campo 'Método de Enseñanza' es obligatorio para la publicación.")
            
        # Cálculo y Preparación del Registro
        nota_final = calcular_nota_final(detalles_notas)
        
        nuevo_registro = {
            'estudiante_ID': est_id,
            'profesor_ID': user_id,
            'periodo': periodo,
            'fecha_publicacion': ESTADO_INICIAL_NOTA, # Pendiente
            'estado_publicacion': False,
            'estado_revision': 'N/A',
            'P_NOTA_FINAL': nota_final,
            'P_METODO_ENS': metodo_ens,
            'P_DETALLES_JSON': json.dumps(detalles_notas), # Almacenar como JSON String
            'promedio_general': ESTADO_INICIAL_NOTA # Se calcula al final
        }
        
        if registro_existente.empty:
            # Nuevo registro: Generar nuevo ID de registro
            nuevo_registro['ID_REGISTRO'] = id_manager.generar_id_registro((est_id, periodo, user_id, datetime.now()))
            nuevos_registros.append(nuevo_registro)
        else:
            # Actualizar registro existente (inplace en el DataFrame)
            idx = registro_existente.index[0]
            for key, val in nuevo_registro.items():
                df.at[idx, key] = val

    # Agregar nuevos registros al DataFrame principal
    if nuevos_registros:
        df_nuevos = pd.DataFrame(nuevos_registros)
        df = pd.concat([df, df_nuevos], ignore_index=True)
    
    print("\n--- RESUMEN DE CAMBIOS ---")
    # El DF actualizado ya tiene profesor_ID como string, el filtro es seguro.
    print(df[df['profesor_ID'] == user_id].tail(len(estudiantes_ids))[['estudiante_ID', 'periodo', 'P_NOTA_FINAL', 'P_METODO_ENS', 'estado_publicacion']])
    
    # Pregunta de Publicación
    confirmacion = input("\n¿Desea PUBLICAR las calificaciones de este periodo ahora? (Escriba 'si' para publicar): ").strip().lower()
    if confirmacion == 'si' and verificar_permiso(user_id, 'publicar_notas'):
        # Aplicar publicación a todos los registros no publicados del profesor para este periodo
        idx_a_publicar = df[
            (df['profesor_ID'] == user_id) & 
            (df['periodo'] == periodo) & 
            (df['estado_publicacion'] == False) &
            (df['P_METODO_ENS'].notnull()) # Solo si el campo obligatorio está lleno
        ].index
        
        if idx_a_publicar.empty:
            print("\nADVERTENCIA: No se publicaron notas. Asegúrese de que el campo 'Método de Enseñanza' esté lleno en todos los registros.")
        else:
            df.loc[idx_a_publicar, 'estado_publicacion'] = True
            df.loc[idx_a_publicar, 'fecha_publicacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n¡ÉXITO! {len(idx_a_publicar)} calificaciones han sido publicadas y BLOQUEADAS para edición por el profesor.")
            
    guardar_datos(df)
    return df

def solicitar_revision(df, user_id, periodo='P1'):
    """Permite al estudiante 'apelar' una calificación."""
    
    registro = df[
        (df['estudiante_ID'] == user_id) & 
        (df['periodo'] == periodo) &
        (df['estado_publicacion'] == True)
    ]
    
    if registro.empty:
        print("No hay calificaciones publicadas para este periodo que puedas apelar.")
        return df
        
    print(f"\n--- SOLICITUD DE REVISIÓN DE CALIFICACIÓN ({periodo}) ---")
    
    idx = registro.index[0]
    
    estado = df.at[idx, 'estado_revision']
    if estado == 'PENDIENTE':
        print("Tu solicitud de revisión ya está PENDIENTE. Espera la respuesta del profesor.")
        return df
        
    if estado == 'RESUELTA':
        print("Tu solicitud anterior fue RESUELTA. Si la nota es incorrecta, habla con tu profesor/a.")
        return df

    comentario = input("Explica brevemente por qué solicitas la revisión de tu nota: ")
    if not comentario:
        print("Solicitud cancelada. Se requiere un comentario.")
        return df
        
    df.at[idx, 'estado_revision'] = 'PENDIENTE'
    # En una app real, aquí se notificaría al profesor asignado
    print("\n¡Tu solicitud de revisión ha sido enviada! El profesor será notificado.")
    guardar_datos(df)
    return df

# --- 6. FLUJOS DE USUARIO ---

def flujo_estudiante(df, user_id):
    """Menú y flujo para estudiantes."""
    print("\n--- Menú Estudiante ---")
    
    while True:
        registros = df[df['estudiante_ID'] == user_id]
        print(f"\nCalificaciones disponibles ({len(registros)} periodos):")
        
        # Mostrar resumen de notas
        if not registros.empty:
            for _, r in registros.iterrows():
                if r['estado_publicacion']:
                    nota_letra = convertir_a_letra(r['P_NOTA_FINAL'])
                    print(f"[{r['periodo']}] Nota: {r['P_NOTA_FINAL']} ({nota_letra}). Estado: Publicada.")
                else:
                    print(f"[{r['periodo']}] Nota: Pendiente de publicación.")
        else:
            print("No hay registros de calificación disponibles.")

        print("\nOpciones:")
        print("[1] Ver Detalles de Calificación (Requiere ID de Registro)")
        print("[2] Solicitar Revisión (Apelación)")
        print("[3] Cerrar Sesión")
        
        opcion = input("Seleccione una opción: ").strip()
        
        if opcion == '1':
            registro_id = input("Ingrese el ID de Registro para ver detalles: ").strip()
            reg = df[(df['ID_REGISTRO'] == registro_id) & (df['estudiante_ID'] == user_id)]
            
            if reg.empty or not reg.iloc[0]['estado_publicacion']:
                print("ID de registro no válido o nota no publicada.")
                continue
                
            detalles = json.loads(reg.iloc[0]['P_DETALLES_JSON'])
            print("\n--- DETALLES DE CALIFICACIÓN ---")
            for campo, nota in detalles.items():
                peso = PESOS_CALIFICACION.get(campo, 0) * 100
                print(f"- {campo} ({peso:.1f}%): {nota}")
            print(f"-> NOTA FINAL PERIODO: {reg.iloc[0]['P_NOTA_FINAL']}")
            print(f"-> NOTA TRADICIONAL: {convertir_a_letra(reg.iloc[0]['P_NOTA_FINAL'])}")
            
        elif opcion == '2':
            # Asumimos que la apelación es sobre el último periodo
            global flujo_global_df
            flujo_global_df = solicitar_revision(df, user_id)
            
        elif opcion == '3':
            break
        else:
            print("Opción no válida.")


def flujo_profesor(df, user_id):
    """Menú y flujo para profesores."""
    # check_alerts ahora es seguro porque df siempre tiene las columnas.
    check_alerts(df, user_id) 
    
    while True:
        print("\n--- Menú Profesor/a ---")
        print("[1] Llenar/Editar/Publicar Calificaciones (P1, P2, P3, P4)")
        print("[2] Revisar Solicitudes de Apelación")
        print("[3] Ver Resumen de Calificaciones Publicadas")
        print("[4] Cerrar Sesión")
        
        opcion = input("Seleccione una opción: ").strip()
        
        if opcion == '1':
            periodo = input("Ingrese el periodo a gestionar (P1, P2, P3, P4): ").strip().upper()
            if periodo in ['P1', 'P2', 'P3', 'P4']:
                global flujo_global_df
                # La función gestiona y devuelve el DF actualizado
                flujo_global_df = gestionar_calificaciones(flujo_global_df, user_id, periodo)
                # Actualizamos la referencia local 'df' para el bucle actual
                df = flujo_global_df
            else:
                print("Periodo no válido.")
                
        elif opcion == '2':
            pendientes = df[
                (df['profesor_ID'] == user_id) & 
                (df['estado_revision'] == 'PENDIENTE')
            ]
            
            if pendientes.empty:
                print("No hay solicitudes de apelación pendientes.")
                continue
                
            print(f"\n--- SOLICITUDES PENDIENTES ({len(pendientes)}) ---")
            for _, r in pendientes.iterrows():
                print(f"Estudiante ID: {r['estudiante_ID']}, Periodo: {r['periodo']}, ID Reg: {r['ID_REGISTRO']}")
            
            # Opción simple: Resolver todas
            resolver = input("Resolver todas las solicitudes (s/n)? ").strip().lower()
            if resolver == 's':
                flujo_global_df.loc[pendientes.index, 'estado_revision'] = 'RESUELTA'
                guardar_datos(flujo_global_df)
                print("Solicitudes resueltas. Debe contactar al estudiante sobre el resultado.")
            
        elif opcion == '3':
            # FIX: Recargar el DataFrame para asegurar que se vean los últimos cambios guardados en el CSV
            df_actualizado = cargar_datos() 
            resumen = df_actualizado[df_actualizado['profesor_ID'] == user_id][['estudiante_ID', 'periodo', 'P_NOTA_FINAL', 'estado_publicacion']]
            print("\n--- RESUMEN DE MIS CALIFICACIONES ---")
            print(resumen)
            
        elif opcion == '4':
            break
        else:
            print("Opción no válida.")

def flujo_admin_registro(df, user_id):
    """Menú para Administración y Encargada de Registro."""
    rol = USUARIOS_MOCK[user_id]
    check_alerts(df, user_id)
    
    while True:
        print(f"\n--- Menú {rol} ---")
        print("[1] Ver TODAS las Calificaciones")
        
        if verificar_permiso(user_id, 'modificar_publicada'):
            print("[2] Modificar Calificación Publicada (Hasta 7 días)")
            
        if verificar_permiso(user_id, 'administrar_usuarios'):
            print("[3] Administrar Usuarios Comunes (Crear nuevos Profesor/Estudiante)")
            
        print("[4] Cerrar Sesión")
        
        opcion = input("Seleccione una opción: ").strip()
        
        if opcion == '1':
            # Recargar para el caso de que otro profesor haya publicado
            df_actualizado = cargar_datos()
            print("\n--- REGISTRO GENERAL DE CALIFICACIONES ---")
            print(df_actualizado[['estudiante_ID', 'profesor_ID', 'periodo', 'P_NOTA_FINAL', 'estado_publicacion', 'fecha_publicacion']])
            
        elif opcion == '2' and verificar_permiso(user_id, 'modificar_publicada'):
            reg_id = input("Ingrese el ID de Registro a modificar: ").strip()
            # El DF ya debe tener los IDs como string gracias a cargar_datos()
            registro = df[df['ID_REGISTRO'] == reg_id]
            
            if registro.empty:
                print("ID de registro no encontrado.")
                continue
                
            idx = registro.index[0]
            fecha_pub = registro.iloc[0]['fecha_publicacion']
            
            # Regla de los 7 días
            if fecha_pub != ESTADO_INICIAL_NOTA:
                fecha_limite = datetime.strptime(fecha_pub, "%Y-%m-%d %H:%M:%S") + timedelta(days=7)
                if datetime.now() > fecha_limite:
                    print("ERROR: Han pasado más de 7 días desde la publicación. Ningún usuario puede modificarla.")
                    continue
            
            print(f"Modificando nota publicada. Nota actual: {registro.iloc[0]['P_NOTA_FINAL']}")
            try:
                nueva_nota = float(input("Ingrese la NUEVA nota final (0-100): "))
                if 0 <= nueva_nota <= 100:
                    df.at[idx, 'P_NOTA_FINAL'] = nueva_nota
                    # Opcional: limpiar la revisión si se modifica la nota
                    df.at[idx, 'estado_revision'] = 'RESUELTA' 
                    guardar_datos(df)
                    print(f"Nota para {reg_id} modificada exitosamente por {rol}.")
                else:
                    print("Nota fuera de rango.")
            except ValueError:
                print("Entrada no válida.")
                
        elif opcion == '3' and verificar_permiso(user_id, 'administrar_usuarios'):
            print("\n--- GESTIÓN DE USUARIOS ---")
            nuevo_rol = input("Rol a crear (Profesor/Estudiante): ").strip().capitalize()
            if nuevo_rol in ['Profesor', 'Estudiante']:
                new_id = id_manager.generar_id_secuencial()
                if new_id is None:
                    print("Error: No se pudo generar una ID segura.")
                    continue
                    
                # Agregar el nuevo usuario al diccionario MOCK
                USUARIOS_MOCK[new_id] = ROLES[nuevo_rol.upper()]
                print(f"Nuevo {nuevo_rol} creado con ID: {new_id} (Garantizado que no se duplica).")
            else:
                print("Rol no reconocido.")
                
        elif opcion == '4':
            break
        else:
            print("Opción no válida.")


def flujo_director(df, user_id):
    """Menú y flujo para la Directora."""
    check_alerts(df, user_id)
    
    while True:
        print("\n--- Menú Directora (TODOS LOS PERMISOS) ---")
        print("[1] Acceso a Gestión de Calificaciones (Profesor)")
        print("[2] Modificar Calificación Publicada (Incluso después de 7 días)")
        print("[3] Suspender/Expulsar Usuarios (Mock)")
        print("[4] Anular Alerta Administrativa (Mock)")
        print("[5] Ver TODOS los Registros")
        print("[6] Crear nuevos Profesor/Estudiante") # Opción agregada para consistencia
        print("[7] Cerrar Sesión")
        
        opcion = input("Seleccione una opción: ").strip()
        
        if opcion == '1':
            periodo = input("Ingrese el periodo a gestionar (P1-P4): ").strip().upper()
            if periodo in ['P1', 'P2', 'P3', 'P4']:
                # El director puede usar la función de profesor
                global flujo_global_df
                flujo_global_df = gestionar_calificaciones(flujo_global_df, user_id, periodo)
                df = flujo_global_df # Actualizamos referencia local
            
        elif opcion == '2':
            reg_id = input("Ingrese el ID de Registro a modificar: ").strip()
            registro = df[df['ID_REGISTRO'] == reg_id]
            
            if registro.empty:
                print("ID de registro no encontrado.")
                continue
                
            idx = registro.index[0]
            print(f"MODIFICACIÓN EXCLUSIVA. Nota actual: {registro.iloc[0]['P_NOTA_FINAL']}")
            try:
                nueva_nota = float(input("Ingrese la NUEVA nota final (0-100): "))
                if 0 <= nueva_nota <= 100:
                    df.at[idx, 'P_NOTA_FINAL'] = nueva_nota
                    guardar_datos(df)
                    print(f"Nota para {reg_id} modificada exitosamente por la Directora.")
                else:
                    print("Nota fuera de rango.")
            except ValueError:
                print("Entrada no válida.")

        elif opcion == '3':
            target_id = input("Ingrese el ID de usuario a suspender/expulsar (Mock): ").strip()
            if target_id in USUARIOS_MOCK and target_id != user_id:
                print(f"Usuario {target_id} (Rol: {USUARIOS_MOCK[target_id]}) ha sido suspendido (Mock).")
            else:
                print("ID no válido o no puedes modificar tu propio ID.")
                
        elif opcion == '4':
            print("Alerta Administrativa ANULADA. El sistema no alertará hasta el próximo reinicio. (Mock)")
            
        elif opcion == '5':
            # Recargar para ver todos los cambios
            df_actualizado = cargar_datos()
            print("\n--- REGISTRO GENERAL DE CALIFICACIONES ---")
            print(df_actualizado)
        
        elif opcion == '6':
            print("\n--- GESTIÓN DE USUARIOS ---")
            nuevo_rol = input("Rol a crear (Profesor/Estudiante): ").strip().capitalize()
            if nuevo_rol in ['Profesor', 'Estudiante']:
                new_id = id_manager.generar_id_secuencial()
                if new_id is None:
                    print("Error: No se pudo generar una ID segura.")
                    continue
                    
                USUARIOS_MOCK[new_id] = ROLES[nuevo_rol.upper()]
                print(f"Nuevo {nuevo_rol} creado con ID: {new_id} (Garantizado que no se duplica).")
            else:
                print("Rol no reconocido.")
            
        elif opcion == '7':
            break
        else:
            print("Opción no válida.")


# --- 7. BUCLE PRINCIPAL Y CONTROL DE ERRORES ---

def main():
    """Función principal que ejecuta la aplicación."""
    global flujo_global_df
    print("Inicializando Sistema...")
    
    # 1. Inicialización de datos
    flujo_global_df = cargar_datos()
    
    while True:
        try:
            user_id, rol = menu_login()
            
            # Si menu_login retorna None, None, el usuario eligió salir.
            if user_id is None: 
                break 
            
            # Se usa flujo_global_df como la base de datos actual para todos los flujos.
            if rol == ROLES['ESTUDIANTE']:
                flujo_estudiante(flujo_global_df, user_id)
            elif rol == ROLES['PROFESOR']:
                flujo_profesor(flujo_global_df, user_id)
            elif rol == ROLES['ADMIN'] or rol == ROLES['REGISTRO']:
                flujo_admin_registro(flujo_global_df, user_id)
            elif rol == ROLES['DIRECTOR']:
                flujo_director(flujo_global_df, user_id)
            
            # Este mensaje se muestra solo si el usuario cierra sesión desde un menú de rol
            print("\nSesión cerrada. Volviendo al menú principal.")

        except Exception as e:
            # Control de Errores: Captura cualquier error inesperado
            print("\n" + "="*50)
            print(f"*** ERROR CRÍTICO DEL PROGRAMA ***")
            # Mostrar un mensaje más detallado para el desarrollador/usuario avanzado
            print(f"Se ha producido un error inesperado (Detalles: {e}).")
            print("El sistema intentará continuar...")
            print("="*50 + "\n")
            
if __name__ == "__main__":
    main()