# Example from https://docs.agno.com/examples/workflows/startup-idea-validator

from aini import aini

from pydantic import BaseModel, Field


class IdeaClarification(BaseModel):

    originality: str = Field(..., description="Originality of the idea.")
    mission: str = Field(..., description="Mission of the company.")
    objectives: str = Field(..., description="Objectives of the company.")


class MarketResearch(BaseModel):

    total_addressable_market: str = Field(..., description="Total addressable market (TAM).")
    serviceable_available_market: str = Field(..., description="Serviceable available market (SAM).")
    serviceable_obtainable_market: str = Field(..., description="Serviceable obtainable market (SOM).")
    target_customer_segments: str = Field(..., description="Target customer segments.")


def idea_validator(model=None, tools=None):
    """Idea validator workflow for startup ideas."""
    if model is None:
        # Use DeepSeek as the default LLM model
        model = aini('lang/llm:ds')
    if tools is None:
        # Use Tavily as the default search tool
        tools = [aini('lang/tool:tavily')]

    # Load roles from the idea_validator configuration
    roles = aini('lang_book/idea_validator')

    kwargs = {'model': model, 'tools': tools}
    return (
        # Agent will use DeepSeek as LLM model and Tavily as search tool by default
        aini('lang/react', response_format=IdeaClarification, prompt=roles['clarifier'], **kwargs)
        | aini('lang/react', response_format=MarketResearch, prompt=roles['researcher'], **kwargs)
        | aini('lang/react', prompt=roles['competitor'], **kwargs)
        | aini('lang/react', prompt=roles['report'], **kwargs)
    )


def gen_report(idea: str):
    """Generate a report for the idea."""
    return idea_validator().invoke({'messages': idea}).get('messages', None)


if __name__ == '__main__':
    # Example usage:
    # CD to parent folder and run: python lang_book/idea_validator.py
    idea = 'Ai agent to produce professional financial reports'
    report = gen_report(idea)
    if report:
        report[-1].pretty_print()
