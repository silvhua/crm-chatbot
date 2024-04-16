from openai import OpenAI
import boto3
import os
from time import time
import re

from langchain_community.chat_models import ChatOpenAI
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory

from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage

from langchain.prompts import MessagesPlaceholder

from langchain.agents import AgentExecutor

from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
try:
    from dotenv import load_dotenv
    load_dotenv()
    cloud = False
except:
    cloud = True

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

class Chatbot_Response(BaseModel):
    response: str = Field(description="The response to the InboundMessage.")
    alert_human: bool = Field(description="Whether or not to alert a human to review the response.")
    phone_number: str = Field(description="The phone number of the contact.")
    tag: str = Field(description="A tag to add to the contact profile.")

def create_system_message(
        business_name, 
        prompts_filepath='/home/silvhua/repositories/GHL-chat/src/app/private/prompts',
        examples_filepath='/home/silvhua/repositories/GHL-chat/src/app/private/data/chat_examples', 
        doc_filepath='/home/silvhua/repositories/GHL-chat/src/app/private/data/rag_docs'
        ):
    instructions_filename = f'{business_name}.md'
    examples_filename = f'{business_name}.txt'
    document_filename = f'{business_name}_doc.md'
    try:
        instructions = load_txt(instructions_filename, prompts_filepath)
        examples = load_txt(examples_filename, examples_filepath)
        document = load_txt(document_filename, doc_filepath)
        base_system_message = load_txt('base_system_message.md', prompts_filepath)
    except Exception as error:
        if cloud == True:
            print(f'[ERROR] {error}')
            print('Loading prompt files from s3...')
        s3 = boto3.client('s3')
        instructions = s3.get_object(
            Bucket='ownitfit-silvhua', Key=instructions_filename
            )['Body'].read().decode('utf-8')
        examples = s3.get_object(
            Bucket='ownitfit-silvhua', Key=examples_filename
            )['Body'].read().decode('utf-8')
        document = s3.get_object(
            Bucket='ownitfit-silvhua', Key=document_filename
            )['Body'].read().decode('utf-8')
        base_system_message = s3.get_object(
            Bucket='ownitfit-silvhua', Key='base_system_message.md'
            )['Body'].read().decode('utf-8')
    # print(f'**Instructions component of system message**: \n{instructions}\n')

    system_message = f"""
# Context

{instructions}

## Relevant documentation

{document}

{base_system_message}

{examples}
    """

    prompt = """
# Task

Write the next OutboundMessage based on the following InboundMessage, 
which is delimited by triple backticks: ```{InboundMessage}```
    """
    system_message = f'{system_message}{prompt}'
    ###
    # print(f'\n**System_message**: {system_message}\n\n')
    return system_message

def create_chatbot(contactId, system_message, tools, model="gpt-3.5-turbo-1106", verbose=True):

    llm = ChatOpenAI(
        temperature = 0,
        openai_organization=os.environ['openai_organization'],
        openai_api_key=os.environ['openai_api_key'],
        model=model, 
        model_kwargs={"response_format": {"type": "json_object"}} # https://platform.openai.com/docs/guides/text-generation/json-mode  # https://api.python.langchain.com/en/latest/chat_models/langchain_community.chat_models.openai.ChatOpenAI.html?highlight=chatopenai#
        )
    message_history = DynamoDBChatMessageHistory(
        table_name="SessionTable", session_id=contactId,
        key={
            "SessionId": contactId,
            "type": 'ChatHistory',
            }
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

    parser = SimpleJsonOutputParser(pydantic_object=Chatbot_Response)
    agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor( # Example of creating a custom agent: https://python.langchain.com/docs/modules/agents/how_to/custom_agent
        agent=agent, tools=tools, 
        verbose=verbose, return_intermediate_steps=True,
        parser=parser  # Add the parser instance to the agent_executor
        )
    agent_info = {
        'agent': agent,
        'agent_executor': agent_executor,
        'chat_history': message_history
    }
    return agent_info

def chat_with_chatbot(user_input, agent_info):
    start_time = time()
    chat_history = agent_info['chat_history'].messages
    print(f'Chat history length: {len(chat_history)}')
    print(f'\nChat history:')
    for item in chat_history:
        print(f'**{item.type.upper()}**: {item.content}')
    last_message = chat_history[-1].content
    manychat_outbound_message_substrings = [
        "I'll be in touch as soon as I'm online next!",
        "I'll give you a personal message here shortly."
    ]
    previous_message_type = chat_history[-2].type if len(chat_history) > 1 else None
    last_message_type = chat_history[-1].type
    if (last_message == user_input): ## Check that the current user_input is the most recent message      
        generate_response = True 
        # If the last message is also Inbound, then join all inbound messages together and delete them from chat history
        if previous_message_type == 'human': 
            last_inbound_messages_list = []
            for item in reversed(chat_history):
                if item.type.lower() == 'human':
                    last_inbound_messages_list.append(item.content)
                    truncated_history = chat_history[:-1]
                else:
                    break
            last_inbound_messages = '\n\n'.join(reversed(last_inbound_messages_list))
            user_input = last_inbound_messages
            print(f'Joining previous messages as full user input: {user_input}')
            chat_history = truncated_history
        else:
            chat_history = chat_history[:-1]
    elif (last_message_type != 'human') & (any(substring in last_message for substring in manychat_outbound_message_substrings)):
        generate_response = True
    else:        
        generate_response = False
    if generate_response == True:
        result = agent_info['agent_executor'].invoke({
                "input": user_input,
                "chat_history": chat_history
            })  
        print(f'Agent response time: {time() - start_time} seconds')
    else:
        result = dict()
        result['output'] = '{"response": "Abort Lambda function", "alert_human": false}'
    return result
    
def placeholder_function(str):
    return ''

def openai_models(env="openai_api_key", organization_key='openai_organization', query='gpt'):
    """
    List the availabel OpenAI models.
    Parameters:
        - env (str): Name of environmental variable storing the OpenAI API key.
        - query (str): Search term for filtering models.
    """
    client = OpenAI(
        api_key=os.environ[env],
        organization=os.environ[organization_key]
    )
    # openai.api_key = os.getenv(env)
    response = client.models.list()
    filtered_models = [model for model in response.data if model.id.find(query) != -1]

    for item in filtered_models:
        print(item.id)
    return filtered_models

def create_paragraphs(input_string):
    """
    Add 2 new lines every 2 sentences. Keep emojis at the end of the previous sentence. 
    Treat emojis as the end of the sentence if stand-alone.
    """
    urls = re.findall(r'http[s]?://\S+', input_string)
    for url in urls:
        input_string = input_string.replace(url, f'URL_{urls.index(url)}.')
    sentences = re.split(r'(?<=[a-zA-Z0-9][.!?]|\s[\u263a-\U0001F917])\s*', input_string)

    result = ""
    for i, sentence in enumerate(sentences):
        # print(f'sentence {i}: {sentence} ({len(sentence)})')
        if (len(sentence) == 1) & (i != 0) & (i+1 != len(sentences)): # emojis
            result += "\n\n"
        elif ((i + 1) % 2 == 0) & (i + 1 != len(sentences)): # odd-number index
            result += f'{sentence} '
            if (i + 1 != len(sentences)) & (len(sentences[i+1]) == 1):
                result += f'{sentences[i+1]}'
            else:                
                result += "\n\n"
        elif i + 1 != len(sentences): # even-number index
            result += f'{sentence} '
            if (len(sentences[i+1]) == 1):
                result += f' {sentences[i+1]} '
    if len(urls) > 0:
        for index, url in enumerate(urls):
            # result = result.replace(f'___URL_{index}___', url)
            result = result.replace(f'URL_{index}.', url)
    return result.strip()