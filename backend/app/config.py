from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Database
    database_url: str = "postgresql+asyncpg://vcf:vcfpass@localhost:5432/vcfdb"

    # VEP
    vep_mode: str = "rest"  # "rest" or "local"
    vep_binary: str = "vep"

    # bcftools
    bcftools_path: str = "bcftools"

    # Storage
    upload_dir: str = "./data/uploads"

    # NCBI
    ncbi_api_key: Optional[str] = None

    # AlphaGenome (DeepMind)
    alphagenome_api_key: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # App
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)
