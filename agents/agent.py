from typing import Any

from agents.tools import tools

from langgraph.prebuilt import create_react_agent

from langchain_core.messages import HumanMessage
from langchain_google_vertexai import ChatVertexAI

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.chat_agent_executor import AgentState

model_with_tools = ChatVertexAI(model='gemini-1.5-flash-002').bind_tools(tools)

QUERY = "How many account does James Smith (credit card number 8248) have?"

class State(AgentState):
    # updated by the tool
    user_id: int

def should_continue(state: State):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


def call_model(state: State):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools)

workflow = StateGraph(State)

# Define the two nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app = workflow.compile()