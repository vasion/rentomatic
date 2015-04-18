__author__ = 'momchilrogelov'

from scraper import *

def testListPageFetch():
    get_property_result_page()
    content = get_property_result_page(1)
    results = parse_result_page(content)
    assert len(results)==50
    for r in results:
        assert isinstance(r, Property)