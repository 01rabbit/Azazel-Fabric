import json
from pathlib import Path
from datetime import timedelta
import pytest
from azazel_fabric.knowledge_context_clocklab import (
    ClockContract, KnowledgeContextRequestV2, KnowledgeContextResponseV2,
    assert_response_correlates_v2, canonical_clocklab_bytes,
)
from azazel_fabric.knowledge_context import assert_response_correlates, KnowledgeContextRequestV1, KnowledgeContextResponseV1

FIX = Path(__file__).parent / 'fixtures/knowledge_context'

def pair(contract):
    values = []
    for kind, model in [('request', KnowledgeContextRequestV2), ('response', KnowledgeContextResponseV2)]:
        d = json.loads((FIX / f'{kind}_v1.json').read_text())
        d.update(schema_version=f'knowledge-context-{kind}/v2', contract_id=contract.contract_id)
        values.append(model.model_validate(d))
    return values

@pytest.mark.parametrize('value', [True, -1, 1, 5001, 5.0, float('nan')])
def test_policy_rejects_non_contract_budget(value):
    with pytest.raises(ValueError): ClockContract(value)

def test_policy_digest_and_mismatch():
    c=ClockContract(5000)
    assert ClockContract.from_dict(c.as_dict()) == c
    d=c.as_dict(); d['skew_budget_us']=0
    with pytest.raises(ValueError): ClockContract.from_dict(d)

@pytest.mark.parametrize('delta,accepted', [(-5001,False),(-5000,True),(-4999,True),(0,True)])
def test_generation_boundary_and_binding(delta, accepted):
    c=ClockContract(5000); req,res=pair(c)
    d=res.model_dump(mode='python'); d['generated_at']=req.requested_at+timedelta(microseconds=delta)
    d['snapshot']['as_of']=d['generated_at']
    res=KnowledgeContextResponseV2.model_validate(d)
    if accepted: assert_response_correlates_v2(req,res,contract=c)
    else:
        with pytest.raises(ValueError): assert_response_correlates_v2(req,res,contract=c)

def test_replay_policy_and_canonical():
    c=ClockContract(5000); req,res=pair(c)
    assert json.loads(canonical_clocklab_bytes(req))['contract_id']==c.contract_id
    for change in [{'request_id':'different'}, {'contract_id':ClockContract().contract_id}]:
        d=res.model_dump(mode='python');d.update(change)
        with pytest.raises(ValueError): assert_response_correlates_v2(req,KnowledgeContextResponseV2.model_validate(d),contract=c)
    with pytest.raises(TypeError): canonical_clocklab_bytes(KnowledgeContextRequestV1.model_validate(json.loads((FIX/'request_v1.json').read_text())))

def test_v1_still_zero():
    req=KnowledgeContextRequestV1.model_validate(json.loads((FIX/'request_v1.json').read_text()))
    d=json.loads((FIX/'response_v1.json').read_text()); d['generated_at']=req.requested_at-timedelta(microseconds=1);d['snapshot']['as_of']=d['generated_at']
    with pytest.raises(ValueError): assert_response_correlates(req,KnowledgeContextResponseV1.model_validate(d))


def test_extreme_timestamp_does_not_overflow_budget_comparison():
    c=ClockContract(5000); req,res=pair(c)
    d=req.model_dump(mode='python'); d['requested_at']='9999-12-31T23:59:59.999999Z'
    req=KnowledgeContextRequestV2.model_validate(d)
    d=res.model_dump(mode='python'); d.update(generated_at='9999-12-31T23:59:59.999998Z',expires_at='9999-12-31T23:59:59.999999Z')
    d['snapshot']['as_of']=d['generated_at']
    assert_response_correlates_v2(req,KnowledgeContextResponseV2.model_validate(d),contract=c)
    d['generated_at']='0001-01-01T00:00:00Z'; d['snapshot']['as_of']=d['generated_at']
    with pytest.raises(ValueError): assert_response_correlates_v2(req,KnowledgeContextResponseV2.model_validate(d),contract=c)


def test_nested_subclass_rejected_before_dump_drops_state():
    from azazel_fabric.knowledge_context import EntityRef
    class ExtraEntity(EntityRef):
        hidden: str = 'unvalidated extra state'
    c=ClockContract(5000);req,_=pair(c)
    entity=req.entities[0]
    extra=ExtraEntity(entity_type=entity.entity_type,value=entity.value)
    forged=req.model_copy(update={'entities':(extra,)})
    with pytest.raises(TypeError): canonical_clocklab_bytes(forged)


def test_previous_policy_revision_and_id_fail_closed():
    c=ClockContract(5000)
    old={'schema':'azazel-clocklab-policy/1','skew_budget_us':5000,
         'max_observation_age_ms':5000,
         'contract_id':'sha256:cf12dddea0953a51e8fb91b4524b6064118d1405a92601f3f89a8a8f28603de5'}
    assert c.as_dict()['schema']=='azazel-clocklab-policy/2'
    assert c.contract_id!=old['contract_id']
    with pytest.raises(ValueError):ClockContract.from_dict(old)
    req,res=pair(c)
    for obj,model,is_request in [(req,KnowledgeContextRequestV2,True),
                                 (res,KnowledgeContextResponseV2,False)]:
        d=obj.model_dump(mode='python');d['contract_id']=old['contract_id'];wrong=model.model_validate(d)
        with pytest.raises(ValueError):
            assert_response_correlates_v2(wrong if is_request else req,
                                         res if is_request else wrong,contract=c)
