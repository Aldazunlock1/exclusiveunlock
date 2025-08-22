import telebot
import requests
import json
import os
import time
import logging
from datetime import datetime, timedelta
from telebot import types
from flask import Flask, request, render_template_string, jsonify
import threading
import signal
import sys
from collections import deque
import psutil

# =================== CONFIGURACIÓN ===================
# CORRECCIÓN: Verificación obligatoria de variables de entorno
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("API_KEY")
API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://alpha.imeicheck.com/api/php-api/create")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 5000))

# Verificar variables críticas
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN no encontrado en variables de entorno")
    sys.exit(1)

if not API_KEY:
    print("❌ ERROR: API_KEY no encontrado en variables de entorno")
    sys.exit(1)

if not WEBHOOK_URL:
    print("❌ ERROR: WEBHOOK_URL no encontrado en variables de entorno")
    sys.exit(1)

# Variables globales para control y estadísticas
server_running = True
start_time = datetime.now()
request_count = 0
error_count = 0
last_activity = datetime.now()

# Logs en memoria (últimas 100 entradas)
memory_logs = deque(maxlen=100)
activity_log = deque(maxlen=50)

AUTHORIZED_USERS = {
    7655366089: {"role": "admin", "name": "Admin Principal", "credits": -1},
    6269867784: {"role": "premium", "name": "Usuario Premium", "credits": 80},
}

SERVICES = {
    "apple": {
        "name": "🍎 Apple Services",
        "emoji": "🍎",
        "services": {
            "1": {"name": "Find My iPhone [FMI] (ON/OFF)", "desc": "Verificar estado FMI", "credits": 1},
            "2": {"name": "Warranty + Activation - PRO", "desc": "Info de garantía profesional", "credits": 2},
            "3": {"name": "Apple FULL INFO [No Carrier]", "desc": "Información completa sin carrier", "credits": 7},
            "4": {"name": "iCloud Clean/Lost Check", "desc": "Estado de iCloud limpio/perdido", "credits": 2},
            "9": {"name": "SOLD BY + GSX - UPDATED", "desc": "Info de venta + GSX actualizado", "credits": 169},
            "12": {"name": "GSX Next Tether + iOS", "desc": "GSX Carrier con iOS", "credits": 60},
            "13": {"name": "Model + Color + Storage + FMI", "desc": "Modelo, color, almacenamiento y FMI", "credits": 2},
            "18": {"name": "iMac FMI Status On/Off", "desc": "Estado FMI para iMac", "credits": 30},
            "19": {"name": "Apple FULL INFO [+Carrier] B", "desc": "Info completa con carrier B", "credits": 12},
            "20": {"name": "Apple SimLock Check", "desc": "Verificar bloqueo SIM", "credits": 2},
            "22": {"name": "Apple BASIC INFO (PRO) - new", "desc": "Info básica profesional nueva", "credits": 4},
            "23": {"name": "Apple Carrier Check (S2)", "desc": "Verificación de carrier S2", "credits": 4},
            "33": {"name": "Replacement Status (Active Device)", "desc": "Estado de reemplazo dispositivo activo", "credits": 1},
            "34": {"name": "Replaced Status (Original Device)", "desc": "Estado reemplazado dispositivo original", "credits": 1},
            "39": {"name": "Apple FULL INFO [+Carrier] A", "desc": "Info completa con carrier A", "credits": 10},
            "41": {"name": "MDM Status ON/OFF", "desc": "Estado MDM activado/desactivado", "credits": 22},
            "46": {"name": "MDM Status + GSX Policy + FMI", "desc": "MDM + política GSX + FMI", "credits": 45},
            "47": {"name": "Apple FULL + MDM + GSMA PRO", "desc": "Info completa + MDM + GSMA Pro", "credits": 75},
            "50": {"name": "Apple SERIAL Info", "desc": "Info de serial Apple", "credits": 1},
            "51": {"name": "Warranty + Activation [SN ONLY]", "desc": "Garantía + activación solo serial", "credits": 1},
            "52": {"name": "Model Description (Any Apple)", "desc": "Descripción modelo cualquier Apple", "credits": 2},
            "61": {"name": "Apple Demo Unit Device Info", "desc": "Info dispositivo demo Apple", "credits": 14},
            "64": {"name": "Model Description - Emergency", "desc": "Descripción modelo emergencia", "credits": 1}
        }
    },
    "samsung": {
        "name": "📱 Samsung",
        "emoji": "📱",
        "services": {
            "8": {"name": "Samsung Info (S1)", "desc": "Información Samsung S1", "credits": 4},
            "21": {"name": "Samsung INFO & KNOX STATUS (S2)", "desc": "Info Samsung + estado Knox S2", "credits": 14},
            "36": {"name": "Samsung Info (S1) + Blacklist", "desc": "Info Samsung S1 + lista negra", "credits": 6},
            "37": {"name": "Samsung Info & KNOX STATUS (S1)", "desc": "Info Samsung + Knox S1", "credits": 9}
        }
    },
    "carriers": {
        "name": "📡 Carriers US",
        "emoji": "📡",
        "services": {
            "15": {"name": "T-mobile (ESN) PRO Check", "desc": "Verificación T-Mobile ESN", "credits": 4},
            "16": {"name": "Verizon (ESN) Clean/Lost Status", "desc": "Estado Verizon limpio/perdido", "credits": 3}
        }
    },
    "chinese": {
        "name": "🏮 Chinese Brands",
        "emoji": "🏮",
        "services": {
            "17": {"name": "Huawei IMEI Info", "desc": "Información Huawei", "credits": 7},
            "25": {"name": "XIAOMI MI LOCK & INFO", "desc": "Bloqueo Mi e info Xiaomi", "credits": 5},
            "27": {"name": "ONEPLUS IMEI INFO", "desc": "Información OnePlus", "credits": 4},
            "58": {"name": "Honor Info", "desc": "Información Honor", "credits": 5},
            "59": {"name": "Realme Info", "desc": "Información Realme", "credits": 3},
            "60": {"name": "Oppo Info", "desc": "Información Oppo", "credits": 3}
        }
    },
    "other_brands": {
        "name": "📱 Other Brands",
        "emoji": "📱",
        "services": {
            "57": {"name": "Google Pixel Info", "desc": "Información Google Pixel", "credits": 12},
            "63": {"name": "Motorola Info", "desc": "Información Motorola", "credits": 5}
        }
    },
    "general": {
        "name": "🌐 Universal",
        "emoji": "🌐",
        "services": {
            "5": {"name": "Blacklist Status (GSMA)", "desc": "Estado lista negra GSMA", "credits": 2},
            "6": {"name": "Blacklist Pro Check (GSMA)", "desc": "Verificación profesional GSMA", "credits": 8},
            "10": {"name": "IMEI to Model [all brands]", "desc": "IMEI a modelo todas las marcas", "credits": 1},
            "11": {"name": "IMEI to Brand/Model/Name", "desc": "IMEI a marca/modelo/nombre", "credits": 1},
            "14": {"name": "IMEI to SN (Full Convertor)", "desc": "Conversor completo IMEI a SN", "credits": 2},
            "55": {"name": "Blacklist Status - cheap", "desc": "Estado lista negra económico", "credits": 1},
            "62": {"name": "EID INFO (IMEI TO EID)", "desc": "Información EID desde IMEI", "credits": 2}
        }
    }
}

# =================== LOGGING PERSONALIZADO ===================
class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'message': self.format(record),
            'module': record.module if hasattr(record, 'module') else 'unknown'
        }
        memory_logs.append(log_entry)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        MemoryLogHandler()
    ]
)
logger = logging.getLogger(__name__)

def add_activity_log(user_id, action, details=""):
    """Agregar entrada al log de actividad"""
    global last_activity
    last_activity = datetime.now()
    activity_entry = {
        'timestamp': last_activity.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': user_id,
        'action': action,
        'details': details
    }
    activity_log.append(activity_entry)

# =================== BOT ===================
# CORRECCIÓN: Manejo de errores en inicialización del bot
try:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
    logger.info("✅ Bot inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando bot: {e}")
    sys.exit(1)

user_data = {}

# =================== FUNCIONES DE CONTROL ===================
def signal_handler(sig, frame):
    global server_running
    logger.info("🛑 Señal de parada recibida, cerrando servidor...")
    server_running = False
    sys.exit(0)

def keep_alive():
    """Función para mantener el bot activo y hacer health checks periódicos"""
    while server_running:
        try:
            time.sleep(300)  # 5 minutos
            if server_running:
                bot.get_me()
                logger.info("🔄 Bot health check: OK")
        except Exception as e:
            logger.warning(f"⚠️ Health check warning: {e}")
            time.sleep(60)

def get_system_stats():
    """Obtener estadísticas del sistema"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used': round(memory.used / 1024 / 1024, 2),
            'memory_total': round(memory.total / 1024 / 1024, 2),
            'disk_percent': disk.percent,
            'disk_used': round(disk.used / 1024 / 1024 / 1024, 2),
            'disk_total': round(disk.total / 1024 / 1024 / 1024, 2)
        }
    except:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used': 0,
            'memory_total': 0,
            'disk_percent': 0,
            'disk_used': 0,
            'disk_total': 0
        }

def verify_environment():
    """Verifica que todas las variables de entorno estén configuradas"""
    required_vars = {
        'BOT_TOKEN': BOT_TOKEN,
        'API_KEY': API_KEY,
        'WEBHOOK_URL': WEBHOOK_URL
    }
    
    missing = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing.append(var_name)
            logger.error(f"❌ Variable de entorno faltante: {var_name}")
    
    if missing:
        logger.error(f"❌ Variables faltantes: {', '.join(missing)}")
        return False
    
    logger.info("✅ Todas las variables de entorno configuradas correctamente")
    return True

# =================== FUNCIONES AUXILIARES ===================
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

def get_user_info(user_id):
    return AUTHORIZED_USERS.get(user_id, None)

def has_credits(user_id, required):
    user_info = get_user_info(user_id)
    if not user_info:
        return False
    credits = user_info.get("credits", 0)
    return credits == -1 or credits >= required

def update_credits(user_id, used):
    if user_id in AUTHORIZED_USERS:
        current = AUTHORIZED_USERS[user_id].get("credits", 0)
        if current != -1:
            AUTHORIZED_USERS[user_id]["credits"] = max(0, current - used)
            logger.info(f"💳 Usuario {user_id} gastó {used} créditos. Restante: {AUTHORIZED_USERS[user_id]['credits']}")

def clean_html(html_content):
    import re
    text = html_content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('\\u003C', '<').replace('\\u003E', '>')
    text = re.sub(r'<[^>]+>', '', text)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def validate_imei(text):
    text = ''.join(c for c in text if c.isalnum())
    return 8 <= len(text) <= 20

def make_api_request(service_id, imei):
    global request_count, error_count
    try:
        request_count += 1
        url = f"{API_ENDPOINT}?key={API_KEY}&service={service_id}&imei={imei}"
        logger.info(f"🌐 API Request: Service {service_id}, IMEI: {imei[:4]}***")
        response = requests.get(url, timeout=45)
        if response.status_code == 200:
            try:
                return {'status': 'success', 'data': response.json()}
            except:
                return {'status': 'success', 'data': {'result': response.text}}
        else:
            error_count += 1
            return {'status': 'failed', 'message': f'HTTP {response.status_code}'}
    except Exception as e:
        error_count += 1
        logger.error(f"❌ Error API: {e}")
        return {'status': 'failed', 'message': str(e)}

def format_field_value(field_key, value):
    """Formatea el valor de un campo específico con emojis apropiados"""
    field_lower = field_key.lower()
    value_lower = value.lower()
    
    if any(keyword in field_lower for keyword in ['demo unit', 'refurbished', 'replaced', 'replacement']):
        if value_lower in ['no', 'false', '0']:
            return '✅️No'
        elif value_lower in ['yes', 'true', '1']:
            return '⚠️Yes'
    
    elif 'find my' in field_lower or field_lower == 'fmi':
        if value_lower in ['on', 'enabled', 'active', 'yes']:
            return '⚠️ON'
        elif value_lower in ['off', 'disabled', 'inactive', 'no']:
            return '✅️OFF'
    
    elif 'icloud' in field_lower:
        if 'clean' in value_lower:
            return '✅️Clean'
        elif any(keyword in value_lower for keyword in ['lost', 'locked', 'stolen']):
            return f'⚠️{value}'
    
    elif 'sim-lock' in field_lower or 'simlock' in field_lower:
        if 'locked' in value_lower:
            return f'⚠️Locked'
        elif 'unlocked' in value_lower or 'clean' in value_lower:
            return f'✅️{value}'
    
    elif any(keyword in field_lower for keyword in ['block', 'blacklist']):
        if any(keyword in value_lower for keyword in ['clean', 'not found', 'clear', 'no']):
            return f'✅️{value}'
        elif any(keyword in value_lower for keyword in ['blocked', 'reported', 'found', 'yes']):
            return f'⚠️{value}'
    
    elif 'warranty' in field_lower:
        return f'✅️{value}'
    
    elif any(keyword in field_lower for keyword in ['coverage', 'service']):
        if 'active' in value_lower:
            return f'✅️{value}'
        elif 'expired' in value_lower or 'inactive' in value_lower:
            return f'⚠️{value}'
    
    return value

def format_device_info(raw_data):
    """Formatea la información del dispositivo de manera estructurada"""
    if isinstance(raw_data, dict):
        if 'result' in raw_data:
            content = raw_data['result']
        else:
            content = str(raw_data)
    else:
        content = str(raw_data)
    
    clean_content = clean_html(content)
    
    field_order = [
        'Model Description', 'Model', 'Network', 'IMEI Number', 'IMEI', 'IMEI2 Number', 'IMEI2',
        'MEID', 'Serial Number', 'Warranty Status', 'Estimated Purchase Date', 'Purchase Date',
        'Purchase Country', 'Repairs and Service Coverage', 'Replaced by Apple', 'Replaced Device',
        'Replacement Device', 'Refurbished', 'Demo Unit', 'Find My iPhone', 'FMI', 'iCloud Status',
        'US Block Status', 'Blacklist Status', 'GSMA Status', 'SIM-Lock Status', 'Sim-Lock Status',
        'Locked Carrier', 'Knox Status', 'Activation Status', 'MDM Status', 'Color', 'Storage', 'Capacity'
    ]
    
    data_dict = {}
    lines = clean_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    data_dict[key] = value
    
    formatted_lines = []
    used_keys = set()
    
    for preferred_field in field_order:
        found_key = None
        found_value = None
        
        for key, value in data_dict.items():
            if key in used_keys:
                continue
            if key.lower() == preferred_field.lower():
                found_key = key
                found_value = value
                break
        
        if not found_key:
            for key, value in data_dict.items():
                if key in used_keys:
                    continue
                if preferred_field.lower() in key.lower() or key.lower() in preferred_field.lower():
                    found_key = key
                    found_value = value
                    break
        
        if found_key and found_value:
            used_keys.add(found_key)
            formatted_value = format_field_value(found_key, found_value)
            formatted_lines.append(f'{found_key}: {formatted_value}')
    
    for key, value in data_dict.items():
        if key not in used_keys:
            formatted_value = format_field_value(key, value)
            formatted_lines.append(f'{key}: {formatted_value}')
    
    if not formatted_lines:
        return clean_content
    
    return '\n'.join(formatted_lines)

def format_success_response(service_name, imei, data):
    response = f"✅ **CONSULTA EXITOSA**\n\n"
    response += f"📋 Servicio: {service_name}\n🔍 IMEI: `{imei}`\n\n"
    
    formatted_info = format_device_info(data)
    response += f"```\n{formatted_info}\n```"
    
    response += "\n🌐 **IaldazCheck** - exclusiveunlock.com"
    return response

def format_error_response(service_name, imei, error):
    return f"""❌ **CONSULTA FALLIDA**

📋 Servicio: {service_name}
🔍 IMEI: `{imei}`

⚠️ Error: {error}

💳 No se han debitado créditos"""

# =================== MENÚS ===================
def create_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, category in SERVICES.items():
        markup.add(types.InlineKeyboardButton(f"{category['emoji']} {category['name']} ({len(category['services'])})", callback_data=f"cat_{key}"))
    markup.add(types.InlineKeyboardButton("💳 Mis Créditos", callback_data="credits"))
    markup.add(types.InlineKeyboardButton("❓ Ayuda", callback_data="help"))
    return markup

def create_category_menu(category_key):
    markup = types.InlineKeyboardMarkup(row_width=1)
    category = SERVICES[category_key]
    for service_id, service in category["services"].items():
        markup.add(types.InlineKeyboardButton(f"• {service['name']} ({service['credits']}💳)", callback_data=f"svc_{service_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu"))
    return markup

def edit_message(call, text, markup=None):
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode='Markdown', reply_markup=markup)
    except Exception as e:
        logger.warning(f"⚠️ Edit message failed: {e}")

# =================== HANDLERS CON MANEJO DE ERRORES ===================
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.from_user.id
        logger.info(f"🔔 /start recibido de usuario {user_id}")
        add_activity_log(user_id, "START", "Usuario inició bot")
        
        if not is_authorized(user_id):
            bot.send_message(message.chat.id, f"🔒 Acceso no autorizado. Tu ID: {user_id}", parse_mode='Markdown')
            return
        
        user_info = get_user_info(user_id)
        credits_text = "Ilimitados" if user_info["credits"] == -1 else str(user_info["credits"])
        text = f"🤖 Bienvenido {user_info['name']} ({user_info['role'].title()})\n💎 Créditos: {credits_text}"
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=create_main_menu())
    except Exception as e:
        logger.error(f"❌ Error en start_command: {e}")
        try:
            bot.send_message(message.chat.id, "❌ Error interno del bot. Intenta más tarde.")
        except:
            pass

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    try:
        user_id = message.from_user.id
        add_activity_log(user_id, "CANCEL", "Operación cancelada")
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(message.chat.id, "❌ Operación cancelada", reply_markup=create_main_menu())
    except Exception as e:
        logger.error(f"❌ Error en cancel_command: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        user_id = message.from_user.id
        if not is_authorized(user_id):
            bot.send_message(message.chat.id, f"🔒 Acceso no autorizado. Tu ID: {user_id}")
            return
        
        text = message.text.strip()
        if user_id in user_data and user_data[user_id].get('waiting_for_imei'):
            if not validate_imei(text):
                bot.reply_to(message, "❌ Formato IMEI/Serial inválido. Intenta nuevamente o /cancel", parse_mode='Markdown')
                return
            process_query(message, user_id, text)
        else:
            bot.reply_to(message, "🤖 Usa /start para comenzar o selecciona una opción del menú", reply_markup=create_main_menu())
    except Exception as e:
        logger.error(f"❌ Error en handle_message: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        user_id = call.from_user.id
        if not is_authorized(user_id):
            bot.answer_callback_query(call.id, "🔒 No autorizado")
            return
        
        data = call.data
        logger.info(f"🔘 Callback de usuario {user_id}: {data}")
        
        if data == "main_menu":
            user_info = get_user_info(user_id)
            credits_text = "Ilimitados" if user_info["credits"] == -1 else str(user_info["credits"])
            text = f"🤖 {user_info['name']} ({user_info['role'].title()})\n💎 Créditos: {credits_text}"
            edit_message(call, text, create_main_menu())
            
        elif data.startswith("cat_"):
            category_key = data.split("_", 1)[1]
            add_activity_log(user_id, "BROWSE", f"Categoría: {category_key}")
            if category_key in SERVICES:
                category = SERVICES[category_key]
                text = f"{category['emoji']} **{category['name']}**\n\nSelecciona un servicio:"
                edit_message(call, text, create_category_menu(category_key))
        
        elif data.startswith("svc_"):
            service_id = data.split("_", 1)[1]
            service_info = None
            for category in SERVICES.values():
                if service_id in category["services"]:
                    service_info = category["services"][service_id]
                    break
            
            if service_info:
                add_activity_log(user_id, "SELECT", f"Servicio: {service_info['name']}")
                if not has_credits(user_id, service_info["credits"]):
                    bot.answer_callback_query(call.id, "❌ Créditos insuficientes")
                    return
                
                user_data[user_id] = {
                    'service_id': service_id,
                    'service_name': service_info['name'],
                    'credits_required': service_info['credits'],
                    'waiting_for_imei': True
                }
                
                text = f"🔍 **{service_info['name']}**\n\n"
                text += f"💳 Costo: {service_info['credits']} créditos\n"
                text += f"📝 {service_info['desc']}\n\n"
                text += "📱 Envía el IMEI/Serial número:"
                
                bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
        
        elif data == "credits":
            user_info = get_user_info(user_id)
            add_activity_log(user_id, "CHECK_CREDITS", f"Créditos: {user_info['credits']}")
            credits_text = "Ilimitados ♾️" if user_info["credits"] == -1 else f"{user_info['credits']} 💎"
            text = f"💳 **MIS CRÉDITOS**\n\n👤 Usuario: {user_info['name']}\n🏆 Rol: {user_info['role'].title()}\n💎 Créditos: {credits_text}"
            edit_message(call, text, types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")))
        
        elif data == "help":
            add_activity_log(user_id, "HELP", "Solicitó ayuda")
            text = """❓ **AYUDA**

🔹 Selecciona una categoría de servicios
🔹 Elige el servicio que necesitas
🔹 Envía el IMEI/Serial del dispositivo
🔹 Recibe el resultado al instante

💡 **Formatos válidos:**
• IMEI: 15 dígitos
• Serial: 8-20 caracteres

⚠️ Los créditos solo se debitan si la consulta es exitosa"""
            edit_message(call, text, types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")))
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"❌ Error en handle_callback: {e}")
        try:
            bot.answer_callback_query(call.id, "❌ Error interno")
        except:
            pass

def process_query(message, user_id, imei):
    try:
        data = user_data[user_id]
        service_id = data['service_id']
        service_name = data['service_name']
        credits_required = data['credits_required']
        
        logger.info(f"🛠 Usuario {user_id} realiza consulta {service_name} para IMEI {imei[:4]}***")
        add_activity_log(user_id, "QUERY", f"Servicio: {service_name}, IMEI: {imei[:4]}***")
        
        if not has_credits(user_id, credits_required):
            bot.reply_to(message, "❌ Créditos insuficientes")
            del user_data[user_id]
            return
        
        processing_msg = bot.reply_to(message, f"⏳ Procesando {service_name}...", parse_mode='Markdown')
        result = make_api_request(service_id, imei)
        
        if result['status'] == 'success':
            update_credits(user_id, credits_required)
            response = format_success_response(service_name, imei, result['data'])
            logger.info(f"✅ Consulta exitosa para usuario {user_id}")
            add_activity_log(user_id, "SUCCESS", f"Consulta exitosa: {service_name}")
        else:
            response = format_error_response(service_name, imei, result.get('message', 'Error desconocido'))
            logger.warning(f"❌ Consulta fallida para usuario {user_id}: {result.get('message')}")
            add_activity_log(user_id, "ERROR", f"Consulta fallida: {result.get('message', 'Error')}")
        
        bot.edit_message_text("✅ Procesamiento completado", message.chat.id, processing_msg.message_id)
        bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=create_main_menu())
        del user_data[user_id]
    except Exception as e:
        logger.error(f"❌ Error en process_query: {e}")
        try:
            bot.send_message(message.chat.id, "❌ Error procesando la consulta. Intenta más tarde.", reply_markup=create_main_menu())
            if user_id in user_data:
                del user_data[user_id]
        except:
            pass

# =================== FLASK APP CON PANEL AVANZADO ===================
app = Flask(__name__)

# Configurar manejo de señales
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Template HTML para el panel de control
PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>IaldazCheck Bot - Panel de Control</title>
    <meta http-equiv="refresh" content="30">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white; 
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1em; }
        .nav-tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
            overflow-x: auto;
        }
        .nav-tab {
            flex: 1;
            padding: 15px 20px;
            text-align: center;
            cursor: pointer;
            border: none;
            background: none;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
            min-width: 120px;
        }
        .nav-tab:hover { background: #e9ecef; }
        .nav-tab.active { 
            background: white; 
            border-bottom-color: #667eea;
            color: #667eea;
            font-weight: 600;
        }
        .tab-content { display: none; padding: 30px; }
        .tab-content.active { display: block; }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 25px;
            border-radius: 15px;
            border-left: 5px solid #667eea;
            transition: transform 0.3s;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 2.5em; font-weight: bold; color: #333; margin-bottom: 5px; }
        .stat-label { color: #666; font-size: 1em; }
        .stat-change { font-size: 0.9em; margin-top: 10px; }
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .neutral { color: #6c757d; }
        .log-container {
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 10px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .log-entry {
            padding: 8px 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
        }
        .log-entry:hover { background: #f1f3f4; }
        .log-timestamp { color: #666; margin-right: 10px; min-width: 130px; }
        .log-level { 
            margin-right: 10px; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 11px;
            font-weight: bold;
            min-width: 60px;
            text-align: center;
        }
        .log-level.INFO { background: #d4edda; color: #155724; }
        .log-level.WARNING { background: #fff3cd; color: #856404; }
        .log-level.ERROR { background: #f8d7da; color: #721c24; }
        .log-message { flex: 1; }
        .system-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .info-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #ddd;
        }
        .info-section h3 { 
            margin-bottom: 15px; 
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 5px;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .info-item:last-child { border-bottom: none; }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s;
        }
        .progress-fill.warning { background: linear-gradient(90deg, #ffc107, #fd7e14); }
        .progress-fill.danger { background: linear-gradient(90deg, #dc3545, #e83e8c); }
        .activity-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
        }
        .activity-time { color: #666; font-size: 0.9em; margin-right: 15px; min-width: 80px; }
        .activity-user { 
            background: #667eea; 
            color: white; 
            padding: 2px 8px; 
            border-radius: 12px; 
            font-size: 0.8em;
            margin-right: 10px;
        }
        .activity-action { flex: 1; }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s;
            font-weight: 500;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-danger { background: #dc3545; color: white; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        @media (max-width: 768px) {
            .container { margin: 10px; border-radius: 10px; }
            .stats-grid { grid-template-columns: 1fr; }
            .system-info { grid-template-columns: 1fr; }
            .nav-tabs { flex-direction: column; }
            .controls { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 IaldazCheck Bot</h1>
            <p>Panel de Control y Monitoreo</p>
            <p style="font-size: 0.9em; opacity: 0.8;">
                Uptime: {{ uptime }} | Última actualización: {{ current_time }}
            </p>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('dashboard')">📊 Dashboard</button>
            <button class="nav-tab" onclick="showTab('logs')">📝 Logs</button>
            <button class="nav-tab" onclick="showTab('activity')">👥 Actividad</button>
            <button class="nav-tab" onclick="showTab('system')">⚙️ Sistema</button>
            <button class="nav-tab" onclick="showTab('tools')">🛠️ Herramientas</button>
        </div>

        <!-- Dashboard Tab -->
        <div id="dashboard" class="tab-content active">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value {{ 'positive' if bot_status == '✅ Activo' else 'negative' }}">
                        {{ bot_status }}
                    </div>
                    <div class="stat-label">Estado del Bot</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ total_services }}</div>
                    <div class="stat-label">Servicios Disponibles</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ request_count }}</div>
                    <div class="stat-label">Requests Totales</div>
                    <div class="stat-change neutral">{{ error_count }} errores</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ active_users }}</div>
                    <div class="stat-label">Usuarios Activos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ len(user_data) }}</div>
                    <div class="stat-label">Sesiones Activas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ success_rate }}%</div>
                    <div class="stat-label">Tasa de Éxito</div>
                    <div class="stat-change {{ 'positive' if success_rate > 90 else 'warning' if success_rate > 70 else 'negative' }}">
                        {{ request_count - error_count }}/{{ request_count }} exitosas
                    </div>
                </div>
            </div>

            <div class="system-info">
                <div class="info-section">
                    <h3>🖥️ Recursos del Sistema</h3>
                    <div class="info-item">
                        <span>CPU Usage:</span>
                        <div style="width: 200px;">
                            <div class="progress-bar">
                                <div class="progress-fill {{ 'danger' if system_stats.cpu_percent > 80 else 'warning' if system_stats.cpu_percent > 60 else '' }}" 
                                     style="width: {{ system_stats.cpu_percent }}%"></div>
                            </div>
                            <small>{{ system_stats.cpu_percent }}%</small>
                        </div>
                    </div>
                    <div class="info-item">
                        <span>Memoria:</span>
                        <div style="width: 200px;">
                            <div class="progress-bar">
                                <div class="progress-fill {{ 'danger' if system_stats.memory_percent > 80 else 'warning' if system_stats.memory_percent > 60 else '' }}" 
                                     style="width: {{ system_stats.memory_percent }}%"></div>
                            </div>
                            <small>{{ system_stats.memory_used }}MB / {{ system_stats.memory_total }}MB</small>
                        </div>
                    </div>
                    <div class="info-item">
                        <span>Disco:</span>
                        <div style="width: 200px;">
                            <div class="progress-bar">
                                <div class="progress-fill {{ 'danger' if system_stats.disk_percent > 80 else 'warning' if system_stats.disk_percent > 60 else '' }}" 
                                     style="width: {{ system_stats.disk_percent }}%"></div>
                            </div>
                            <small>{{ system_stats.disk_used }}GB / {{ system_stats.disk_total }}GB</small>
                        </div>
                    </div>
                </div>

                <div class="info-section">
                    <h3>📊 Estadísticas Bot</h3>
                    <div class="info-item">
                        <span>Uptime:</span>
                        <strong>{{ uptime }}</strong>
                    </div>
                    <div class="info-item">
                        <span>Última Actividad:</span>
                        <strong>{{ last_activity_time }}</strong>
                    </div>
                    <div class="info-item">
                        <span>Webhook URL:</span>
                        <small>{{ webhook_url[:50] }}...</small>
                    </div>
                    <div class="info-item">
                        <span>Puerto:</span>
                        <strong>{{ port }}</strong>
                    </div>
                </div>
            </div>
        </div>

        <!-- Logs Tab -->
        <div id="logs" class="tab-content">
            <div class="controls">
                <button class="btn btn-primary" onclick="refreshLogs()">🔄 Actualizar Logs</button>
                <button class="btn btn-warning" onclick="clearLogs()">🗑️ Limpiar Logs</button>
                <a href="/api/logs/download" class="btn btn-success">💾 Descargar Logs</a>
            </div>
            <div class="log-container" id="logContainer">
                {% for log in logs %}
                <div class="log-entry">
                    <span class="log-timestamp">{{ log.timestamp }}</span>
                    <span class="log-level {{ log.level }}">{{ log.level }}</span>
                    <span class="log-message">{{ log.message }}</span>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Activity Tab -->
        <div id="activity" class="tab-content">
            <div class="controls">
                <button class="btn btn-primary" onclick="refreshActivity()">🔄 Actualizar</button>
            </div>
            <div class="log-container">
                {% for activity in activities %}
                <div class="activity-item">
                    <span class="activity-time">{{ activity.timestamp.split(' ')[1] }}</span>
                    <span class="activity-user">{{ activity.user_id }}</span>
                    <span class="activity-action">{{ activity.action }}: {{ activity.details }}</span>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- System Tab -->
        <div id="system" class="tab-content">
            <div class="system-info">
                <div class="info-section">
                    <h3>🔧 Configuración</h3>
                    <div class="info-item">
                        <span>Bot Token:</span>
                        <strong>{{ '✅ Configurado' if bot_token else '❌ Faltante' }}</strong>
                    </div>
                    <div class="info-item">
                        <span>API Key:</span>
                        <strong>{{ '✅ Configurado' if api_key else '❌ Faltante' }}</strong>
                    </div>
                    <div class="info-item">
                        <span>Webhook:</span>
                        <strong>{{ '✅ Configurado' if webhook_url else '❌ Faltante' }}</strong>
                    </div>
                    <div class="info-item">
                        <span>Modo:</span>
                        <strong>{{ 'Webhook' if webhook_url else 'Polling' }}</strong>
                    </div>
                </div>

                <div class="info-section">
                    <h3>👥 Usuarios Autorizados</h3>
                    {% for user_id, user_info in authorized_users.items() %}
                    <div class="info-item">
                        <span>{{ user_info.name }}</span>
                        <div>
                            <small>{{ user_info.role }}</small><br>
                            <strong>{{ '♾️' if user_info.credits == -1 else user_info.credits }} créditos</strong>
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <div class="info-section">
                    <h3>🏷️ Servicios por Categoría</h3>
                    {% for cat_key, category in services.items() %}
                    <div class="info-item">
                        <span>{{ category.emoji }} {{ category.name }}</span>
                        <strong>{{ len(category.services) }} servicios</strong>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Tools Tab -->
        <div id="tools" class="tab-content">
            <div class="controls">
                <button class="btn btn-primary" onclick="testWebhook()">🔧 Test Webhook</button>
                <button class="btn btn-success" onclick="checkBotStatus()">✅ Check Bot</button>
                <button class="btn btn-warning" onclick="restartBot()">🔄 Restart Bot</button>
                <a href="/api/backup" class="btn btn-primary">💾 Backup Config</a>
            </div>
            
            <div class="system-info">
                <div class="info-section">
                    <h3>🛠️ Herramientas de Administración</h3>
                    <p>Usa estas herramientas para administrar y monitorear el bot.</p>
                    
                    <div style="margin-top: 20px;">
                        <h4>📡 APIs Disponibles:</h4>
                        <ul style="margin-left: 20px; margin-top: 10px;">
                            <li><a href="/health" target="_blank">/health</a> - Estado completo</li>
                            <li><a href="/ping" target="_blank">/ping</a> - Test rápido</li>
                            <li><a href="/metrics" target="_blank">/metrics</a> - Métricas</li>
                            <li><a href="/api/logs" target="_blank">/api/logs</a> - Logs JSON</li>
                            <li><a href="/api/stats" target="_blank">/api/stats</a> - Estadísticas</li>
                            <li><a href="/debug" target="_blank">/debug</a> - Debug Info</li>
                        </ul>
                    </div>
                </div>

                <div class="info-section">
                    <h3>📊 Comandos de Test</h3>
                    <div id="testResults" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 10px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto;">
                        Resultados de test aparecerán aquí...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // Ocultar todos los tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Mostrar tab seleccionado
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        function refreshLogs() {
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    const container = document.getElementById('logContainer');
                    container.innerHTML = '';
                    data.forEach(log => {
                        const entry = document.createElement('div');
                        entry.className = 'log-entry';
                        entry.innerHTML = `
                            <span class="log-timestamp">${log.timestamp}</span>
                            <span class="log-level ${log.level}">${log.level}</span>
                            <span class="log-message">${log.message}</span>
                        `;
                        container.appendChild(entry);
                    });
                });
        }

        function refreshActivity() {
            fetch('/api/activity')
                .then(response => response.json())
                .then(data => location.reload());
        }

        function clearLogs() {
            if(confirm('¿Estás seguro de que quieres limpiar los logs?')) {
                fetch('/api/logs/clear', {method: 'POST'})
                    .then(() => location.reload());
            }
        }

        function testWebhook() {
            const results = document.getElementById('testResults');
            results.innerHTML = 'Probando webhook...';
            
            fetch('/api/test/webhook', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    results.innerHTML = `Webhook Test: ${data.status}\\n${data.message}`;
                })
                .catch(err => {
                    results.innerHTML = `Error: ${err.message}`;
                });
        }

        function checkBotStatus() {
            const results = document.getElementById('testResults');
            results.innerHTML = 'Verificando bot...';
            
            fetch('/api/test/bot', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    results.innerHTML = `Bot Status: ${data.status}\\n${JSON.stringify(data.data, null, 2)}`;
                })
                .catch(err => {
                    results.innerHTML = `Error: ${err.message}`;
                });
        }

        function restartBot() {
            if(confirm('¿Estás seguro de que quieres reiniciar el bot?')) {
                const results = document.getElementById('testResults');
                results.innerHTML = 'Reiniciando bot...';
                
                fetch('/api/restart', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        results.innerHTML = `Restart: ${data.message}`;
                    });
            }
        }

        // Auto refresh cada 30 segundos
        setInterval(() => {
            if(document.querySelector('.nav-tab.active').textContent.includes('Dashboard')) {
                location.reload();
            }
        }, 30000);
    </script>
</body>
</html>
"""

# CORRECCIÓN: Webhook con ruta segura
@app.route('/webhook', methods=['POST'])
def webhook():
    if not server_running:
        return "Service unavailable", 503
    
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        logger.info("✅ Webhook procesado exitosamente")
        return "OK", 200
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}")
        global error_count
        error_count += 1
        return "Error", 500

@app.route('/')
def index():
    if not server_running:
        return "Service starting...", 503
    
    try:
        # Verificar estado del bot
        try:
            bot_info = bot.get_me()
            bot_status = "✅ Activo"
            bot_name = bot_info.first_name
            bot_username = f"@{bot_info.username}"
        except Exception as e:
            bot_status = "❌ Error"
            bot_name = "IaldazCheck"
            bot_username = f"Error: {str(e)[:30]}..."
        
        # Calcular estadísticas
        uptime = str(datetime.now() - start_time).split('.')[0]
        total_services = sum(len(cat["services"]) for cat in SERVICES.values())
        success_rate = round(((request_count - error_count) / max(request_count, 1)) * 100, 1)
        last_activity_time = last_activity.strftime('%H:%M:%S')
        system_stats = get_system_stats()
        
        return render_template_string(PANEL_TEMPLATE,
            bot_status=bot_status,
            bot_name=bot_name,
            bot_username=bot_username,
            total_services=total_services,
            request_count=request_count,
            error_count=error_count,
            success_rate=success_rate,
            active_users=len(AUTHORIZED_USERS),
            user_data=user_data,
            uptime=uptime,
            last_activity_time=last_activity_time,
            system_stats=system_stats,
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            logs=list(memory_logs),
            activities=list(activity_log),
            webhook_url=WEBHOOK_URL,
            port=PORT,
            bot_token=bool(BOT_TOKEN),
            api_key=bool(API_KEY),
            authorized_users=AUTHORIZED_USERS,
            services=SERVICES,
            len=len
        )
        
    except Exception as e:
        logger.error(f"Error en panel: {e}")
        return f"<h1>Error en Panel</h1><p>{str(e)}</p>", 500

# =================== API ENDPOINTS ===================
@app.route('/health')
def health():
    try:
        config_status = {
            "bot_token": "✅ Configurado" if BOT_TOKEN else "❌ Faltante",
            "api_key": "✅ Configurado" if API_KEY else "❌ Faltante",
            "webhook_url": "✅ Configurado" if WEBHOOK_URL else "❌ Faltante"
        }
        
        bot_status = "❌ Error"
        bot_username = "Error"
        try:
            bot_info = bot.get_me()
            bot_status = "✅ Activo"
            bot_username = bot_info.username
        except Exception as e:
            bot_username = f"Error: {str(e)[:50]}"
        
        server_status = "✅ Activo" if server_running else "❌ Parado"
        uptime = str(datetime.now() - start_time).split('.')[0]
        
        response = {
            "status": "healthy" if server_running and bot_status == "✅ Activo" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime,
            "server": {
                "status": server_status,
                "platform": "Render.com",
                "requests": request_count,
                "errors": error_count,
                "success_rate": round(((request_count - error_count) / max(request_count, 1)) * 100, 1)
            },
            "bot": {
                "name": "IaldazCheck",
                "status": bot_status,
                "username": bot_username,
                "services_count": sum(len(cat["services"]) for cat in SERVICES.values()),
                "authorized_users": len(AUTHORIZED_USERS),
                "active_sessions": len(user_data)
            },
            "config": config_status,
            "system": get_system_stats()
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/logs')
def api_logs():
    return jsonify(list(memory_logs))

@app.route('/api/logs/clear', methods=['POST'])
def clear_logs():
    memory_logs.clear()
    logger.info("🗑️ Logs limpiados desde panel")
    return jsonify({"status": "success", "message": "Logs limpiados"})

@app.route('/api/logs/download')
def download_logs():
    from flask import Response
    log_data = "\n".join([f"[{log['timestamp']}] {log['level']}: {log['message']}" for log in memory_logs])
    return Response(
        log_data,
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename=bot_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"}
    )

@app.route('/api/activity')
def api_activity():
    return jsonify(list(activity_log))

@app.route('/api/stats')
def api_stats():
    uptime = str(datetime.now() - start_time).split('.')[0]
    return jsonify({
        "uptime": uptime,
        "requests": request_count,
        "errors": error_count,
        "success_rate": round(((request_count - error_count) / max(request_count, 1)) * 100, 1),
        "active_sessions": len(user_data),
        "system": get_system_stats(),
        "last_activity": last_activity.isoformat()
    })

@app.route('/api/test/webhook', methods=['POST'])
def test_webhook():
    try:
        webhook_info = bot.get_webhook_info()
        return jsonify({
            "status": "success",
            "message": f"Webhook URL: {webhook_info.url}\nPending updates: {webhook_info.pending_update_count}\nLast error: {webhook_info.last_error_date or 'None'}"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error checking webhook: {str(e)}"
        })

@app.route('/api/test/bot', methods=['POST'])
def test_bot():
    try:
        bot_info = bot.get_me()
        return jsonify({
            "status": "success",
            "data": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "can_join_groups": bot_info.can_join_groups,
                "can_read_all_group_messages": bot_info.can_read_all_group_messages,
                "supports_inline_queries": bot_info.supports_inline_queries
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error checking bot: {str(e)}"
        })

@app.route('/api/restart', methods=['POST'])
def restart_bot():
    try:
        logger.info("🔄 Restart solicitado desde panel")
        return jsonify({
            "status": "success",
            "message": "Restart signal sent (Note: May not work in all hosting environments)"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error during restart: {str(e)}"
        })

@app.route('/api/backup')
def backup_config():
    try:
        from flask import Response
        import json
        
        backup_data = {
            "authorized_users": AUTHORIZED_USERS,
            "services_count": sum(len(cat["services"]) for cat in SERVICES.values()),
            "backup_date": datetime.now().isoformat(),
            "bot_config": {
                "webhook_url": WEBHOOK_URL,
                "api_endpoint": API_ENDPOINT,
                "port": PORT
            }
        }
        
        return Response(
            json.dumps(backup_data, indent=2),
            mimetype="application/json",
            headers={"Content-disposition": f"attachment; filename=bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
        )
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error creating backup: {str(e)}"
        })

@app.route('/ping')
def ping():
    return jsonify({
        "message": "pong",
        "timestamp": datetime.now().isoformat(),
        "status": "ok",
        "uptime": str(datetime.now() - start_time).split('.')[0]
    })

@app.route('/metrics')
def metrics():
    """Endpoint para métricas básicas"""
    try:
        uptime = str(datetime.now() - start_time).split('.')[0]
        return jsonify({
            "bot_status": "active" if server_running else "inactive",
            "services_count": sum(len(cat["services"]) for cat in SERVICES.values()),
            "users_count": len(AUTHORIZED_USERS),
            "active_sessions": len(user_data),
            "requests_total": request_count,
            "errors_total": error_count,
            "success_rate": round(((request_count - error_count) / max(request_count, 1)) * 100, 1),
            "uptime": uptime,
            "timestamp": datetime.now().isoformat(),
            "system": get_system_stats()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/debug')
def debug_info():
    """Endpoint para debugging"""
    try:
        # Verificar estado del bot
        bot_info = bot.get_me()
        webhook_info = bot.get_webhook_info()
        
        return jsonify({
            "bot_info": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name
            },
            "webhook_info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "last_error_date": str(webhook_info.last_error_date) if webhook_info.last_error_date else None,
                "last_error_message": webhook_info.last_error_message,
                "max_connections": webhook_info.max_connections,
                "allowed_updates": webhook_info.allowed_updates
            },
            "server_info": {
                "server_running": server_running,
                "uptime": str(datetime.now() - start_time).split('.')[0],
                "request_count": request_count,
                "error_count": error_count
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# CORRECCIÓN: Configurar el webhook de manera más robusta
def configure_webhook():
    """Configura el webhook con reintentos"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # CORRECCIÓN: Usar ruta segura sin token
            webhook_url = f"{WEBHOOK_URL}/webhook"
            logger.info(f"🔧 Intento {attempt + 1}: Configurando webhook en {webhook_url}")
            
            # Remover webhook existente
            bot.remove_webhook()
            time.sleep(2)
            
            # Configurar nuevo webhook
            result = bot.set_webhook(url=webhook_url)
            
            if result:
                logger.info("✅ Webhook configurado exitosamente")
                return True
            else:
                logger.warning(f"⚠️ Intento {attempt + 1} falló")
                
        except Exception as e:
            logger.error(f"❌ Error configurando webhook (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
    
    logger.error("❌ No se pudo configurar el webhook después de varios intentos")
    return False

if __name__ == "__main__":
    logger.info("🚀 Iniciando IaldazCheck Bot con Panel Avanzado...")
    
    # Verificar variables de entorno
    if not verify_environment():
        logger.error("❌ Configuración incompleta. Deteniendo bot.")
        sys.exit(1)
    
    # Configurar webhook para Render
    if WEBHOOK_URL:
        logger.info("🌐 Modo Webhook (Render.com)")
        
        # Iniciar hilo para keep-alive
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        logger.info("🔄 Keep-alive thread iniciado")
        
        # Configurar webhook
        if configure_webhook():
            logger.info(f"📡 Webhook activo en: {WEBHOOK_URL}/webhook")
        else:
            logger.error("❌ No se pudo configurar webhook. Continuando de todas formas...")
        
        logger.info(f"🌐 Iniciando servidor Flask con Panel en puerto {PORT}")
        logger.info(f"📊 Panel disponible en: {WEBHOOK_URL}")
        
        # Configurar Flask para producción
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        try:
            app.run(
                host='0.0.0.0', 
                port=PORT, 
                debug=False,
                threaded=True,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"❌ Error iniciando servidor: {e}")
            server_running = False
    
    # Modo local (polling) - para desarrollo
    else:
        logger.info("🔄 Modo Polling (desarrollo local)")
        try:
            flask_thread = threading.Thread(target=lambda: app.run(
                host='0.0.0.0', 
                port=PORT, 
                debug=False,
                threaded=True,
                use_reloader=False
            ), daemon=True)
            flask_thread.start()
            logger.info(f"📊 Panel local disponible en: http://localhost:{PORT}")
            
            bot.remove_webhook()
            logger.info("✅ Webhook removido, iniciando polling...")
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
        finally:
            server_running = False