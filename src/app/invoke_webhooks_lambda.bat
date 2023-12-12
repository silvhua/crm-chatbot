sam local invoke WebhooksLambda --event events/OutboundMessageTest.json
sam local invoke WebhooksLambda --event events/ContactTagUpdateTest.json
sam local invoke WebhooksLambda --event events/InboundMessageTest.json
sam local invoke WebhooksLambda --event events/InboundMessageTest.json --force-image-build