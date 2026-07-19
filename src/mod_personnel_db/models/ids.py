"""不透明なID型。docs/api/models.md#id型 に対応する。"""

from typing import NewType

CandidateId = NewType("CandidateId", int)
PersonnelSectionId = NewType("PersonnelSectionId", int)
GoldRecordId = NewType("GoldRecordId", int)
KnowledgeItemId = NewType("KnowledgeItemId", int)
PdfId = NewType("PdfId", int)
DocumentId = NewType("DocumentId", int)
JobId = NewType("JobId", int)
ParserVersionId = NewType("ParserVersionId", int)
LayoutId = NewType("LayoutId", int)
ExportId = NewType("ExportId", int)
ReviewSessionId = NewType("ReviewSessionId", int)
ReviewItemId = NewType("ReviewItemId", int)
LearningRecordId = NewType("LearningRecordId", int)
