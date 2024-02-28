class Config:
    def __init__(self, 
                base_url: str,
                login_url: str, 
                username: str, 
                password: str, 
                redis_host: str,
                proxy: str = None):
        self.base_url = base_url
        self.login_url = login_url
        self.username = username
        self.password = password
        self.proxy = proxy
        self.redis_host = redis_host