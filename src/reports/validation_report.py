import sys
import json
import time
from pathlib import Path
from src.utils.logger import get_logger
from src.utils.config_loader import load_global_config

logger = get_logger("validation_report")

def generate_report(version_id: str) -> str:
    """
    Merges data validator JSON logs and cleaning action logs
    to render a comprehensive Markdown audit report for version control.
    """
    logger.info(f"Generating Markdown audit report for pipeline version: {version_id}")
    
    project_root = Path(__file__).resolve().parent.parent.parent
    logs_dir = project_root / "data" / "logs"
    
    val_json_path = logs_dir / "latest_validation_report.json"
    clean_json_path = logs_dir / "cleaning_log.json"
    
    if not val_json_path.exists():
        err_msg = f"Latest validation JSON report not found at {val_json_path}."
        logger.error(err_msg)
        return ""
        
    try:
        with open(val_json_path, 'r', encoding='utf-8') as f:
            val_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read validation JSON report: {e}")
        raise e
        
    cleaning_data = []
    if clean_json_path.exists():
        try:
            with open(clean_json_path, 'r', encoding='utf-8') as f:
                cleaning_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read cleaning log JSON: {e}")
            
    # Formulate Markdown structure
    md = []
    md.append(f"# QuantEngine Pipeline Audit Report - Version {version_id}")
    md.append(f"**Execution Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Overall Status**: {val_data['summary']['status']}\n")
    
    md.append("## 1. Summary Statistics")
    md.append(f"- **Total Rows Evaluated**: {val_data['summary']['total_rows']}")
    md.append(f"- **Failed Validation Categories**: {val_data['summary']['issues_count']}\n")
    
    md.append("## 2. Integrity Checks Breakdown")
    md.append("| Validation Category | Status | Error Count | Details / Affected Columns |")
    md.append("| :--- | :--- | :--- | :--- |")
    
    for check_name, info in val_data["checks"].items():
        status = info["status"]
        count = info["count"]
        details = info["details"]
        
        # Format details text
        if isinstance(details, dict):
            details_str = ", ".join([f"'{k}': {v} gaps" for k, v in details.items()])
        elif isinstance(details, list):
            if len(details) > 0:
                details_str = "; ".join([str(x) for x in details[:3]])
                if len(details) > 3:
                    details_str += f" and {len(details) - 3} more dates"
            else:
                details_str = "None"
        else:
            details_str = str(details)
            
        status_md = f"**{status}**" if status == "PASS" else f"`{status}`"
        md.append(f"| {check_name.upper()} | {status_md} | {count} | {details_str if count > 0 else 'None'} |")
        
    md.append("\n## 3. Automated Cleaning Adjustments Log")
    if not cleaning_data:
        md.append("No automated cleaning adjustments were required for this run.")
    else:
        md.append("| Preprocessing Stage | Clean Operation | Impact Details |")
        md.append("| :--- | :--- | :--- |")
        for log_item in cleaning_data:
            stage = log_item.get("stage", "unknown").upper()
            action = log_item.get("action", "")
            
            # Format row logs differently depending on schema
            if "date" in log_item:
                details_str = f"Date: {log_item['date']} | Before: {log_item.get('before')} | After: {log_item.get('after')}"
                md.append(f"| {stage} | {action} | {details_str} |")
            else:
                impact = log_item.get("impact", "")
                details = log_item.get("details", {})
                md.append(f"| {stage} | {action} - {impact} | {details} |")
                
    md_str = "\n".join(md)
    report_file = logs_dir / f"validation_report_{version_id}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md_str)
        
    logger.info(f"Markdown audit report generated successfully at: {report_file}")
    return str(report_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python validation_report.py <version_id>")
        sys.exit(1)
    generate_report(sys.argv[1])
