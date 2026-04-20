# Copy this file to .env and fill in your values
# Never commit .env to version control

# Required: Get from https://console.anthropic.com
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Tune fuzzy match sensitivity for CGHS procedure lookup (0.0 to 1.0)
# Lower = more matches but more false positives, Higher = fewer but more precise
CGHS_CONFIDENCE_THRESHOLD=0.6

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
