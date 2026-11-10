"""Extração e análise de evidências do repositório/código para roteirização.

Garante a regra fundamental:
"Construa uma narrativa baseada em evidências do código. Não invente funcionalidades."
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List

def analyze_repo_evidence(repo_path: str | Path) -> Dict[str, Any]:
    """Analisa o repositório local e extrai fatos concretos comprovados."""
    root = Path(repo_path)
    if not root.exists():
        return {"error": f"Caminho não encontrado: {repo_path}"}
    
    evidence = {
        "project_name": root.name,
        "description": "",
        "main_language": "unknown",
        "tech_stack": [],
        "features": [],
        "cli_commands": [],
        "files_sampled": [],
    }
    
    # 1. Procurar README.md
    readme_candidates = list(root.glob("README*.md")) + list(root.glob("readme*.md"))
    if readme_candidates:
        readme_file = readme_candidates[0]
        content = readme_file.read_text(encoding="utf-8", errors="ignore")
        evidence["files_sampled"].append(readme_file.name)
        
        # Pega título e primeiro parágrafo
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        for l in lines:
            if l.startswith("# ") and not evidence["description"]:
                evidence["project_name"] = l.lstrip("# ").strip()
            elif not l.startswith("#") and not l.startswith("!") and not l.startswith("[") and not evidence["description"]:
                evidence["description"] = l
                
        # Procura bullet points de funcionalidades
        bullet_matches = re.findall(r"^[-*]\s+\*\*?([^\n:*]+)\*\*?:?\s*(.*)$", content, flags=re.MULTILINE)
        for name, desc in bullet_matches[:8]:
            feat = f"{name.strip()}: {desc.strip()}".strip(" :")
            if feat and len(feat) > 5:
                evidence["features"].append(feat)
                
    # 2. Identificar package.json / pyproject.toml / requirements.txt / Cargo.toml
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            evidence["tech_stack"].append("Node.js")
            if "name" in pkg and not evidence["description"]:
                evidence["project_name"] = pkg["name"]
            if "description" in pkg and pkg["description"]:
                evidence["description"] = pkg["description"]
            deps = list(pkg.get("dependencies", {}).keys()) + list(pkg.get("devDependencies", {}).keys())
            for d in ["react", "vue", "typescript", "express", "tailwind", "next", "vite"]:
                if any(d in dep.lower() for dep in deps):
                    evidence["tech_stack"].append(d.capitalize())
        except Exception:
            pass

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        evidence["tech_stack"].append("Python")

    # 3. Detectar SKILL.md se for uma skill
    if (root / "SKILL.md").exists():
        content = (root / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
        evidence["tech_stack"].append("Antigravity / Agent Skill")
        skill_name = re.search(r"^name:\s*(.*)$", content, re.MULTILINE)
        if skill_name:
            evidence["project_name"] = skill_name.group(1).strip()
        skill_desc = re.search(r"^description:\s*(.*)$", content, re.MULTILINE)
        if skill_desc:
            evidence["description"] = skill_desc.group(1).strip()
            
    evidence["tech_stack"] = sorted(list(set(evidence["tech_stack"])))
    return evidence

