import telebot
import requests
import json
import os
import time
import logging
from datetime import datetime
from telebot import types
from flask import Flask, request

# =================== CONFIGURACIÓN ===================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8219926342:AAGb9IRXThYg5AvC8up5caAUxYv9SbaMTAw")
API_KEY = os.environ.get("API_KEY", "z4o3T-525kS-Jbz8M-98WY3-CCZK2-HsST0")
API_ENDPOINT = os.environ.get("API_ENDPOINT", "https://alpha.imeicheck.com/api/php-api/create")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
PORT = int(os.environ.get("PORT", 5000))

AUTHORIZED_USERS = {
    7655366089: {"role": "admin", "name": "Admin Principal", "credits": -1},
  6269867784: {"role": "premium", "name": "Usuario Premium", "credits": 8.8},
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

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK"

@app.route('/')
def index():
    return f"""
    <html>
    <head><title>IaldazCheck Bot</title></head>
    <body style="font-family: Arial; text-align: center; margin-top: 100px;">
        <h1>🤖 IaldazCheck Bot</h1>
        <p>✅ Bot está activo y funcionando</p>
        <p>🌐 Webhook configurado correctamente</p>
        <hr>
        <small>exclusiveunlock.com</small>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "ok", "bot": "IaldazCheck", "timestamp": datetime.now().isoformat()}

# =================== INICIO PRINCIPAL ===================
if __name__ == "__main__":
    logger.info("🚀 Iniciando IaldazCheck Bot...")
    
    # Modo Render (webhook)
    if WEBHOOK_URL:
        webhook_url = WEBHOOK_URL + BOT_TOKEN
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=webhook_url)
            logger.info(f"📡 Webhook configurado: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Error configurando webhook: {e}")
        
        logger.info(f"🌐 Iniciando servidor Flask en puerto {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
    
    # Modo local (polling)
    else:
        logger.info("✅ Modo polling activado (desarrollo local)")
        bot.remove_webhook()
        bot.polling(none_stop=True)