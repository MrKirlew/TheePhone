# main.py - Simplified version for testing
import functions_framework
from flask import jsonify

@functions_framework.http
def multimodal_agent_orchestrator(request):
    """
    Simple test version of the orchestrator
    """
    if request.method != 'POST':
        return 'Method Not Allowed', 405
    
    return jsonify({
        "status": "success",
        "message": "Function is working!"
    }), 200