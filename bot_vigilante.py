import time
import requests
import joblib
import pandas as pd
import ta
import numpy as np
import yfinance as yf
from datetime import datetime

# --- 🤖 CONFIGURACIÓN TELEGRAM (Poner tus datos aquí) ---
TELEGRAM_TOKEN = "8559822331:AAGgbcCG6pJQOl6qZgkSFkMtxwAftVY70uQ"  # El que te dio BotFather
CHAT_ID = "5823519021"            # El que te dio userinfobot

# --- CONFIGURACIÓN DEL TIEMPO ---
TIEMPO_ESPERA = 60 * 60  # 3600 segundos = 1 Hora (Revisa cada hora)

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

def obtener_datos_actuales(simbolo="BTC-USD"):
    # Descargamos datos
    df = yf.download(simbolo, period="1mo", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    # Indicadores (Igual que el entrenamiento)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))

    # Memoria
    columnas_lag = ['Close', 'RSI', 'Log_Returns']
    for col in columnas_lag:
        for i in range(1, 4):
            df[f'{col}_Lag_{i}'] = df[col].shift(i)

    return df.iloc[-1:].copy()

def vigilar_mercado():
    print(f"[{datetime.now().strftime('%H:%M')}] 🔍 Escaneando mercado...")
    
    try:
        model = joblib.load('modelo_trading_btc.pkl')
    except:
        print("❌ Error: No encuentro el cerebro (.pkl)")
        return

    datos = obtener_datos_actuales("BTC-USD")
    precio = datos['Close'].values[0]
    atr = datos['ATR'].values[0]
    
    # Preparamos las características en orden
    features = [
        'RSI', 'SMA_50', 'ATR', 'Log_Returns',       
        'RSI_Lag_1', 'RSI_Lag_2', 'RSI_Lag_3',       
        'Log_Returns_Lag_1', 'Log_Returns_Lag_2',    
        'Close_Lag_1'                                
    ]
    
    probabilidad = model.predict_proba(datos[features])[0][1]
    
    # Parámetros
    UMBRAL = 0.53
    ATR_MAXIMO = 300
    
    # Lógica de decisión
    if atr > ATR_MAXIMO:
        print("⛔ Mercado peligroso (ATR Alto).")
        # Opcional: Avisar si quieres saber que está vivo pero no opera
        # enviar_telegram(f"⚠️ BTC Volátil (${atr:.2f}). Bot en pausa.")
        
    elif probabilidad > UMBRAL:
        # ¡BINGO! Señal encontrada
        tp = precio + (3.0 * atr)
        sl = precio - (2.0 * atr)
        
        mensaje = (
            f"🚀 **SEÑAL DE COMPRA BTC DETECTADA** 🚀\n\n"
            f"💰 **Precio:** ${precio:,.2f}\n"
            f"🤖 **Confianza IA:** {probabilidad:.2%}\n"
            f"-------------------\n"
            f"🎯 **Take Profit:** ${tp:,.2f}\n"
            f"🛡️ **Stop Loss:** ${sl:,.2f}\n"
            f"-------------------\n"
            f"⚠️ *Ejecutar orden ahora en Binance*"
        )
        print("✅ ¡SEÑAL ENVIADA A TELEGRAM!")
        enviar_telegram(mensaje)
    else:
        print(f"⚪ Todo tranquilo (Confianza: {probabilidad:.2%}). Sigo vigilando.")

# --- EL BUCLE INFINITO ---
if __name__ == "__main__":
    print("--- 🤖 BOT CENTINELA ACTIVADO ---")
    enviar_telegram("🤖 Bot Finzi Iniciado y Vigilando BTC...")
    
    while True:
        try:
            vigilar_mercado()
        except Exception as e:
            print(f"Error en el ciclo: {e}")
            enviar_telegram(f"⚠️ Error en el bot: {e}")
        
        print(f"💤 Durmiendo {TIEMPO_ESPERA/60} minutos...")
        time.sleep(TIEMPO_ESPERA) # Espera 1 hora antes de volver a revisar