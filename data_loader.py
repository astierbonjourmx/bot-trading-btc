import yfinance as yf
import pandas as pd
import ta
import numpy as np

def obtener_datos_pro(simbolo, periodo="2y", intervalo="1h"):
    print(f"--- Descargando datos para {simbolo} ---")
    
    df = yf.download(simbolo, period=periodo, interval=intervalo, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    
    # Limpieza inicial
    df = df.dropna()

    # --- 1. INDICADORES TÉCNICOS ---
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    
    # Retornos Logarítmicos (El cambio % puro)
    df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))

    # --- 2. MEMORIA DE CORTO PLAZO (LAGS) --- 
    # Aquí está el truco: Le damos a la IA lo que pasó hace 1, 2 y 3 horas
    # para que detecte patrones de movimiento.
    
    columnas_lag = ['Close', 'RSI', 'Log_Returns']
    for col in columnas_lag:
        for i in range(1, 4): # Creamos Lag 1, 2 y 3
            df[f'{col}_Lag_{i}'] = df[col].shift(i)

    # --- 3. TARGET (OBJETIVO) ---
    # Para filtrar el "ruido" (movimientos minúsculos), solo marcamos 1 si sube
    # PERO, vamos a intentar predecir el movimiento a 3 HORAS vista, no 1.
    # A veces 1 hora es puro ruido, 3 horas es tendencia.
    futuro = 3 
    df['Target'] = np.where(df['Close'].shift(-futuro) > df['Close'], 1, 0)

    # Borramos los nulos generados por los Lags
    df = df.dropna()
    
    print(f"Datos procesados con Memoria. Total de velas: {len(df)}")
    return df

if __name__ == "__main__":
    datos = obtener_datos_pro("BTC-USD")
    # Imprimimos las columnas nuevas para verificar
    cols_nuevas = [c for c in datos.columns if 'Lag' in c]
    print("\n--- NUEVAS COLUMNAS DE MEMORIA ---")
    print(datos[cols_nuevas].tail(3))