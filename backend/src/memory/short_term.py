from collections import deque
from collections import defaultdict
from typing import Iterable

from langgraph.store.base import PutOp

from .storage.base import BaseStorage
from .utils import ensure_directory_exists, get_timestamp

import logging
logger = logging.getLogger(__name__)

class ShortTermMemory:

    namespace_prefix = "short_term_memory"

    def __init__(self, storage: BaseStorage, max_capacity=10):
        super().__init__()

        self.max_capacity = max_capacity
        self.storage = storage
        self.user_session_memory = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))
        self.load()

    
    def add_memory(self, user_id, session_id, mem: dict):
        """ 添加 short term memory """

        # 维护 FIFO 队列
        self.user_session_memory[user_id][session_id].append(mem)
        
        # 入库
        self.storage.add_short_term_memory(user_id, session_id, mem)
    
    def get_memory(self, user_id, session_id):
        """ 获取用户会话历史 """
        return self.user_session_memory[user_id][session_id]



    def is_full(self, user_id, session_id):
        session = self.user_session_memory.get(user_id)
        memory = session.get(session_id)
        return len(memory) >= self.max_capacity


    def pop_oldest(self, user_id, session_id):
        session = self.user_session_memory.get(user_id)
        memory = session.get(session_id)
        if memory:
            msg = memory.popleft()
            self.storage.pop_oldest_short_term_memory(user_id, session_id)
            logger.info(f"ShortTermMemory: Popped oldest message: {msg}")
            return msg
        return None



    


    def load(self):
        """ initialize memory from storage """
        try:
            loaded_memory = self.storage.get_short_term_memory()

            self.user_session_memory = loaded_memory

            logger.info(f"ShortTermMemory: Loaded {len(self.user_session_memory)} items.")
        except Exception as e:
            logger.info(f"ShortTermMemory: Error loading: {e}. Initializing new memory.") 