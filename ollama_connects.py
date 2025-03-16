from os import access

import ollama

def list_available_models():
    """Lists all models currently installed on the local Ollama instance."""
    try:
        models = ollama.list()
        return [n.model for n in models.models]
    except Exception as e:
        return f"Error listing models: {e}"

def download_model(model_name):
    """Downloads a specified model if it is available in Ollama's library."""
    try:
        ollama.pull(model_name)
        return f"Model '{model_name}' downloaded successfully."
    except Exception as e:
        return f"Error downloading model '{model_name}': {e}"

def delete_model(model_name):
    """Deletes a specified model from the local Ollama instance."""
    try:
        ollama.delete(model_name)
        return f"Model '{model_name}' deleted successfully."
    except Exception as e:
        return f"Error deleting model '{model_name}': {e}"


import subprocess
import requests


def get_ollama_response(prompt, model, mode="local", api_url=None, access_token=None):
    """
    Retrieve a response either by calling the local LLM (using ollama) or by sending a request to a remote API.

    Parameters:
        prompt (str): The input prompt.
        model (str): The model to use.
        mode (str): "local" to call the local LLM; "api" to call a remote API endpoint.
        api_url (str): The URL of the remote API endpoint. Required if mode is "api".
        access_token (str): Optional. If provided, will be sent as a Bearer token in the Authorization header for the API.

    Returns:
        str: The response from the model, or an error message.
    """
    if mode == "local":
        try:
            result = subprocess.run(
                ['ollama', 'run', model],
                input=prompt,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {str(e)}"

    elif mode == "api":
        if not api_url:
            return "Error: API URL must be provided in API mode."
        headers = {}
        if access_token:
            access_token = access_token
            headers["Authorization"] = f"Bearer {access_token}"
        try:
            payload = {"prompt": prompt}
            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json().get("result", "").strip()
            else:
                return f"Error: API returned status code {response.status_code} with message: {response.text}"
        except Exception as e:
            return f"Error: {str(e)}"

    else:
        return "Error: Invalid mode specified. Use 'local' or 'api'."


