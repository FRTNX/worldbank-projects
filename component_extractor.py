import os
import json
import spacy
from spacy_layout import spaCyLayout
from argparse import ArgumentParser

nlp = spacy.blank("en")
layout = spaCyLayout(nlp)

parser = ArgumentParser(description='Fetch project data and documents from the World Bank')
parser.add_argument('-d', '--document-dir', required=True,
    help='The directory contain ICRR documents.')

args = parser.parse_args()

# some notes on spaCy's awesomeness. although this function may look simple,
# spaCy is using a compination of layout analysis and text labeling. each section 
# of text is labeled by its parent heading and works very well with nested layouts.
def fetch_components_by_keyword(doc, keyword):
    components = []
    for span in doc.spans['layout']:
        span_heading = str(span._.heading)
   
        if keyword in span_heading.lower():
            if len(str(span.text).split(' ')) > 4: # omit misc data
                components.append(span.text)
    return components

def extract_components(document):
    # extract project id from document. consistently document names are formatted: 
    # <project_id>_<project_id><-?><uuid>, e.g., P174223_P174223-cd0e0c4b-ca67-43e2-b850-c44cbf73d31e.pdf
    project_id = document[:document.find('_')]
    print(f'Extracting components from {project_id} ICR Review')
    doc = layout(f'{args.document_dir}/{document}')
    
    # often times spacy correctly finds the component heading and labels accordingly
    # when this data is present it is xmas and you can likely ignore project objectives
    components = fetch_components_by_keyword(doc, 'component')
    print('found components: ', components)
    
    # in some cases many cases project are embedded within project objectives without separate 
    # headings. in this case we cam extract all sections related to projected objectives. this will typically 
    # fetch the components we seek but will also fetch objective outcomes where present, along with initial objectives,
    # adding to the noise.
    objectives = fetch_components_by_keyword(doc, 'objective')
    print('found objectives:', objectives)
    
    return {
        'project_id': project_id,
        'components': components,
        'objectives': objectives
    }

if __name__ == '__main__':
    print('using document directory:', args.document_dir)
    documents = os.listdir(args.document_dir)
    pdf_docs = []
    for document in documents:
        filename, file_extension = os.path.splitext(document)
        if file_extension == '.pdf':
            pdf_docs.append(document)
    
    dataset = []
    for document in pdf_docs:
        project_components = extract_components(document)
        dataset.append(project_components)
        with open('components.json', 'w') as f:
            data = { 'data': dataset }
            f.write(json.dumps(data, indent=4))

        