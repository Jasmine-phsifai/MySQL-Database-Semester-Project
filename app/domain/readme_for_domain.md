# readme_for_domain

M1 阶段为空; M2 用于放业务实体 dataclass + 校验函数 (PNP 16 学分上限校验、A/A+ 30% 上限计算等跨表规则).

调用方向: `backend.repos.generic` (M2 改造为返回 dataclass) 与 `backend.services.*` (M2 新建).
