import os
import requests
import joblib
import pandas as pd
import ta
import numpy as np
import yfinance as yf

# --- LEEMOS LOS SECRETOS DE LA CONFIGURACIÓN DE GITHUB ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

def obtener_datos_actuales(simbolo="BTC-USD"):
    df = yf.download(simbolo, period="1mo", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))

    columnas_lag = ['Close', 'RSI', 'Log_Returns']
    for col in columnas_lag:
        for i in range(1, 4):
            df[f'{col}_Lag_{i}'] = df[col].shift(i)

    return df.iloc[-1:].copy()

def vigilar_mercado():
    print("--- ☁️ EJECUTANDO EN LA NUBE ---")
    
    try:
        # La nube buscará el archivo en su propia carpeta
        model = joblib.load('modelo_trading_btc.pkl')
    except:
        print("❌ Error: No encuentro el modelo .pkl")
        return

    datos = obtener_datos_actuales("BTC-USD")
    precio = datos['Close'].values[0]
    atr = datos['ATR'].values[0]
    
    features = [
        'RSI', 'SMA_50', 'ATR', 'Log_Returns',       
        'RSI_Lag_1', 'RSI_Lag_2', 'RSI_Lag_3',       
        'Log_Returns_Lag_1', 'Log_Returns_Lag_2',    
        'Close_Lag_1'                                
    ]
    
    probabilidad = model.predict_proba(datos[features])[0][1]
    
    UMBRAL = 0.53
    ATR_MAXIMO = 300
    
    if atr > ATR_MAXIMO:
        print(f"⛔ Mercado peligroso (ATR: {atr:.2f}).")
    elif probabilidad > UMBRAL:
        tp = precio + (3.0 * atr)
        sl = precio - (2.0 * atr)
        mensaje = (
            f"🚀 **SEÑAL DE COMPRA BTC (Desde la Nube)** 🚀\n\n"
            f"💰 **Precio:** ${precio:,.2f}\n"
            f"🤖 **Confianza:** {probabilidad:.2%}\n"
            f"🎯 **TP:** ${tp:,.2f}\n"
            f"🛡️ **SL:** ${sl:,.2f}"
        )
        enviar_telegram(mensaje)
        print("✅ Señal enviada.")
    else:
        print(f"⚪ Sin señal (Confianza: {probabilidad:.2%}).")

if __name__ == "__main__":
    vigilar_mercado()
