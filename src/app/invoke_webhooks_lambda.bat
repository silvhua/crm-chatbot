source activate-ghl.sh
sam local invoke WebhooksLambda --event events/OutboundMessageTest.json
sam local invoke WebhooksLambda --event events/ContactTagUpdateTest.json
sam local invoke WebhooksLambda --event events/InboundMessageTest.json
sam local invoke WebhooksLambda --event events/InboundMessage.json
sam local invoke WebhooksLambda --event events/InboundMessageTest.json --force-image-build
sam local invoke WebhooksLambda --event events/EmailOutboundMessage.json


sam local invoke ReplyLambda --event events/InboundMessageTest.json
sam local invoke ReplyLambda --event events/InboundMessageTest.json --force-image-build
sam local invoke ReplyLambda --event events/InboundMessageFromLambda.json
sam local invoke ReplyLambda --event events/InboundMessageFromLambda.json --force-image-build


sam local invoke FollowupLambda --event events/followupWorkflowWebhook.json

@REM sam local invoke WebhooksLambda --event events/CustomInboundMessage.json
@REM sam local invoke WebhooksLambda --event events/CustomInboundMessageTest.json
@REM sam local invoke WebhooksLambda --event events/CustomInboundMessage.json