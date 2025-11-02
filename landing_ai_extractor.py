import os
import json
import requests
from io import BytesIO

from argparse import ArgumentParser

parser = ArgumentParser(description='Fetch project data and documents from the World Bank')
parser.add_argument('-d', '--document-dir', required=False,
    help='The directory contain ICRR documents.')

args = parser.parse_args()

VA_API_KEY = 'API_KEY' # Replace with your API key
headers = {"Authorization": f"Basic {VA_API_KEY}"}

# Extract fields using the schema
schema = {
  "type": "object",
  "title": "Project Objectives and Components Extraction Schema",
  "$schema": "http://json-schema.org/draft-07/schema#",
  "required": [
    "objectives",
    "components"
  ],
  "properties": {
    "objectives": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "objective"
        ],
        "properties": {
          "objective": {
            "type": "string",
            "title": "Objective Statement",
            "description": "The full text of the project objective."
          }
        }
      },
      "title": "Project Objectives",
      "description": "A list of the main objectives of the project as stated in the document."
    },
    "components": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "name",
          "original_allocation",
          "actual_expenditure",
          "description"
        ],
        "properties": {
          "name": {
            "type": "string",
            "title": "Component Name",
            "description": "The name or title of the project component."
          },
          "original_allocation": {
            "type": "string",
            "title": "Original Allocation",
            "description": "The original budget allocation for the component (in USD or stated currency)."
          },
          "actual_expenditure": {
            "type": "string",
            "title": "Actual Expenditure",
            "description": "The actual expenditure for the component (in USD or stated currency)."
          },
          "description": {
            "type": "string",
            "title": "Component Description",
            "description": "A brief description of the component's purpose and activities."
          }
        }
      },
      "title": "Project Components",
      "description": "A list of the main components of the project, each with its name, original allocation, actual expenditure, and a brief description."
    }
  },
  "description": "Schema for extracting the project objectives and components from a markdown document related to the Togo COVID-19 Education Response (GPE) project."
}

def extract_components(document, document_dir):
    project_id = document[:document.find('_')]
    print(f'Extracting components from {project_id} ICR Review')
    pdf_path = f'{document_dir}/{document}'
    
    # Parse the document first
    parse_response = requests.post(
        url="https://api.va.landing.ai/v1/ade/parse",
        headers=headers,
        files=[("document", open(pdf_path, "rb"))],
        data={"model": "dpt-2"}
    )
    
    markdown_content = parse_response.json()["markdown"]
    extract_response = requests.post(
        url="https://api.va.landing.ai/v1/ade/extract", 
        headers=headers,
        files=[("markdown", BytesIO(markdown_content.encode('utf-8')))],
        data={"schema": json.dumps(schema)},
    ).json()
    
    return {
        'project_id': project_id,
        'data': extract_response
    }


if __name__ == '__main__':
    document_dir = args.document_dir if args.document_dir else 'documents/icrr'
    print('using document directory:', document_dir)
    documents = os.listdir(document_dir)
    pdf_docs = []
    for document in documents:
        filename, file_extension = os.path.splitext(document)
        if file_extension == '.pdf':
            pdf_docs.append(document)
    
    dataset = []
    print('found pdf docs:', pdf_docs)
    for document in pdf_docs:
        project_components = extract_components(document, document_dir)
        print('extracted project components:', project_components)
        dataset.append(project_components)
        with open('landing_ai_components.json', 'w') as f:
            data = { 'data': dataset }
            f.write(json.dumps(data, indent=4))
