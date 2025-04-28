import asyncio
import os
import streamlit as st
from dotenv import load_dotenv
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from pydantic import BaseModel
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.llm_selector import ModelPreferences
from mcp_agent.workflows.llm.augmented_llm_azure import AzureAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM
from mcp_agent.config import (
    Settings,
    OpenAISettings,
    AzureSettings,
    GoogleSettings,
    MCPSettings,
    MCPServerSettings,
)


load_dotenv(override=True)

settings = Settings(
        execution_engine="asyncio",
        mcp=MCPSettings(
            servers={
                "puppeteer": MCPServerSettings(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-puppeteer"],
                ),
            }
        ),
        gemini=GoogleSettings(
            api_key=os.environ["GEMINI_API_KEY"],
            default_model=os.environ["GEMINI_MODEL"],
        ),
        azure=AzureSettings(
            api_key=os.getenv("GITHUB_TOKEN"),
            endpoint=os.getenv("BASE_URL"),
            default_model=os.getenv("GITHUB_MODEL", "gpt-4.1"),
        )
        # openai=OpenAISettings(
        #     api_key=os.environ["GITHUB_TOKEN"],
        #     base_url=os.environ["BASE_URL"],
        #     model = os.getenv("GITHUB_MODEL", "gpt-4.1")
        # ),
    )


class Essay(BaseModel):
    title: str
    body: str
    conclusion: str


# Streamlit config
st.set_page_config(page_title="Browser Agent with MCP", page_icon="🌐", layout="wide")

# Custom CSS for styling
st.markdown("""
     <style>
    .main {
        background-color: #f8f9fa;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3, h4 {
        font-family: 'Segoe UI', sans-serif;
        color: #212529;
    }
    .stTextArea textarea {
        border-radius: 10px;
        border: 1px solid #ced4da;
        font-size: 16px;
        padding: 1rem;
    }
    .stButton button {
        background-color: #e63946;
        color: white;
        font-weight: 600;
        height: 3em;
        border-radius: 10px;
        border: none;
        margin-top: 1rem;
        transition: background-color 0.3s ease;
    }
    .stButton button:hover {
        background-color: #d62828;
    }
    .info-box {
        /*background-color: black;*/
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1.5rem;
    }
    .info-box ol, .info-box ul {
        padding-left: 1.5rem;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        font-size: 0.9rem;
        color: #6c757d;
    }
    .sidebar .sidebar-content {
        background-color: #f1f3f5;
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar examples
st.sidebar.title("Example Prompts")
st.sidebar.markdown("""
- Go to `https://modelcontextprotocol.io/introduction`
- Click on the link to object detection and take a screenshot
- Scroll down and summarize the content page

_Note: The agent uses Puppeteer to control a real browser._
""")

# Page content
st.markdown('<div class="centered-title"><h1>🌐 Intelligent Browser Agent with MCP</h1><p>Chat with a smart browsing agent that can explore and interact with websites just like you would</p></div>', unsafe_allow_html=True)


# User input
query = st.text_area("Your Prompt", placeholder="Ask the agent to navigate to websites and interact with them")

# Session state setup
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.mcp_app = MCPApp(name="streamlit_mcp_agent") # settings=settings
    st.session_state.mcp_context = None
    st.session_state.mcp_agent_app = None
    st.session_state.browser_agent = None
    st.session_state.llm = None
    st.session_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(st.session_state.loop)


# Setup agent function
async def setup_agent():
    if not st.session_state.initialized:
        try:
            st.session_state.mcp_context = st.session_state.mcp_app.run()
            st.session_state.mcp_agent_app = await st.session_state.mcp_context.__aenter__()

            st.session_state.browser_agent = Agent(
                name="browser",
                instruction="""You are a helpful web browsing assistant that can interact with websites using puppeteer.
                    - Navigate to websites and perform browser actions (click, scroll, type)
                    - Extract information from web pages 
                    - Take screenshots of page elements when useful
                    - Provide concise summaries of web content using markdown
                    - Follow multi-step browsing sequences to complete tasks
                """,
                server_names=["puppeteer"],

            )
            await st.session_state.browser_agent.initialize()

            # Use the custom LLM
            st.session_state.llm = await st.session_state.browser_agent.attach_llm(GoogleAugmentedLLM)

            logger = st.session_state.mcp_agent_app.logger
            tools = await st.session_state.browser_agent.list_tools()
            logger.info("Tools available:", data=tools)

            st.session_state.initialized = True
        except Exception as e:
            return f"Error during initialization: {str(e)}"
    return None


# Agent run function
async def run_mcp_agent(message):
    try:
        error = await setup_agent()
        if error:
            return error

        result = await st.session_state.llm.generate_str(
            message=message, 
            request_params=RequestParams
            (
                use_history=True,
                modelPreferences=ModelPreferences
                (
                    costPriority=0.1, speedPriority=0.2, intelligencePriority=0.5
                ),
            ),
        )
        return result
    except Exception as e:
        return f"Error: {str(e)}"

# Run button
if st.button("🧠 Run Prompt"):
    with st.spinner("Processing your request..."):
        result = st.session_state.loop.run_until_complete(run_mcp_agent(query))
    st.markdown("### 🤖 Agent Response")
    st.markdown(result)

# Help instructions
if 'result' not in locals():
    st.markdown("""
        <div class="info-box">
            <h4>How to use this app:</h4>
            <ol>
                <li>Define <code>GITHUB_TOKEN</code> and optional <code>GITHUB_MODEL</code> in environment variables</li>
                <li>Type a command for the agent to navigate and interact with websites</li>
                <li>Click 'Run Prompt' to see results</li>
            </ol>
            <h5>Capabilities:</h5>
            <ul>
                <li>Navigate to websites using Puppeteer</li>
                <li>Click on elements, scroll, and type text</li>
                <li>Take screenshots of specific elements</li>
                <li>Extract information from web pages</li>
                <li>Perform multi-step browsing tasks</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    © 2025 — Created with ❤️ using Streamlit, Puppeteer, and the MCP-Agent Framework
</div>
""", unsafe_allow_html=True)
