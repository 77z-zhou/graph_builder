from langchain.agents import AgentState


class SimpleGraphRAGState(AgentState):
    question: str   # 用户问题