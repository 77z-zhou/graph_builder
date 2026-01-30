from abc import ABC, abstractmethod


class BaseStorage(ABC):

    def __init__(self):
        super().__init__()


    @abstractmethod
    def add_short_term_memory(self, user_id: str, session_id: str, memory: dict):
        """Add short term memory"""
        ...

    @abstractmethod
    def get_short_term_memory(self):
        """Get short term memory"""
        ...

    @abstractmethod
    def pop_oldest_short_term_memory(self, user_id: str, session_id: str):
        """ pop short term oldest memory """
        ...


    @abstractmethod
    def add_mid_term_memory(self, user_id: str, segments: dict, access_frequency: dict):
        """Add mid term memory"""
        ...

    @abstractmethod
    def search_mid_term_segment(self, user_id: str, query_embedding: list[float], topk: int):
        ...
    

    @abstractmethod
    def load_mid_term_memory(self):
        """ Load mid term memory """
        ...


    @abstractmethod
    def add_long_term_memory(self, user_id: str,  user_profile, user_knowledge, assistant_knowledge):
        """ add long term memory """
        ...


    @abstractmethod
    def load_long_term_memory(self, knowledge_capacity):
        """ Load long term memory """
        ...

    
