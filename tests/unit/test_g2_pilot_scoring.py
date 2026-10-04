"""Frozen interpretation expectations must not borrow oracle item selection."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from tools.g2_pilot_scoring import load_pilot, score_intent, summarize

MANIFEST = Path('evals/operational_agents/g2-pilot-v1.json')


def test_frozen_pilot_counts_and_clarification_contract():
    cases = load_pilot()
    assert len(cases) == 48
    assert sum(c['expected'] == 'investigate' for c in cases) == 28
    assert sum(c['expected'] == 'clarify' for c in cases) == 16
    assert sum(c['expected'] == 'unsupported' for c in cases) == 4
    assert {c['split'] for c in cases} == {'development', 'validation', 'test'}


@pytest.mark.parametrize('mutation', ['duplicate', 'omitted', 'extra', 'hash', 'expected'])
def test_invalid_frozen_manifest_rejected(tmp_path, mutation):
    data = json.loads(MANIFEST.read_text())
    if mutation == 'duplicate':
        data['cases'][1] = deepcopy(data['cases'][0])
    elif mutation == 'omitted':
        data['cases'].pop()
    elif mutation == 'extra':
        data['cases'][0]['item'] = 'GPU-A'
    elif mutation == 'hash':
        data['queries_sha256'] = '0' * 64
    else:
        data['cases'][0]['expected'] = 'pass'
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_pilot(manifest=path)


def accepted(case):
    return {'interpretation': {'status': 'investigate', 'item': case['item'],
                              'as_of': case['as_of'], 'run_id': 'r'},
            'workflow': {'run_id': 'r', 'execution_kind': 'live',
                         'brief': {'run': {'project_id': case['project']}}}}


@pytest.mark.parametrize('mutation', ['item', 'date', 'foreign', 'fixture', 'run'])
def test_intent_rejects_wrong_binding(mutation):
    case = load_pilot()[0]
    outcome = accepted(case)
    if mutation in ('item', 'date'):
        outcome['interpretation']['item' if mutation == 'item' else 'as_of'] = 'wrong'
    elif mutation == 'foreign':
        outcome['workflow']['brief']['run']['project_id'] = 'foreign'
    elif mutation == 'fixture':
        outcome['workflow']['execution_kind'] = 'fixture'
    else:
        outcome['workflow']['run_id'] = 'other'
    assert score_intent(case, outcome)


def test_false_confident_answer_and_unexpected_workflow_rejected():
    case = next(c for c in load_pilot() if c['expected'] == 'clarify')
    assert score_intent(case, accepted(case))
    assert score_intent(case, {'interpretation': {'status': 'clarify'}, 'workflow': {}})
    assert not score_intent(case, {'interpretation': {'status': 'clarify'}, 'workflow': None})


def test_missing_duplicate_and_invalid_outcomes_fail_closed():
    cases = load_pilot()
    report = summarize(cases, [{'id': cases[0]['id'], 'outcome': 'pass', 'errors': []}])
    assert report['counts'] == {'pass': 1, 'fail': 0, 'unknown': 47, 'not_applicable': 0}
    assert not report['ready']
    assert report['by_split']['test']['unknown'] == 12
    for results in ([{'id': cases[0]['id'], 'outcome': 'pass'}] * 2,
                    [{'id': cases[0]['id'], 'outcome': 'nonsense'}]):
        with pytest.raises(ValueError):
            summarize(cases, results)
