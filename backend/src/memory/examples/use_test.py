from backend.src.memory.memoryos import MemoryOS
from langchain.chat_models import init_chat_model
from langchain_huggingface import HuggingFaceEmbeddings
llm = init_chat_model("deepseek-chat")

embedding = HuggingFaceEmbeddings(model_name=r"E:\my_github_work\graph_builder\backend\local_model\Qwen\Qwen3-Embedding-0___6B")

mem = MemoryOS(llm=llm, embedding_fuc=embedding, storage_dir="./memory_test", short_term_max_capacity=3)

mem.save_memory("1","2233",user_query="What is the capital of France?", assistant_response="The capital of France is Paris.")

mem.save_memory("1", "2233", user_query="Who wrote 'To Kill a Mockingbird'?", assistant_response="Harper Lee wrote 'To Kill a Mockingbird'.")

mem.save_memory("1", "2233", user_query="What is the largest planet in our solar system?", assistant_response="Jupiter is the largest planet in our solar system.")

mem.save_memory("1", "2233", user_query="What is the boiling point of water?", assistant_response="The boiling point of water is 100°C at standard atmospheric pressure.")

mem.save_memory("1", "2233", user_query="Who painted the Mona Lisa?", assistant_response="Leonardo da Vinci painted the Mona Lisa.")