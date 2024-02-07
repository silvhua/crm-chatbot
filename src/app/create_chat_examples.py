import os
import re
import sys
sys.path.append(r"/home/silvhua/custom_python")
from silvhua import save_text

# From 2024-01-02 notebook

def load_conversation(contact_id, filepath='/home/silvhua/repositories/GHL-chat/data/chat_examples/Coach_Mcloone/alert'):
    
    filename = f'{filepath}/'.replace('\\','/') + f'{contact_id}.txt'
    with open(filename, 'r', encoding='utf-8') as file:
        text = file.read()
    return text

def annotate_conversation(contact_id, filepath):
    text = load_conversation(contact_id, filepath)
    text = f'Contact ID {contact_id}:\n\t' + re.sub(r'\n', r'\n\t', text)
    text = re.sub(r'\d\d:\d\d\n\t\?', 'OutboundMessage:', text)
    text = re.sub(r'\d\d:\d\d\n+', 'InboundMessage:', text)
    return text

def create_chat_examples(directory='/home/silvhua/repositories/GHL-chat/data/chat_examples/Coach_Mcloone/alert'):
    """
    Iterate through all .txt files in a directory to create a list of the 
    results of the annotate_conversation function. Each result is appended 
    to the list.
    Join the elements of the list, separated by newlines, to create a long string.
    """

    chat_examples = []
    filenames = sorted(os.listdir(directory))
    for filename in filenames:
        if filename.endswith('.txt'):
            contact_id = filename.split('.')[0]
            text = annotate_conversation(contact_id=contact_id, filepath=directory)
            chat_examples.append(text)
    result = ''.join([f"{example}\n\n" for example in chat_examples])
    return result
    
if __name__ == '__main__':
    text_string = create_chat_examples()
    save_text(
        text_string, 'CoachMcloone', path='../data/chat_examples',append_version=True
        )
