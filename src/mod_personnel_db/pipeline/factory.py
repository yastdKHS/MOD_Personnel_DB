"""PipelineBuilderの生成のみを責務とする。"""

from mod_personnel_db.pipeline.builder import PipelineBuilder


class PipelineFactory:
    @staticmethod
    def create_builder() -> PipelineBuilder:
        return PipelineBuilder()
