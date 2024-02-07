import sys
sys.path.append(r"/home/silvhua/custom_python")
sys.path.append(r'/home/silvhua/repositories/GHL-chat/src/')

from  chat_functions import load_txt, create_system_message
from silvhua import save_text

if __name__ == "__main__":
    print('Saving prompt version...')
    system_message_dict = dict()
    conversation_id = 1
    system_message_dict[conversation_id] = create_system_message(
        'CoachMcloone', 
        prompts_filepath='app/private/prompts',
        examples_filepath='app/private/data/chat_examples', doc_filepath='app/private/data/rag_docs'
    )
    print(f'**System_message**: {system_message_dict[conversation_id]}')
    save_text(
        system_message_dict[conversation_id], 
        filename='full_prompt', path='/home/silvhua/repositories/GHL-chat/private/prompts',
        append_version=True
        )