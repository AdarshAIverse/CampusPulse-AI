def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8")
