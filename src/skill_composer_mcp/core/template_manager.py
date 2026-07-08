"""
TemplateManager - 组合模板管理器
保存/加载常用组合模板
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from loguru import logger

from ..models import Template


class TemplateManager:
    """模板管理器"""

    def __init__(self, templates_dir: str = "~/.composed_skills/templates"):
        self._templates_dir = Path(os.path.expanduser(templates_dir))
        self._templates_dir.mkdir(parents=True, exist_ok=True)

    def save_template(
        self,
        name: str,
        base_skill: str,
        additions: list[str],
        description: str = "",
    ) -> Template:
        """保存组合模板"""
        template = Template(
            name=name,
            base_skill=base_skill,
            additions=additions,
            created_at=datetime.now(),
            description=description,
        )

        file_path = self._templates_dir / f"{name}.json"
        file_path.write_text(
            template.model_dump_json(indent=2), encoding="utf-8"
        )
        logger.info(f"模板已保存: {file_path}")
        return template

    def load_template(self, name: str) -> Template | None:
        """加载模板"""
        file_path = self._templates_dir / f"{name}.json"
        if not file_path.exists():
            # 模糊匹配
            for f in self._templates_dir.glob("*.json"):
                if name.lower() in f.stem.lower():
                    file_path = f
                    break
            else:
                logger.warning(f"模板不存在: {name}")
                return None

        data = json.loads(file_path.read_text(encoding="utf-8"))
        return Template(**data)

    def list_templates(self) -> list[dict[str, str]]:
        """列出所有模板"""
        templates: list[dict[str, str]] = []
        for f in sorted(self._templates_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                templates.append(
                    {
                        "name": data.get("name", f.stem),
                        "base_skill": data.get("base_skill", ""),
                        "additions": ", ".join(data.get("additions", [])),
                        "description": data.get("description", ""),
                        "created_at": data.get("created_at", ""),
                    }
                )
            except Exception as e:
                logger.warning(f"读取模板 {f} 失败: {e}")
        return templates

    def delete_template(self, name: str) -> bool:
        """删除模板"""
        file_path = self._templates_dir / f"{name}.json"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"模板已删除: {name}")
            return True

        # 模糊匹配删除
        for f in self._templates_dir.glob("*.json"):
            if name.lower() in f.stem.lower():
                f.unlink()
                return True

        return False
