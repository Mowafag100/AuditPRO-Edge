import structlog
import logging
import sys
from datetime import datetime

def configure_logging():
    """تكوين التسجيل المنظم باستخدام structlog"""
    
    # إعداد معالج (processor) لإضافة الوقت والمستوى
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # إعداد معالج (handler) لكتابة السجلات إلى stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    # إعداد الـ root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # تعطيل سجلات المكتبات الخارجية المزعجة
    for lib in ["httpx", "httpcore", "uvicorn", "uvicorn.access", "uvicorn.error"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
