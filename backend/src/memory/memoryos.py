from langgraph.store.base import BaseStore, Item, SearchItem, PutOp
from langchain_core.language_models import BaseLanguageModel
from langchain_core.embeddings import Embeddings


from .mid_term import MidTermMemory
from .long_term import LongTermMemory
from .short_term import ShortTermMemory
from .updater import MemoryUpdater
from .retriever import MemoryRetriever
from .multitask_llm import MultiTaskLLM
from .storage.file_storage import FileStorage

from .utils import *

import json

import logging
logger = logging.getLogger(__name__)

class MemoryOS(BaseStore):

    def __init__(self, 
                 llm: BaseLanguageModel, 
                 embedding_fuc: Embeddings, 
                 storage_dir: str, 
                 short_term_max_capacity=10,
                 mid_term_max_capacity=2000,
                 topic_similarity_threshold=0.6,
                 mid_term_heat_threshold=5.0,
                 knowledge_capacity=100,
                 retrieval_page_topk=7
    ):
        super().__init__()

        self.llm = llm
        self.storage = FileStorage(storage_dir)

        self.multitask_llm = MultiTaskLLM(llm)

        # 短期记忆
        self.short_term_memory = ShortTermMemory(
            storage=self.storage, 
            max_capacity=short_term_max_capacity
        )

        # 中期记忆
        self.mid_term_memory = MidTermMemory(
            multitask_llm=self.multitask_llm,
            embedding_func=embedding_fuc,
            storage=self.storage,
            max_capacity=mid_term_max_capacity
        )

        # 长期记忆
        self.long_term_memory = LongTermMemory(
            embedding_func=embedding_fuc,
            storage=self.storage,
            knowledge_capacity=knowledge_capacity
        )
        
        # 记忆更新器 (STM->MTM  ,MTM->LTM)
        self.memory_updater = MemoryUpdater(
            multitask_llm=self.multitask_llm, 
            short_term_memory=self.short_term_memory,
            mid_term_memory=self.mid_term_memory,
            long_term_memory=self.long_term_memory,
            topic_similarity_threshold=topic_similarity_threshold,
            mid_term_heat_threshold=mid_term_heat_threshold
        )

        # 记忆检索器
        self.memory_retriever = MemoryRetriever(
            short_term_memory=self.short_term_memory,
            mid_term_memory=self.mid_term_memory,
            long_term_memory=self.long_term_memory,
            retrieval_page_topk=retrieval_page_topk
        )


    def save_memory(self, 
                    user_id: str, 
                    session_id: str, 
                    user_query: str, 
                    assistant_response: str, 
                    timestamp: str=None    # 完成会话的时间
    ):
        if not timestamp:
            timestamp = get_timestamp()

        messages = {
            "user": user_query,
            "assistant": assistant_response
        }

        namespace = (user_id,)
        key = session_id
        self.put(namespace, key, messages)



    def _put_memory(self, op: PutOp):
        """ 添加记忆 """
        user_id = op.namespace[0]
        session_id = op.key
        mem = op.value

        # 1. 添加短期记忆
        self.short_term_memory.add_memory(user_id, session_id, mem)

        # 2. 短期记忆已满，则将短期记忆转移到中期记忆中
        if self.short_term_memory.is_full(user_id, session_id):
            self.memory_updater.process_short_term_to_mid_term(user_id, session_id)

        # 3. 检查中期记忆中的热点segment,若达到阈值则触发用户画像/知识更新
        self.memory_updater._trigger_profile_and_knowledge_update_if_needed(user_id)



    
    def search_memory(self, 
                      user_id: str, 
                      session_id: str, 
                      query: str, 
                      user_conversation_meta_data: dict = None  # 提供的额外用户对话元信息
    ):
        """ 检索用户跟问题相关的记忆 """

        logger.info(f" Retrieve memory for user question:{query[:50]}")

        # 1. 检索上下文 (中期记忆 + 长期记忆)
        retrieval_result = self.memory_retriever.retriever_memory(user_id, query)


        retrieved_pages = retrieval_result["retrieved_pages"]  # 检索到中期记忆的pages
        retrieved_user_knowledge = retrieval_result["retrieved_user_knowledge"]  # 检索到的用户长期知识
        retrieved_assistant_knowledge = retrieval_result["retrieved_assistant_knowledge"] # 检索到的助手长期知识


         # 2. 获取 短期记忆(会话历史)
        short_term_history = self.short_term_memory.get_memory(user_id, session_id)
        short_term_memory = "\n".join([
            f"User: {qa.get('user', '')}\nAssistant: {qa.get('assistant', '')} (Time: {qa.get('timestamp', '')})"
            for qa in short_term_history
        ])


        # 3. 格式化检索的 中期记忆pages
        mid_term_memory = "\n".join([
            f"【Historical Memory】\nUser: {page.get('user', '')}\nAssistant: {page.get('assistant', '')}\nTime: {page.get('timestamp', '')}\nConversation chain overview: {page.get('meta_info','N/A')}"
            for page in retrieved_pages
        ])

        # 4. 获取用户画像
        user_profile_text = self.long_term_memory.get_user_profile(user_id)
        if not user_profile_text or user_profile_text.lower() == "none": 
            user_profile_text = "No detailed profile available yet."

        # 5. 格式化用户长期知识
        user_knowledge_background = ""
        if retrieved_user_knowledge:
            user_knowledge_background = "\n【Relevant User Knowledge Entries】\n"
            for kn_entry in retrieved_user_knowledge:
                user_knowledge_background += f"- {kn_entry['knowledge']} (Recorded: {kn_entry['timestamp']})\n"
        
        background_context = f"【User Profile】\n{user_profile_text}\n{user_knowledge_background}"

        # 6. 格式化 助手长期知识
        assistant_knowledge_text_for_prompt = "【Assistant Knowledge Base】\n"
        if retrieved_assistant_knowledge:
            for ak_entry in retrieved_assistant_knowledge:
                assistant_knowledge_text_for_prompt += f"- {ak_entry['knowledge']} (Recorded: {ak_entry['timestamp']})\n"
        else:
            assistant_knowledge_text_for_prompt += "- No relevant assistant knowledge found for this query.\n"

    
        # 7. 格式化用户对话的元信息
        meta_data_text_for_prompt = "【Current Conversation Metadata】\n"
        if user_conversation_meta_data:
            try:
                meta_data_text_for_prompt += json.dumps(user_conversation_meta_data, ensure_ascii=False, indent=2)
            except TypeError:
                meta_data_text_for_prompt += str(user_conversation_meta_data)
        else:
            meta_data_text_for_prompt += "None provided for this turn."


        return {
            "short_term_memory": short_term_memory,
            "mid_term_memory": mid_term_memory,
            "user_background_context": background_context,
            "assistant_knowledge_text_for_prompt": assistant_knowledge_text_for_prompt,
            "meta_data_text_for_prompt": meta_data_text_for_prompt
        }




    def batch(self, ops):
        for i, op in enumerate(ops):
            if isinstance(op, PutOp):
                self._put_memory(op)

        return []

    
    async def abatch(self, ops):
        return []
    




