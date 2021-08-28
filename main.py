import os
import json
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

parser = ArgumentParser(description='Fetch project data and documents from the World Bank.')
parser.add_argument('-n', '--number-projects', type=int, default=10,
    help='The number of projects to fetch documents for. Test default is 10.')
parser.add_argument('-pid', '--project-id', type=str,
    help='Fetches key documents for a single project')
parser.add_argument('-d', '--documents', action='store_true', help='Fetch key project documents')
parser.add_argument('-md', '--metadata', action='store_true',
    help='Fetches project metadata and adds details to the aggregated.json file')
parser.add_argument('-hl', '--headless', action='store_true', help='Run in headless mode')
args = parser.parse_args()

if (args.project_id == None):
    projects_data = open('aggregated.json', 'r')
    projects = json.loads(projects_data.read())
    project_ids = list(projects.keys())
else:
    project_ids = [args.project_id]

options = Options()
if (args.headless):
    options.headless = True

driver = webdriver.Chrome(chrome_options=options)


def get_project_documents(project_id):
    print('Extracting documents for project: ', project_id)
    document_detail_url = f'https://projects.worldbank.org/en/projects-operations/document-detail/{project_id}'
    driver.get(document_detail_url)

    table_rows = []
    for tr in driver.find_elements_by_xpath('//tr'):
        tds = tr.find_elements_by_tag_name('td')
        table_rows.append([td.text for td in tds])
    print('Got document rows: ', table_rows)

    target_rows = []
    for row in table_rows:
        [target_rows.append(row) for data in row if data in document_search_terms]
    print('Target rows: ', target_rows)

    document_page_links = [driver.find_element_by_link_text(data[0]).get_attribute('href') for data in target_rows]
    print('Got doc links: ', document_page_links)

    for document_page in document_page_links:
        driver.get(document_page)

        links = driver.find_elements_by_tag_name('a')
        link_urls = [link.get_attribute('href') for link in links]
        document_file_links = [link for link in link_urls if link and (link.endswith('.txt') or link.endswith('.pdf'))]

        for file_link in document_file_links:
            # todo: check if doc already exists
            os.system(f"wget {file_link} -O './documents/{project_id}_{os.path.basename(file_link)}'")


def get_project_metadata(project_id):
    print('Extracting metadata for project: ', project_id)
    document_detail_url = f'https://projects.worldbank.org/en/projects-operations/document-detail/{project_id}'
    driver.get(document_detail_url)

    ## uncomment in the event of troublsome ajax loading.
    ## not necessary with current site structure.
    # WebDriverWait(driver, 10).until(
    #     EC.presence_of_element_located((By.XPATH, '//tr'))
    # )

    table_rows = []
    for tr in driver.find_elements_by_xpath('//tr'):
        tds = tr.find_elements_by_tag_name('td')
        table_rows.append([td.text for td in tds])
    print('Got table rows: ', table_rows)

    document_details = []
    [document_details.append({
        'document_name': row[0],
        'date': row[1],
        'report_number': row[2],
        'document_type': row[3],
        'document_url': driver.find_element_by_link_text(row[0]).get_attribute('href')
    }) for row in table_rows if len(row) == 4]
    
    print('Document details: ', document_details)

    for document in document_details:
        driver.get(document['document_url'])

        doc_detail_rows = []
        for tr in driver.find_elements_by_xpath('//ul'):
            tds = tr.find_elements_by_tag_name('li')
            doc_detail_rows.append([td.text for td in tds if '\n' in td.text])
        print('Got doc details: ', doc_detail_rows)
        

if __name__ == '__main__':
    # todo: create path for project id + document type
    if args.metadata and args.project_id:
        get_project_metadata(args.project_id)

    if args.metadata and args.project_id == None:
        [get_project_metadata(project_ids[i]) for i in range(0, args.number_projects)]

    if args.documents and args.project_id:
        get_project_documents(args.project_id)

    if args.documents and args.project_id == None:
        [get_project_documents(project_ids[i]) for i in range(0, args.number_projects)]
    