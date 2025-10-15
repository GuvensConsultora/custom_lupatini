# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Cantidad de líneas para albaranes OUT (entregas) - guardado en ir.config_parameter
    preprint_lines_out = fields.Integer(
        string="Líneas por albarán de entregas",
        config_parameter="stock_preprinted_delivery.preprint_lines_out",  # clave del parámetro
        default=25,  # valor por defecto razonable
        help="Cantidad de renglones impresos en remitos/albaranes OUT (entregas).",
    )

    # Cantidad de líneas para albaranes INT (mov. internos) - guardado en ir.config_parameter
    preprint_lines_int = fields.Integer(
        string="Líneas por albarán internos",
        config_parameter="stock_preprinted_delivery.preprint_lines_int",
        default=25,
        help="Cantidad de renglones impresos en remitos/albaranes INT (movimientos internos).",
    )


class AlbaranPrintHelloWizard(models.TransientModel):
    _name = "albaran.print.hello.wizard"
    _description = "Wizard de impresión - Hola"

    message = fields.Char(
        string="Mensaje",
        default="Hola mundo",
        readonly=True
    )

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_print_intercept(self):
        self.ensure_one()
        if self.picking_type_code not in ("outgoing", "internal"):
            raise UserError("Solo disponible para albaranes OUT o INT.")

        # Acción completa: res_model + views + view_id + target=new
        view = self.env.ref("stock_preprinted_delivery_settings.view_albaran_print_hello_wizard")
        return {
            "type": "ir.actions.act_window",
            "name": "Imprimir",
            "res_model": "albaran.print.hello.wizard",
            "view_mode": "form",
            "view_id": view.id,
            "views": [(view.id, "form")],
            "target": "new",
            "context": {"default_message": "Hola munod"},
        }

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    print_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Secuencia de impresión",
        help="Secuencia usada para numeración/folio del impreso",
        domain="[('company_id','=',False),'|',('company_id','=',False),('company_id','=', company_id)]",
    )
    
