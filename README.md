![AINI](images/aini.gif)

# aini

Declarative AI components - make **AI** component **ini**tialization easy with auto-imports.

## Installation

```bash
pip install aini
```

## Why aini?

- Simplified Initialization: Configure complex AI components with clean YAML files
- Variable Substitution: Use environment variables and defaults for sensitive values
- Auto-Imports: No need for multiple import statements
- Debugging Tools: Inspect objects with `aview` for better debugging
- Reusable Configs: Share configurations across projects

## Core Features

### Main Components

- `aini()`: Loads and instantiates objects from configuration files
- `aview()`: Visualizes complex nested objects for debugging
- `ameth()`: Lists available methods on an object

## Usage

### [LangChain / LangGraph](https://langchain-ai.github.io/langgraph/)

Use [`DeepSeek`](https://platform.deepseek.com/) to invoke messages:

```python
In [1]: from aini import aini, aview

In [2]: ds = aini('lang/llm:ds')
In [3]: ds.invole('hi').pretty_print()
======================== Ai Message ========================

Hello! 😊 How can I assist you today?
```

Idea validator example from [Agno](https://docs.agno.com/examples/workflows/startup-idea-validator):

```python
In [4]: from lang_book.idea_validator import gen_report

In [5]: report = gen_report(idea='A new social media platform for pet owners.')
In [6]: report[-1].pretty_print()
======================== Ai Message ========================

### **Startup Report: A Social Media Platform for Pet Owners**

---

#### **1. Executive Summary**
The startup proposes a dedicated social media platform exclusively
for pet owners, addressing gaps in existing platforms like Facebook,
Instagram, and Reddit. By combining pet-centric features, localized
communities, and expert resources, the platform aims to become the
go-to hub for pet lovers worldwide.

...
```

### [Autogen](https://github.com/microsoft/autogen)

Use [`DeepSeek`](https://platform.deepseek.com/) as the model for the assistant agent.

```python
# Load assistant agent with DeepSeek as its model - requires DEEPSEEK_API_KEY
In [7]: client = aini('autogen/client', model=aini('autogen/llm:ds'))
In [8]: agent = aini('autogen/assistant', name='deepseek', model_client=client)

# Run the agent
In [9]: ans = await agent.run(task='What is your name')

# Display result structure
In [10]: aview(ans)
Out [10]:
<autogen_agentchat.base._task.TaskResult>
{
  'messages': [
    {'source': 'user', 'content': 'What is your name', 'type': 'TextMessage'},
    {
      'source': 'deepseek',
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
In [11]: aview(agent._model_context, inc_=True, max_depth=5)
Out [11]:
<autogen_core.model_context._unbounded_chat_completion_context.UnboundedChatCompletionContext>
{
  '_messages': [
    {'content': 'What is your name', 'source': 'user', 'type': 'UserMessage'},
    {
      'content': 'My name is DeepSeek Chat! 😊 How can I assist you today?',
      'source': 'deepseek',
      'type': 'AssistantMessage'
    }
  ]
}
```

### [Agno](https://github.com/agno-agi/agno)

```python
# Load an agent with tools from configuration files
In [12]: agent = aini('agno/agent', tools=[aini('agno/tools:google')])

# Run the agent
In [13]: ans = agent.run('Compare MCP and A2A')

# Display component structure with filtering
In [14]: aview(ans, exc_keys=['metrics'])
Out [14]:
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
In [15]: aview(ans, to_file='debug/output.yaml')
```

### [Mem0](https://mem0.ai/)

```python
In [16]: memory = aini('mem0/memory:mem0')
```

## Configuration File Format

`aini` uses YAML or JSON configuration files to define class instantiation. Here's how they work:

### Basic Structure

```yaml
# Optional defaults section for fallback values
defaults:
  api_key: "default-key-value"
  temperature: 0.7

# Component definition
assistant:
  class: autogen_agentchat.agents.AssistantAgent
  params:
    name: ${name}
    model_client: ${model_client|client}
    tools: ${tools}

# Nested components
mem0:
  class: mem0.Memory
  init: from_config
  params:
    config_dict:
      history_db_path: ${history_db_path}
      graph_store:
        provider: neo4j
        config:
          url: bolt://localhost:7687
          username: ${neo4j_user}
          password: ${neo4j_pass}
```

### Variable Substitution

`aini` supports variable substitution with the `${var}` syntax:

```yaml
model_config:
  class: "openai.OpenAI"
  params:
    api_key: ${OPENAI_API_KEY}  # Uses environment variable
    model: ${model|'gpt-4'}     # Uses input parameter or default 'gpt-4'
    temperature: ${temp|0.7}    # Uses input parameter or default 0.7
```

### Variable resolution priority:

1. Input variables (passed as kwargs to `aini()`)
2. Environment variables
3. Default variables from the `defaults` section
4. Fallback values after the pipe `|` character

### Custom Initialization Methods

By default, `aini` uses the class constructor (`__init__`), but you can specify custom initialization methods:

```yaml
model_client:
  class: autogen_core.models.ChatCompletionClient
  init: load_component
  params:
    model: ${model}
    expected: ${expected}
```

## Advanced Features

### Raw Configuration Access

Use the `araw` parameter to get the resolved configuration without building objects:

```python
# Get raw configuration with variables resolved
In [17]: config = aini('openai/model_config', araw=True)

# Get specific component configuration
In [18]: model_config = aini('openai/model_config', akey='gpt4', araw=True)
```
