#!/bin/bash
# Manually trigger the daily newsletter generation Lambda
# Usage: ./trigger-newsletter.sh [date]
# Example: ./trigger-newsletter.sh 2026-03-07

FUNCTION_NAME="dev-cdmx-traffic-generate-newsletter"
REGION="us-east-1"

# Get date parameter or use today's date
if [ -z "$1" ]; then
  DATE=$(date +%Y-%m-%d)
else
  DATE="$1"
fi

echo "Triggering newsletter generation for date: $DATE"
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --payload "{\"date\": \"$DATE\"}" \
  --cli-binary-format raw-in-base64-out \
  response.json

echo ""
echo "Response:"
cat response.json
echo ""
echo ""
echo "Done! Check CloudWatch logs for details."
