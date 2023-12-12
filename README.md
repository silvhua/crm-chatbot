# Go High Level SMS Chatbot
## Objectives
The objective of this project is to leverage generative AI and automations to reduce how much time the staff spend on communicating with leads via text message.

This project integrates a large language model with Go High Level, a CRM software, to auto-generate responses to inbound text messages to a small business. 

The project is currently being deployed for private use by a small fitness business.

## Methods
When a contact sends a message to the business, the application generates a response message using Open AI's Chat Completion endpoint, then creates a task on Go High Level that includes:
1. the AI-generated response message. 
2. the corresponding contact ID.

A staff member can then review the task and send the response to the contact, making modifications as needed. Keeping the "human in the loop" ensures AI safety.

## Evaluation
AI-generated responses will be compared with the staff members' responses to evaluate the quality of the application. 

### Tech Stack
* Amazon Web Services: API Gateway, S3, DynamoDB, Lambda, CloudWatch, Serverless Application Model (SAM)
* Go High Level and Go High Level API
* Python
* LangChain
* OpenAI
* VS Code

## Future Directions
Once the application reliably produces quality results, it will be scaled for commercial use, primarily for small fitness businesses.