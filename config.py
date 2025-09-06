from openai import AzureOpenAI

# Azure OpenAI Configuration
AZURE_ENDPOINT = "https://365tune-open-ai.openai.azure.com/"
MODEL_NAME = "o4-mini"
DEPLOYMENT = "o4-mini"
SUBSCRIPTION_KEY = "Bqn1HNJdNQcyJC1vFJcFlT1s2hA4kBB4GaJMkIkbBrQ5b3qW7AL4JQQJ99BHACYeBjFXJ3w3AAABACOGa8Hk"
API_VERSION = "2024-12-01-preview"

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

def ask_o4_mini(question):
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": question,
            }
        ],
        max_completion_tokens=500,  # Reduced further for faster processing
        timeout=20,  # Reduced timeout to 20 seconds
        model=DEPLOYMENT
    )
    return response.choices[0].message.content