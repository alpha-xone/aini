![AINI](images/aini.gif)

# aini

Make **AI** class **ini**tialization easy with auto-imports.

## Installation

```bash
pip install aini
```

## Usage

### [Autogen](https://github.com/microsoft/autogen)

Use [DeepSeek](https://platform.deepseek.com/) as the model for the assistant agent.

```python
from aini import aini, aview

# Load assistant agent with DeepSeek as its model - requires DEEPSEEK_API_KEY
client = aini('autogen/client', model=aini('autogen/llm', 'ds'))
agent = aini('autogen/assistant', name='deepseek', model_client=client)

# Run the agent
ans = await agent.run(task='What is your name')

# Display result structure
aview(ans)
[Output]
<autogen_agentchat.base._task.TaskResult>
{
  'messages': [
    {'source': 'user', 'content': 'What is your name', 'type': 'TextMessage'},
    {
      'source': 'ds',
      'models_usage <autogen_core.models._types.RequestUsage>': {
        'prompt_tokens': 32,
        'completion_tokens': 17
      },
      'content': 'My name is DeepSeek Chat! 😊 How can I assist you today?',
      'type': 'TextMessage'
    }
  ]
}

# Display agent structure with private keys included
aview(agent._model_context, inc_=True, max_depth=5)
[Output]
<autogen_core.model_context._unbounded_chat_completion_context.UnboundedChatCompletionContext>
{
  '_messages': [
    {'content': 'What is your name', 'source': 'user', 'type': 'UserMessage'},
    {
      'content': 'My name is DeepSeek Chat! 😊 How can I assist you today?',
      'source': 'ds',
      'type': 'AssistantMessage'
    }
  ]
}
```

### [Agno](https://github.com/agno-agi/agno)

```python
# Load an agent with tools from configuration files
agent = aini('agno/agent', tools=[aini('agno/tools', 'google')])

# Run the agent
ans = agent.run('Compare MCP and A2A')

# Display component structure with filtering
aview(ans, exclude_keys=['metrics'])
[Output]
<agno.run.response.RunResponse>
{
  'content': "Here's a comparison between **MCP** and **A2A**: ...",
  'content_type': 'str',
  'event': 'RunResponse',
  'messages': [
    {
      'role': 'user',
      'content': 'Compare MCP and A2A',
      'add_to_agent_memory': True,
      'created_at': 1746758165
    },
    {
      'role': 'assistant',
      'tool_calls': [
        {
          'id': 'call_0_21871e19-3de7-4a8a-9275-9b4128fb743c',
          'function': {
            'arguments': '{"query":"MCP vs A2A comparison","max_results":5}',
            'name': 'google_search'
          },
          'type': 'function'
        }
      ]
    }
  ]
  ...
}

# Export to YAML for debugging
aview(ans, to_file='debug/output.yaml')
```

### [Mem0](https://mem0.ai/)

```python
memory = aini('mem0/mem0', 'mem0')
```
