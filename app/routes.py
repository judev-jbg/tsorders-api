"""
API Routes - All endpoints for TS Orders API (REFACTORED)
Protected by JWT Authentication
"""
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.auth import get_current_user
from app.services import OrderService, GLSService
from app.schemas import (
    UpdateStockFlag,
    UpdateFakeFlag,
    ShipmentData,
    UpdateShipment,
    DeleteShipment,
    RegisterShipment
)
from app.utils import (
    success_response,
    empty_response,
    created_response,
    updated_response,
    deleted_response,
    check_order_exists,
    check_order_not_shipped,
    handle_database_error
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ORDER ENDPOINTS
# ============================================================================

@router.get("/order/{order_id}", tags=["Orders"])
async def get_order_by_id(
    order_id: str = Path(..., description="Amazon Order ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get order details by ID.

    **Migrated from PHP**: `GET /order/{id}`
    """
    try:
        logger.info(f"Fetching order: {order_id}")

        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedByOrderId",
            {"id": order_id}
        )

        if result:
            return success_response(result)
        else:
            return empty_response()

    except Exception as e:
        return handle_database_error(e, f"fetching order {order_id}")


# ============================================================================
# ORDERS PENDING ENDPOINTS
# ============================================================================

@router.get("/orderspending", tags=["Orders Pending"])
@router.get("/orderspending/", tags=["Orders Pending"])
async def get_orders_pending(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all pending orders."""
    try:
        logger.info("Fetching all pending orders")

        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshipped"
        )

        return success_response(result, resource="orderspending", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching pending orders")


@router.get("/orderspending/untiltoday", tags=["Orders Pending"])
async def get_orders_pending_until_today(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get pending orders with deadline until today."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedExpireToday"
        )

        return success_response(result, resource="orderspending/untiltoday", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching pending orders until today")


@router.get("/orderspending/delayed", tags=["Orders Pending"])
async def get_orders_pending_delayed(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get delayed pending orders."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedDelayed"
        )

        return success_response(result, resource="orderspending/delayed", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching delayed pending orders")


@router.patch("/orderspending", tags=["Orders Pending"])
async def update_order_flag_stock(
    data: UpdateStockFlag,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update stock flag for an order."""
    try:
        logger.info(f"Updating stock flag for order {data.idOrder}")

        rows_affected = OrderService.update_order_flag(
            db,
            "ordersdetail",
            "pendingWithoutStock",
            data.withoutstock,
            data.idOrder
        )

        return updated_response(rows_affected)

    except Exception as e:
        return handle_database_error(e, f"updating stock flag for {data.idOrder}")


# ============================================================================
# ORDERS OUT OF STOCK ENDPOINTS
# ============================================================================

@router.get("/ordersoutofstock", tags=["Out of Stock"])
@router.get("/ordersoutofstock/", tags=["Out of Stock"])
async def get_orders_out_of_stock(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all orders out of stock."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedWithOutStock"
        )

        return success_response(result, resource="ordersoutofstock", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching out of stock orders")


@router.get("/ordersoutofstock/untiltoday", tags=["Out of Stock"])
async def get_orders_out_of_stock_until_today(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get out of stock orders with deadline until today."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedWithOutStockExpireToday"
        )

        return success_response(result, resource="ordersoutofstock/untiltoday", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching out of stock orders until today")


@router.get("/ordersoutofstock/delayed", tags=["Out of Stock"])
async def get_orders_out_of_stock_delayed(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get delayed out of stock orders."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedWithOutStockDelayed"
        )

        return success_response(result, resource="ordersoutofstock/delayed", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching delayed out of stock orders")


@router.patch("/ordersoutofstock", tags=["Out of Stock"])
async def update_order_flag_fake(
    data: UpdateFakeFlag,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update fake flag for an order."""
    try:
        logger.info(f"Updating fake flag for order {data.idOrder}")

        rows_affected = OrderService.update_order_flag(
            db,
            "ordersdetail",
            "isShipFake",
            data.isFake,
            data.idOrder
        )

        return updated_response(rows_affected)

    except Exception as e:
        return handle_database_error(e, f"updating fake flag for {data.idOrder}")


# ============================================================================
# SHIPMENTS ENDPOINTS
# ============================================================================

@router.get("/ordersshipfake", tags=["Shipments"])
async def get_orders_ship_fake(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get orders marked for fake shipment."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersDetailUnshippedFake"
        )

        return success_response(result, resource="ordersshipfake", count=len(result))

    except Exception as e:
        return handle_database_error(e, "fetching fake shipment orders")


@router.get("/ordersreadytoship", tags=["Shipments"])
async def get_orders_ready_to_ship(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get orders selected for shipment."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getOrdersSelectedShipment",
            group_items=False
        )

        return success_response(result)

    except Exception as e:
        return handle_database_error(e, "fetching ready to ship orders")


@router.get("/ordershistory", tags=["History"])
@router.get("/ordershistory/", tags=["History"])
async def get_orders_history(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get shipments history."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getHistoryShipment",
            group_items=False
        )

        return success_response(result)

    except Exception as e:
        return handle_database_error(e, "fetching shipments history")


@router.get("/ordershistory/{filename}", tags=["History"])
async def get_shipments_by_filename(
    filename: str = Path(..., description="File name to search"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get shipments generated by filename."""
    try:
        result = OrderService.get_orders_by_procedure(
            db,
            "uSp_getShipmentsGeneratedByFileName",
            {"filename": filename},
            group_items=False
        )

        return success_response([result] if result else [])

    except Exception as e:
        return handle_database_error(e, f"fetching shipments for file {filename}")


@router.post("/ordersreadytoship", tags=["Shipments"], status_code=201)
async def create_order_ready_to_ship(
    data: ShipmentData,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add order to shipment queue.

    **Migrated from PHP**: `POST /ordersreadytoship`
    """
    try:
        logger.info(f"Creating shipment for order {data.idOrder}")

        # Validate order
        if not check_order_exists(db, data.idOrder):
            return created_response(0, "El pedido no existe")

        if not check_order_not_shipped(db, data.idOrder):
            return created_response(0, "El pedido ya fue enviado")

        # Update shipment flag
        sp_name = "uSp_updateMarkShipment" if data.shipmentType == "usingFile" else "uSp_updateSelectedShipment"

        db.execute(
            text(f"CALL toolstock_amz.{sp_name}(:value, :idOrder)"),
            {"value": data.value, "idOrder": data.idOrder}
        )
        db.commit()

        # Insert shipment data
        insert_query = """
            CALL toolstock_amz.uSp_insertSelectedshipment(
                :servicio, :horario, :destinatario, :direccion,
                :pais, :cp, :poblacion, :telefono, :email,
                :departamento, :contacto, :observaciones,
                :bultos, :movil, :refC, :idOrder, :process
            )
        """

        result = db.execute(text(insert_query), {
            "servicio": data.servicio,
            "horario": data.horario,
            "destinatario": data.destinatario,
            "direccion": data.direccion,
            "pais": data.pais,
            "cp": data.cp,
            "poblacion": data.poblacion,
            "telefono": data.telefono,
            "email": data.email,
            "departamento": data.departamento,
            "contacto": data.contacto,
            "observaciones": data.observaciones,
            "bultos": data.bultos,
            "movil": data.movil,
            "refC": data.refC,
            "idOrder": data.idOrder,
            "process": data.process
        })

        db.commit()
        rows_affected = result.rowcount

        logger.info(f"Shipment created for order {data.idOrder}")
        return created_response(rows_affected)

    except Exception as e:
        db.rollback()
        return handle_database_error(e, f"creating shipment for {data.idOrder}")


@router.patch("/ordersreadytoship", tags=["Shipments"])
async def update_order_ready_to_ship(
    data: UpdateShipment,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update shipment data for an order.

    **Valid columnName values:**
    - servicio, horario, destinatario, direccion, pais, cp, poblacion
    - telefono, email, departamento, contacto, observaciones, bultos, movil, refC
    """
    try:
        logger.info(f"Updating shipment for order {data.idOrder}, field: {data.columnName}")

        # Dynamic update query - columnName is validated by Pydantic schema
        query = f"""
            UPDATE toolstock_amz.selectedShipment
            SET {data.columnName} = :columnValue
            WHERE idOrder = :idOrder AND fileGenerateName IS NULL
        """

        result = db.execute(text(query), {
            "columnValue": data.columnValue,
            "idOrder": data.idOrder
        })
        db.commit()

        rows_affected = result.rowcount
        logger.info(f"Shipment updated for order {data.idOrder}")

        return updated_response(rows_affected)

    except Exception as e:
        db.rollback()
        return handle_database_error(e, f"updating shipment for {data.idOrder}")


@router.delete("/ordersreadytoship", tags=["Shipments"])
async def delete_order_ready_to_ship(
    data: DeleteShipment,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove order from shipment queue."""
    try:
        logger.info(f"Deleting shipment for order {data.idOrder}")

        # Validate order exists
        if not check_order_exists(db, data.idOrder):
            return deleted_response(0, "El pedido no existe")

        # Delete from selectedshipment
        delete_query = """
            DELETE FROM toolstock_amz.selectedshipment
            WHERE idOrder = :idOrder
        """

        result = db.execute(text(delete_query), {"idOrder": data.idOrder})
        db.commit()

        rows_deleted = result.rowcount

        if rows_deleted > 0:
            # Update flag based on shipment type
            sp_name = "uSp_updateMarkShipment" if data.shipmentType == "usingFile" else "uSp_updateSelectedShipment"

            db.execute(
                text(f"CALL toolstock_amz.{sp_name}(:value, :idOrder)"),
                {"value": data.value or 0, "idOrder": data.idOrder}
            )
            db.commit()

            logger.info(f"Shipment deleted for order {data.idOrder}")

        return deleted_response(rows_deleted)

    except Exception as e:
        db.rollback()
        return handle_database_error(e, f"deleting shipment for {data.idOrder}")


@router.patch("/registershipment", tags=["Shipments"])
async def register_shipment(
    data: RegisterShipment,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Register shipment - Generate file or send to GLS Web Service.

    **Most complex endpoint - handles:**
    - File generation for bulk shipments
    - Individual shipment via GLS SOAP Web Service
    """
    try:
        logger.info(f"Registering shipment: {data.shipmentType}")

        # === FILE GENERATION ===
        if data.shipmentType == "usingFile":
            return await _register_shipment_file(db)

        # === WEB SERVICE ===
        else:
            return await _register_shipment_ws(db, data.idOrder)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return handle_database_error(e, "registering shipment")


async def _register_shipment_file(db: Session):
    """Handle file generation for bulk shipments."""
    rows = OrderService.get_orders_by_procedure(
        db,
        "uSp_getOrdersForShipmentFile",
        group_items=False
    )

    if not rows:
        return empty_response()

    # Generate file name
    from datetime import datetime
    file_name = f"Envios_{datetime.now().strftime('%d%m%Y_%H%M%S')}.xlsx"

    # Add filename to each record
    for record in rows:
        record["fileGenerateName"] = file_name

    # Update database with file name
    db.execute(
        text("CALL toolstock_amz.uSp_updateShipmentFile(:fileGenerateName)"),
        {"fileGenerateName": file_name}
    )
    db.commit()

    # Update orders detail
    db.execute(text("CALL toolstock_amz.uSp_updateOrdersDetailFile()"))
    db.commit()

    logger.info(f"File shipment registered: {file_name}")

    return success_response(rows)


async def _register_shipment_ws(db: Session, order_id: str):
    """Handle individual shipment via GLS Web Service."""
    if not order_id:
        raise HTTPException(
            status_code=400,
            detail="idOrder es requerido para shipmentType=usingWS"
        )

    # Validate order not shipped
    if not check_order_not_shipped(db, order_id):
        return success_response([], content=0, message="El pedido ya fue enviado")

    # Get shipment data
    shipment_data = db.execute(
        text("CALL toolstock_amz.uSp_getOrdersForShipmentWS(:idOrder)"),
        {"idOrder": order_id}
    ).fetchone()

    if not shipment_data:
        return empty_response()

    # Convert to dict
    envio = dict(shipment_data)

    # Call GLS Web Service
    gls_service = GLSService()
    gls_response = await gls_service.request_shipment_ws(envio)

    # If successful, update database
    if gls_response.get("codResponseWS") == "0":
        # Update orders detail
        db.execute(
            text("""CALL toolstock_amz.uSp_updateOrdersDetailWS(
                :idOrder, :uIdExp, :expeditionTraking, :codBar
            )"""),
            {
                "idOrder": gls_response["idOrder"],
                "uIdExp": gls_response.get("uidExp", ""),
                "expeditionTraking": gls_response.get("exp", ""),
                "codBar": gls_response.get("codBar", "")
            }
        )
        db.commit()

        # Update shipment status
        db.execute(
            text("CALL toolstock_amz.uSp_updateShipmentWS(:idOrder)"),
            {"idOrder": order_id}
        )
        db.commit()

        # Update orders table
        db.execute(
            text("CALL toolstock_amz.uSp_updateOrdersWS(:idOrder, :exp)"),
            {"idOrder": order_id, "exp": gls_response.get("exp", "")}
        )
        db.commit()

        logger.info(f"WS shipment registered for order {order_id}")

    return success_response(gls_response)


logger.info("All routes loaded successfully (REFACTORED)")
