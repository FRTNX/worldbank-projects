import os
import json
import xlrd
import requests
from argparse import ArgumentParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

document_search_terms = [
    'Project Appraisal Document',
    'Project Information Document',
    'Project Information and Integrated Safeguards Data Sheet',
    'Staff Appraisal Report',
    'Memorandum & Recommendation of the President'
]

parser = ArgumentParser(description='Fetch project data and documents from the World Bank')
parser.add_argument('-n', '--number-projects', type=int, default=10,
    help='the number of projects to fetch documents for. Test default is 10')
parser.add_argument('-a', '--all-projects', action='store_true',
     help='fetches all project data and/or documents')
parser.add_argument('-pid', '--project-id', type=str,
    help='fetches key documents for a single project')
parser.add_argument('-d', '--documents', action='store_true',
    help='fetches documents and/or metadata for a single document')
parser.add_argument('-m', '--metadata', action='store_true',
    help='fetches project metadata and adds details to the aggregated.json file')
parser.add_argument('-s', '--staff-information', action='store_true', 
    help='fetches staff information for related project(s)')
parser.add_argument('-dt', '--document-type', help='Fetch specific document-type, including non-default types.')
parser.add_argument('-hl', '--headless', default=True, help='run the script in headless \
    mode, does not require Chrome to be running. Default is True. Set to False to track \
    script execution from the browser')
parser.add_argument('-agg', '--aggregate', action='store_true',
    help='fetch project data from the World Bank API and add missing details to corresponding projects in aggregated.json')
parser.add_argument('-x', '--xls-to-json', action='store_true', help='convert a World Bank xls data dump to a json file used for \
    future aggregations. Run in cases where aggregated.json does not exist or is corrupted.')
parser.add_argument('-f', '--filepath', help='Defines a filepath for arguments that accept custom files \
    for example, python main.py --xls-to-json -f "./path_to_custom.xls"')
parser.add_argument('-r', '--reset', action='store_true', help='resets the extraction status \
    of either documents, metadata or staff information. e.g., python main.py -r -d resets the \
    log of projects with downloaded documents. Note that reset targets must be explicitly defined')
parser.add_argument('--stats', action='store_true', help='prints extraction status for documents \
    metadata, and staff information')
parser.add_argument('--retro', action='store_true', help='Updates extraction details with pre-existing \
    documents and/or data.')
args = parser.parse_args()


def transform_xls_to_json():
    filepath = args.filepath if args.filepath else './World_Bank_Projects_downloaded_8_17_2021.xls'
    print(f'Transforming {filepath} to json')
    workbook = xlrd.open_workbook(filepath) 
    sheet = workbook.sheet_by_index(0) 

    abbr_keys = []
    for cell in sheet.row(2):                                                                                      
        abbr_keys.append(cell.value)

    data = {}
    for i in range(3, sheet.nrows):                                                                                
        project_id = sheet.row(i)[0].value;                                                                        
        print('Tranforming project: ' + project_id)                                                              
        data[project_id] = {}                                                                                   
        for index in range(len(sheet.row(i))):                                                                     
            data[project_id][abbr_keys[index]] = sheet.row(i)[index].value
            
    print(f'Transform complete. Processed {len(data.keys())} projects')
    with open('aggregated.json', 'w') as f:
        f.write(json.dumps(data))


if not os.path.exists('aggregated.json'):
    print('aggregated.json not found. creating it from default xls file')
    transform_xls_to_json()
    args.xls_to_json = False

projects = {}
with open('aggregated.json', 'r') as f:
    projects = json.loads(f.read())

if (args.project_id == None):
    project_ids = list(projects.keys())
else:
    project_ids = [args.project_id]

options = Options()
if (args.headless):
    options.headless = True

if args.document_type:
    args.documents = True

if not os.path.exists('extraction_details.json'):
    with open('extraction_details.json', 'w') as f:
        f.write(json.dumps({ 'documents': [], 'metadata': [], 'staff_information': [] }))

extraction_details = {}
with open('extraction_details.json', 'r') as f:
    extraction_details = json.loads(f.read())

driver = webdriver.Chrome(chrome_options=options)


def get_project_documents(project_id):
    if project_id in extraction_details['documents']:
        print('Project documents already extracted for project: ', project_id)
        return
    
    print('Extracting documents for project: ', project_id)
    document_detail_url = f'https://projects.worldbank.org/en/projects-operations/document-detail/{project_id}'
    driver.get(document_detail_url)

    table_rows = []
    for tr in driver.find_elements_by_xpath('//tr'):
        tds = tr.find_elements_by_tag_name('td')
        table_rows.append([td.text for td in tds])

    target_rows = []
    for row in table_rows:
        document_types = [args.document_type] if args.document_type else document_search_terms
        [target_rows.append(row) for data in row if data in document_types]

    document_page_links = [driver.find_element_by_link_text(data[0]).get_attribute('href') for data in target_rows]
    print('Got document page links: ', document_page_links)

    for document_page in document_page_links:
        driver.get(document_page)

        links = driver.find_elements_by_tag_name('a')
        link_urls = [link.get_attribute('href') for link in links]
        document_file_links = [link for link in link_urls if link and (link.endswith('.txt') or link.endswith('.pdf'))]
        print('Found documents: ', document_file_links)

        for file_link in document_file_links:
            filename = f'{project_id}_{os.path.basename(file_link)}'
            os.system('mkdir documents') if not os.path.exists('./documents') else None
            if not os.path.exists(f'./documents/{filename}'):
                os.system(f"wget {file_link} -O './documents/{filename}'")
            else:
                print('Document already exists: ', filename)

    # document_page_links sometimes returns empty, even where documents exist.
    # marking it as not extracted to be re-attempted on the next
    # execution of the script
    if len(document_page_links) > 0:
        extraction_details['documents'].append(project_id)
        with open('extraction_details.json', 'w') as f:
            print('Persisting extraction details: ', extraction_details)
            f.write(json.dumps(extraction_details))


def get_project_metadata(project_id):
    if project_id in extraction_details['metadata']:
        print('Project metadata already extracted for project: ', project_id)
        return

    print('Extracting metadata for project ', project_id)
    
    project_details_url = f'https://projects.worldbank.org/en/projects-operations/project-detail/{project_id}'
    driver.get(project_details_url)

    table_rows = []
    for tr in driver.find_elements_by_xpath('//tr'):
        tds = tr.find_elements_by_tag_name('td')
        row_object = {}
        for td in tds:
            data_key = td.get_attribute('data-th')
            if len(data_key) > 0 and data_key.endswith(':'):
                row_object = { **row_object, data_key[:len(data_key)-1]: td.text }
        if len(row_object.keys()) > 0:
            table_rows.append(row_object)

    key_mapping = [
        { 'FinancingPlan': ['Financier', 'Commitments']},
        { 'TotalProjectFinancingTableOne': ['IBRD/IDA', 'Product Line' ]},
        { 'TotalProjectFinancingTableTwo': ['Investment Project Financing', 'Lending Instrument']},
        { 'SummaryStatusOfWBFinancing': ['Financier', 'Approval Date', 'Closing Date', 'Principal', 'Disbursed', 'Repayments', 'Interest, Charges & Fees']},
        { 'DetailedFinancialActivity': ['Period', 'Financier', 'Transaction Type', 'Amount (US$)']}
    ]

    project_details = {
        'FinancingPlan': [],
        'TotalProjectFinancingTableOne': [],
        'TotalProjectFinancingTableTwo': [],
        'SummaryStatusOfWBFinancing': [],
        'DetailedFinancialActivity': []
    }

    # append details accordingly
    for row in table_rows:
        for project_detail in key_mapping:
            if sorted(list(row.keys())) == sorted(list(project_detail.values())[0]):
                project_details[(list(project_detail.keys())[0])].append(row)

    print('Found project details: ', project_details)
    projects[project_id]['addtional_details'] = project_details
    
    document_details_url = f'https://projects.worldbank.org/en/projects-operations/document-detail/{project_id}'
    driver.get(document_details_url)

    table_rows = []
    for tr in driver.find_elements_by_xpath('//tr'):
        tds = tr.find_elements_by_tag_name('td')
        table_rows.append([td.text for td in tds])

    document_details = []
    [document_details.append({
        'document_name': row[0],
        'date': row[1],
        'report_number': row[2],
        'document_type': row[3],
        'document_url': driver.find_element_by_link_text(row[0]).get_attribute('href')
    }) for row in table_rows if len(row) == 4]   
    print(f'Document details for project {project_id}: ', document_details)

    projects[project_id]['project_documents'] = document_details

    with open('aggregated.json', 'w') as f:
        f.write(json.dumps(projects))

    extraction_details['metadata'].append(project_id)
    with open('extraction_details.json', 'w') as f:
        print('Persisting extraction details: ', extraction_details)
        f.write(json.dumps(extraction_details))


# Extracts staff information from downloaded document txt files.
# This function assumes that the project documents have already been extracted.
# if not, this is achievable by adding the -d flag to any command that extracts staff information
def extract_staff_information(project_id):
    if project_id in extraction_details['staff_information']:
        print('Project staff information already extracted for project: ', project_id)
        return

    print('Extracting staff information for project ', project_id)
    search_terms = ['Vice President:', 'Country Director:', 'Sector Manager:', 'Task Team Leader:']
    staff_information = {}
    for filename in [x for x in os.listdir('./documents') if x.startswith(project_id) and x.endswith('.txt')]:
        with open(f'./documents/{filename}', 'r', encoding='latin1') as f:
            for line in f.readlines():
                for search_term in search_terms:
                    if search_term in line:
                        key, value = ' '.join(line.split()).split(':')
                        staff_information[key] = value

    print(f'Found staff information for project {project_id}: ', staff_information)
    projects[project_id]['staff_information'] = staff_information
    with open('aggregated.json', 'w') as f:
        f.write(json.dumps(projects))

    extraction_details['staff_information'].append(project_id)
    with open('extraction_details.json', 'w') as f:
        print('Persisting extraction details: ', extraction_details)
        f.write(json.dumps(extraction_details))


# Fetches api data and merges it with the xls-derived data in aggregated.json
def fetch_api_data(number_projects):
    print(f'Fetching api data for {number_projects} project(s)')
    api_response = requests.get(f'http://search.worldbank.org/api/v2/projects?format=json&source=IBRD&rows={number_projects}')
    print(f'Fetch project api data returned status code {api_response.status_code}', api_response)
    if api_response.status_code == 200:
        try:
            api_data = api_response.json()
        except Exception as e:
            print('Error: ', e)
            return

        api_projects = api_data['projects']
        for project_id in api_projects.keys():
            print('Aggregating data for project: ', project_id)                                                                          
            project = projects[project_id]                                                                      
            api_project = api_projects[project_id]                                                                  
            for key in api_project.keys():                                                                          
                if key not in project.keys():                                                                   
                    project[key] = api_project[key]

        with open('aggregated.json', 'w') as f:
            f.write(json.dumps(projects))
        print('Data aggregation complete. Saved to aggregated.json')

    
def reset_extraction_details():
    if args.documents:
        extraction_details['documents'] = []
    if args.metadata:
        extraction_details['metadata'] = []
    if args.staff_information:
        extraction_details['staff_information'] = []

    with open('extraction_details.json', 'w') as f:
        f.write(json.dumps(extraction_details))
    print('Extraction details successfully (re)set')


def retroactively_populate_extraction_details():
    print('Updating extraction details...')
    
    if args.documents:
        for filename in os.listdir('./documents'):
            project_id = filename[:filename.find('_')]
            if project_id not in extraction_details['documents']:
                extraction_details['documents'].append(project_id)

    if args.metadata:
        [
            extraction_details['metadata'].append(project_id) for project_id in projects.keys() if 'project_documents' in projects[project_id].keys() and \
                ('additional_details' in projects[project_id].keys() or 'addtional_details' in projects[project_id].keys()) \
                and project_id not in extraction_details['metadata'] # ^ atonement for an old typo
        ]

    if args.staff_information:
        [
            extraction_details['staff_information'].append(project_id) for project_id in projects.keys() \
                if 'staff_information' in projects[project_id].keys() and project_id not in extraction_details['staff_information']
        ]

    with open('extraction_details.json', 'w') as f:
        f.write(json.dumps(extraction_details))
    print('Extraction details successfully updated')


def extraction_stats():
    total_projects = len(projects.keys())
    print(f'Documents: {len(extraction_details["documents"])}/{total_projects}')
    print(f'Metadata: {len(extraction_details["metadata"])}/{total_projects}')
    print(f'Staff information: {len(extraction_details["staff_information"])}/{total_projects}')


def extraction_handler():
    if args.reset: return reset_extraction_details()

    if args.retro: return retroactively_populate_extraction_details()

    if args.stats: return extraction_stats()

    number_projects = len(projects.keys()) if args.all_projects else args.number_projects
    print(f'Running extraction script on {1 if args.project_id else number_projects} project(s)')

    if args.all_projects and not args.documents and not args.metadata \
        and not args.aggregate and not args.reset:
        [get_project_documents(project_ids[i]) for i in range(0, number_projects)]
        [get_project_metadata(project_ids[i]) for i in range(0, number_projects)]
        [extract_staff_information(project_ids[i]) for i in range(0, number_projects)]

    if args.documents and args.project_id:
        get_project_documents(args.project_id)

    if args.documents and args.project_id == None:
        [get_project_documents(project_ids[i]) for i in range(0, number_projects)]

    if args.metadata and args.project_id:
        get_project_metadata(args.project_id)

    if args.metadata and args.project_id == None:
        [get_project_metadata(project_ids[i]) for i in range(0, number_projects)]

    if args.staff_information and args.project_id:
        extract_staff_information(args.project_id)

    if args.staff_information and not args.project_id:
        [extract_staff_information(project_ids[i]) for i in range(0, number_projects)]

    if args.xls_to_json: transform_xls_to_json()

    if args.aggregate: fetch_api_data(number_projects)


if __name__ == '__main__':
    # encapsulated for the benefit of using return statements
    extraction_handler()
