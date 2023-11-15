import os
from time import time

from langchain.chat_models import ChatOpenAI

# Create memory 
from langchain.memory.chat_message_histories import DynamoDBChatMessageHistory
from langchain.memory import ConversationBufferMemory

from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage

from langchain.prompts import MessagesPlaceholder

from langchain.agents import AgentExecutor

def load_txt(filename, filepath, encoding='utf-8'):
    """
    Load a text file as a string using the specified file path copied from Windows file explorer.
    Backslashes in the file path will be converted to forward slashes.

    Arguments:
    - filepath (raw string): Use the format r'<path>'.
    - filename (string).

    Returns: string object.
    """
    filename = f'{filepath}/'.replace('\\','/') + filename
    with open(filename, 'r', encoding=encoding) as file:
        text = file.read()
    return text

def create_system_message(
        business_name, business_dict, prompts_filepath='../prompts',
        examples_filepath='../data/chat_examples', doc_filepath='../data/rag_docs'
        ):
    instructions = load_txt(business_dict[business_name][0], prompts_filepath)
    examples = load_txt(business_dict[business_name][1], examples_filepath)
    document = load_txt(business_dict[business_name][2], doc_filepath)

    system_message = f"""{instructions}

    **Examples**

    {examples}

    **Relevant documentation**

    {document}

    """

    prompt = """
    Write the next OutboundMessage based on the following InboundMessage, 
    which is delimited by triple backticks: ```{InboundMessage}```
    """
    system_message = f'{system_message}{prompt}'
    return system_message

def create_chatbot(contactId, system_message, tools, model="gpt-3.5-turbo-16k", verbose=True):

    llm = ChatOpenAI(
        temperature = 0,
        openai_organization=os.environ['openai_organization'],
        openai_api_key=os.environ['openai_api_key'],
        model=model
        )
    message_history = DynamoDBChatMessageHistory(
        table_name="SessionTable", session_id=contactId,
        key={
            "PK": "SessionId",
            "SK": "type",
            }
        )
    memory = ConversationBufferMemory(
        memory_key="ChatHistory", chat_memory=message_history, return_messages=True, 
        input_key='input', output_key="output" # Required to avoid `ValueError: One output key expected, got dict_keys(['output', 'intermediate_steps'])`; https://github.com/langchain-ai/langchain/issues/2068
    )
    system_message = SystemMessage(
        content=(system_message),
        input_variables=['InboundMessage']
    )
    
    prompt = OpenAIFunctionsAgent.create_prompt(
        system_message=system_message,
        extra_prompt_messages=[
            MessagesPlaceholder(variable_name='chat_history')
            ]
    )

    agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, memory=memory, verbose=verbose, return_intermediate_steps=True
        )
    agent_info = {
        'agent': agent,
        'agent_executor': agent_executor,
        'chat_history': message_history.messages
    }
    return agent_info

def chat_with_chatbot(user_input, agent_info):
    start_time = time()
    print(f'Chat history length: {len(agent_info["chat_history"])}')
    chat_history = agent_info['chat_history']
    result = agent_info['agent_executor']({
        "input": user_input,
        "chat_history": chat_history
        })
    print(f'Response time: {time() - start_time} seconds')
    
    return result

def fake_func(inp: str) -> str:
    return "foo"
