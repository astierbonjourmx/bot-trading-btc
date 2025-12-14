import os
import requests
import joblib
import pandas as pd
import ta
import numpy as np
import yfinance as yf
import ccxt  # <--- La librería para operar

# --- 1. CONFIGURACIÓN DE SECRETOS ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
API_KEY = os.environ["BINANCE_API_KEY"]
SECRET_KEY = os.environ["BINANCE_SECRET_KEY"]

# --- 2. CONFIGURACIÓN DE TRADING ---
MONTO_INVERSION = 20  # Cantidad en USDT a comprar por operación
SIMBOLO_EXCHANGE = 'BTC/USDT' # Formato para Binance

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error Telegram: {e}")

def ejecutar_compra_real(precio_entrada):
    print("--- ⚡ INTENTANDO EJECUTAR COMPRA AUTOMÁTICA ---")
    
    try:
        # Conexión con Binance (o cambia 'binance' por 'bybit' si usas ese)
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': SECRET_KEY,
            'enableRateLimit': True
        })
        
        # 1. Verificar saldo USDT
        balance = exchange.fetch_balance()
        usdt_disponible = balance['USDT']['free']
        
        if usdt_disponible < MONTO_INVERSION:
            return f"❌ SALDO INSUFICIENTE. Tienes ${usdt_disponible:.2f}, necesitas ${MONTO_INVERSION}."
            
        # 2. Calcular cuánto BTC comprar
        # Ejemplo: 20 USDT / $90,000 = 0.000222 BTC
        cantidad = MONTO_INVERSION / precio_entrada
        
        # 3. LANZAR LA ORDEN DE MERCADO 🚀
        # 'create_market_buy_order' compra YA al mejor precio disponible
        orden = exchange.create_market_buy_order(SIMBOLO_EXCHANGE, cantidad)
        
        print("✅ ORDEN EJECUTADA CORRECTAMENTE")
        return (f"✅ **COMPRA AUTOMÁTICA ÉXITOSA**\n"
                f"🆔 ID Orden: {orden['id']}\n"
                f"💎 Cantidad: {orden['amount']} BTC\n"
                f"💵 Costo: ${orden['cost']:.2f} USDT")
                
    except Exception as e:
        print(f"❌ FALLO EN LA EJECUCIÓN: {e}")
        return f"⚠️ **ERROR AL COMPRAR:** {str(e)}"

# ... (El resto de funciones de datos e IA siguen igual) ...
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
    print("--- ☁️ EJECUTANDO VIGILANCIA + TRADING ---")
    
    try:
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
        # CALCULO DE SALIDAS (Solo informativo por ahora)
        tp = precio + (3.0 * atr)
        sl = precio - (2.0 * atr)
        
        mensaje_base = (
            f"🚀 **SEÑAL DETECTADA** 🚀\n"
            f"💰 Precio Base: ${precio:,.2f}\n"
            f"🤖 Confianza: {probabilidad:.2%}\n"
            f"🎯 TP Sugerido: ${tp:,.2f}\n"
            f"🛡️ SL Sugerido: ${sl:,.2f}\n"
            f"--------------------------\n"
        )
        
        # --- AQUÍ OCURRE LA MAGIA AUTOMÁTICA ---
        resultado_trading = ejecutar_compra_real(precio)
        
        enviar_telegram(mensaje_base + resultado_trading)
        print("✅ Ciclo completado.")
        
    else:
        print(f"⚪ Sin señal (Confianza: {probabilidad:.2%}).")

if __name__ == "__main__":
    vigilar_mercado()
