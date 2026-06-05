"""Azure Functions v2 entry point — registers all blueprints."""
import azure.functions as func

from src.functions.webhook_handler.function import bp as webhook_bp
from src.functions.predict_trigger.function import bp as predict_bp
from src.functions.diagnose_trigger.function import bp as diagnose_bp
from src.functions.act_trigger.function import bp as act_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(webhook_bp)
app.register_functions(predict_bp)
app.register_functions(diagnose_bp)
app.register_functions(act_bp)
