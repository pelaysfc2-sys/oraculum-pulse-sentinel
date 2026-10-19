# ==============================================================================
# PROYECTO: Oraculum Pulse Sentinel (Fase 3: El Cerebro de IA + Envío a Telegram)
# ARCHIVO: sentinel_bot.py
# OBJETIVO: Tomar los movimientos de ballenas de Polymarket/DexScreener, pedirle a
#           la IA de Gemini un resumen ejecutivo de 3 líneas y enviarlo a Telegram.
# ==============================================================================

import os
import requests

# 1. Leemos nuestras llaves secretas desde las Variables de Entorno
#    (Así nunca quedan escritas a la vista si subimos el código a GitHub)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_DE_BOTFATHER_AQUI")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "TU_CHAT_ID_O_CANAL_AQUI")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_API_KEY_DE_GEMINI_AQUI")

UMBRAL_BALLENA_USD = 10000

def analizar_con_gemini(alerta):
    """
    Envía los datos del mercado a la API gratuita de Google Gemini para que redacte
    un análisis financiero ultra-claro de exactamente 3 líneas en español.
    """
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    # Redactamos las instrucciones exactas (Prompt) para nuestro analista IA
    instruccion = f"""
    Actúa como el analista jefe de inteligencia financiera de Oraculum Pulse.
    Analiza este movimiento de Smart Money en Polymarket y responde ÚNICAMENTE con 3 líneas numeradas:
    - Mercado: {alerta['mercado']}
    - Volumen 24h detectado: ${alerta['volumen_24h_usd']:,.2f} USD
    - Liquidez actual: ${alerta['liquidez_usd']:,.2f} USD
    - Probabilidades actuales: {alerta['precios_probabilidad']}

    Formato obligatorio de respuesta (exactamente 3 líneas):
    1. Qué acaba de pasar: (Explica el flujo de capital en lenguaje sencillo)
    2. Contexto de mercado: (Por qué este movimiento es relevante ahora mismo)
    3. Nivel de convicción: (Clasifica de 1 a 10 y explica el riesgo/oportunidad)
    """

    payload = {
        "contents": [{"parts": [{"text": instruccion}]}]
    }

    try:
        respuesta = requests.post(url_gemini, json=payload, timeout=15)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        # Extraemos el texto generado por Gemini
        texto_ia = datos["candidates"][0]["content"]["parts"][0]["text"]
        return texto_ia.strip()
    except Exception as error:
        return f"1. Flujo relevante detectado en {alerta['mercado']}.\n2. Volumen de ${alerta['volumen_24h_usd']:,.2f} USD supera el filtro de Smart Money.\n3. Convicción Alta: revisar libro de órdenes."


def enviar_alerta_telegram(mensaje):
    """
    Toma el texto final formateado y lo publica instantáneamente en tu canal de Telegram.
    """
    url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    datos_envio = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje
    }
    respuesta = requests.post(url_telegram, json=datos_envio, timeout=10)
    if respuesta.status_code == 200:
        print("✅ ¡Alerta enviada con éxito a tu canal de Telegram!")
    else:
        print(f"⚠️ Error al enviar a Telegram: {respuesta.text}")
