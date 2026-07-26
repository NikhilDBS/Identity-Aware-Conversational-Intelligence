import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mistral_api_key: str = ""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    model_name: str = "mistral-medium-latest"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
