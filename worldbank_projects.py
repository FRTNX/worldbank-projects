# coding=utf-8

"""World Bank Projects Dataset"""

from __future__ import absolute_import, division, print_function

import json
import re

import datasets


logger = datasets.logging.get_logger(__name__)


_CITATION = """\
@InProceedings{huggingface:dataset,
title   = {World Bank Projects Dataset},
authors = {Busani Ndlovu, Luke Jordan},
year    = {2021}
}
"""

# TODO: Complete description
_DESCRIPTION = """World Bank Projects Dataset"""

# Redundant but may useful in future.
_URL = "https://frtnx.github.io/worldbank-projects/dataset"
_URLS = {
    'train': _URL + 'train-v1.0.json'
}


class WorldBankProjectsConfig(datasets.BuilderConfig):
    """BuilderConfig for World Bank Projects Dataset."""

    def __init__(self, **kwargs):
        """BuilderConfig for World Bank Projects Dataset.
        Args:
          **kwargs: keyword arguments forwarded to super.
        """
        super(WorldBankProjectsConfig, self).__init__(**kwargs)


class WorldBankProjects(datasets.GeneratorBasedBuilder):
    """World Bank Projects Dataset"""

    VERSION = datasets.Version("1.1.0")

    def _info(self):
        return datasets.DatasetInfo(
            description=_DESCRIPTION,
            features=datasets.Features(
                {
                    'project_id': datasets.Value('string'),
                    'filename': datasets.Value('string'),
                    'document_text': datasets.Value('string')
                }
            ),
            supervised_keys=None,
            homepage='https://huggingface.co/datasets/FRTNX/worldbank-projects',
            citation=_CITATION,
        )

    def _split_generators(self, dl_manager):
        downloaded_files = dl_manager.download_and_extract(_URLS)
        
        return [
            datasets.SplitGenerator(name=datasets.Split.TRAIN, gen_kwargs={'filepath': downloaded_files['train']})
        ]

    def _generate_examples(self, filepath):
        """This function returns the examples in the raw (text) form."""
        logger.info('generating examples from = %s', filepath)
        with open(filepath, encoding="utf-8") as f:
            worldbank_projects = json.load(f)
            for row in worldbank_projects['data']:
                id_ = row['project_id']
                result = {
                    'id': row['project_id'],
                    'filename': row['filename'],
                    'document_text': row['document_text']
                }

                yield id_, result
