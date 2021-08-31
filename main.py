import os
import json
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
parser.add_argument('-d', '--documents', action='store_true', help='fetch key project documents')
parser.add_argument('-m', '--metadata', action='store_true',
    help='fetches project metadata and adds details to the aggregated.json file')
parser.add_argument('-dt', '--document-type', help='Fetch specific document-type, including non-default types.')
parser.add_argument('-hl', '--headless', default=False,
    help='run the script in headless mode, does not require chrome to be running')
args = parser.parse_args()

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

driver = webdriver.Chrome(chrome_options=options)


def get_project_documents(project_id):
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


def get_project_metadata(project_id):
    print('Extracting metadata for project: ', project_id)
    
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
    
    document_detail_url = f'https://projects.worldbank.org/en/projects-operations/document-detail/{project_id}'
    driver.get(document_detail_url)

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


# Fetches api data and merges it with the xls-derived data in aggregated.json
def fetch_api_data():
    api_data = requests.get(
        f'http://search.worldbank.org/api/v2/projects?format=json&source=IBRD&rows={len(projects.keys())}'
    ).json()
    api_projects = api_data['projects']
    for project_id in api_projects.keys():                                                                             
        xls_project = projects[project_id]                                                                      
        api_project = api_projects[project_id]                                                                  
        for key in api_project.keys():                                                                          
            if key not in xls_project.keys():                                                                   
                xls_project[key] = api_project[key] 


if __name__ == '__main__':
    number_projects = len(projects.keys()) if args.all_projects else args.number_projects
    print(f'Running extraction script on {1 if args.project_id else number_projects} project(s)')

    if args.all_projects and not args.documents and not args.metadata:
        [get_project_documents(project_ids[i]) for i in range(0, number_projects)]
        [get_project_metadata(project_ids[i]) for i in range(0, number_projects)]

    if args.metadata and args.project_id:
        get_project_metadata(args.project_id)

    if args.metadata and args.project_id == None:
        [get_project_metadata(project_ids[i]) for i in range(0, number_projects)]

    if args.documents and args.project_id:
        get_project_documents(args.project_id)

    if args.documents and args.project_id == None:
        [get_project_documents(project_ids[i]) for i in range(0, number_projects)]
    
    