"""
Utility functions and response helpers
"""
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# RESPONSE BUILDERS
# ============================================================================

def success_response(
    payload: Any,
    content: int = 1,
    message: Optional[str] = None,
    resource: Optional[str] = None,
    count: Optional[int] = None
) -> Dict:
    """
    Build standardized success response

    Args:
        payload: Response data
        content: 1 if has data, 0 if empty
        message: Optional message
        resource: Optional resource name
        count: Optional count of items

    Returns:
        Standardized response dict
    """
    header = {"status": "ok", "content": content}

    if resource:
        header["resource"] = resource
    if count is not None:
        header["count"] = count

    response = {"header": header, "payload": payload}

    if message:
        response["message"] = message

    return response


def empty_response(message: Optional[str] = None) -> Dict:
    """Build empty response"""
    return success_response([], content=0, message=message)


def created_response(rows_affected: int, message: str = "Registro insertado") -> Dict:
    """Build creation response"""
    return {
        "header": {"status": "ok", "insertedRows": rows_affected},
        "message": message if rows_affected > 0 else "No se insertó el registro"
    }


def updated_response(rows_affected: int, message: str = "Registro actualizado") -> Dict:
    """Build update response"""
    return {
        "header": {"status": "ok", "updatedRows": rows_affected},
        "message": message if rows_affected > 0 else "No se actualizó el registro"
    }


def deleted_response(rows_affected: int, message: str = "Registro eliminado") -> Dict:
    """Build delete response"""
    return {
        "header": {"status": "ok", "deletedRows": rows_affected},
        "message": message if rows_affected > 0 else "No se pudo eliminar el registro"
    }


# ============================================================================
# ORDER VALIDATION HELPERS
# ============================================================================

def check_order_exists(db: Session, order_id: str) -> bool:
    """
    Check if order exists in database

    Args:
        db: Database session
        order_id: Order ID to check

    Returns:
        True if exists, False otherwise
    """
    try:
        from sqlalchemy import text
        result = db.execute(
            text("CALL toolstock_amz.uSp_isExistOrder(:idOrder)"),
            {"idOrder": order_id}
        ).fetchall()

        return bool(result and len(result) > 0)
    except Exception as e:
        logger.error(f"Error checking order existence: {str(e)}")
        return False


def check_order_not_shipped(db: Session, order_id: str) -> bool:
    """
    Check if order has not been shipped yet

    Args:
        db: Database session
        order_id: Order ID to check

    Returns:
        True if not shipped, False if already shipped
    """
    try:
        from sqlalchemy import text
        result = db.execute(
            text("CALL toolstock_amz.uSp_isOrderNotShipped(:idOrder)"),
            {"idOrder": order_id}
        ).fetchall()

        return bool(result and len(result) > 0)
    except Exception as e:
        logger.error(f"Error checking order shipping status: {str(e)}")
        return False


def validate_order_for_shipment(db: Session, order_id: str) -> Optional[Dict]:
    """
    Validate order exists and is not shipped.
    Returns error response if validation fails, None if valid.

    Args:
        db: Database session
        order_id: Order ID to validate

    Returns:
        Error response dict if invalid, None if valid
    """
    if not check_order_exists(db, order_id):
        return empty_response("El pedido no existe")

    if not check_order_not_shipped(db, order_id):
        return empty_response("El pedido ya fue enviado")

    return None


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def execute_stored_procedure(
    db: Session,
    procedure_name: str,
    params: Optional[Dict] = None
) -> List[Dict]:
    """
    Execute stored procedure and return results as list of dicts

    Args:
        db: Database session
        procedure_name: Name of stored procedure
        params: Optional parameters

    Returns:
        List of result rows as dictionaries
    """
    try:
        if params:
            param_placeholders = ', '.join([f':{key}' for key in params.keys()])
            sql = f"CALL toolstock_amz.{procedure_name}({param_placeholders})"
        else:
            sql = f"CALL toolstock_amz.{procedure_name}()"

        from sqlalchemy import text
        result = db.execute(text(sql), params or {})
        rows = result.fetchall()

        if rows:
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]

        return []
    except Exception as e:
        logger.error(f"Error executing {procedure_name}: {str(e)}")
        raise


def execute_update(
    db: Session,
    query: str,
    params: Dict
) -> int:
    """
    Execute UPDATE/DELETE query and return affected rows

    Args:
        db: Database session
        query: SQL query
        params: Query parameters

    Returns:
        Number of affected rows
    """
    try:
        from sqlalchemy import text
        result = db.execute(text(query), params)
        db.commit()
        return result.rowcount
    except Exception as e:
        db.rollback()
        logger.error(f"Error executing update: {str(e)}")
        raise


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handle_database_error(e: Exception, operation: str, order_id: Optional[str] = None):
    """
    Handle database errors consistently

    Args:
        e: Exception that occurred
        operation: Description of operation
        order_id: Optional order ID for context

    Raises:
        HTTPException with 500 status
    """
    error_msg = f"Error in {operation}"
    if order_id:
        error_msg += f" for order {order_id}"

    logger.error(f"{error_msg}: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail="Error interno")


# ============================================================================
# DATA TRANSFORMATION
# ============================================================================

def group_orders_with_items(rows: List[Dict]) -> List[Dict]:
    """
    Group order data with their items.
    Replicates PHP groupOrdersWithItems logic.

    Args:
        rows: Raw database rows

    Returns:
        List of orders with nested items
    """
    if not rows:
        return []

    product_fields = [
        'orderItemId', 'sku', 'productName', 'quantityPurchased',
        'itemPrice', 'itemTax', 'shippingPrice', 'shippingTax',
        'vatExclusiveItemPrice', 'vatExclusiveShippingPrice',
        'asin', 'referenciaProv'
    ]

    grouped_orders = []
    processed_order_ids = {}

    for row in rows:
        # Convert SQLAlchemy Row to dict if needed
        if hasattr(row, '_mapping'):
            row = dict(row._mapping)

        order_id = row.get('amazonOrderId')

        # Extract product info
        product_info = {
            field: row.get(field)
            for field in product_fields
            if field in row
        }

        # First time seeing this order
        if order_id not in processed_order_ids:
            # Create order info without product fields
            order_info = {
                key: value
                for key, value in row.items()
                if key not in product_fields
            }

            # Add items array with first product
            order_info['items'] = [product_info]

            grouped_orders.append(order_info)
            processed_order_ids[order_id] = len(grouped_orders) - 1
        else:
            # Add product to existing order
            index = processed_order_ids[order_id]
            grouped_orders[index]['items'].append(product_info)

    return grouped_orders


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_column_name(column_name: str, allowed_columns: List[str]) -> bool:
    """
    Validate that column name is in allowed list

    Args:
        column_name: Column name to validate
        allowed_columns: List of allowed column names

    Returns:
        True if valid, False otherwise
    """
    return column_name in allowed_columns


# Allowed columns for shipment updates
ALLOWED_SHIPMENT_COLUMNS = [
    "servicio", "horario", "destinatario", "direccion", "pais",
    "cp", "poblacion", "telefono", "email", "departamento",
    "contacto", "observaciones", "bultos", "movil", "refC"
]
