from langchain_core.embeddings import Embeddings

import faiss
from collections import defaultdict, deque

from .utils import * 
from .storage.base import BaseStorage



import logging
logger = logging.getLogger(__name__)

class LongTermMemory:

    def __init__(self, embedding_func: Embeddings, storage: BaseStorage, knowledge_capacity: int=100):
        
        self.embedding_func = embedding_func
        self.storage = storage
        self.knowledge_capacity = knowledge_capacity

        self.user_profiles = defaultdict(dict)  # {user_id: {data: "profile_string", "last_updated": "timestamp"}}
        self.user_knowledge = defaultdict(lambda: deque(maxlen=knowledge_capacity))
        self.assistant_knowledge = defaultdict(lambda: deque(maxlen=knowledge_capacity))

        self.load()


    def get_user_profile(self, user_id: str):
        """ 获取用户画像 """
        return self.user_profiles.get(user_id)
    

    def add_knowledge_entry(self, knowledge_text, knowledge_deque: deque):
        """ 添加用户/助手 知识长期记忆"""

        vec = self.embedding_func.embed_documents([knowledge_text])[0]
        vec = normalize_vector(vec).tolist()

        entry = {
            "knowledge": knowledge_text,
            "timestamp": get_timestamp(),
            "knowledge_embedding": vec
        }
        knowledge_deque.append(entry)
        self.save()

    def add_user_knowledge(self, user_id, text: str):
        self.add_knowledge_entry(text, self.user_knowledge[user_id])

    def add_assistant_knowledge(self, user_id, text: str):
        self.add_knowledge_entry(text, self.assistant_knowledge[user_id])

    def update_user_profile(self, user_id: str, new_profile_data: str, merge: bool=True):
        """ 更新用户画像 """
        if merge and user_id in self.user_profiles and self.user_profiles[user_id].get("data"):
            current_data = self.user_profiles[user_id]["data"]
            if isinstance(current_data, str) and isinstance(new_profile_data, str):
                updated_data = f"{current_data}\n\n--- Updated on {get_timestamp()} ---\n{new_profile_data}"
            else: 
                updated_data = new_profile_data
        
        else:
            updated_data = new_profile_data
        
        self.user_profiles[user_id] = {
            "data": updated_data,
            "last_updated": get_timestamp()
        }
        
        self.save(user_id)

    def _search_knowledge_deque(self, query, knowledge_deque: deque, threshold=0.1, top_k=5):
        """ 检索 用户长期知识 / 助手长期知识"""
        # base case
        if not knowledge_deque:
            return []
        
        # 1. embed query
        query_vec = self.embedding_func.embed_query(query)
        query_vec = normalize_vector(query_vec)
        

        # 2. 取出 knowledge embedding
        embeddings = []
        valid_entries = []
        for entry in knowledge_deque:
            if "knowledge_embedding" in entry and entry["knowledge_embedding"]:
                embeddings.append(np.array(entry["knowledge_embedding"], dtype=np.float32))
                valid_entries.append(entry)
            else:
                print(f"Warning: Entry without embedding found in knowledge_deque: {entry.get('knowledge','N/A')[:50]}")

        if not embeddings:
            return []
        
        # 3. 校验embedding是否存在
        embeddings_np = np.array(embeddings, dtype=np.float32)
        if embeddings_np.ndim == 1: 
            if embeddings_np.shape[0] == 0: return [] 
            embeddings_np = embeddings_np.reshape(1, -1)
    
        if embeddings_np.shape[0] == 0: # No valid embeddings
            return []

        # 4. 使用faiss构建索引
        dim = embeddings_np.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings_np)
        
        # 5. IP内积计算相似度分数
        query_arr = np.array([query_vec], dtype=np.float32)
        distances, indices = index.search(query_arr, min(top_k, len(valid_entries)))
        
        # 6. 筛选相似度分数超过阈值的
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1: # -1 是无效索引
                similarity_score = float(distances[0][i]) 
                if similarity_score >= threshold:
                    results.append(valid_entries[idx])
        
        
        results.sort(key=lambda x: float(np.dot(np.array(x["knowledge_embedding"], dtype=np.float32), query_vec)), reverse=True)
        return results

    def search_user_knowledge(self, user_id, query, threshold=0.1, top_k=5):
        """ 检索用户长期知识 """
        results = self._search_knowledge_deque(query, self.user_knowledge[user_id], threshold, top_k)
        return results
    
    def search_assistant_knowledge(self, user_id, query, threshold=0.1, top_k=5):
        """ 检索助手长期知识 """
        results = self._search_knowledge_deque(query, self.assistant_knowledge[user_id], threshold, top_k)
        return results
    
    def save(self, user_id):
        user_profile = self.user_profiles[user_id]
        user_knowledge = self.user_knowledge[user_id]
        assistant_knowledge = self.user_knowledge[user_id]
        self.storage.add_long_term_memory(user_id, user_profile, user_knowledge, assistant_knowledge)

    def load(self):
        try:
            user_profiles, user_knowledge, assistant_knowledge = self.storage.load_long_term_memory(self.knowledge_capacity)
            self.user_profiles = user_profiles
            self.user_knowledge = user_knowledge
            self.assistant_knowledge = assistant_knowledge
        except Exception as e:
            logger.error(f"LongTermMemory: Error loading: {e}. Initializing new memory.")