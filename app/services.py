"""
Business logic and services layer - REFACTORED
"""
from sqlalchemy.orm import Session
import logging
from typing import List, Dict, Any, Optional
import httpx
from datetime import datetime
import os
from app.utils import (
    execute_stored_procedure,
    execute_update,
    group_orders_with_items
)

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order-related operations - REFACTORED"""

    @staticmethod
    def get_orders_by_procedure(
        db: Session,
        procedure_name: str,
        params: Optional[Dict] = None,
        group_items: bool = True
    ) -> List[Dict]:
        """
        Generic method to get orders from any stored procedure

        Args:
            db: Database session
            procedure_name: Name of stored procedure
            params: Optional parameters
            group_items: Whether to group orders with items

        Returns:
            List of orders (grouped or raw)
        """
        rows = execute_stored_procedure(db, procedure_name, params)

        if group_items and rows:
            return group_orders_with_items(rows)

        return [dict(row) if hasattr(row, '_mapping') else row for row in rows]

    @staticmethod
    def update_order_flag(
        db: Session,
        table: str,
        column: str,
        value: Any,
        order_id: str
    ) -> int:
        """
        Generic method to update order flags

        Args:
            db: Database session
            table: Table name
            column: Column to update
            value: New value
            order_id: Order ID

        Returns:
            Number of affected rows
        """
        query = f"""
            UPDATE toolstock_amz.{table}
            SET {column} = :value
            WHERE orderId = :idOrder
        """

        return execute_update(db, query, {"value": value, "idOrder": order_id})


class GLSService:
    """Service for GLS (shipping) integration - REFACTORED"""

    def __init__(self):
        # Load GLS configuration from environment
        self.config = {
            "uid_cliente": os.getenv("GLS_UID"),
            "url_save_ship": os.getenv("GLS_SAVE_SHIP_URL"),
            "portes": os.getenv("GLS_PORTES"),
            "reembolso": os.getenv("GLS_REEMBOLSO"),
            "nombre_org": os.getenv("GLS_NOMBRE_ORG"),
            "direccion_org": os.getenv("GLS_DIRECCION_ORG"),
            "poblacion_org": os.getenv("GLS_POBLACION_ORG"),
            "pais_org": os.getenv("GLS_PAIS_ORG"),
            "cp_org": os.getenv("GLS_CP_ORG")
        }

    def generate_soap_xml(self, envio: Dict) -> str:
        """
        Generate SOAP XML for GLS request

        Args:
            envio: Shipment data

        Returns:
            XML string
        """
        fecha = datetime.now().strftime("%d/%m/%Y")

        # Build XML using template
        xml_template = '''<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
<soap12:Body>
<GrabaServicios xmlns="http://www.asmred.com/">
<docIn>
   <Servicios uidcliente="{uid_cliente}" xmlns="http://www.asmred.com/">
   <Envio>
      <Fecha>{fecha}</Fecha>
      <Servicio>{servicio}</Servicio>
      <Horario>{horario}</Horario>
      <Bultos>{bultos}</Bultos>
      <Peso>{peso}</Peso>
      <Portes>{portes}</Portes>
      <Importes>
         <Reembolso>{reembolso}</Reembolso>
      </Importes>
      <Remite>
         <Nombre>{nombre_org}</Nombre>
         <Direccion>{direccion_org}</Direccion>
         <Poblacion>{poblacion_org}</Poblacion>
         <Pais>{pais_org}</Pais>
         <CP>{cp_org}</CP>
      </Remite>
      <Destinatario>
         <Nombre>{destinatario}</Nombre>
         <Direccion>{direccion}</Direccion>
         <Poblacion>{poblacion}</Poblacion>
         <Pais>{pais}</Pais>
         <CP>{cp}</CP>
         <Telefono>{telefono}</Telefono>
         <Movil>{movil}</Movil>
         <Email>{email}</Email>
         <Departamento>{departamento}</Departamento>
         <Observaciones>{observaciones}</Observaciones>
      </Destinatario>
      <Referencias>
         <Referencia tipo="C">{refC}</Referencia>
      </Referencias>
      <DevuelveAdicionales>
         <Etiqueta tipo="PDF"/>
      </DevuelveAdicionales>
   </Envio>
   </Servicios>
   </docIn>
</GrabaServicios>
</soap12:Body>
</soap12:Envelope>'''

        # Merge config and envio data
        data = {**self.config, **envio, "fecha": fecha}

        return xml_template.format(**data)

    async def request_shipment_ws(self, envio: Dict) -> Dict:
        """
        Send shipment request to GLS Web Service

        Args:
            envio: Shipment data

        Returns:
            Response dictionary with shipment result
        """
        try:
            # Generate XML
            xml = self.generate_soap_xml(envio)

            # Make SOAP request
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                response = await client.post(
                    self.config["url_save_ship"],
                    content=xml,
                    headers={'Content-Type': 'text/xml; charset=UTF-8'}
                )

            logger.info(f"GLS WS Response status: {response.status_code}")

            # Parse XML response
            return self._parse_gls_response(response.text, envio.get("idOrder", ""))

        except Exception as e:
            logger.error(f"Error in GLS WS request: {str(e)}")
            return self._build_error_response(str(e), envio.get("idOrder", ""))

    def _parse_gls_response(self, xml_response: str, order_id: str) -> Dict:
        """
        Parse GLS XML response

        Args:
            xml_response: XML response string
            order_id: Order ID

        Returns:
            Parsed response dict
        """
        try:
            import xml.etree.ElementTree as ET

            # Parse XML
            root = ET.fromstring(xml_response)

            # Define namespaces
            namespaces = {
                'soap': 'http://www.w3.org/2003/05/soap-envelope',
                'asm': 'http://www.asmred.com/'
            }

            # Extract result node
            result_node = root.find('.//asm:GrabaServiciosResult', namespaces)
            if result_node is None:
                return self._build_error_response("Respuesta XML inválida", order_id)

            envio_node = result_node.find('.//Envio')
            if envio_node is None:
                return self._build_error_response("Nodo Envio no encontrado", order_id)

            resultado_node = envio_node.find('.//Resultado')
            if resultado_node is None:
                return self._build_error_response("Nodo Resultado no encontrado", order_id)

            return_code = resultado_node.get('return', '-1')

            if return_code == "0":
                # Success - extract data
                cod_bar = envio_node.get('codbarras', '')
                uid = envio_node.get('uid', '')
                exp = envio_node.get('codexp', '')

                # Extract references
                referencias = envio_node.findall('.//Referencias/Referencia')
                refs = [
                    {
                        "type": ref.get('tipo', ''),
                        "value": ref.text or ''
                    }
                    for ref in referencias
                ]

                # Extract label
                etiqueta_node = envio_node.find('.//Etiquetas/Etiqueta')
                etiqueta = etiqueta_node.text if etiqueta_node is not None else ''

                return {
                    "codResponseWS": return_code,
                    "responseWS": "",
                    "messageWS": "Envio insertado Ok",
                    "idOrder": order_id,
                    "uidExp": uid,
                    "codBar": cod_bar,
                    "exp": exp,
                    "refs": refs,
                    "LabelBase64": etiqueta
                }
            else:
                # Error - extract error message
                error_node = envio_node.find('.//Errores/Error')
                error_msg = error_node.text if error_node is not None else "Error desconocido"

                return {
                    "codResponseWS": return_code,
                    "responseWS": error_msg,
                    "messageWS": self.get_error_message(return_code) or error_msg,
                    "idOrder": order_id
                }

        except Exception as e:
            logger.error(f"Error parsing GLS response: {str(e)}")
            return self._build_error_response(f"Error parseando respuesta: {str(e)}", order_id)

    def _build_error_response(self, error: str, order_id: str) -> Dict:
        """Build error response"""
        return {
            "codResponseWS": "-1",
            "responseWS": error,
            "messageWS": "Error en solicitud GLS",
            "idOrder": order_id
        }

    @staticmethod
    def get_error_message(error_code: str) -> str:
        """
        Get human-readable error message for GLS error code

        Args:
            error_code: GLS error code

        Returns:
            Error message
        """
        errors = {
            "+38": "Error, Número de teléfono del destinatario no válido.",
            "36": "Error, Código postal del destinatario, formato incorrecto.",
            "-1": "Tiempo de espera expirado.",
            "-3": "Error, El código de barras del envío ya existe.",
            "-33": "Cp destino no existe o no es de esa plaza",
            "-48": "Error, servicio EuroEstandar/EBP: El número de paquetes debe ser siempre 1.",
            "-49": "Error, servicio EuroEstandar/EBP: El peso debe ser <= 31,5 kgs.",
            "-70": "Error, El número de pedido ya existe",
            "-99": "Advertencia, los servicios web están temporalmente fuera de servicio.",
            "-128": "Error, Nombre del destinatario debe tener al menos tres caracteres.",
            "-129": "Error, la dirección del destinatario debe tener al menos tres caracteres.",
            "-130": "Error, La Ciudad del Destinatario debe tener al menos tres caracteres.",
            "-131": "Error, Consignee Zipcode debe tener al menos cuatro caracteres.",
        }

        return errors.get(error_code, "")
