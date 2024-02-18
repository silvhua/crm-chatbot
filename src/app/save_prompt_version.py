import sys
sys.path.append(r"/home/silvhua/custom_python")
sys.path.append(r'/home/silvhua/repositories/GHL-chat/src/')

from  chat_functions import load_txt, create_system_message
from silvhua import save_text
    
def process_leads_csv(csv_filename, csv_path):
    df = load_csv(csv_filename, csv_path)
    # Update the index to start at 2 instead of zero
    df.index = df.index + 2
    print(f'Index updated to start at 2 isntead of 0.')
    return df

if __name__ == "__main__":
    print('Saving prompt version...')
    system_message_dict = dict()
    conversation_id = 1
    system_message_dict[conversation_id] = create_system_message(
        'CoachMcloone'
    )
    print(f'**System_message**: {system_message_dict[conversation_id]}')
    save_text(
        system_message_dict[conversation_id], 
        filename='full_prompt', path='/home/silvhua/repositories/GHL-chat/private/prompts',
        append_version=True
        )