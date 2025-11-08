"""
Symbol mapping API routes for admin management.
"""
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile

from api_gateway.middleware import require_auth, require_role
from api_gateway.symbol_mapping_service import SymbolMappingServiceAPI


logger = logging.getLogger(__name__)

symbol_mapping_bp = Blueprint('symbol_mapping', __name__, url_prefix='/api/symbol-mappings')


@symbol_mapping_bp.route('/upload', methods=['POST'])
@require_auth
@require_role(['admin'])
def upload_symbol_mappings():
    """
    Upload symbol mappings from CSV file (Admin only).
    
    Request:
        - file: CSV file with symbol mappings
        - broker_name: Name of the broker
    
    Response:
        {
            "success": true,
            "loaded": 50,
            "failed": 2,
            "errors": ["error1", "error2"]
        }
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        broker_name = request.form.get('broker_name')
        
        if not broker_name:
            return jsonify({"error": "broker_name is required"}), 400
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "File must be a CSV"}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        
        try:
            file.save(temp_path)
            
            # Load mappings
            service = SymbolMappingServiceAPI()
            result = service.load_mappings_from_csv(broker_name, temp_path)
            
            return jsonify(result), 200 if result['success'] else 400
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"Failed to upload symbol mappings: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_mapping_bp.route('/<broker_name>', methods=['GET'])
@require_auth
@require_role(['admin', 'trader'])
def get_broker_mappings(broker_name: str):
    """
    Get all symbol mappings for a broker.
    
    Response:
        {
            "broker_name": "Angel One",
            "mappings": [
                {
                    "standard_symbol": "RELIANCE",
                    "broker_symbol": "RELIANCE-EQ",
                    "broker_token": "2885",
                    "exchange": "NSE",
                    "instrument_type": "EQ",
                    "lot_size": 1,
                    "tick_size": 0.05
                }
            ]
        }
    """
    try:
        service = SymbolMappingServiceAPI()
        mappings = service.get_all_mappings(broker_name)
        
        return jsonify({
            "broker_name": broker_name,
            "mappings": [
                {
                    "standard_symbol": m.standard_symbol,
                    "broker_symbol": m.broker_symbol,
                    "broker_token": m.broker_token,
                    "exchange": m.exchange,
                    "instrument_type": m.instrument_type,
                    "lot_size": m.lot_size,
                    "tick_size": float(m.tick_size)
                }
                for m in mappings
            ]
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get broker mappings: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_mapping_bp.route('/<broker_name>/<standard_symbol>', methods=['GET'])
@require_auth
def get_symbol_mapping(broker_name: str, standard_symbol: str):
    """
    Get specific symbol mapping details.
    
    Response:
        {
            "standard_symbol": "RELIANCE",
            "broker_symbol": "RELIANCE-EQ",
            "broker_token": "2885",
            "exchange": "NSE",
            "instrument_type": "EQ",
            "lot_size": 1,
            "tick_size": 0.05
        }
    """
    try:
        service = SymbolMappingServiceAPI()
        mapping = service.get_mapping_details(broker_name, standard_symbol)
        
        if not mapping:
            return jsonify({"error": "Mapping not found"}), 404
        
        return jsonify({
            "standard_symbol": mapping.standard_symbol,
            "broker_symbol": mapping.broker_symbol,
            "broker_token": mapping.broker_token,
            "exchange": mapping.exchange,
            "instrument_type": mapping.instrument_type,
            "lot_size": mapping.lot_size,
            "tick_size": float(mapping.tick_size)
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to get symbol mapping: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_mapping_bp.route('/<broker_name>/<standard_symbol>/validate', methods=['GET'])
@require_auth
def validate_symbol(broker_name: str, standard_symbol: str):
    """
    Validate if a symbol exists in the mapping.
    
    Response:
        {
            "valid": true,
            "broker_token": "2885"
        }
    """
    try:
        service = SymbolMappingServiceAPI()
        is_valid = service.validate_symbol(broker_name, standard_symbol)
        
        if is_valid:
            broker_token = service.get_broker_symbol(broker_name, standard_symbol)
            return jsonify({
                "valid": True,
                "broker_token": broker_token
            }), 200
        else:
            return jsonify({
                "valid": False,
                "error": f"Symbol {standard_symbol} not found for broker {broker_name}"
            }), 404
    
    except Exception as e:
        logger.error(f"Failed to validate symbol: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_mapping_bp.route('/<broker_name>/<standard_symbol>', methods=['DELETE'])
@require_auth
@require_role(['admin'])
def delete_symbol_mapping(broker_name: str, standard_symbol: str):
    """
    Delete a symbol mapping (Admin only).
    
    Response:
        {
            "success": true,
            "message": "Mapping deleted successfully"
        }
    """
    try:
        service = SymbolMappingServiceAPI()
        success = service.delete_mapping(broker_name, standard_symbol)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Mapping deleted successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Mapping not found"
            }), 404
    
    except Exception as e:
        logger.error(f"Failed to delete symbol mapping: {e}")
        return jsonify({"error": str(e)}), 500


@symbol_mapping_bp.route('/<broker_name>', methods=['DELETE'])
@require_auth
@require_role(['admin'])
def clear_broker_mappings(broker_name: str):
    """
    Clear all mappings for a broker (Admin only).
    
    Response:
        {
            "success": true,
            "message": "All mappings cleared for broker"
        }
    """
    try:
        service = SymbolMappingServiceAPI()
        success = service.clear_broker_mappings(broker_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"All mappings cleared for {broker_name}"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to clear mappings"
            }), 500
    
    except Exception as e:
        logger.error(f"Failed to clear broker mappings: {e}")
        return jsonify({"error": str(e)}), 500
