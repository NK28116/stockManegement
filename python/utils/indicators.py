def signal_from_close(prev_close, curr_close):
    return "+" if curr_close > prev_close else "-"