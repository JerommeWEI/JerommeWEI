import json
import re
from pathlib import Path
from collections import Counter

DATA_FILE = Path(__file__).parent / "patents_data.json"
SKILLS_FILE = Path(__file__).parent / "skills_tree.json"

DESIGN_SOFTWARE = {
    "SolidWorks": ["solidworks", "solid works", "sw"],
    "ZEMAX": ["zemax", "opticstudio"],
    "CodeV": ["codev", "code v", "code-v"],
    "Macleod": ["macleod", "mac leod", "essential macleod"],
    "TFCal": ["tfcal", "tf cal"],
    "AutoCAD": ["autocad", "auto cad"],
    "ProE": ["proe", "pro/e", "pro engineer", "creo"],
    "ANSYS": ["ansys"],
    "COMSOL": ["comsol"],
    "LightTools": ["lighttools", "light tools"],
    "TracePro": ["tracepro", "trace pro"],
    "OSLO": ["oslo"],
    "Zemax OpticStudio": ["zemax opticstudio", "opticstudio"],
}

TECH_KEYWORDS = {
    "光学设计": ["光学设计", "optical design", "lens design", "镜头设计", "lens", "透镜", "镜片"],
    "薄膜设计": ["薄膜设计", "thin film", "coating design", "膜系设计", "镀膜", "coating"],
    "机械设计": ["机械设计", "mechanical design", "结构设计", "structural design", "结构", "structure", "mirror", "反射镜", "reflect"],
    "激光技术": ["激光", "laser", "光束", "beam", "lidar", "radar"],
    "精密测量": ["精密测量", "precision measurement", "测量系统", "measurement system", "ranging", "测距"],
    "光学系统": ["光学系统", "optical system", "成像系统", "imaging system", "receiving system", "transmitting system"],
    "光谱分析": ["光谱", "spectrum", "spectral", "分光", "beam splitter"],
    "光电子": ["光电子", "optoelectronic", "光电", "photoelectric", "photodetector", "detector"],
    "信号处理": ["信号处理", "signal processing", "数据处理", "control method"],
    "仿真分析": ["仿真", "simulation", "模拟", "analysis"],
    "三维建模": ["三维建模", "3d modeling", "cad", "建模", "device", "apparatus"],
    "像差分析": ["像差", "aberration", "光学性能"],
    "光路设计": ["光路", "optical path", "光束路径", "scanning"],
    "成像质量": ["成像质量", "image quality", "mtf", "分辨率"],
}

SKILL_CATEGORIES = {
    "光学设计软件": ["ZEMAX", "CodeV", "LightTools", "TracePro", "OSLO"],
    "薄膜设计软件": ["Macleod", "TFCal"],
    "机械设计软件": ["SolidWorks", "AutoCAD", "ProE"],
    "仿真分析软件": ["ANSYS", "COMSOL"],
    "编程语言": ["Python", "MATLAB"],
}

def load_patents():
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        print("Please run fetch_patents.py first.")
        return []
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_software_mentions(patents):
    software_found = Counter()
    software_contexts = {}
    
    for patent in patents:
        title = patent.get("title", "").lower()
        abstract = patent.get("abstract", "").lower()
        full_text = f"{title} {abstract}"
        
        for software, keywords in DESIGN_SOFTWARE.items():
            for keyword in keywords:
                if keyword in full_text:
                    software_found[software] += 1
                    if software not in software_contexts:
                        software_contexts[software] = []
                    software_contexts[software].append({
                        "patent_id": patent.get("patent_id", ""),
                        "title": patent.get("title", ""),
                    })
                    break
    
    return software_found, software_contexts

def extract_tech_skills(patents):
    skills_found = Counter()
    skill_contexts = {}
    
    for patent in patents:
        title = patent.get("title", "")
        abstract = patent.get("abstract", "")
        full_text = f"{title} {abstract}".lower()
        
        for skill, keywords in TECH_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in full_text:
                    skills_found[skill] += 1
                    if skill not in skill_contexts:
                        skill_contexts[skill] = []
                    skill_contexts[skill].append({
                        "patent_id": patent.get("patent_id", ""),
                        "title": patent.get("title", ""),
                    })
                    break
    
    return skills_found, skill_contexts

def build_skill_tree(software_skills, tech_skills):
    skill_tree = {
        "设计软件工具": {},
        "技术领域": {},
        "技能分类": {}
    }
    
    for software, count in software_skills.most_common():
        for category, items in SKILL_CATEGORIES.items():
            if software in items:
                if category not in skill_tree["设计软件工具"]:
                    skill_tree["设计软件工具"][category] = []
                skill_tree["设计软件工具"][category].append({
                    "name": software,
                    "count": count,
                    "level": "精通" if count >= 5 else "熟练" if count >= 2 else "了解"
                })
                break
    
    for skill, count in tech_skills.most_common():
        skill_tree["技术领域"][skill] = {
            "count": count,
            "level": "精通" if count >= 10 else "熟练" if count >= 5 else "了解"
        }
    
    return skill_tree

def generate_summary(software_skills, tech_skills, software_contexts, tech_contexts, patents_count):
    summary = {
        "summary": {
            "total_patents_analyzed": patents_count,
            "software_tools_found": len(software_skills),
            "tech_skills_found": len(tech_skills),
        },
        "design_software": [
            {
                "name": software,
                "count": count,
                "level": "精通" if count >= 5 else "熟练" if count >= 2 else "了解",
                "patents": software_contexts.get(software, [])[:3]
            }
            for software, count in software_skills.most_common()
        ],
        "technical_skills": [
            {
                "name": skill,
                "count": count,
                "level": "精通" if count >= 10 else "熟练" if count >= 5 else "了解",
                "patents": tech_contexts.get(skill, [])[:3]
            }
            for skill, count in tech_skills.most_common()
        ],
        "skill_tree": build_skill_tree(software_skills, tech_skills)
    }
    
    return summary

def infer_software_from_patents(patents):
    software_inferred = Counter()
    software_reasons = {}
    
    for patent in patents:
        title = patent.get("title", "").lower()
        abstract = patent.get("abstract", "").lower()
        full_text = f"{title} {abstract}"
        
        if any(kw in full_text for kw in ["lens", "optical system", "receiving system", "transmitting", "laser radar", "lidar", "beam", "mirror", "reflective", "透镜", "光学系统", "激光雷达", "反射镜", "光束", "scanning"]):
            software_inferred["ZEMAX"] += 1
            if "ZEMAX" not in software_reasons:
                software_reasons["ZEMAX"] = []
            software_reasons["ZEMAX"].append(f"光学系统设计: {patent.get('title', '')[:50]}")
        
        if any(kw in full_text for kw in ["lens design", "镜头设计", "imaging", "成像", "aberration", "像差"]):
            software_inferred["CodeV"] += 1
            if "CodeV" not in software_reasons:
                software_reasons["CodeV"] = []
            software_reasons["CodeV"].append(f"镜头设计与像差分析: {patent.get('title', '')[:50]}")
        
        if any(kw in full_text for kw in ["thin film", "coating", "薄膜", "镀膜", "膜系", "spectral", "光谱"]):
            software_inferred["Macleod"] += 1
            if "Macleod" not in software_reasons:
                software_reasons["Macleod"] = []
            software_reasons["Macleod"].append(f"薄膜设计: {patent.get('title', '')[:50]}")
            software_inferred["TFCal"] += 1
            if "TFCal" not in software_reasons:
                software_reasons["TFCal"] = []
            software_reasons["TFCal"].append(f"薄膜与光谱分析: {patent.get('title', '')[:50]}")
        
        if any(kw in full_text for kw in ["device", "apparatus", "system", "structure", "mechanical", "结构", "装置", "设备", "mirror base", "connecting bridge", "extinction member"]):
            software_inferred["SolidWorks"] += 1
            if "SolidWorks" not in software_reasons:
                software_reasons["SolidWorks"] = []
            software_reasons["SolidWorks"].append(f"机械结构设计: {patent.get('title', '')[:50]}")
        
        if any(kw in full_text for kw in ["photolithography", "光刻", "projection", "照明系统", "illumination system"]):
            software_inferred["LightTools"] += 1
            if "LightTools" not in software_reasons:
                software_reasons["LightTools"] = []
            software_reasons["LightTools"].append(f"照明与投影系统设计: {patent.get('title', '')[:50]}")
    
    return software_inferred, software_reasons

def main():
    patents = load_patents()
    
    if not patents:
        print("No patents to analyze.")
        print("\nTo fetch patents, run:")
        print("  python fetch_patents.py")
        return None
    
    print(f"Analyzing {len(patents)} patents for skills and software...")
    
    software_skills, software_contexts = extract_software_mentions(patents)
    tech_skills, tech_contexts = extract_tech_skills(patents)
    inferred_software, inferred_reasons = infer_software_from_patents(patents)
    
    for software, count in inferred_software.items():
        if software not in software_skills:
            software_skills[software] = count
            software_contexts[software] = [{"patent_id": "推断", "title": reason} for reason in inferred_reasons[software][:3]]
    
    summary = generate_summary(software_skills, tech_skills, software_contexts, tech_contexts, len(patents))
    
    with open(SKILLS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Skills & Software Analysis ===")
    print(f"\n设计软件工具 (Design Software):")
    for software, count in software_skills.most_common():
        level = "精通" if count >= 5 else "熟练" if count >= 2 else "了解"
        print(f"  - {software}: {count}次 ({level})")
    
    print(f"\n技术领域 (Technical Skills):")
    for skill, count in tech_skills.most_common()[:10]:
        level = "精通" if count >= 10 else "熟练" if count >= 5 else "了解"
        print(f"  - {skill}: {count}次 ({level})")
    
    print(f"\nSkills tree saved to: {SKILLS_FILE}")
    
    return summary

if __name__ == "__main__":
    main()
