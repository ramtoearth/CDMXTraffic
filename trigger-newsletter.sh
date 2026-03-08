#!/bin/bash
# Manually trigger the daily newsletter generation Lambda

FUNCTION_NAME="dev-cdmx-traffic-generate-newsletter"
REGION="us-east-1"

echo "Triggering newsletter generation..."
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json

echo ""
echo "Response:"
cat response.json
echo ""
echo ""
echo "Done! Check CloudWatch logs for details."
