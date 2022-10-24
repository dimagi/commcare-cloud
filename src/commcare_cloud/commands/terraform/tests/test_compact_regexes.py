import re

from commcare_cloud.commands.terraform.constants import COMMCAREHQ_XML_POST_URLS_REGEX
from commcare_cloud.commands.terraform.terraform import compact_waf_regexes_simply, compact_waf_regexes


def test_compact_waf_regexes_simply__single_pattern():
    assert compact_waf_regexes_simply([r'^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$']) \
           == [r'^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$']


def test_compact_waf_regexes_simply__two_patterns():
    assert compact_waf_regexes_simply([
        r'^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$',
        r'^/a/([\w\.:-]+)/api/v0\.6/case(?:/([\w\-,]+))?/?$'
    ]) == [
        r'^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$|^/a/([\w\.:-]+)/api/v0\.6/case(?:/([\w\-,]+))?/?$'
    ]


def test_compact_waf_regexes_simply__match_examples():
    _test_compact_function_against_examples(compact_waf_regexes_simply, COMMCAREHQ_XML_POST_URLS_REGEX)


def test_compact_waf_regexes__single_pattern():
    assert compact_waf_regexes([r'^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$']) \
           == [r'^/a/([\w\.:-]+)/(api/v([\d\.]+)/form/)$']


def test_compact_waf_regexes__two_patterns():
    assert compact_waf_regexes([
        r'^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$',
        r'^/a/([\w\.:-]+)/api/v0\.6/case(?:/([\w\-,]+))?/?$'
    ]) == [
        r'^/a/([\w\.:-]+)/(api/v([\d\.]+)/form/|api/v0\.6/case(?:/([\w\-,]+))?/?)$'
    ]


def test_compact_waf_regexes__single_non_matching_pattern():
    assert compact_waf_regexes([r'abc']) \
           == [r'abc']


def test_compact_waf_regexes__match_examples():
    _test_compact_function_against_examples(compact_waf_regexes, COMMCAREHQ_XML_POST_URLS_REGEX)


def test_compact_waf_regexes__pattern_length():
    compacted_patterns = compact_waf_regexes(COMMCAREHQ_XML_POST_URLS_REGEX)
    for pattern in compacted_patterns:
        assert len(pattern) <= 200, pattern


def test_compact_waf_regexes__number_of_patterns():
    compacted_patterns = compact_waf_regexes(COMMCAREHQ_XML_POST_URLS_REGEX)
    assert len(compacted_patterns) <= 10


def _test_compact_function_against_examples(compact_function, patterns):
    examples = [_generate_matching_example(pattern) for pattern in patterns]
    compacted_patterns = compact_function(patterns)

    # make sure that all of the example strings match
    for example in examples:
        assert any(re.match(pattern, example) for pattern in compacted_patterns), (example, compacted_patterns)

    # make sure not just any string matches
    for example in ['fish', '/a/b/c/d/']:
        assert not any(re.match(pattern, example) for pattern in compacted_patterns), (example, compacted_patterns)


def _generate_matching_example(pattern):
    """
    Taking a regex pattern and return a string that will match it

    Current implementation very loose, possibly not even strictly correct.

    TODO: If you add a new regex that uses a "special" pattern not listed here, add it to fix this function
    """
    return pattern \
        .replace(r'(?:/([\w-]+))?', '') \
        .replace(r'(\w+)', 'onetwothreefour') \
        .replace(r'([\w]+)', 'onetwothreefour') \
        .replace(r'([ \w-]+)', 'one two three four') \
        .replace(r'([\w\.:-]+)', 'one.two:three-four') \
        .replace(r'([\d\.]+)', '0.5') \
        .replace(r'([\w-]+)', 'one-two-three-four') \
        .replace(r'([\w\-]+)', 'one-two-three-four') \
        .replace(r'^', '') \
        .replace(r'$', '') \
        .replace(r'\.', '.') \
        .replace(r'(?:/([\w\-,]+))?', '') \
        .replace(r'/?', '/') \
        .replace(r'(case_list_explorer|duplicate_cases)', 'duplicate_cases')
