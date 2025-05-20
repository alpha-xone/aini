# === Idea Validator Implementation in Graph ===

from aini import aini

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, START, END


class IdeaClarification(BaseModel):

    originality: str = Field(..., description="Originality of the idea.")
    mission: str = Field(..., description="Mission of the company.")
    objectives: str = Field(..., description="Objectives of the company.")


class MarketResearch(BaseModel):

    total_addressable_market: str = Field(..., description="Total addressable market (TAM).")
    serviceable_available_market: str = Field(..., description="Serviceable available market (SAM).")
    serviceable_obtainable_market: str = Field(..., description="Serviceable obtainable market (SOM).")
    target_customer_segments: str = Field(..., description="Target customer segments.")


roles = aini('./idea_validator')
formatter = {'clarifier': IdeaClarification, 'researcher': MarketResearch}


def agent(role: str):
    """Create an agent for a specific role."""
    return aini(
        'lang/react',
        name=role,
        prompt=roles[role],
        model=aini('lang/llm:ds'),
        response_format=formatter.get(role, None),
    )


graph = (
    StateGraph(MessagesState)
    .add_node("clarifier", agent("clarifier"))
    .add_node("researcher", agent("researcher"))
    .add_node("competitor", agent("competitor"))
    .add_node("report", agent("report"))
    .add_edge(START, "clarifier")
    .add_edge("clarifier", "researcher")
    .add_edge("researcher", "competitor")
    .add_edge("competitor", "report")
    .add_edge("report", END)
    .compile()
)
