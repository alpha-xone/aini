![AINI](images/aini.png)

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
ds = aini('autogen/llm', 'ds')
agent = aini('autogen/assistant', name='deepseek', model=ds)

# Run the agent
ans = await agent.run('What is your name')

# Display component structure
aview(ans)
[Output]
<autogen_agentchat.base._task.TaskResult>
{
  'messages': [
    {
      'source': 'user',
      'content': 'What is your name',
      'type': 'TextMessage'
    },
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
