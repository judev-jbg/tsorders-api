"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


# Base Response Schema
class APIResponse(BaseModel):
    """Standard API response format"""
    header: Dict[str, Any]
    payload: Optional[List[Dict[str, Any]]] = []
    message: Optional[str] = None


# Order Item Schema
class OrderItem(BaseModel):
    """Individual product item in an order"""
    orderItemId: str
    sku: str
    productName: str
    quantityPurchased: int
    itemPrice: float
    itemTax: float
    shippingPrice: float
    shippingTax: float
    vatExclusiveItemPrice: Optional[float] = None
    vatExclusiveShippingPrice: Optional[float] = None
    asin: Optional[str] = None
    referenciaProv: Optional[str] = None


# Order Schema
class Order(BaseModel):
    """Complete order with items"""
    amazonOrderId: str
    purchaseDate: str
    lastUpdateDate: str
    orderStatus: str
    fulfillmentChannel: str
    salesChannel: str
    shipServiceLevel: str
    shippingAddressName: str
    shippingAddressAddressLine1: str
    shippingAddressCity: str
    shippingAddressStateOrRegion: Optional[str] = None
    shippingAddressPostalCode: str
    shippingAddressCountryCode: str
    numberOfItemsShipped: int
    numberOfItemsUnshipped: int
    paymentMethod: str
    marketplace: str
    shipmentServiceLevelCategory: str
    orderTotal: float
    isPremiumOrder: bool
    isPrime: bool
    isBusinessOrder: bool
    latestShipDate: str
    latestDeliveryDate: str
    items: List[OrderItem] = []


# Update Stock Flag Schema
class UpdateStockFlag(BaseModel):
    """Schema for updating stock flag"""
    withoutstock: int = Field(..., ge=0, le=1, description="0 or 1")
    idOrder: str = Field(..., min_length=1)


# Update Fake Flag Schema
class UpdateFakeFlag(BaseModel):
    """Schema for updating fake flag"""
    isFake: int = Field(..., ge=0, le=1, description="0 or 1")
    idOrder: str = Field(..., min_length=1)


# Shipment Data Schema
class ShipmentData(BaseModel):
    """Complete shipment data"""
    servicio: Union[str, int] = Field(...)
    horario: Union[str, int] = Field(...)
    destinatario: str = Field(..., min_length=3)
    direccion: str = Field(..., min_length=3)
    pais: Union[str, int] = Field(...)
    cp: str = Field(..., min_length=4)
    poblacion: str = Field(..., min_length=3)
    telefono: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    departamento: str = Field(default="")
    contacto: str = Field(default="")
    observaciones: str = Field(default="")
    bultos: int = Field(..., ge=1)
    movil: str = Field(default="")
    refC: str = Field(default="")
    idOrder: str = Field(..., min_length=1)
    process: str = Field(..., min_length=1)
    shipmentType: str = Field(..., pattern="^(usingFile|usingWS)$")
    value: Optional[int] = Field(default=1)

    @validator('servicio', 'horario', 'pais', pre=True)
    def convert_to_string(cls, v):
        """Convert numeric values to string"""
        return str(v)

    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if '@' not in v:
            raise ValueError('Email must contain @')
        return v


# Update Shipment Schema
class UpdateShipment(BaseModel):
    """Schema for updating shipment data"""
    columnName: str = Field(
        ...,
        pattern="^(servicio|horario|destinatario|direccion|pais|cp|poblacion|telefono|email|departamento|contacto|observaciones|bultos|movil|refC)$"
    )
    columnValue: str = Field(..., min_length=1)
    idOrder: str = Field(..., min_length=1)


# Delete Shipment Schema
class DeleteShipment(BaseModel):
    """Schema for deleting shipment"""
    idOrder: str = Field(..., min_length=1)
    shipmentType: str = Field(..., pattern="^(usingFile|usingWS)$")
    value: Optional[int] = Field(default=0)


# Register Shipment Schema
class RegisterShipment(BaseModel):
    """Schema for registering shipment"""
    shipmentType: str = Field(..., pattern="^(usingFile|usingWS)$")
    idOrder: Optional[str] = None

    @validator('idOrder')
    def validate_id_order_for_ws(cls, v, values):
        """Validate that idOrder is required for usingWS"""
        if values.get('shipmentType') == 'usingWS' and not v:
            raise ValueError('idOrder is required for shipmentType=usingWS')
        return v


# GLS Shipment Data (for WS integration)
class GLSShipmentData(BaseModel):
    """Data structure for GLS Web Service shipment"""
    idOrder: str
    servicio: str
    horario: str
    bultos: int
    peso: float
    destinatario: str
    direccion: str
    poblacion: str
    pais: str
    cp: str
    telefono: str
    movil: str
    email: str
    departamento: str
    observaciones: str
    refC: str
