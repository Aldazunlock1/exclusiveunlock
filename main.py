import telebot
import requests
import json
import os
import time
import logging
from datetime import datetime
from telebot import types
from flask import Flask, request
import threading
import signal
import sys

# =================== CONFIGURACIÓN ===================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8219926342:AAGb9IRXThYg5AvC8up5caAUxYv9SbaMTAw")
API_KEY = os.environ.get("API_KEY", "z4o3T-525kS-Jbz8M-98WY3-CCZK2-HsST0")
API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://alpha.imeicheck.com/api/php-api/create")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://exclusiveunlock-m4o8.onrender.com")
PORT = int(os.environ.get("PORT", 5000))

# Variable global para control del servidor
server_running = True

AUTHORIZED_USERS = {
    7655366089: {"role": "admin", "name": "Admin Principal", "credits": -1},
    6269867784: {"role": "premium", "name": "Usuario Premium", "credits": 100},
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

# =================== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# =================== BOT ===================
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
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
            # Hacer un health check cada 5 minutos
            time.sleep(300)
            if server_running:
                # Verificar que el bot sigue funcionando
                bot.get_me()
                logger.info("🔄 Bot health check: OK")
        except Exception as e:
            logger.warning(f"⚠️ Health check warning: {e}")
            time.sleep(60)  # Esperar menos tiempo si hay error

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
    # Reemplazar <br> con saltos de línea
    text = html_content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    # Reemplazar entidades HTML comunes
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('\\u003C', '<').replace('\\u003E', '>')
    # Remover todas las etiquetas HTML incluyendo spans con estilos
    text = re.sub(r'<[^>]+>', '', text)
    # Limpiar líneas vacías
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def validate_imei(text):
    text = ''.join(c for c in text if c.isalnum())
    return 8 <= len(text) <= 20

def make_api_request(service_id, imei):
    try:
        url = f"{API_ENDPOINT}?key={API_KEY}&service={service_id}&imei={imei}"
        logger.info(f"🌐 API Request: {url}")
        response = requests.get(url, timeout=45)
        if response.status_code == 200:
            try:
                return {'status': 'success', 'data': response.json()}
            except:
                return {'status': 'success', 'data': {'result': response.text}}
        else:
            return {'status': 'failed', 'message': f'HTTP {response.status_code}'}
    except Exception as e:
        logger.error(f"❌ Error API: {e}")
        return {'status': 'failed', 'message': str(e)}

def format_field_value(field_key, value):
    """Formatea el valor de un campo específico con emojis apropiados"""
    field_lower = field_key.lower()
    value_lower = value.lower()
    
    # Campos que indican estado positivo cuando son "No"
    if any(keyword in field_lower for keyword in ['demo unit', 'refurbished', 'replaced', 'replacement']):
        if value_lower in ['no', 'false', '0']:
            return '✅️No'
        elif value_lower in ['yes', 'true', '1']:
            return '⚠️Yes'
    
    # Find My iPhone
    elif 'find my' in field_lower or field_lower == 'fmi':
        if value_lower in ['on', 'enabled', 'active', 'yes']:
            return '⚠️ON'
        elif value_lower in ['off', 'disabled', 'inactive', 'no']:
            return '✅️OFF'
    
    # iCloud Status
    elif 'icloud' in field_lower:
        if 'clean' in value_lower:
            return '✅️Clean'
        elif any(keyword in value_lower for keyword in ['lost', 'locked', 'stolen']):
            return f'⚠️{value}'
    
    # SIM-Lock Status
    elif 'sim-lock' in field_lower or 'simlock' in field_lower:
        if 'locked' in value_lower:
            return f'⚠️Locked'
        elif 'unlocked' in value_lower or 'clean' in value_lower:
            return f'✅️{value}'
    
    # Block/Blacklist Status
    elif any(keyword in field_lower for keyword in ['block', 'blacklist']):
        if any(keyword in value_lower for keyword in ['clean', 'not found', 'clear', 'no']):
            return f'✅️{value}'
        elif any(keyword in value_lower for keyword in ['blocked', 'reported', 'found', 'yes']):
            return f'⚠️{value}'
    
    # Warranty Status
    elif 'warranty' in field_lower:
        return f'✅️{value}'
    
    # Coverage/Service Status
    elif any(keyword in field_lower for keyword in ['coverage', 'service']):
        if 'active' in value_lower:
            return f'✅️{value}'
        elif 'expired' in value_lower or 'inactive' in value_lower:
            return f'⚠️{value}'
    
    # Valor por defecto sin emoji
    return value

def format_device_info(raw_data):
    """Formatea la información del dispositivo de manera estructurada con monoespacio"""
    if isinstance(raw_data, dict):
        if 'result' in raw_data:
            content = raw_data['result']
        else:
            content = str(raw_data)
    else:
        content = str(raw_data)
    
    # Limpiar HTML y Unicode
    clean_content = clean_html(content)
    
    # Orden de campos preferido
    field_order = [
        'Model Description', 'Model', 'Network', 'IMEI Number', 'IMEI', 'IMEI2 Number', 'IMEI2',
        'MEID', 'Serial Number', 'Warranty Status', 'Estimated Purchase Date', 'Purchase Date',
        'Purchase Country', 'Repairs and Service Coverage', 'Replaced by Apple', 'Replaced Device',
        'Replacement Device', 'Refurbished', 'Demo Unit', 'Find My iPhone', 'FMI', 'iCloud Status',
        'US Block Status', 'Blacklist Status', 'GSMA Status', 'SIM-Lock Status', 'Sim-Lock Status',
        'Locked Carrier', 'Knox Status', 'Activation Status', 'MDM Status', 'Color', 'Storage', 'Capacity'
    ]
    
    # Parsear líneas y crear diccionario
    data_dict = {}
    lines = clean_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
            
        # Buscar patrones "Campo: Valor"
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    data_dict[key] = value
    
    formatted_lines = []
    used_keys = set()
    
    # Procesar campos en orden preferido
    for preferred_field in field_order:
        found_key = None
        found_value = None
        
        # Buscar coincidencia exacta primero
        for key, value in data_dict.items():
            if key in used_keys:
                continue
            if key.lower() == preferred_field.lower():
                found_key = key
                found_value = value
                break
        
        # Si no hay coincidencia exacta, buscar parcial
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
    
    # Agregar campos no procesados al final
    for key, value in data_dict.items():
        if key not in used_keys:
            formatted_value = format_field_value(key, value)
            formatted_lines.append(f'{key}: {formatted_value}')
    
    # Si no se pudo formatear, devolver el contenido limpio
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

# =================== HANDLERS ===================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    logger.info(f"🔔 /start recibido de usuario {user_id}")
    if not is_authorized(user_id):
        bot.send_message(message.chat.id, f"🔒 Acceso no autorizado. Tu ID: {user_id}", parse_mode='Markdown')
        return
    
    user_info = get_user_info(user_id)
    credits_text = "Ilimitados" if user_info["credits"] == -1 else str(user_info["credits"])
    text = f"🤖 Bienvenido {user_info['name']} ({user_info['role'].title()})\n💎 Créditos: {credits_text}"
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=create_main_menu())

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_id = message.from_user.id
    if user_id in user_data:
        del user_data[user_id]
    bot.send_message(message.chat.id, "❌ Operación cancelada", reply_markup=create_main_menu())

@bot.message_handler(func=lambda message: True)
def handle_message(message):
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

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
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
        credits_text = "Ilimitados ♾️" if user_info["credits"] == -1 else f"{user_info['credits']} 💎"
        text = f"💳 **MIS CRÉDITOS**\n\n👤 Usuario: {user_info['name']}\n🏆 Rol: {user_info['role'].title()}\n💎 Créditos: {credits_text}"
        edit_message(call, text, types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Menú Principal", callback_data="main_menu")))
    
    elif data == "help":
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

def process_query(message, user_id, imei):
    data = user_data[user_id]
    service_id = data['service_id']
    service_name = data['service_name']
    credits_required = data['credits_required']
    
    logger.info(f"🛠 Usuario {user_id} realiza consulta {service_name} para IMEI {imei}")
    
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
    else:
        response = format_error_response(service_name, imei, result.get('message', 'Error desconocido'))
        logger.warning(f"❌ Consulta fallida para usuario {user_id}: {result.get('message')}")
    
    bot.edit_message_text("✅ Procesamiento completado", message.chat.id, processing_msg.message_id)
    bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=create_main_menu())
    del user_data[user_id]

# =================== FLASK APP PARA WEBHOOK ===================
app = Flask(__name__)

# Configurar manejo de señales
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if not server_running:
        return "Service unavailable", 503
    
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}")
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
        
        # Contar servicios
        total_services = sum(len(cat["services"]) for cat in SERVICES.values())
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>IaldazCheck Bot - Status</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta http-equiv="refresh" content="300">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    margin: 0;
                    padding: 20px;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                    width: 100%;
                }}
                .status {{
                    font-size: 2.5em;
                    margin-bottom: 20px;
                }}
                .title {{
                    color: #333;
                    font-size: 2em;
                    margin-bottom: 10px;
                    font-weight: 300;
                }}
                .subtitle {{
                    color: #666;
                    font-size: 1.1em;
                    margin-bottom: 30px;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 20px;
                    margin: 30px 0;
                }}
                .info-card {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }}
                .info-label {{
                    font-size: 0.9em;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .info-value {{
                    font-size: 1.2em;
                    color: #333;
                    font-weight: 500;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #666;
                    font-size: 0.9em;
                }}
                .health-link {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 10px 20px;
                    background: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background 0.3s;
                }}
                .health-link:hover {{
                    background: #218838;
                }}
                .uptime {{
                    background: #e8f4fd;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                    border-left: 4px solid #007bff;
                }}
                @media (max-width: 600px) {{
                    .info-grid {{
                        grid-template-columns: 1fr;
                    }}
                    .container {{
                        padding: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="status">🤖</div>
                <h1 class="title">IaldazCheck Bot</h1>
                <p class="subtitle">Sistema de Verificación IMEI/Serial</p>
                
                <div class="uptime">
                    <div class="info-label">Estado del Sistema</div>
                    <div class="info-value">🟢 Operativo - Render.com</div>
                </div>
                
                <div class="info-grid">
                    <div class="info-card">
                        <div class="info-label">Estado del Bot</div>
                        <div class="info-value">{bot_status}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Nombre</div>
                        <div class="info-value">{bot_name}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Username</div>
                        <div class="info-value">{bot_username}</div>
                    </div>
                    <div class="info-card">
                        <div class="info-label">Servicios</div>
                        <div class="info-value">{total_services}</div>
                    </div>
                </div>
                
                <div class="info-card" style="margin: 20px 0;">
                    <div class="info-label">Modo de Operación</div>
                    <div class="info-value">🌐 Webhook Mode - Optimizado para Render</div>
                </div>
                
                <a href="/health" class="health-link">📊 Health Check API</a>
                <a href="/ping" class="health-link" style="margin-left: 10px;">🏓 Ping Test</a>
                
                <div class="footer">
                    <strong>exclusiveunlock.com</strong><br>
                    Powered by Render.com<br>
                    <small>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</small>
                </div>
            </div>
        </body>
        </html>
        """
    
    except Exception as e:
        return f"""
        <html>
        <body style="font-family: Arial; text-align: center; margin-top: 100px; background: #f8f9fa;">
            <h1>⚠️ Error en el Bot</h1>
            <p>Error: {str(e)}</p>
            <a href="/health">Ver Health Check</a>
        </body>
        </html>
        """, 500

@app.route('/health')
def health():
    try:
        # Verificar configuración básica
        config_status = {
            "bot_token": "✅ Configurado" if BOT_TOKEN else "❌ Faltante",
            "api_key": "✅ Configurado" if API_KEY else "❌ Faltante",
            "webhook_url": "✅ Configurado" if WEBHOOK_URL else "❌ Faltante"
        }
        
        # Verificar conectividad del bot
        bot_status = "❌ Error"
        bot_username = "Error"
        try:
            bot_info = bot.get_me()
            bot_status = "✅ Activo"
            bot_username = bot_info.username
        except Exception as e:
            bot_username = f"Error: {str(e)[:50]}"
        
        # Estado del servidor
        server_status = "✅ Activo" if server_running else "❌ Parado"
        
        # Respuesta completa
        response = {
            "status": "healthy" if server_running and bot_status == "✅ Activo" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "server": {
                "status": server_status,
                "uptime": "Active",
                "platform": "Render.com"
            },
            "bot": {
                "name": "IaldazCheck",
                "status": bot_status,
                "username": bot_username,
                "services_count": sum(len(cat["services"]) for cat in SERVICES.values()),
                "authorized_users": len(AUTHORIZED_USERS)
            },
            "config": config_status,
            "environment": {
                "webhook_mode": bool(WEBHOOK_URL),
                "port": PORT,
                "webhook_configured": bool(WEBHOOK_URL)
            }
        }
        
        return response, 200
    
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
            "server_running": server_running
        }, 500

# Nuevos endpoints para monitoreo mejorado
@app.route('/status')
def status():
    return {
        "online": True,
        "service": "IaldazCheck Bot",
        "timestamp": datetime.now().isoformat(),
        "uptime": "Active",
        "mode": "webhook"
    }, 200

@app.route('/ping')
def ping():
    return {
        "message": "pong",
        "timestamp": datetime.now().isoformat(),
        "status": "ok"
    }, 200

@app.route('/metrics')
def metrics():
    """Endpoint para métricas básicas"""
    try:
        return {
            "bot_status": "active" if server_running else "inactive",
            "services_count": sum(len(cat["services"]) for cat in SERVICES.values()),
            "users_count": len(AUTHORIZED_USERS),
            "active_sessions": len(user_data),
            "timestamp": datetime.now().isoformat()
        }, 200
    except Exception as e:
        return {"error": str(e)}, 500

# Configurar el webhook de manera más robusta
def configure_webhook():
    """Configura el webhook con reintentos"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
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
    logger.info("🚀 Iniciando IaldazCheck Bot...")
    
    # Configurar webhook para Render
    if WEBHOOK_URL:
        logger.info("🌐 Modo Webhook (Render.com)")
        
        # Iniciar hilo para keep-alive
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        logger.info("🔄 Keep-alive thread iniciado")
        
        # Configurar webhook
        if configure_webhook():
            logger.info(f"📡 Webhook activo en: {WEBHOOK_URL}/{BOT_TOKEN}")
        else:
            logger.warning("⚠️ Webhook no configurado, pero el servidor seguirá funcionando")
        
        logger.info(f"🌐 Iniciando servidor Flask en puerto {PORT}")
        
        # Configurar Flask para producción
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        
        try:
            # Usar el servidor de desarrollo de Flask para Render
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
            bot.remove_webhook()
            logger.info("✅ Webhook removido, iniciando polling...")
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            logger.error(f"❌ Error en polling: {e}")
        finally:
            server_running = False