from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from .tools import get_repo_tree, read_file, search_code, get_repo_info

load_dotenv()

tools = [get_repo_tree, read_file, search_code, get_repo_info]

llm = ChatGroq(model="openai/gpt-oss-120b")

SYSTEM_PROMPT = """You are a code assistant. When given a GitHub repo and a question:
- Use get_repo_info and get_repo_tree first to understand the repo
- Use read_file to read relevant files
- Use search_code to find specific functions or keywords
- Use save_answer to answer the question asked by the user
- Answer clearly with file references and code examples
- Suggest exact fixes when asked about bugs"""

agent = create_react_agent(
    llm,
    tools=tools,
    state_modifier=SYSTEM_PROMPT
)
