import asyncio
import os
from dotenv import load_dotenv
import chainlit as cl
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_azure import AzureAugmentedLLM
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.config import (
    Settings,
    GoogleSettings,
    OpenAISettings,
    AzureSettings,
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


mcp_app = MCPApp(name="chainlit_mcp_agent")
mcp_context = None
mcp_agent_app = None
browser_agent = None
llm = None

@cl.on_chat_start
async def on_chat_start():
    global mcp_context, mcp_agent_app, browser_agent, llm

    try:
        mcp_context = mcp_app.run()
        mcp_agent_app = await mcp_context.__aenter__()

        # Create the browser agent
        browser_agent = Agent(
            name="browser",
            instruction="""You are a helpful web browsing assistant that can interact with websites using puppeteer.
            - Navigate to websites and perform browser actions (click, scroll, type)
            - Extract information from web pages 
            - Take screenshots of page elements when useful
            - Provide concise summaries of web content using markdown
            - Follow multi-step browsing sequences to complete tasks
            When navigating, start with "https://modelcontextprotocol.io/introduction" unless instructed otherwise.""",
            server_names=["puppeteer"],
        )
        await browser_agent.initialize()

        # Attach Gemini-based LLM
        llm = await browser_agent.attach_llm(GoogleAugmentedLLM)

        tools = await browser_agent.list_tools()
        mcp_agent_app.logger.info("Tools available:", data=tools)

        await cl.Message(content="✅ Agent initialized and ready!").send()

    except Exception as e:
        await cl.Message(content=f"❌ Error during initialization: {str(e)}").send()


@cl.on_message
async def on_message(message: cl.Message):
    global llm

    if not llm:
        await cl.Message(content="❌ Agent not initialized.").send()
        return

    try:
        result = await llm.generate_str(
            message=message.content,
            request_params=RequestParams(use_history=True)
        )
        await cl.Message(content=result).send()

    except Exception as e:
        await cl.Message(content=f"❌ Error while processing your message: {str(e)}").send()
        