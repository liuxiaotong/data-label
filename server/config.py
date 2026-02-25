"""服务配置"""

try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        host: str = "0.0.0.0"
        port: int = 8210
        debug: bool = False
        # antgather 回调地址（标注结果提交目标）
        antgather_url: str = "http://localhost:8200"

        class Config:
            env_prefix = "DATA_LABEL_"

except ImportError:
    from dataclasses import dataclass, field

    @dataclass
    class Settings:  # type: ignore[no-redef]
        host: str = "0.0.0.0"
        port: int = 8210
        debug: bool = False
        antgather_url: str = "http://localhost:8200"


settings = Settings()
