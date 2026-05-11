#!/usr/bin/env python3
import os
import re
import sys

def audit_story(story_id, path):
    """审计单个 Story 目录"""
    if not os.path.exists(path):
        return f"目录缺失: {path}"
    
    missing_files = []
    for f in ["implementation_plan.md", "task.md", "walkthrough.md"]:
        if not os.path.exists(os.path.join(path, f)):
            missing_files.append(f)
    
    if missing_files:
        return f"缺失文档: {', '.join(missing_files)}"
    
    # 深入审计内容
    with open(os.path.join(path, "implementation_plan.md"), 'r') as f:
        plan_content = f.read()
        if "激活角色" not in plan_content:
            return "实施计划缺失角色声明"
            
    with open(os.path.join(path, "walkthrough.md"), 'r') as f:
        wt_content = f.read()
        if "TRUTH_EXTRACT" not in wt_content and "Automated Evidence" not in wt_content:
            return "验收报告缺失物理真源证据"
            
    return "OK"

def main():
    feedback_file = "docs/IMPLEMENTATION_FEEDBACK.md"
    if not os.path.exists(feedback_file):
        print(f"Error: {feedback_file} not found.")
        sys.exit(1)

    print("--- Workflow Compliance Audit ---")
    
    with open(feedback_file, 'r') as f:
        content = f.read()
        # 匹配反馈表中的路径行
        stories = re.findall(r'\| (E\d+-S\d+) \| .*? \| (docs/.*?) \| DONE \|', content)

    total = len(stories)
    passed = 0
    
    for story_id, path in stories:
        result = audit_story(story_id, path.strip())
        if result == "OK":
            passed += 1
            print(f"✅ {story_id}: Pass")
        else:
            print(f"❌ {story_id}: {result}")

    print(f"\nAudit Summary: {passed}/{total} Stories are compliant.")
    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    main()
