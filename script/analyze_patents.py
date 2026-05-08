import json
import re
from collections import Counter
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent / "patents_data.json"
ANALYSIS_FILE = Path(__file__).parent / "analysis_results.json"

IPC_FIELDS = {
    "A": ("Human Necessities", "人类生活需要"),
    "B": ("Performing Operations; Transporting", "作业；运输"),
    "C": ("Chemistry; Metallurgy", "化学；冶金"),
    "D": ("Textiles; Paper", "纺织；造纸"),
    "E": ("Fixed Constructions", "固定建筑物"),
    "F": ("Mechanical Engineering; Lighting; Heating; Weapons; Blasting", "机械工程；照明；加热；武器；爆破"),
    "G": ("Physics", "物理"),
    "H": ("Electricity", "电学"),
}


def load_patents():
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        print("Please run fetch_patents.py first.")
        return []
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_year(date_str):
    if not date_str:
        return None
    match = re.search(r'(\d{4})', str(date_str))
    if match:
        year = int(match.group(1))
        if 1990 <= year <= datetime.now().year + 1:
            return year
    return None


def analyze_patents(patents):
    analysis = {
        "total_count": len(patents),
        "by_year": {},
        "by_assignee": {},
        "by_ipc_field": {},
        "by_status": {
            "granted": 0,
            "pending": 0,
            "unknown": 0
        },
        "years_range": {"min": None, "max": None},
        "assignees": [],
        "technical_fields": [],
        "timeline": [],
    }
    
    years = []
    
    for patent in patents:
        year = extract_year(patent.get("publication_date") or patent.get("filing_date"))
        if year:
            years.append(year)
            analysis["by_year"][year] = analysis["by_year"].get(year, 0) + 1
        
        assignee = patent.get("assignee", "").strip()
        if assignee:
            analysis["by_assignee"][assignee] = analysis["by_assignee"].get(assignee, 0) + 1
        
        ipc_codes = patent.get("ipc_codes", [])
        for code in ipc_codes:
            if code:
                main_class = code[0].upper() if len(code) > 0 else None
                if main_class and main_class in IPC_FIELDS:
                    analysis["by_ipc_field"][main_class] = analysis["by_ipc_field"].get(main_class, 0) + 1
        
        patent_id = patent.get("patent_id", "")
        if patent_id:
            if "A" in patent_id.upper() and not any(x in patent_id.upper() for x in ["B", "C"]):
                analysis["by_status"]["pending"] += 1
            elif any(x in patent_id.upper() for x in ["B", "C"]):
                analysis["by_status"]["granted"] += 1
            else:
                analysis["by_status"]["unknown"] += 1
        else:
            analysis["by_status"]["unknown"] += 1
    
    if years:
        analysis["years_range"]["min"] = min(years)
        analysis["years_range"]["max"] = max(years)
        
        for year in range(min(years), max(years) + 1):
            analysis["timeline"].append({
                "year": year,
                "count": analysis["by_year"].get(year, 0)
            })
    
    analysis["assignees"] = sorted(
        [{"name": k, "count": v} for k, v in analysis["by_assignee"].items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]
    
    for code, count in sorted(analysis["by_ipc_field"].items(), key=lambda x: x[1], reverse=True):
        if code in IPC_FIELDS:
            analysis["technical_fields"].append({
                "code": code,
                "name_en": IPC_FIELDS[code][0],
                "name_cn": IPC_FIELDS[code][1],
                "count": count
            })
    
    return analysis


def generate_summary(analysis):
    summary = {
        "total_patents": analysis["total_count"],
        "granted": analysis["by_status"]["granted"],
        "pending": analysis["by_status"]["pending"],
        "year_range": f"{analysis['years_range']['min']}-{analysis['years_range']['max']}" if analysis['years_range']['min'] else "N/A",
        "top_assignees": analysis["assignees"][:5],
        "technical_fields": analysis["technical_fields"][:5],
        "timeline": analysis["timeline"],
    }
    return summary


def main():
    patents = load_patents()
    
    if not patents:
        print("No patents to analyze.")
        return None
    
    print(f"Analyzing {len(patents)} patents...")
    
    analysis = analyze_patents(patents)
    summary = generate_summary(analysis)
    
    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Patent Analysis Results ===")
    print(f"Total Patents: {analysis['total_count']}")
    print(f"Granted: {analysis['by_status']['granted']}")
    print(f"Pending: {analysis['by_status']['pending']}")
    print(f"Year Range: {summary['year_range']}")
    
    print(f"\nTop Assignees:")
    for a in analysis["assignees"][:5]:
        print(f"  - {a['name']}: {a['count']}")
    
    print(f"\nTechnical Fields:")
    for field in analysis["technical_fields"][:5]:
        print(f"  - {field['code']}: {field['name_en']} ({field['count']})")
    
    print(f"\nTimeline:")
    for item in analysis["timeline"]:
        print(f"  {item['year']}: {item['count']} patents")
    
    print(f"\nAnalysis saved to: {ANALYSIS_FILE}")
    
    return analysis


if __name__ == "__main__":
    main()
