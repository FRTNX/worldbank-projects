# worldbank-projects
Tools for extracting project information and documents from the World Bank

![](image.gif)

## Extracting Project Documents
### Fetching Standard Documents

Here, standard documents refers to a projects appraisal and information documents.

To fetch documents for a single project (for example, project P176630):
```
python main.py -d -pid P176630
```

Note: arguments and flags may be provided in any order.

To fetch documents for ```n``` number of projects, (for example, where ```n``` equals 2718, S/O Euler)
```
python main.py -d -n 2718
```

To fetch documents for all World Bank projects
```
python main.py -d -a
```

To specify projects to fetch via csv as well as specific documents of interest (assuming your csv file specifies 12064 targets):
```
python main.py --target-package pcodes_to_fetch.csv --document-types "Project Appraisal Document" "Project Paper" -n 12064
```

or in short form:
```
python main.py -tp pcodes_to_fetch.csv -dt "Project Appraisal Document" "Project Paper" -n 12064
```

### Fetching Other Document Types
Documents other than project information and appraisals may also be downloaded.

For a single project this is achievable with
```
python main.py -pid P175987 -dt "Stakeholder Engagement Plan"
```
or verbosely
```
python main.py --project-id P175987 --document-type "Stakeholder Engagement Plan"
```
The ```-dt``` argument can be used with the ```-n``` and ```-a``` arguments to fetch custom document types for a subset or all projects. 

## Extracting Project Metadata
Project metadata may be downloaded and persisted into the aggregated.json file with the following commands. 

For a single project:
```
python main.py -pid P175987 -m
```
or verbosely:
```
python main.py --project-id P175987 --metadata
```

For a subset of projects:
```
python main.py -n 30 -m
```

For all projects:
```
python main.py -m -a
```
The result of these commands is saved in the relevant project object in aggregated.json, in the document_details and addition_details keys.

## Extracting Staff Information
IMPORTANT: This command finds project staff information from project documents and assumes the relevant documents have already been downloaded. Where uncertain, simply add the ```-d``` flag to the command and the program will first check for the relevant documents (and download them if absent) before extracting staff information.

To find staff information for a single project:
```
python main.py -pid P175987 -s
```
or verbosely
```
python main.py -pid P175987 --staff-information
```

Staff information for a subset of projects:
```
python main.py -s -n 5
```

Staff information for all projects
```
python main.py -s -a
```
The result of these commands is saved in the relevant project object in aggregated.json, in the staff_information key.

For a full listing of options:
```
python main.py -h
```
