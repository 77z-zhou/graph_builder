from config import settings
from langchain_core.callbacks.manager import CallbackManager
from langchain_core.callbacks import BaseCallbackHandler
from langchain.chat_models import init_chat_model


import logging
logger = logging.getLogger(__name__)

class UniversalTokenUsageHandler(BaseCallbackHandler):
    """ 通用的 LLM token 使用统计处理类 """
    def __init__(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def on_llm_end(self, response, *, run_id, parent_run_id = None, **kwargs):
        usage = response.llm_output.get("token_usage") if response.llm_output else None

        if usage:
            self.total_prompt_tokens += usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            self.total_completion_tokens += usage.get("completion_tokens") or usage.get("output_tokens") or 0
            return 
    
        for generations in response.generations:
            for generation in generations:
                if hasattr(generation, "message"):
                    metadata = getattr(generation.message, "usage_metadata")
                    if metadata:
                        self.total_prompt_tokens += metadata.get("input_tokens", 0)
                        self.total_completion_tokens += metadata.get("output_tokens", 0)

    def report(self):
        """ 输出统计结果 """
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens
        }



def get_llm(model: str):
    """ 根据模型名称 获取指定的 LLM """

    # 1. 获取模型的 api key, base_url等
    model = model.lower().replace("-","_").strip()
    env_key = f"LLM_MODEL_{model}"
    env_value = getattr(settings, env_key)
    if not env_value:
        err = f"Environment variable '{env_key}' is not defined as per format or missing"
        logger.error(err)
        raise Exception(err)  
    
    logger.info(f"Model:{env_key}")

    callback_handler = UniversalTokenUsageHandler()
    # callback_manager = CallbackManager([callback_handler])

    try:
        if "deepseek" in model:
            model_name, api_key, base_url = env_value.split(",")
            llm = init_chat_model(model_name, api_key=api_key, base_url=base_url)
    
        elif "dashscope" in model:
            model_name, api_key, base_url = env_value.split(",")
            llm = init_chat_model(model_name, api_key=api_key, base_url=base_url)


    except Exception as e:
        err = f"Error while creating LLM '{model}': {str(e)}"
        logger.error(err)
        raise Exception(err)
    
    logger.info(f"Model created - Model Version: {model}")
    return llm, model_name, callback_handler

