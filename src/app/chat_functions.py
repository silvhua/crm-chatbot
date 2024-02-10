from openai import OpenAI
import boto3
import os
from time import time

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
    except Exception as error:
        if cloud == True:
            print(f'Error: {error}')
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
    # print(f'**Instructions component of system message**: \n{instructions}\n')

    system_message = f"""{instructions}

## Other Messages

Only repond to inbound messages that can be answered by the message templates or provided 
documenation. Otherwise, return "[ALERT HUMAN]". 
If the message indicates the contact has an eating disorder, suicidal ideation, or other serious mental health 
conditions, return "[ALERT HUMAN]". 
The "[ALERT HUMAN]" message will trigger a human staff member to review the messages to write a response. 
It is better to err on the side of caution and flag a staff rather than give a wrong response.
    
# Stage 1

Determine if you should generate a response to the inbound message. If so, generate the response and proceed 
to Stage 2. Otherwise, return "[ALERT HUMAN]".

Return your response on a JSON format with the following keys:
- "response" (string): The response to the InboundMessage, if applicable. If a human is to be alerted, the value will be [ALERT HUMAN]
- "alert_human" (True or False): Whether or not to alert a human to review the response.
- "phone_number" (string or None): The phone number of the contact, if available.

## Examples

Below are example conversations with leads. Each lead as a unique contact ID.
An InboundMessage is from the lead. An OutboundMessage is from you.

{examples}

## Relevant documentation

{document}

# Stage 2

Review your response from stage 1. 
Revise your response if needed to make sure you followed the instructions.
Revise your response if needed to avoid asking questions that have already been answered in previous messages.
Make sure that if the question cannot be answered through the message templates or documentation, 
you return "[ALERT HUMAN]".

# Stage 3

Review your response from stage 2 to revise as needed to make it concise.
    """

    prompt = """
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

def placeholder_function(str):
    return None

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