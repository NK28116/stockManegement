import numpy as np

def moving_average(data, window):
    return np.convolve(data, np.ones(window)/window, mode='valid')

def rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100./(1.+rs)

    for i in range(period, len(prices)):
        delta = deltas[i-1]
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up*(period-1)+upval)/period
        down = (down*(period-1)+downval)/period
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1.+rs)
    return rsi[-1]