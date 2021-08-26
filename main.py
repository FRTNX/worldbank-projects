import os
import json
from argparse import ArgumentParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

parser = ArgumentParser(description='Fetch project data and documents from the World Bank.')
parser.add_argument('-n', '--number-projects', type=int, default=10,
    help='The number of projects to fetch documents for. Test default is 10.')
parser.add_argument('-pid', '--project-id', type=str,
    help='Fetches documents for a single project')
args = parser.parse_args()

if (args.project_id == None):
    projects_data = open('aggregated.json', 'r')
    projects = json.loads(projects_data.read())
    project_ids = list(projects.keys())
else:
    project_ids = [args.project_id]

driver = webdriver.Chrome()

def get_project_documents(project_id):
    print('Processing project: ', project_id)
    document_detail_url = f'https://projects.worldbank.org/en/projects-operations/document-detail/{project_id}'
    driver.get(document_detail_url)

    links = driver.find_elements_by_tag_name('a')
    link_urls = [link.get_attribute('href') for link in links]

    document_links = [link for link in link_urls if link and 'curated' in link]

    for document_link in document_links:
        driver.get(document_link)

        links = driver.find_elements_by_tag_name('a')
        link_urls = [link.get_attribute('href') for link in links]
        documents = [link for link in link_urls if link and (link.endswith('.txt') or link.endswith('.pdf'))]

        for document in documents:
            # todo: check if doc already exists
            os.system(f'wget {document} -P ./documents/{project_id}/')


if __name__ == '__main__':
    if args.project_id == None:
        for i in range(0, args.number_projects):
            get_project_documents(project_ids[i])
    else:
        get_project_documents(args.project_id)