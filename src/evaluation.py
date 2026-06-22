import re
from typing import List, Dict

def extract_key_points(text: str) -> List[str]:
    """استخراج النقاط الرئيسية من تحليل Ollama"""
    # نمط بسيط للبحث عن نقاط المخاطر والتوصيات
    risks = re.findall(r'risks["\s:]*\[([^\]]*)\]', text, re.IGNORECASE)
    recommendations = re.findall(r'recommendations["\s:]*\[([^\]]*)\]', text, re.IGNORECASE)
    points = []
    for r in risks:
        points.extend([p.strip().strip('"\'') for p in r.split(',') if p.strip()])
    for rec in recommendations:
        points.extend([p.strip().strip('"\'') for p in rec.split(',') if p.strip()])
    return points

def calculate_precision_recall(predicted: List[str], reference: List[str]) -> Dict:
    """حساب الدقة والاستدعاء (precision/recall) لمقارنة النقاط المستخلصة"""
    if not reference:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    # بافتراض أن النقاط المتطابقة هي التي تظهر في كلا القائمتين (تطابق نصي بسيط)
    # يمكن تحسينها باستخدام تضمينات أو تشابه دلالي
    pred_set = set(predicted)
    ref_set = set(reference)
    common = pred_set.intersection(ref_set)
    precision = len(common) / len(pred_set) if pred_set else 0.0
    recall = len(common) / len(ref_set) if ref_set else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}

def evaluate_analysis(analysis: dict, reference_text: str) -> dict:
    """
    تقييم تحليل العقد مقابل نص مرجعي معروف النتائج.
    assumes analysis يحتوي على 'risks' و 'recommendations'
    """
    predicted_points = analysis.get("risks", []) + analysis.get("recommendations", [])
    # استخراج النقاط المرجعية من النص المرجعي (بافتراض أنه يحتوي على قوائم)
    ref_points = extract_key_points(reference_text)
    metrics = calculate_precision_recall(predicted_points, ref_points)
    return {
        "score": analysis.get("score", 0),
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "predicted_count": len(predicted_points),
        "reference_count": len(ref_points)
    }
