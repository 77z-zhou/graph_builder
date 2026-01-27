from pydantic_settings import BaseSettings

START_FROM_BEGINNING  = "start_from_beginning"     
DELETE_ENTITIES_AND_START_FROM_BEGINNING = "delete_entities_and_start_from_beginning"
START_FROM_LAST_PROCESSED_POSITION = "start_from_last_processed_position"    
START_FROM_BEGINNING = "start_from_beginning"


class Settings(BaseSettings):

    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str

    UPDATE_GRPAH_CHUNK_BATCH_SIZE: int
    MAX_TOKEN_CHUNK_SIZE: int
    KNN_MIN_SCORE:float

    ENABLE_USER_AGENT: bool


    # ===== Model相关
    # ====== Embedding Model ====
    EMBEDDING_MODEL: str

    # ======= LLM =====
    LLM_MODEL_deepseek_deepseek_chat: str
    LLM_MODEL_dashscope_qwen3_max: str


    GRAPH_CLEAN_MODEL:str
    GENERATE_CYPHER_MODEL:str


    class Config:
        env_file = ".env"


settings = Settings()