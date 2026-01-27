from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from modelscope import snapshot_download

from threading import Lock
import logging
import os

logger = logging.getLogger(__name__)


_lock = Lock()
_embedding_instance = None
MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
MODEL_PATH =  os.path.join(os.path.dirname(os.path.dirname(__file__)),"local_model")


def load_embedding_model(model_name: str):

    if model_name == "sentence_transformer":
        embeddings = get_local_sentence_transformer_embedding()
        dimension = 1024
        logger.info(f"Embedding: Using Langchain HuggingFaceEmbeddings. Dimension:{dimension}")
        
    return embeddings, dimension


def get_local_sentence_transformer_embedding():
    """ 加载 sentence transformer embedding"""
    # DCL
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance
    
    with _lock:
        if _embedding_instance is not None:
            return _embedding_instance
        # 1. 判断模型是否下载了
        model_path = os.path.join(MODEL_PATH, MODEL_NAME.replace(".","___").replace("/","\\") if "." in MODEL_NAME else MODEL_NAME.replace("/","\\"))
        
        print(model_path)
        if os.path.isdir(model_path):
            logger.info(f"Embedding Model already download at: {model_path}")
        else:
            # 2. 模型没有下载，则下载
            logger.info(f"Downloading model:{MODEL_NAME} to: {MODEL_PATH}")
            model_dir = snapshot_download(MODEL_NAME, cache_dir=MODEL_PATH)
            logger.info(f"Model:{MODEL_NAME} downloaded and saved:{model_dir}.")
        
        _embedding_instance = HuggingFaceEmbeddings(model_name=model_path,)
        logger.info("Embedding model initialized.")
        return _embedding_instance



