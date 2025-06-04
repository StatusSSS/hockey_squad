def build(proxy_raw: str | None):
    """
    host:port:user:pass  →  dict для requests.
    """
    if not proxy_raw:
        return None
    host, port, user, pwd = proxy_raw.split(":")
    url = f"http://{user}:{pwd}@{host}:{port}"
    print("Proxy url:", url)
    return {"http": url, "https": url}
