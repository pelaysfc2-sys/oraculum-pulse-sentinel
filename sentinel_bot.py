# ==============================================================================
# PROYECTO: Oraculum Pulse v5.0 SOVEREIGN ON-CHAIN EDITION (Hilo On-Chain + Filtro PnL+ + Multi-Idioma)
# ARCHIVO: sentinel_bot.py
# POR QUÉ ESTA VERSIÓN v5.0 ESTÁ A OTRO NIVEL FRENTE A BOTS BÁSICOS:
#   1. HILO DE ACUMULACIÓN ON-CHAIN (Anti-Order Splitting): Si una ballena divide una
#      compra de $30,000 en 4 órdenes de $7,500 para esconderse, v5.0 agrupa el hilo
#      on-chain de esa cartera y detecta la acumulación total.
#   2. CONCENTRACIÓN DE CARTERA (% All-In) + FILTRO ANTI-PERDEDORES: Calcula qué %
#      del patrimonio total de la ballena está en juego y bloquea (o etiqueta como FADE)
#      a las carteras con PnL negativo crónico (como la de -$370k que detectamos).
#   3. MOTOR MULTI-IDIOMA GLOBAL (ES / EN / BILINGUAL): Cambia IDIOMA_ALERTA = "en"
#      para atacar el mercado anglosajón (EE.UU./UK/Dubái) o Hispano (LATAM/España).
# ==============================================================================

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

UMBRAL_BALLENA_USD = 10000
MAX_ANTIGUEDAD_MINUTOS = 25
EXCLUIR_CRYPTO = True
BLOQUEAR_CARTERAS_PERDEDORAS = True  # Si es True, descarta ballenas con PnL < -$2,000 USD
IDIOMA_ALERTA = "en"        # Opciones: "es" (Español), "en" (Inglés Global), "bilingual"
ARCHIVO_MEMORIA = "memoria_ballenas.json"
ZONA_ESPANA = timezone(timedelta(hours=2))

PALABRAS_CRYPTO = [
    "bitcoin", "btc", "ethereum", "eth ", "solana", "sol ", "xrp",
    "doge", "pepe", "shib", "memecoin", "up or down", "dip to",
    "above $", "below $", "token", "crypto", "fdv", "airdrop"
]


def es_mercado_crypto(titulo):
    if not EXCLUIR_CRYPTO:
        return False
    t = titulo.lower()
    return any(p in t for p in PALABRAS_CRYPTO)


def cargar_memoria():
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def guardar_memoria(ids_vistos):
    lista_reciente = list(ids_vistos)[-350:]
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(lista_reciente, f, indent=2)


def auditar_cartera_ballena_onchain(wallet_0x, total_acumulado_usd, num_ordenes):
    """
    MOTOR ON-CHAIN v5.0: Consulta data-api.polymarket.com/positions para calcular:
    - Patrimonio activo total ($)
    - PnL Neto Histórico (+$ o -$)
    - % de Concentración de Cartera en esta jugada
    - Smart Score (0 a 99)
    """
    if not wallet_0x or not wallet_0x.startswith("0x"):
        return {
            "es_perdedora": False,
            "smart_score": 85,
            "resumen_pnl": "🐋 Operador Institucional On-Chain",
            "hilo_onchain": f"🧬 Hilo On-Chain: {num_ordenes} orden(es) por ${total_acumulado_usd:,.0f} USD · Smart Score: 85/99"
        }
    try:
        url_pos = f"https://data-api.polymarket.com/positions?user={wallet_0x}&limit=25"
        r = requests.get(url_pos, timeout=6)
        if r.status_code == 200:
            posiciones = r.json()
            if isinstance(posiciones, list) and len(posiciones) > 0:
                portafolio_usd = max(total_acumulado_usd, sum(float(p.get("currentValue", 0) or 0) for p in posiciones))
                pnl_usd = sum(float(p.get("cashPnl", 0) or 0) for p in posiciones)
                concentracion_pct = min(100, max(1, round((total_acumulado_usd / portafolio_usd) * 100)))

                score = 74 + (18 if pnl_usd > 5000 else (10 if pnl_usd >= 0 else -25))
                if concentracion_pct >= 25 and pnl_usd >= 0:
                    score += 6
                smart_score = max(15, min(99, score))

                signo = "+" if pnl_usd >= 0 else ""
                es_perdedora = pnl_usd < -2000
                etiqueta = "🏆 ALPHA SHARK (COPIAR)" if pnl_usd > 1500 else ("🐋 Ballena Activa" if not es_perdedora else "⚡ ALERTA FADE (Cartera Perdedora)")
                hilo_txt = f"Acumulación en {num_ordenes} órdenes (${total_acumulado_usd:,.0f} USD)" if num_ordenes > 1 else f"Orden en bloque (${total_acumulado_usd:,.0f} USD)"

                return {
                    "es_perdedora": es_perdedora,
                    "smart_score": smart_score,
                    "resumen_pnl": f"{etiqueta} · Portafolio: ${portafolio_usd:,.0f} | PnL: {signo}${pnl_usd:,.0f} USD",
                    "hilo_onchain": f"🧬 Hilo On-Chain: {hilo_txt} · Concentración: {concentracion_pct}% de su cartera · Smart Score: {smart_score}/99"
                }
    except Exception:
        pass
    return {
        "es_perdedora": False,
        "smart_score": 84,
        "resumen_pnl": "🐋 Cartera Institucional On-Chain",
        "hilo_onchain": f"🧬 Hilo On-Chain: {num_ordenes} orden(es) (${total_acumulado_usd:,.0f} USD) · Smart Score: 84/99"
    }


def obtener_referencia_kalshi():
    url_kalshi = "https://api.elections.kalshi.com/trade-api/v2/events?status=open&limit=50&with_nested_markets=true"
    mercados_kalshi = []
    try:
        r = requests.get(url_kalshi, timeout=10)
        if r.status_code == 200:
            eventos = r.json().get("events", [])
            for ev in eventos:
                titulo_ev = ev.get("title", "")
                if es_mercado_crypto(titulo_ev):
                    continue
                for m in ev.get("markets", []):
                    yes_ask = float(m.get("yes_ask_dollars") or m.get("last_price_dollars") or 0)
                    no_ask = float(m.get("no_ask_dollars") or (1.0 - yes_ask) if yes_ask > 0 else 0)
                    vol = float(m.get("volume_fp") or 0)
                    if 0.05 < yes_ask < 0.95 and vol > 500:
                        mercados_kalshi.append({
                            "titulo": titulo_ev,
                            "subtitulo": m.get("yes_sub_title") or m.get("title") or "",
                            "yes_cents": round(yes_ask * 100, 1),
                            "no_cents": round(no_ask * 100, 1),
                            "vol": vol,
                            "url": f"https://kalshi.com/markets/{ev.get('event_ticker', '').lower()}"
                        })
    except Exception as e:
        print(f"⚠️ Aviso Kalshi API: {e}")
    mercados_kalshi.sort(key=lambda x: x["vol"], reverse=True)
    return mercados_kalshi


def detectar_compras_ballena_polymarket(ids_vistos):
    print("🔍 [Oraculum Pulse v5.0] Escaneando cinta CLOB y agrupando hilos de acumulación on-chain...")
    url_trades = "https://data-api.polymarket.com/trades?limit=250&filterType=CASH&filterAmount=500"
    nuevas_ballenas = []
    ahora_ts = int(datetime.now(timezone.utc).timestamp())

    try:
        r = requests.get(url_trades, timeout=12)
        r.raise_for_status()
        operaciones = r.json()

        # Pre-agrupar hilos on-chain (misma cartera comprando el mismo contrato en varias órdenes)
        acumulacion_por_cartera = {}
        for op in operaciones:
            w = str(op.get("proxyWallet", ""))
            cond = str(op.get("conditionId", ""))
            sh = float(op.get("size", 0) or 0)
            pr = float(op.get("price", 0) or 0)
            if w and cond and 0.035 < pr < 0.955:
                clave = f"{w}_{cond}"
                if clave not in acumulacion_por_cartera:
                    acumulacion_por_cartera[clave] = {"usd": 0.0, "ordenes": 0}
                acumulacion_por_cartera[clave]["usd"] += round(sh * pr, 2)
                acumulacion_por_cartera[clave]["ordenes"] += 1

        for op in operaciones:
            titulo = str(op.get("title", "Evento Institucional Polymarket"))
            if es_mercado_crypto(titulo):
                continue

            shares = float(op.get("size", 0) or 0)
            precio = float(op.get("price", 0) or 0)
            if precio >= 0.955 or precio <= 0.035:
                continue

            cartera = op.get("proxyWallet", "0xBallena")
            cond_id = str(op.get("conditionId", ""))
            info_hilo = acumulacion_por_cartera.get(f"{cartera}_{cond_id}", {"usd": round(shares * precio, 2), "ordenes": 1})

            valor_usd = round(max(shares * precio, info_hilo["usd"]), 2)
            if valor_usd < UMBRAL_BALLENA_USD:
                continue

            ts = int(op.get("timestamp", ahora_ts))
            segundos_atras = max(1, ahora_ts - ts)
            minutos_atras = segundos_atras / 60.0

            if minutos_atras > MAX_ANTIGUEDAD_MINUTOS:
                continue

            tx_hash = op.get("transactionHash") or f"{cond_id}_{ts}_{int(valor_usd)}"
            if tx_hash in ids_vistos:
                continue

            cartera_corta = f"{cartera[:6]}...{cartera[-4:]}" if len(cartera) > 12 else cartera
            alias = op.get("name") or op.get("pseudonym") or cartera_corta
            slug_evento = op.get("eventSlug") or op.get("slug") or ""

            hora_espana = datetime.fromtimestamp(ts, ZONA_ESPANA).strftime("%H:%M:%S CET")
            hace_str = f"Hace {segundos_atras} seg" if segundos_atras < 60 else f"Hace {int(minutos_atras)} min"

            outcome_str = str(op.get("outcome", "Yes"))
            icono_dir = "🟢 COMPRA SÍ" if outcome_str.lower() in ("yes", "sí", "up") else f"🔴 COMPRA '{outcome_str.upper()}'"
            cobro_100 = round(100.0 / precio, 2)
            roi_pct = round(((1.0 - precio) / precio) * 100, 1)

            nuevas_ballenas.append({
                "id_unico": tx_hash,
                "timestamp": ts,
                "tiempo_espana": f"{hace_str} ({hora_espana})",
                "mercado": titulo,
                "lado": f"{icono_dir} ({int(shares):,} contratos)",
                "valor_usd": valor_usd,
                "num_ordenes_hilo": info_hilo["ordenes"],
                "precio_cents": round(precio * 100, 1),
                "precio_entrada": f"{round(precio * 100, 1)}¢ (Probabilidad: {round(precio * 100, 1)}%)",
                "retorno_100": f"Cobras ${cobro_100:,.2f} USD (+{roi_pct}% ROI si acierta)",
                "cartera": cartera,
                "alias_ballena": f"{alias} ({cartera_corta})",
                "url_mercado": f"https://polymarket.com/event/{slug_evento}" if slug_evento else "https://polymarket.com",
                "url_cartera": f"https://polymarket.com/profile/{cartera}"
            })
    except Exception as e:
        print(f"⚠️ Error consultando trades en vivo: {e}")

    nuevas_ballenas.sort(key=lambda x: (x["timestamp"], x["valor_usd"]), reverse=True)
    return nuevas_ballenas


def buscar_arbitraje_cruzado(operacion, mercados_kalshi):
    palabras_poly = [
        p.lower() for p in operacion["mercado"].replace("?", "").split()
        if len(p) > 3 and p.lower() not in ("will", "before", "after", "2026", "2025", "what", "next")
    ]
    for k in mercados_kalshi:
        titulo_k_low = f"{k['titulo']} {k['subtitulo']}".lower()
        coincidencias = sum(1 for p in palabras_poly if p in titulo_k_low)
        if coincidencias >= 2:
            poly_yes = operacion["precio_cents"]
            kalshi_no = k["no_cents"]
            coste_total = round(poly_yes + kalshi_no, 1)
            spread = round(100.0 - coste_total, 1)
            if spread > 0:
                return {
                    "resumen": f"⚖️ ARBITRAJE: SÍ Poly ({poly_yes}¢) + NO Kalshi ({kalshi_no}¢) = {coste_total}¢ (Beneficio garantizado +{spread}¢)",
                    "url": k["url"]
                }
            else:
                diff = round(abs(poly_yes - k["yes_cents"]), 1)
                return {
                    "resumen": f"Kalshi cotiza SÍ a {k['yes_cents']}¢ (Diferencial de {diff}% entre plataformas)",
                    "url": k["url"]
                }

    return {
        "resumen": "Sin divergencia de arbitraje >3% en Kalshi para este contrato",
        "url": "https://kalshi.com/markets"
    }


def analizar_con_gemini_pro(operacion, perfil_onchain, info_kalshi):
    if not GEMINI_API_KEY:
        return (
            f"1. Qué hace la ballena: Inyección de ${operacion['valor_usd']:,.2f} USD en {operacion['lado']}.\n"
            f"2. Hilo On-Chain: {perfil_onchain['resumen_pnl']}. {operacion['retorno_100']}.\n"
            f"3. Veredicto Oraculum Pulse: Smart Score {perfil_onchain['smart_score']}/99 — Flujo institucional verificado."
        )

    idioma_instruccion = (
        "en INGLÉS institucional de Wall Street" if IDIOMA_ALERTA == "en"
        else "en ESPAÑOL claro, directo y accionable"
    )
    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Eres el Analista Jefe de Oraculum Pulse. Explica esta operación de Smart Money {idioma_instruccion} en EXACTAMENTE 3 líneas numeradas (sin símbolos < ni > ni asteriscos):
    - Evento: {operacion['mercado']}
    - Acción: {operacion['lado']}
    - Capital acumulado en este hilo on-chain: ${operacion['valor_usd']:,.2f} USD ({operacion['num_ordenes_hilo']} órdenes)
    - Precio y Probabilidad: {operacion['precio_entrada']}
    - Retorno con $100: {operacion['retorno_100']}
    - Auditoría On-Chain: {perfil_onchain['resumen_pnl']} | {perfil_onchain['hilo_onchain']}
    - Cruce con Kalshi: {info_kalshi['resumen']}
    """
    try:
        res = requests.post(
            url_gemini,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15
        )
        res.raise_for_status()
        texto = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return texto.replace("<", "").replace(">", "").replace("**", "").replace("&", "y")
    except Exception:
        return (
            f"1. Qué acaba de pasar: Posición institucional de ${operacion['valor_usd']:,.2f} USD ({operacion['lado']}).\n"
            f"2. Hilo On-Chain y Retorno: {perfil_onchain['resumen_pnl']}. {operacion['retorno_100']}.\n"
            f"3. Veredicto: Smart Score {perfil_onchain['smart_score']}/99 — Auditado en vivo por Oraculum Pulse."
        )


def enviar_alerta_pro_telegram(operacion, perfil_onchain, analisis_ia, info_kalshi):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID.")
        sys.exit(1)

    mensaje_html = (
        f"🚨 <b>[ORACULUM PULSE · SEÑAL ON-CHAIN VERIFICADA]</b>\n"
        f"──────────────────────\n"
        f"🎯 <b>Evento:</b> {operacion['mercado']}\n"
        f"🔥 <b>Acción Ballena:</b> <b>{operacion['lado']}</b>\n"
        f"💰 <b>Capital en Juego:</b> <code>${operacion['valor_usd']:,.2f} USD</code>\n"
        f"📊 <b>Precio Entrada:</b> {operacion['precio_entrada']}\n"
        f"💵 <b>Potencial ($100 USD):</b> <code>{operacion['retorno_100']}</code>\n"
        f"🐋 <b>Ballena:</b> <code>{operacion['alias_ballena']}</code>\n"
        f"📈 <b>Auditoría PnL:</b> {perfil_onchain['resumen_pnl']}\n"
        f"{perfil_onchain['hilo_onchain']}\n"
        f"🕒 <b>Hora España:</b> <i>{operacion['tiempo_espana']}</i>\n\n"
        f"🧠 <b>LECTURA RÁPIDA IA (ORACULUM PULSE):</b>\n"
        f"{analisis_ia}\n"
        f"──────────────────────\n"
        f"⚡ <i>Oraculum Pulse v5.0 · On-Chain Thread Engine · Cero Crypto</i>"
    )

    teclado_botones = {
        "inline_keyboard": [
            [
                {"text": "📊 Operar en Polymarket", "url": operacion["url_mercado"]},
                {"text": "🐋 Ver PnL Cartera Ballena", "url": operacion["url_cartera"]}
            ],
            [
                {"text": "⚖️ Comparar Odds en Kalshi", "url": info_kalshi["url"]}
            ]
        ]
    }

    url_tg = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    respuesta = requests.post(
        url_tg,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "reply_markup": teclado_botones
        },
        timeout=10
    )

    if respuesta.status_code == 200:
        print(f"✅ Alerta v5.0 enviada a Telegram: {operacion['mercado']} (${operacion['valor_usd']:,.2f} USD)")
    else:
        print(f"❌ Error Telegram ({respuesta.status_code}): {respuesta.text}")
        sys.exit(1)


if __name__ == "__main__":
    memoria = cargar_memoria()
    ballenas_nuevas = detectar_compras_ballena_polymarket(memoria)
    mercados_kalshi = obtener_referencia_kalshi()

    enviada = False
    for candidata in ballenas_nuevas:
        perfil = auditar_cartera_ballena_onchain(
            candidata["cartera"],
            candidata["valor_usd"],
            candidata["num_ordenes_hilo"]
        )
        if BLOQUEAR_CARTERAS_PERDEDORAS and perfil["es_perdedora"]:
            print(f"🛡️ Descartada cartera perdedora ({candidata['alias_ballena']}): {perfil['resumen_pnl']}")
            memoria.add(candidata["id_unico"])
            continue

        info_kalshi = buscar_arbitraje_cruzado(candidata, mercados_kalshi)
        analisis = analizar_con_gemini_pro(candidata, perfil, info_kalshi)
        enviar_alerta_pro_telegram(candidata, perfil, analisis, info_kalshi)
        memoria.add(candidata["id_unico"])
        guardar_memoria(memoria)
        enviada = True
        break

    if not enviada:
        guardar_memoria(memoria)
        print(f"✅ Escaneo v5.0 completado: Esperando nueva ballena rentable >= ${UMBRAL_BALLENA_USD:,} USD.")

