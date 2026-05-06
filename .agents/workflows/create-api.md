---
description: 根据表名或SQL自动生成API接口 (命令: /create-api)
---

# Create API Workflow

This workflow triggers the `MySQL to API` skill to generate FastAPI endpoints.

1.  **Check Input**: If the user hasn't provided a table name or SQL, ask for it.
2.  **Load Skill**: Read `.agent/skills/mysql_to_api/SKILL.md` to understand the full lifecycle requirements.
3.  **Execute**: Follow the skill's "Workflow Steps" exactly:
    - **Inspect**: Run DB Schema inspection.
    - **Develop**: Generate Model, Service, and Router files.
    - **Integrate**: Register the router in `main.py`.
    - **Verify (QC)**: Run automated tests and health checks.
    - **Repair**: If verification fails, diagnose and fix until passed.
    - **Finalize**: Generate documentation and commit changes (Git).

