from openai import AzureOpenAI

# Azure OpenAI Configuration
AZURE_ENDPOINT = "https://365tune-open-ai.openai.azure.com/"
MODEL_NAME = "gpt-4o-mini-2024-07-18-ft-6948d064ebb7406ca4477f051eea39c1"
DEPLOYMENT = "gpt-4o-mini-2024-07-18-ft-6948d064ebb7406ca4477f051eea39c1"
SUBSCRIPTION_KEY = "Bqn1HNJdNQcyJC1vFJcFlT1s2hA4kBB4GaJMkIkbBrQ5b3qW7AL4JQQJ99BHACYeBjFXJ3w3AAABACOGa8Hk"
API_VERSION = "2025-01-01-preview"

# SQL Server Configuration
SQL_SERVER = 'liclensdbsrv.database.windows.net'
SQL_DATABASE = 'LicLensDev'
SQL_USERNAME = 'liclensadmin'
SQL_PASSWORD = 'jpO8m&$&3oq@dn'

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_version=API_VERSION,
    azure_endpoint=AZURE_ENDPOINT,
    api_key=SUBSCRIPTION_KEY,
)

def ask_o4_mini(question, max_tokens=2000):
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": question,
                }
            ],
            max_completion_tokens=max_tokens,
            timeout=15,  # Reduced from 60 to 15 seconds for faster failure
            model=DEPLOYMENT
        )

        # Check if response exists and has content
        if not response or not response.choices:
            raise Exception("API returned no choices")

        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            print(f"[Azure OpenAI] Model: {DEPLOYMENT[:30]}...")
            print(f"[Token Usage] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}")
            print(f"[Response] Status: {finish_reason} | Length: {len(content) if content else 0} chars")
        else:
            print(f"API finish_reason: {finish_reason}, content length: {len(content) if content else 0}")

        if content is None or len(content) == 0:
            raise Exception(f"API returned empty content (finish_reason: {finish_reason})")

        # Clean content of any special characters that might cause encoding issues
        try:
            # Try to encode as ascii to catch any problematic characters early
            content = content.encode('ascii', errors='ignore').decode('ascii')
        except Exception as e:
            print(f"Warning: Encoding issue in API response: {e}")
            pass

        return content

    except Exception as e:
        print(f"Error in ask_o4_mini: {type(e).__name__}: {str(e)}")
        raise Exception(f"Azure OpenAI API call failed: {str(e)}")

def ask_with_history(messages, max_tokens=2000):
    """
    Ask OpenAI with conversation history to maintain context.
    Messages format: [{"role": "system"/"user"/"assistant", "content": "..."}]

    This allows the model to maintain context across multiple queries without
    repeating the schema and system prompts every time.
    """
    try:
        response = client.chat.completions.create(
            messages=messages,
            max_completion_tokens=max_tokens,
            timeout=60,
            model=DEPLOYMENT
        )

        if not response or not response.choices:
            raise Exception("API returned no choices")

        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            print(f"[Azure OpenAI] Model: {DEPLOYMENT[:30]}...")
            print(f"[Token Usage] Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}")
            print(f"[Response] Status: {finish_reason} | Length: {len(content) if content else 0} chars")
        else:
            print(f"API finish_reason: {finish_reason}, content length: {len(content) if content else 0}")

        if content is None or len(content) == 0:
            raise Exception(f"API returned empty content (finish_reason: {finish_reason})")

        # Clean content of any special characters
        try:
            content = content.encode('ascii', errors='ignore').decode('ascii')
        except Exception as e:
            print(f"Warning: Encoding issue in API response: {e}")
            pass

        return content

    except Exception as e:
        print(f"Error in ask_with_history: {type(e).__name__}: {str(e)}")
        raise Exception(f"Azure OpenAI API call failed: {str(e)}")