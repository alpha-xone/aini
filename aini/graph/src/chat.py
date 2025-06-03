from aini import aini

llm = aini('lang/llm:ds')
tools = [aini('lang/tools:tavily')]
agent = aini('lang/react', name='chat', model=llm, tools=tools)

graph = (
    aini('lang/graph', state_schema=aini('lang/msg:msg_state'))
    .add_node('chat', agent)
    .add_edge('__start__', 'chat')
    .add_edge('chat', '__end__')
)
