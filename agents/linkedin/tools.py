from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.openapi_tool.auth.auth_helpers import AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_credential import HttpAuth, HttpCredentials
from fastapi.openapi.models import HTTPBearer
import yaml
import os
from dotenv import load_dotenv

load_dotenv()

PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")

def get_proxycurl_tools():
    # Construct the absolute path to proxycurl.yaml
    current_dir = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.join(current_dir, 'proxycurl.yaml')

    # load the openapi spec from the file
    with open(spec_path, 'r') as file:
        spec = yaml.safe_load(file)

    # Configure the auth scheme to match what's defined in the YAML spec (BearerAuth with http bearer scheme)
    auth_scheme = HTTPBearer(
        bearerFormat="JWT"  # Common format, can be omitted if not specified in the spec
    )
    
    auth_credential = AuthCredential(
        auth_type=AuthCredentialTypes.HTTP,
        http=HttpAuth(
            scheme="bearer",
            credentials=HttpCredentials(token=PROXYCURL_API_KEY)
        )
    )
    
    tools = OpenAPIToolset(
        spec_dict=spec,
        auth_scheme=auth_scheme,
        auth_credential=auth_credential
    ).get_tools()
    return tools

if __name__ == "__main__":
    tools = get_proxycurl_tools()
    print(tools)