from app.agents import compare_requirements
def r(i,t,d="same",s="confirmed"):
    return {"id":i,"title":t,"description":d,"status":s,"priority":"must","acceptance_criteria":[]}
def test_added_modified_removed():
    result=compare_requirements([r("REQ-1","Search"),r("REQ-2","CSV")],[r("REQ-1","Search","changed"),r("REQ-3","Spanish")])
    assert result["counts"]=={"added":1,"modified":1,"removed":1}
def test_open_question():
    result=compare_requirements([], [r("REQ-1","AI",s="open_question")])
    assert len(result["unresolved"])==1
