# Go High Level SMS Chatbot
## Objectives
The objective of this project is to leverage generative AI and automations to reduce how much time the staff spend on communicating with leads via text message.

This project integrates a large language model with Go High Level, a CRM software, to auto-generate responses to inbound text messages to a small business. 

The project is currently being deployed for private use by a small fitness business.

# Methods
## Architecture

This app consists of two AWS Lambda functions:
- `WebhooksLambda`: Defined in `ghl_chat_history_lambda.py`. This receives webhooks and handles the data appropriately.
- `ReplyLambda`: Defined in `ghl_reply_lambda.py`. This receives data from the `WebhooksLambda` to generate a response to inbound messages.

## Tech Stack
* Amazon Web Services: API Gateway, S3, DynamoDB, Lambda, CloudWatch, Serverless Application Model (SAM)
* Go High Level and Go High Level API
* Python
* LangChain
* OpenAI
* VS Code

# Release History

Version | Description | Date | Commit
--- | ---- | --- | ---
1.0.0 | Automatically send messages | 2024-02-09 10:10 | dbc881337e118ed6fa7bfee9446baf78b31961ae
1.0.1 | wait 30-115 sec before sending response | 2024-02-09 | abce71b51c46f262862c5c774a7fe109e02f8c80
1.1.0 | `WebhooksLambda`: If tags_to_ignore present, create task to trigger `chatbot alerting staff` workflow | 2024-02-10 | 1950d69ad7774547265e75331535b233d318acbd
1.1.1 | `ReplyLambda`: Add `no chatbot` tag if task created due to chatbot generating human alert task. | 2024-02-10 01:21 | 4970c8c8a6dd8f41a6f4f1b7fc6aa955ecf3f75e
1.1.2 | Updated the prompt to avoid chatbot asking twice about desired results. | 2024-02-10 09:11 | uploaded prompt file to S3
1.1.2 | Updated the system_message | 2024-02-10 13:51 | 5b840cdef0c8a27913631c48fb640123211491ab
1.1.3 | Updated the system_message and prompt. Avoid creating tasks if I am testing the chatbot. | 2024-02-10 16:47 | 57933487c59d8ac769e241cef329e2be2c83bd8d
1.1.4 | If contact does not reply to the ManyChat message asking for height and weight, they will be put into this a GHL workflow which sends a follow up Facebook message. If they still don’t respond after 5 minutes, an email notification will be sent via the other workflow ("chatbot alerting staff”). | 2024-02-10 19:05 | n/a
1.1.5 | Commented out lines that tag contact; use ghl workflow instead | 2024-02-11 11:12 | e3456f67330db7e360553d3db9f7e41784fc20d8
1.1.6 | Prompt update: Remove new line characters between lines in first message of script. | 2024-02-11 12:12 | 
1.1.7 | Print chat history in Reply Lambda | 2024-02-11 12:53
1.1.8 | Updated prompt template to avoid redundant responses. Update step 1 of business-specific script. | 2024-02-11 23:11 | 79e614b4295443f882ec2de87ae8c4a45fbc1a1d
1.1.9 | Removed waiting period if InboundMessage is sent by me. | 2024-02-11 23:30 | 824587766e6d9c4bf71f178bea148eab544d18d9
1.1.10 | Update step 4 of business-specific script to avoid redundancy. Updated print statements. | 2024-02-11 11:59 | 3c390090494110f61e0f9ada2c2df2119f6f86c4
1.1.11 | Add messages to chat history with using `sam local invoke ReplyLambda` | 2024-02-12 00:33 | c69ed7de213e02f6d03f847053911b9e9f7d1b95
1.1.12 | No GHL requests if running with `"noReply": "1"` in payload body | 2024-02-12 00:55 |
1.1.13 | Updated prompt by adding a newline character in 2nd message template of step 1. | 2024-02-12 07:55 
1.1.14 | Ignore an additional message that is handled by ManyChat. Turned off the Manychat workflow that adds the `chatgpt` tag. | 2024-02-12 15:21 | 
1.1.15 | Modified the a chat example so it would not get used in a response. | 2024-02-12 15:34 |
1.1.16 | Add AI OutboundMessage to ChatHistory when testing locally | 2024-02-12 16:15 
1.1.17 | Added AI OutboundMessage to ChatHistory when testing locally | 2024-02-12 16:15 
1.1.18 | Updated step 2 of business-specific script | 2024-02-12 16:24
1.1.19 | If response is multiple JSON strings concatenated together, take the first valid JSON instead of the last | 2024-02-12 16:31
1.1.20 | Account for another string in payload indicating a mass email. | 2024-02-12 21:37
1.2.0 | Check for back to back messages. Abort ReplyLambda if payload InboundMessage != latest message in chat history. | 2024-02-12 16:45 | c5a4ad61a0274f36d2a0dcd343cdb953a76916ea
1.2.1 | Update ManyChat and GHL workflows to follow up with leads who don't complete ManyChat workflow | 2024-02-13 23:06
1.2.2 | Account for case if chatbot response does not include a `phone_number` key. Corrected print statement. | 2024-02-13 23:44
1.2.3 | Chatbot generates response even if last message in chat history if outbound, as long as contains the specified substring. | 2024-02-14 11:45
1.3.0 | Updated business-specific prompt and RAG doc. | 2024-02-15 12:21 |
1.3.1 | Updated data_functions/parse_json_string function to handle Pythonic JSON strings which cause JSON decode error | 2024-02-15 12:50e
1.3.2 | Updated business-specific prompt and RAG doc. | 2024-02-15 13:23
1.3.3 | Updated stages 1+2 of system_message template; `placeholder_function`: no args; updated description. Updated business-specific prompt. | 2024-02-15 14:37
1.3.4 | Added back the parameter to `placeholder` function as it caused problems with response generation. | 2024-02-15 14:51 
1.3.5 | Updated message template of step 2a of business-specific prompt. | 2024-02-16 11:38 
1.3.6 | Updated message template to question about cost. | 2024-02-17 22:04
1.4.0 | Updated `ghl_chat_history_lambda` to read the ManyChat tags so those who complete ManyChat worfklow are handled by the chatbot | 2024-02-17 22:45
1.4.1 | Updated `ghl_chat_history_lambda` to add contact to the GHL follow up workflow if InboundMessage is from the ManyChat workflow GUI. GHL follow up workflow will send follow up message if no response after 5 minutes. | 2024-02-18 00:38
1.4.2 | Updated business-specific message templates. Last 2 steps had duplicated number (6) and were missing end quote. | 2024-02-18 23:40
1.4.3 | Removed newline character in Step 4 message template. Turned steps 6-7 message templates to JSON format with `"alert_human": true`. | 2024-02-19 00:47
1.4.4 | `chat_with_chatbot`: Account for Dynamodb ChatHistory record not saving messages in the right sequence. Add missing quotation in step 7 message template. | 2024-02-19 15:22
1.4.5 | Split mult-sentence essages into paragraphs | 2024-02-19 16:41
1.4.6 | Account for URLs in outbound message when splitting into paragraphs. | 2024-02-19 18:06
1.4.7 | Send long responses multiple messages. | 2024-02-19 21:23
1.4.8 | Alert human if AI-generated response matches previous OutboundMessage. | 2024-02-19 22:46
1.4.9 | Fixed `alert_human` value in business-specific prompt. | 2024-02-19 23:21
1.4.10 | Webhooks Lambda: Moved `tags_to_ignore` definition to outside try/except block so it exists even if GHL and ManyChat requests fail. | 2024-02-20 16:27
1.4.11 | Webhooks Lambda: If contact has no tags in GHL or ManyChat, create a task to notify staff. | 2024-02-20 16:27
1.4.12 | Webhooks Lambda: Add GHL tags to trigger GHL follow up workflow if message in `messages_to_ignore` | 2024-02-20 22:31
1.4.13 | Webhooks Lambda: Add `chatgpt` tag if InboundMessage is "get started" (case-insensitive). | 2024-02-21 00:14
1.4.14 | Webhooks Lambda: Commented out the steps that look up ManyChat tags. | 2024-02-21 01:08
1.4.15 | Reply Lambda: Do not generate reply if contact tags that trigger GHL follow up workflow are present. | 2024-02-21 09:52
1.4.16 | Cancel out last commit | 2024-02-21 10:46
1.4.17 | Webhooks Lambda: Remove contact from GHL follow up workflow if "no height and weight" tag is present. | 2024-02-21 11:56
1.4.18 | Webhooks Lambda: Remove `no height and weight` tag when inbound message is received. | 2024-02-21 12:40
1.5.0 | Update of stage 1 system message template. Removed newline characters in message templates in business-specific prompt. | 2024-02-21 2024-02-21 12:56
1.5.1 | Updated business-specific prompt step 6. Moved FAQ to RAG doc. | 2024-02-21 22:18
1.5.2 | Check for duplicate response in the body of the Reply Lambda after AI-generated response has been parsed to dictionary, allowing extracted phone number to be retained. | 2024-02-21 23:49
1.5.2 | Updated business-specific prompt and RAG doc. | 2024-02-22 10:58
1.5.3 | Updated RAG doc. | 2024-02-22 14:03
1.5.6 | Reply Lambda: Remove punctuation and emojis when comparing if AI-generated response is contained in a past message. Updated system message template step 3. | 2024-02-22 2024-02-22 14:28
1.5.7 | Update of stage 1 system message template. Comment out print statements. | 2024-02-22 17:05 
1.5.8 | Update of stage 2 system message template. | 2024-02-22 17:16
1.5.9 | Update business-specific prompt step 7. | 2024-02-23 13:06 
1.5.10 | Convert incorrectly-formated Irish phone number to international format if Irish phone number is extracted from inbound message. | 2024-02-23 14:17
1.5.11 | If contact has previously entered the ManyChat funnel, skip the chatbot workflow, add tags, and create a task to notify staff. | 2024-02-23 
1.5.12 | Update business-specific prompt: Combined steps 4-5. | 2024-02-24 01:54
1.5.13 | Alert human if placeholders in message templates haven't been replaced in the AI response. | 2024-02-24 02:38
1.5.14 | Add contact name when creating GHL task. Update step 4 of business-specific prompt. | 2024-02-24 22:02
1.5.15 | Re-attempt GHL sendMessage and createTask requests up to 3 times if it fails. | 2024-02-24 23:02
1.5.16 | Use `.get()` instead of indexing for `ghl_request` response object. | 2024-02-25 11:18
1.5.17 | Only compare generated message to past messages if not None | 2024-02-25 11:34
1.5.19 | Webhooks Lambda: Allow function to run even if `refresh_token` fails. `chat_with_chatbot`: `add_to_chat_history`: get attachments if body is empty. | 2024-02-25 12:53
1.5.20 | Webhooks Lambda: If inbound/outbound message has no text, make the payload body the attachment URLs as string . | 2024-02-25 13:06
Add `[ERROR] ` to error print statements for cloudwatch SNS alerts.
1.5.21 | Bug fix to Reply Lambda: `ghl_api_response.get('status_code', None)` -> `ghl_api_response.get('status_code', 500)` | 2024-02-26 15:31
1.5.22 | `parse_json_string`: Update print statements to remove `ERROR` | 2024-02-26 20:39
1.5.23 | Webhooks Lambda: Prevent duplicate intro outbound messages (both GHL Workflow and ChatGPT) in case contact responds to ManyChat multiple-choice question more than once. | 2024-02-27 00:30
1.5.24 | In case contact responds to ManyChat multiple-choice question more than once after already completing the ManyChat workflow, add the tag 'no chatbot' to avoid unexpected chatbot responses. | 2024-02-27 00:51
1.6.0 | Show outbound messages as being sent from chatbot's GHL staff account. | 2024-02-27 10:03
1.6.1 | Process the opt-in InboundMessage even if contact is not yet in the database. This accounts for slight delay in the webhook for ContactCreate and InboundMessage. | 2024-02-27 14:23
1.6.2 | Made parent repository private. Created git subtree. | 2024-02-28 15:49
1.6.3 | Avoid adding ['re-entered ManyChat funnel', 'no chatbot'] tags if last inbound message was also a ManyChat opt-in message. Print event JSON for easier troubleshotting of duplicate triggers. | 2024-02-29 23:34 
1.6.4 | To avoid sending duplicate outbound messages, split past outbound messages into sentences to see if it is contained in the AI-generated response. Added [license file](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.txt)