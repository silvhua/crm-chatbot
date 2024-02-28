source activate-ghl.sh
sam local invoke WebhooksLambda --event src/events/OutboundMessageTest.json
sam local invoke WebhooksLambda --event src/events/ContactTagUpdateTest.json
sam local invoke WebhooksLambda --event src/events/InboundMessageTest.json
sam local invoke WebhooksLambda --event src/events/InboundMessage.json
sam local invoke WebhooksLambda --event src/events/InboundMessageTest.json --force-image-build
sam local invoke WebhooksLambda --event src/events/EmailOutboundMessage.json


sam local invoke ReplyLambda --event src/events/InboundMessage.json
sam local invoke ReplyLambda --event src/events/InboundMessageTest.json
sam local invoke ReplyLambda --event src/events/InboundMessageTest.json --force-image-build
@REM sam local invoke ReplyLambda --event events/InboundMessageFromLambda.json
@REM sam local invoke ReplyLambda --event events/InboundMessageFromLambda.json --force-image-build


sam local invoke FollowupLambda --event src/events/followupWorkflowWebhook.json

@REM sam local invoke WebhooksLambda --event events/CustomInboundMessage.json
@REM sam local invoke WebhooksLambda --event events/CustomInboundMessageTest.json
@REM sam local invoke WebhooksLambda --event events/CustomInboundMessage.json